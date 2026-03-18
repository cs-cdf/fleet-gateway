"""
fleet_gateway.search — SearXNG web search integration.

SearXNG is a self-hosted, privacy-respecting meta search engine.
Self-host it for free; no API key required.

Setup options:
  1. Docker:  docker run -d -p 8888:8080 searxng/searxng
  2. Env var: export SEARXNG_URL=http://localhost:8888
  3. Config:  tools.searxng.url in config.yaml
  4. Public:  Use any public SearXNG instance (less reliable)
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


class SearXNG:
    """Web search via SearXNG JSON API."""

    def __init__(self, cfg: dict):
        self._url = (cfg.get("url") or "").rstrip("/")
        self._enabled = cfg.get("enabled", False) or bool(self._url)
        self._default_language = cfg.get("default_language", "en")
        self._default_categories = cfg.get("default_categories", ["general"])
        self._max_results = int(cfg.get("max_results", 10))

    def is_available(self) -> bool:
        return bool(self._url)

    def _require_configured(self):
        if not self._url:
            raise RuntimeError(
                "SearXNG not configured. "
                "Set SEARXNG_URL env var or add 'tools.searxng.url' to config.yaml. "
                "To self-host: docker run -d -p 8888:8080 searxng/searxng"
            )

    def search(
        self,
        query: str,
        *,
        num_results: int = 10,
        language: Optional[str] = None,
        categories: Optional[List[str]] = None,
        timeout: float = 15.0,
    ) -> List[Dict[str, str]]:
        """Search and return a list of results.

        Returns:
            List of dicts with keys: title, url, content, engine (optional).

        Raises:
            RuntimeError: if SearXNG is not configured.
        """
        self._require_configured()

        params = {
            "q": query,
            "format": "json",
            "language": language or self._default_language,
            "categories": ",".join(categories or self._default_categories),
        }
        url = f"{self._url}/search?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "fleet-gateway/0.1 (search client)"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            _log(f"SearXNG search error: {e}")
            return []

        results = []
        for item in data.get("results", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", "") or item.get("snippet", ""),
                "engine": item.get("engine", ""),
            })
        return results

    def search_text(self, query: str, **kwargs) -> str:
        """Search and return results as a formatted text block.

        Useful for injecting search results into an LLM prompt.
        """
        results = self.search(query, **kwargs)
        if not results:
            return f"No results found for: {query}"
        lines = [f"Search results for: {query}\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}")
            lines.append(f"   URL: {r['url']}")
            if r.get("content"):
                lines.append(f"   {r['content'][:200]}...")
            lines.append("")
        return "\n".join(lines)


def _log(msg: str):
    print(f"[fleet_gateway.search] {msg}", file=sys.stderr, flush=True)
