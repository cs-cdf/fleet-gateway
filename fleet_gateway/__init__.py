"""
fleet-gateway — Lightweight LLM gateway with routing, fallback chains,
optional web tools (SearXNG search, Firecrawl scraping), and multi-model
reasoning patterns (consensus, loop, review, challenge, brainstorm, swot).

QUICKSTART (no config file needed):
    export GROQ_API_KEY=your_key_here
    python -c "from fleet_gateway import call; print(call('general', 'Hello!'))"

OR with a config file:
    # config.yaml (see config.example.yaml for full reference)
    from fleet_gateway import Fleet
    fleet = Fleet("config.yaml")
    response = fleet.call("coding", "Write a Python hello world")
    results  = fleet.search("Python async tips")
    content  = fleet.scrape("https://example.com")

    # Multi-model patterns
    result = fleet.patterns.consensus("Is Rust better than Go for CLIs?")
    result = fleet.patterns.challenge("We should rewrite everything in microservices")
    result = fleet.patterns.review(code_string, content_type="code")
    result = fleet.patterns.loop("Write a sorting function", iterations=3)
    result = fleet.patterns.brainstorm("names for a developer tool")
    result = fleet.patterns.swot("Switching our stack to Rust")
    result = fleet.patterns.perspectives("Remote-first vs office-first teams")
    result = fleet.patterns.adversarial("We should deprecate REST and use GraphQL only")

Module-level functions use a default Fleet instance (auto-configured
from env vars or config.yaml in the current directory).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from .config import Config, load_config
from .router import Router
from .search import SearXNG
from .scrape import Firecrawl
from .patterns import Patterns

__version__ = "0.1.0"
__all__ = [
    "Fleet", "Patterns",
    "call", "search", "scrape", "models", "capabilities",
    "consensus", "loop", "review", "challenge", "brainstorm", "swot",
]


class Fleet:
    """Main entry point for fleet-gateway.

    Args:
        config: One of:
          - None (default): auto-configure from env vars + config.yaml
          - str/Path: path to a YAML config file
          - dict: raw config dict
    """

    def __init__(self, config=None):
        if isinstance(config, (str,)) or hasattr(config, "__fspath__"):
            from pathlib import Path
            import os
            path = Path(config)
            from .config import _load_yaml, _merge_env_keys
            raw = _load_yaml(path)
            _merge_env_keys(raw)
            self._config = Config(raw)
        elif isinstance(config, dict):
            self._config = Config(config)
        else:
            self._config = load_config()

        self._router = Router(self._config)
        self._searxng = SearXNG(self._config.tools.get("searxng", {}))
        self._firecrawl = Firecrawl(self._config.tools.get("firecrawl", {}))
        self.patterns = Patterns(self._router)

    # ── LLM ──────────────────────────────────────────────────

    def call(
        self,
        model_or_capability: str,
        messages: Union[str, List[Dict[str, str]]],
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        timeout: float = 120.0,
        system: Optional[str] = None,
        **kwargs,
    ) -> Optional[str]:
        """Call an LLM model or capability.

        Args:
            model_or_capability: Capability alias ("coding", "general") or
                                  direct reference ("groq/llama-3.3-70b-versatile").
            messages: Either a prompt string or a list of message dicts
                      [{"role": "user", "content": "..."}].
            max_tokens: Max tokens in the response.
            temperature: Sampling temperature (0=deterministic, 1=creative).
            timeout: Seconds to wait for a response.
            system: Optional system prompt (prepended to messages).
            **kwargs: Extra params forwarded to the backend.

        Returns:
            Response text, or None if all backends failed.
        """
        msgs = _normalize_messages(messages, system)
        return self._router.call(
            model_or_capability,
            messages=msgs,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            **kwargs,
        )

    # ── Web search ───────────────────────────────────────────

    def search(
        self,
        query: str,
        *,
        num_results: int = 10,
        language: Optional[str] = None,
        categories: Optional[List[str]] = None,
    ) -> List[Dict[str, str]]:
        """Search the web via SearXNG.

        Requires SEARXNG_URL env var or 'tools.searxng.url' in config.

        Returns list of {"title": ..., "url": ..., "content": ...} dicts.
        Raises RuntimeError if SearXNG is not configured.
        """
        return self._searxng.search(query, num_results=num_results, language=language, categories=categories)

    # ── Web scraping ─────────────────────────────────────────

    def scrape(self, url: str, *, timeout: Optional[int] = None) -> str:
        """Scrape a URL and return its content as Markdown.

        Requires FIRECRAWL_URL env var or 'tools.firecrawl.url' in config.

        Returns markdown string.
        Raises RuntimeError if Firecrawl is not configured.
        """
        return self._firecrawl.scrape(url, timeout=timeout)

    # ── Introspection ────────────────────────────────────────

    def models(self) -> List[Dict[str, Any]]:
        """Return all configured models with availability status."""
        return self._router.available_models()

    def capabilities(self) -> Dict[str, List[str]]:
        """Return capability → routing chain mapping."""
        return self._router.available_capabilities()

    def health(self) -> Dict[str, Any]:
        """Return health summary: available models, tool status."""
        all_models = self.models()
        available = [m for m in all_models if m["available"]]
        return {
            "status": "ok" if available else "degraded",
            "models_total": len(all_models),
            "models_available": len(available),
            "searxng": self._searxng.is_available(),
            "firecrawl": self._firecrawl.is_available(),
        }


# ── Module-level convenience API ─────────────────────────────────────────────
# Uses a lazily-created default Fleet instance.

_default: Optional[Fleet] = None


def _get_default() -> Fleet:
    global _default
    if _default is None:
        _default = Fleet()
    return _default


def call(
    model_or_capability: str,
    messages: Union[str, List[Dict[str, str]]],
    **kwargs,
) -> Optional[str]:
    """Call an LLM using the default Fleet instance.

    Examples:
        from fleet_gateway import call
        response = call("coding", "Write a Python hello world")
        response = call("general", [{"role": "user", "content": "What is 2+2?"}])
    """
    return _get_default().call(model_or_capability, messages, **kwargs)


def search(query: str, **kwargs) -> List[Dict[str, str]]:
    """Search the web via SearXNG (default Fleet instance)."""
    return _get_default().search(query, **kwargs)


def scrape(url: str, **kwargs) -> str:
    """Scrape a URL via Firecrawl (default Fleet instance)."""
    return _get_default().scrape(url, **kwargs)


def models() -> List[Dict[str, Any]]:
    """List all configured models (default Fleet instance)."""
    return _get_default().models()


def capabilities() -> Dict[str, List[str]]:
    """Show capability routing table (default Fleet instance)."""
    return _get_default().capabilities()


# ── Module-level pattern shortcuts ───────────────────────────────────────────

def consensus(question: Union[str, list], **kwargs) -> Dict[str, Any]:
    """Multi-model consensus (default Fleet instance).

    Example:
        from fleet_gateway import consensus
        result = consensus("Is GraphQL better than REST?")
        print(result["synthesis"])
    """
    return _get_default().patterns.consensus(question, **kwargs)


def loop(prompt: str, **kwargs) -> Dict[str, Any]:
    """Iterative refinement loop (default Fleet instance).

    Example:
        from fleet_gateway import loop
        result = loop("Write a Python quicksort", iterations=3)
        print(result["final"])
    """
    return _get_default().patterns.loop(prompt, **kwargs)


def review(content: str, **kwargs) -> Dict[str, Any]:
    """Multi-model review with synthesis (default Fleet instance).

    Example:
        from fleet_gateway import review
        result = review(my_code, content_type="code")
        print(result["synthesis"])
    """
    return _get_default().patterns.review(content, **kwargs)


def challenge(idea: str, **kwargs) -> Dict[str, Any]:
    """Devil's advocate challenge (default Fleet instance).

    Example:
        from fleet_gateway import challenge
        result = challenge("We should migrate to microservices")
        print(result["challenge"])
    """
    return _get_default().patterns.challenge(idea, **kwargs)


def brainstorm(topic: str, **kwargs) -> Dict[str, Any]:
    """Multi-model brainstorm (default Fleet instance).

    Example:
        from fleet_gateway import brainstorm
        result = brainstorm("Product names for a developer tool")
        print(result["synthesis"])
    """
    return _get_default().patterns.brainstorm(topic, **kwargs)


def swot(subject: str, **kwargs) -> Dict[str, Any]:
    """SWOT analysis (default Fleet instance).

    Example:
        from fleet_gateway import swot
        result = swot("Adopting Rust for our backend")
        print(result["analysis"])
    """
    return _get_default().patterns.swot(subject, **kwargs)


def perspectives(topic: str, **kwargs) -> Dict[str, Any]:
    """Multi-perspective analysis (default Fleet instance).

    Example:
        from fleet_gateway import perspectives
        result = perspectives("Remote-first vs office-first")
        print(result["synthesis"])
    """
    return _get_default().patterns.perspectives(topic, **kwargs)


def adversarial(claim: str, **kwargs) -> Dict[str, Any]:
    """Adversarial debate (default Fleet instance).

    Example:
        from fleet_gateway import adversarial
        result = adversarial("We should deprecate REST and use GraphQL only")
        print(result["verdict"])
    """
    return _get_default().patterns.adversarial(claim, **kwargs)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_messages(
    messages: Union[str, List[Dict[str, str]]],
    system: Optional[str] = None,
) -> List[Dict[str, str]]:
    if isinstance(messages, str):
        msgs = [{"role": "user", "content": messages}]
    else:
        msgs = list(messages)
    if system:
        msgs = [{"role": "system", "content": system}] + msgs
    return msgs
