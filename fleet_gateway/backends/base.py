"""fleet_gateway.backends.base — Abstract backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List, Optional


class BaseBackend(ABC):
    """Abstract base for all LLM backends."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.name: str = cfg.get("name", "unknown")

    @abstractmethod
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
        """Send messages to a model and return the text response.

        Returns None on failure (caller should try next backend).
        Raises nothing — all exceptions are caught and return None.
        """

    def is_available(self) -> bool:
        """Check if this backend has a valid API key / is reachable.

        Override for backends that need a health check.
        """
        return bool(self.cfg.get("api_key") or self.cfg.get("url", "").startswith("http://localhost"))

    def model_id_for(self, model_ref: str) -> str:
        """Resolve a model reference (id or alias) to the actual API model ID.

        model_ref is the 'id' field in the models list; the actual API id
        may differ (stored in 'model_id' field).
        """
        for m in self.cfg.get("models") or []:
            if m.get("id") == model_ref:
                return m.get("model_id") or model_ref
        return model_ref

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
