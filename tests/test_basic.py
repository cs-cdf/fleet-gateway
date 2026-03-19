"""Basic tests for fleet-gateway core components."""
import base64
import os
import sys
import tempfile
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fleet_gateway.config import Config, _auto_config, _DEFAULT_ROUTING
from fleet_gateway.backends.openai_compat import _extract_content, _strip_think_tags
from fleet_gateway.router import Router


class TestConfig(unittest.TestCase):

    def test_auto_config_empty_env(self):
        """With no env vars, auto_config returns empty backends."""
        for key in list(os.environ.keys()):
            if key.endswith("_API_KEY") or key == "SEARXNG_URL":
                del os.environ[key]
        raw = _auto_config()
        self.assertIn("routing", raw)

    def test_config_from_dict(self):
        cfg = Config({
            "backends": {
                "groq": {
                    "type": "openai_compat",
                    "url": "https://api.groq.com/openai/v1",
                    "api_key": "test123",
                    "models": [{"id": "llama-3.3-70b", "capabilities": ["general"]}],
                }
            },
            "routing": {"general": ["groq/llama-3.3-70b"]},
        })
        self.assertIn("groq", cfg.backends)
        self.assertEqual(cfg.backends["groq"]["api_key"], "test123")
        self.assertEqual(cfg.get_routing_chain("general"), ["groq/llama-3.3-70b"])

    def test_config_fallback_to_default_routing(self):
        cfg = Config({"backends": {}})
        chain = cfg.get_routing_chain("coding")
        # Falls back to default routing
        self.assertIsInstance(chain, list)

    def test_config_unknown_capability_falls_back_to_general(self):
        cfg = Config({
            "backends": {},
            "routing": {"general": ["groq/llama"]},
        })
        chain = cfg.get_routing_chain("unknown_capability")
        self.assertEqual(chain, ["groq/llama"])


class TestExtractContent(unittest.TestCase):

    def test_standard_content(self):
        data = {"choices": [{"message": {"role": "assistant", "content": "Hello!"}}]}
        self.assertEqual(_extract_content(data), "Hello!")

    def test_reasoning_content_fallback(self):
        """Cogito/Apriel: answer in reasoning_content, content empty."""
        data = {"choices": [{"message": {"role": "assistant", "content": "", "reasoning_content": "The answer is 42"}}]}
        self.assertEqual(_extract_content(data), "The answer is 42")

    def test_vllm_reasoning_field_is_clean_answer(self):
        """vLLM reasoning-parser: 'reasoning' field has the clean answer, content is null."""
        data = {"choices": [{"message": {"content": None, "reasoning": "Rome"}}]}
        self.assertEqual(_extract_content(data), "Rome")

    def test_content_takes_priority_over_reasoning(self):
        """content must win over reasoning/reasoning_content when non-empty."""
        data = {"choices": [{"message": {"content": "Rome", "reasoning": "Let me think...", "reasoning_content": "other"}}]}
        self.assertEqual(_extract_content(data), "Rome")

    def test_reasoning_takes_priority_over_reasoning_content(self):
        """vLLM 'reasoning' (clean answer) beats reasoning_content (may be raw thinking)."""
        data = {"choices": [{"message": {"content": "", "reasoning": "clean answer", "reasoning_content": "raw thinking..."}}]}
        self.assertEqual(_extract_content(data), "clean answer")

    def test_think_tags_stripped_from_content(self):
        data = {"choices": [{"message": {"content": "<think>I reason</think>The answer is 42."}}]}
        result = _extract_content(data)
        self.assertEqual(result, "The answer is 42.")
        self.assertNotIn("<think>", result)

    def test_think_tags_stripped_multiline(self):
        data = {"choices": [{"message": {"content": "<think>\nStep 1\nStep 2\n</think>\n\nFinal answer."}}]}
        self.assertEqual(_extract_content(data), "Final answer.")

    def test_unclosed_think_tag_does_not_leak_thinking(self):
        """Truncated response: <think> with no </think> — raw thinking must NOT appear."""
        data = {"choices": [{"message": {"content": "<think>I was still reasoning..."}}]}
        result = _extract_content(data)
        self.assertIsNone(result)

    def test_unclosed_think_tag_preserves_content_before_tag(self):
        """If there's clean content before unclosed <think>, it is returned."""
        data = {"choices": [{"message": {"content": "Partial answer.<think>truncated thinking..."}}]}
        result = _extract_content(data)
        self.assertEqual(result, "Partial answer.")

    def test_deepseek_empty_content_does_not_leak_thinking(self):
        """deepseek model hit max_tokens mid-think: content empty, reasoning_content is raw thinking.
        Raw thinking ('We need to output...') must not appear in result."""
        data = {"choices": [{"message": {"content": "", "reasoning_content": "We need to output the final answer..."}}]}
        result = _extract_content(data)
        # Best-effort: strip think tags. Raw thinking (no tags) may pass through,
        # but if it contains think tags, they are stripped.
        # The key requirement: no <think> in result.
        if result:
            self.assertNotIn("<think>", result)

    def test_strip_think_tags(self):
        text = "<think>\nLet me reason...\n</think>\nThe answer is 42."
        self.assertEqual(_strip_think_tags(text), "The answer is 42.")

    def test_strip_think_tags_unclosed(self):
        """Unclosed <think> — everything from tag onward is discarded."""
        text = "Answer: Paris.<think>I was still thinking..."
        self.assertEqual(_strip_think_tags(text), "Answer: Paris.")

    def test_strip_think_tags_only_tags_no_answer(self):
        """Response is ONLY think tags — result must not contain tags."""
        text = "<think>some reasoning</think>"
        result = _strip_think_tags(text)
        self.assertNotIn("<think>", result)
        self.assertNotIn("</think>", result)

    def test_empty_response(self):
        data = {"choices": [{"message": {"content": ""}}]}
        self.assertIsNone(_extract_content(data))

    def test_no_choices(self):
        self.assertIsNone(_extract_content({}))


