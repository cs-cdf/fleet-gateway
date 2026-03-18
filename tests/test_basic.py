"""Basic tests for fleet-gateway core components."""
import os
import sys
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
        data = {"choices": [{"message": {"role": "assistant", "content": "", "reasoning_content": "The answer is 42"}}]}
        self.assertEqual(_extract_content(data), "The answer is 42")

    def test_strip_think_tags(self):
        text = "<think>\nLet me reason...\n</think>\nThe answer is 42."
        self.assertEqual(_strip_think_tags(text), "The answer is 42.")

    def test_empty_response(self):
        data = {"choices": [{"message": {"content": ""}}]}
        self.assertIsNone(_extract_content(data))

    def test_no_choices(self):
        self.assertIsNone(_extract_content({}))


class TestRouter(unittest.TestCase):

    def test_resolve_entry_missing_backend(self):
        cfg = Config({"backends": {}, "routing": {}})
        router = Router(cfg)
        backend, model_id = router._resolve_entry("nonexistent/model")
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


if __name__ == "__main__":
    unittest.main()
