"""
fleet_gateway.backends.anthropic — Native Anthropic API backend.

Anthropic uses a different API format (/v1/messages, x-api-key header,
anthropic-version header). This backend handles the translation.

Zero external dependencies (stdlib only).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from .base import BaseBackend

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicBackend(BaseBackend):
    """Backend for the native Anthropic Messages API."""

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self._api_key = cfg.get("api_key") or ""
        self._base_url = cfg.get("base_url", "https://api.anthropic.com/v1")

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
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

        # Anthropic: system messages must be extracted
        system = ""
        user_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system = msg.get("content", "")
            else:
                user_messages.append({"role": msg["role"], "content": _to_anthropic_content(msg.get("content", ""))})

        body: Dict[str, Any] = {
            "model": actual_id,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_messages,
        }
        if system:
            body["system"] = system

        url = f"{self._base_url.rstrip('/')}/messages"

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers=self._headers(),
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read(20_000_000).decode("utf-8"))
            return _extract_anthropic_content(data)
        except urllib.error.HTTPError as e:
            _log(f"[anthropic] HTTP {e.code}: {e.reason}")
            return None
        except urllib.error.URLError as e:
            _log(f"[anthropic] Connection error: {e.reason}")
            return None
        except Exception as e:
            _log(f"[anthropic] Unexpected error: {e}")
            return None


def _to_anthropic_content(content):
    """Convert OpenAI content (str or list) to Anthropic format.

    OpenAI image_url blocks:
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,ABC"}}
    become Anthropic image source blocks:
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "ABC"}}

    Text blocks and plain strings pass through unchanged.
    """
    if isinstance(content, str):
        return content

    if not isinstance(content, list):
        return content

    result = []
    for block in content:
        if not isinstance(block, dict):
            result.append(block)
            continue
        if block.get("type") == "image_url":
            url_val = block.get("image_url", {}).get("url", "")
            if url_val.startswith("data:") and ";base64," in url_val:
                header, b64_data = url_val.split(";base64,", 1)
                media_type = header[len("data:"):]
                result.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64_data},
                })
            else:
                result.append({
                    "type": "image",
                    "source": {"type": "url", "url": url_val},
                })
        else:
            result.append(block)
    return result


def _extract_anthropic_content(data: dict) -> Optional[str]:
    """Extract text from an Anthropic /v1/messages response."""
    content = data.get("content")
    if not content:
        return None
    parts = []
    for block in content:
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts).strip() or None


def _log(msg: str):
    import sys
    print(f"[fleet_gateway] {msg}", file=sys.stderr, flush=True)