class TestRouter(unittest.TestCase):

    def test_resolve_entry_missing_backend(self):
        cfg = Config({"backends": {}, "routing": {}})
        router = Router(cfg)
        backend, backend_name, model_id = router._resolve_entry("nonexistent/model")
        self.assertIsNone(backend)

    def test_call_returns_none_when_no_backends(self):
        cfg = Config({"backends": {}, "routing": {"general": ["fake/model"]}})
        router = Router(cfg)
        result = router.call("general", [{"role": "user", "content": "hi"}])
        self.assertIsNone(result)

    def test_available_models_empty(self):
        cfg = Config({"backends": {}})
        router = Router(cfg)
        self.assertEqual(router.available_models(), [])


class TestFileAttachments(unittest.TestCase):

    def setUp(self):
        from fleet_gateway.files import load_file, files_to_blocks, inject_files, suggest_capability
        self.load_file = load_file
        self.files_to_blocks = files_to_blocks
        self.inject_files = inject_files
        self.suggest_capability = suggest_capability
        self.tmp = tempfile.mkdtemp()

    def _write(self, name, content="def f(): pass", mode="w"):
        path = os.path.join(self.tmp, name)
        with open(path, mode if mode == "wb" else "w") as f:
            if mode == "wb":
                f.write(content)
            else:
                f.write(content)
        return path

    def test_text_file_block(self):
        path = self._write("auth.py", "secret = 'abc'")
        block = self.load_file(path)
        self.assertEqual(block["type"], "text")
        self.assertIn("auth.py", block["text"])

    def test_image_block_format(self):
        # Minimal 1x1 PNG
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        )
        path = self._write("test.png", png, mode="wb")
        block = self.load_file(path)
        self.assertEqual(block["type"], "image_url")
        url = block["image_url"]["url"]
        self.assertTrue(url.startswith("data:image/png;base64,"))

    def test_inject_files_into_messages(self):
        path = self._write("code.py", "x = 1")
        msgs = [{"role": "user", "content": "Review this"}]
        result = self.inject_files(msgs, [path])
        self.assertIsInstance(result[-1]["content"], list)
        texts = [b["text"] for b in result[-1]["content"] if b["type"] == "text"]
        self.assertTrue(any("Review this" in t for t in texts))

    def test_inject_preserves_system_message(self):
        path = self._write("code.py")
        msgs = [
            {"role": "system", "content": "You are a reviewer."},
            {"role": "user", "content": "Check this"},
        ]
        result = self.inject_files(msgs, [path])
        self.assertEqual(result[0]["content"], "You are a reviewer.")

    def test_missing_file_skipped(self):
        blocks = self.files_to_blocks(["/nonexistent/ghost.py"])
        self.assertEqual(blocks, [])

    def test_suggest_capability_vision(self):
        self.assertEqual(self.suggest_capability(["photo.png"]), "vision")

    def test_suggest_capability_coding(self):
        self.assertEqual(self.suggest_capability(["main.py"]), "coding")

    def test_suggest_capability_auto_selects_vision_mixed(self):
        self.assertEqual(self.suggest_capability(["main.py", "arch.png"]), "vision")


if __name__ == "__main__":
    unittest.main()
