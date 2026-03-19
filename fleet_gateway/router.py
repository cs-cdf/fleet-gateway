"""
fleet_gateway.router — Capability-based routing with fallback chains.

The router takes a model reference (capability alias or "backend/model_id")
and returns the response from the first available backend.

Routing chain format:
  - "backend_name/model_id"     → explicit backend + model
  - "model_id"                   → search all backends for this model
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

from .backends import get_backend
from .config import Config
from .ratelimit import RateLimiter

logger = logging.getLogger(__name__)


class Router:
    """Routes LLM requests through a fallback chain of backends."""

    def __init__(self, config: Config):
        self._config = config
        # Instantiate backend objects lazily (cache by name)
        self._backend_cache: Dict[str, Any] = {}
        # Per-backend rate limiters (populated on first access)
        self._limiters: Dict[str, RateLimiter] = {}
        # Single lock protecting both _backend_cache and _limiters writes
        self._cache_lock = threading.Lock()
        # Pre-built index: bare model_id -> backend_name (O(1) lookup)
        self._model_index: Dict[str, str] = self._build_model_index()

    def _build_model_index(self) -> Dict[str, str]:
        """Build a {model_id: backend_name} index from config for O(1) bare-ID lookup."""
        index: Dict[str, str] = {}
        for backend_name, cfg in self._config.backends.items():
            for m in (cfg.get("models") or []):
                for key in ("id", "model_id"):
                    mid = m.get(key)
                    if mid and mid not in index:
                        index[mid] = backend_name
        return index

    def _get_backend(self, backend_name: str):
        # Fast path without lock
        if backend_name in self._backend_cache:
            return self._backend_cache[backend_name]
        with self._cache_lock:
            # Re-check inside lock (double-checked locking)
            if backend_name not in self._backend_cache:
                cfg = self._config.get_backend(backend_name)
                if cfg is None:
                    return None
                self._backend_cache[backend_name] = get_backend(cfg)
        return self._backend_cache[backend_name]

    def _get_limiter(self, backend_name: str) -> RateLimiter:
        # Fast path without lock
        if backend_name in self._limiters:
            return self._limiters[backend_name]
        with self._cache_lock:
            # Re-check inside lock (double-checked locking)
            if backend_name not in self._limiters:
                cfg = self._config.get_backend(backend_name) or {}
                rpm = cfg.get("rate_limit")
                self._limiters[backend_name] = RateLimiter(rpm)
        return self._limiters[backend_name]

    def _resolve_entry(self, entry: str):
        """Resolve a routing chain entry like 'groq/llama-3.3-70b-versatile'.

        Returns (backend, backend_name, model_id) or (None, None, None).
        """
        if "/" in entry:
            parts = entry.split("/", 1)
            backend_name, model_id = parts[0], parts[1]
        else:
            # Bare model ID: O(1) index lookup instead of O(N×M) scan
            backend_name = self._model_index.get(entry)
            if backend_name is None:
                return None, None, None
            model_id = entry

        backend = self._get_backend(backend_name)
        if backend is None or not backend.is_available():
            return None, None, None

        return backend, backend_name, model_id

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
            backend, backend_name, model_id = self._resolve_entry(entry)
            if backend is None:
                logger.debug("Skipping %r: backend unavailable", entry)
                continue

            limiter = self._get_limiter(backend_name)
            if not limiter.acquire(timeout=timeout):
                logger.debug("Rate limit exceeded for %r, trying next...", entry)
                continue

            logger.debug("Trying %r...", entry)
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
                logger.debug("Success: %r", entry)
                return result

            logger.debug("Failed: %r, trying next...", entry)

        logger.debug("All entries exhausted for %r", model_or_capability)
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


