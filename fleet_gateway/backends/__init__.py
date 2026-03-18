"""fleet_gateway.backends — LLM backend implementations."""

from .openai_compat import OpenAICompatBackend
from .anthropic import AnthropicBackend

__all__ = ["OpenAICompatBackend", "AnthropicBackend", "get_backend"]


def get_backend(cfg: dict):
    """Instantiate the right backend from a backend config dict."""
    backend_type = cfg.get("type", "openai_compat")
    if backend_type == "anthropic":
        return AnthropicBackend(cfg)
    return OpenAICompatBackend(cfg)
