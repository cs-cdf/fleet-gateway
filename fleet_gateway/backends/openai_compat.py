"""
fleet_gateway.backends.openai_compat — OpenAI-compatible backend.

Works with: local llama.cpp, vLLM, Ollama, LM Studio, Groq, Cerebras,
SambaNova, Mistral, NVIDIA NIM, OpenRouter, OpenAI, Gemini (OpenAI compat),
and any other server that speaks /v1/chat/completions.

Zero external dependencies (stdlib only).
"""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .base import BaseBackend

# Optional: model deprecation detection (fleet_model_checker in llm_tools/)
try:
    _llm_tools = Path(__file__).resolve().parents[4] / "_SHARED" / "llm_tools"
    if str(_llm_tools) not in sys.path:
        sys.path.insert(0, str(_llm_tools))
    from fleet_model_checker import is_deprecation_error as _is_dep_error  # type: ignore
    from fleet_model_checker import run_check as _run_model_check  # type: ignore
    _DEPRECATION_CHECK_ENABLED = True
except Exception:
    _DEPRECATION_CHECK_ENABLED = False
    def _is_dep_error(code, body): return False  # type: ignore
    def _run_model_check(**kw): return []  # type: ignore

_last_dep_check: Dict[str, float] = {}
_DEP_CHECK_INTERVAL = 3600.0


def _trigger_dep_check(provider: str) -> None:
    """Debounced: schedule background model check at most once per hour per provider."""
    now = time.time()
    if now - _last_dep_check.get(provider, 0) < _DEP_CHECK_INTERVAL:
        return
    _last_dep_check[provider] = now
    threading.Thread(target=_deprecation_bg, args=(provider,), daemon=True).start()


def _deprecation_bg(provider: str) -> None:
    """Background thread: run model check and log results."""
    try:
        results = _run_model_check(providers=[provider], notify=True)
        for r in results:
            for iss in r.issues:
                if iss.issue_type == "not_found":
                    _log(f"[model_checker] {r.provider}/{iss.model_id} deprecated. Suggest: {iss.suggested or 'unknown'}")
    except Exception as exc:
        pass  # best-effort


class OpenAICompatBackend(BaseBackend):
    """Backend for any OpenAI-compatible endpoint."""

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self._base_url = cfg.get("url", "http://localhost:8080/v1").rstrip("/")
        self._api_key = cfg.get("api_key") or cfg.get("api_key_literal") or "dummy"

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

    def call(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
        timeout: float = 120.0,
        stream: bool = False,
        **kwargs,
    ) -> Optional[str]:
        actual_id = self.model_id_for(model_id)
        body: Dict[str, Any] = {
            "model": actual_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }
        if stream:
            body["stream"] = True

        url = f"{self._base_url}/v1/chat/completions"
        # Some backends already include /v1 in their base_url
        if "/v1" in self._base_url:
            url = f"{self._base_url}/chat/completions"

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers=self._headers(),
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if stream:
                    return self._collect_stream(resp)
                data = json.loads(resp.read(20_000_000).decode("utf-8"))
            return _extract_content(data)
        except urllib.error.HTTPError as e:
            # Log to stderr but don't raise — caller tries next backend
            _log(f"[{self.name}] HTTP {e.code} for model {actual_id}: {e.reason}")
            if _DEPRECATION_CHECK_ENABLED:
                body = ""
                try:
                    body = e.read(2048).decode("utf-8", errors="replace")
                except Exception:
                    pass
                if _is_dep_error(e.code, body):
                    _trigger_dep_check(self._provider_name())
            return None
        except urllib.error.URLError as e:
            _log(f"[{self.name}] Connection error for model {actual_id}: {e.reason}")
            return None
        except Exception as e:
            _log(f"[{self.name}] Unexpected error for model {actual_id}: {e}")
            return None

    def _collect_stream(self, resp) -> Optional[str]:
        """Collect an SSE stream into a single string."""
        parts = []
        for raw_line in resp:
            line = raw_line.decode("utf-8").strip()
            if not line or line == "data: [DONE]":
                continue
            if line.startswith("data: "):
                try:
                    chunk = json.loads(line[6:])
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    if delta.get("content"):
                        parts.append(delta["content"])
                except Exception:
                    pass
        return "".join(parts) or None

    def _provider_name(self) -> str:
        """Infer provider name from base_url for deprecation check routing."""
        url = self._base_url.lower()
        for p in ("gemini", "openai", "anthropic", "groq", "mistral", "cerebras", "openrouter"):
            if p in url:
                return p
        return "unknown"

    def list_models(self, timeout: float = 5.0) -> List[str]:
        """Query /v1/models and return list of model IDs."""
        url = f"{self._base_url}/v1/models"
        if "/v1" in self._base_url:
            url = f"{self._base_url}/models"
        try:
            req = urllib.request.Request(url, headers=self._headers())
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return [m.get("id", "") for m in data.get("data", [])]
        except Exception:
            return []

    def health(self, timeout: float = 3.0) -> bool:
        """Check backend health via /health or /v1/models."""
        base = self._base_url
        if "/v1" in base:
            base = base.rsplit("/v1", 1)[0]
        for path in ["/health", "/v1/models"]:
            try:
                req = urllib.request.Request(f"{base}{path}", headers=self._headers())
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.status < 400
            except Exception:
                pass
        return False


def _extract_content(data: dict) -> Optional[str]:
    """Extract the final answer from a /v1/chat/completions response.

    Priority (in order):
    1. ``content`` — standard field; always the clean answer when non-empty.
    2. ``reasoning`` — vLLM reasoning-parser (``--reasoning-parser qwen3``) puts
       the extracted clean answer here when ``content`` is null/empty.
    3. ``reasoning_content`` — Cogito/Apriel put the full answer here;
       deepseek models also use it for raw thinking (content empty = hit
       max_tokens mid-think).  Best-effort: strip think tags.

    Think tags are stripped defensively at every level.
    """
    if not isinstance(data, dict):
        return None
    choices = data.get("choices")
    if not choices:
        return None
    msg = choices[0].get("message", {})

    content = msg.get("content") or ""
    # vLLM reasoning-parser separates thinking into 'reasoning'; content has the answer
    reasoning = msg.get("reasoning") or ""
    # Cogito/Apriel/deepseek: full answer (or raw thinking) in reasoning_content
    reasoning_content = msg.get("reasoning_content") or ""

    if content.strip():
        return _strip_think_tags(content) or None

    # vLLM: reasoning field is the clean extracted answer (not raw thinking)
    if reasoning.strip():
        return _strip_think_tags(reasoning) or None

    # Cogito/Apriel pattern: reasoning_content holds the full answer
    # (deepseek models: may be raw thinking if model hit max_tokens mid-think)
    if reasoning_content.strip():
        return _strip_think_tags(reasoning_content) or None

    return None


def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> CoT blocks from model output.

    Also handles truncated responses where ``<think>`` has no closing tag
    (model hit max_tokens during reasoning) — discards everything from the
    unclosed tag onward so raw thinking never leaks into the answer.
    """
    import re
    # Strip complete <think>...</think> blocks (multiline, non-greedy)
    cleaned = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)
    # Handle unclosed <think> tag (truncated mid-thinking)
    if "<think>" in cleaned:
        cleaned = cleaned[: cleaned.index("<think>")]
    return cleaned.strip()


def _log(msg: str):
    import sys
    print(f"[fleet_gateway] {msg}", file=sys.stderr, flush=True)
