"""
fleet_gateway.router — Capability-based routing with fallback chains.

The router takes a model reference (capability alias or "backend/model_id")
and returns the response from the first available backend.

Routing chain format:
  - "backend_name/model_id"     → explicit backend + model
  - "model_id"                   → search all backends for this model
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional

from .backends import get_backend
from .config import Config


class Router:
    """Routes LLM requests through a fallback chain of backends."""

    def __init__(self, config: Config):
        self._config = config
        # Instantiate backend objects lazily (cache by name)
        self._backend_cache: Dict[str, Any] = {}

    def _get_backend(self, backend_name: str):
        if backend_name not in self._backend_cache:
            cfg = self._config.get_backend(backend_name)
            if cfg is None:
                return None
            self._backend_cache[backend_name] = get_backend(cfg)
        return self._backend_cache[backend_name]

    def _resolve_entry(self, entry: str):
        """Resolve a routing chain entry like 'groq/llama-3.3-70b-versatile'.

        Returns (backend, model_id) or (None, None).
        """
        if "/" in entry:
            parts = entry.split("/", 1)
            backend_name, model_id = parts[0], parts[1]
        else:
            # Bare model ID: search all backends
            for name, cfg in self._config.backends.items():
                for m in (cfg.get("models") or []):
                    if m.get("id") == entry or m.get("model_id") == entry:
                        backend_name = name
                        model_id = entry
                        break
                else:
                    continue
                break
            else:
                return None, None

        backend = self._get_backend(backend_name)
        if backend is None or not backend.is_available():
            return None, None

        return backend, model_id

    def call(
        self,
        model_or_capability: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
        timeout: float = 120.0,
        stream: bool = False,
        **kwargs,
    ) -> Optional[str]:
        """Call a model or capability, trying the fallback chain.

        model_or_capability can be:
          - A capability alias: "coding", "general", "translate", ...
          - A direct reference: "groq/llama-3.3-70b-versatile"
          - A bare model id: "llama-3.3-70b-versatile"
        """
        # Build the chain to try
        chain = self._config.get_routing_chain(model_or_capability)

        # If not a capability alias, treat as direct entry
        if not chain or model_or_capability not in self._config.routing:
            chain = [model_or_capability]

        last_error = None
        for entry in chain:
            backend, model_id = self._resolve_entry(entry)
            if backend is None:
                _log(f"Skipping {entry!r}: backend unavailable")
                continue

            _log(f"Trying {entry!r}...")
            result = backend.call(
                model_id=model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
                stream=stream,
                **kwargs,
            )
            if result is not None:
                _log(f"Success: {entry!r}")
                return result

            _log(f"Failed: {entry!r}, trying next...")

        _log(f"All entries exhausted for {model_or_capability!r}")
        return None

    def available_models(self) -> List[Dict[str, Any]]:
        """Return list of all configured models with availability status."""
        models = []
        for backend_name, cfg in self._config.backends.items():
            backend = self._get_backend(backend_name)
            available = backend.is_available() if backend else False
            for model in (cfg.get("models") or []):
                models.append({
                    "id": f"{backend_name}/{model.get('id', '')}",
                    "backend": backend_name,
                    "model_id": model.get("model_id") or model.get("id"),
                    "capabilities": model.get("capabilities", []),
                    "available": available,
                })
        return models

    def available_capabilities(self) -> Dict[str, List[str]]:
        """Return routing table (capability → chain entries)."""
        return dict(self._config.routing)


def _log(msg: str):
    print(f"[fleet_gateway.router] {msg}", file=sys.stderr, flush=True)
