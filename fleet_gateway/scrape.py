"""
fleet_gateway.scrape — Firecrawl web scraping integration.

Firecrawl converts any URL into clean Markdown, handling JS-rendered pages,
anti-bot measures, PDFs, and sitemaps.

Self-host options:
  1. Docker:  See docker-compose.yml in this project
  2. Cloud:   https://www.firecrawl.dev (free tier available)
  3. Env vars: FIRECRAWL_URL + optionally FIRECRAWL_API_KEY

Self-hosted Firecrawl doesn't require an API key.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


class Firecrawl:
    """Web scraping via Firecrawl /v0/scrape or /v1/scrape API."""

    def __init__(self, cfg: dict):
        self._url = (cfg.get("url") or "").rstrip("/")
        self._api_key = cfg.get("api_key") or ""
        self._timeout = int(cfg.get("timeout", 30))
        self._enabled = cfg.get("enabled", False) or bool(self._url)

    def is_available(self) -> bool:
        return bool(self._url)

    def _require_configured(self):
        if not self._url:
            raise RuntimeError(
                "Firecrawl not configured. "
                "Set FIRECRAWL_URL env var or add 'tools.firecrawl.url' to config.yaml. "
                "Self-host: see docker-compose.yml in this project. "
                "Cloud: https://www.firecrawl.dev"
            )

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    def scrape(self, url: str, *, timeout: Optional[int] = None, formats: Optional[List[str]] = None) -> str:
        """Scrape a URL and return its content as Markdown.

        Args:
            url: The URL to scrape.
            timeout: Override default timeout in seconds.
            formats: Output formats (default: ["markdown"]). Options: markdown, html, links.

        Returns:
            Markdown string of the page content.

        Raises:
            RuntimeError: if Firecrawl is not configured or scraping fails.
        """
        self._require_configured()

        body = {
            "url": url,
            "formats": formats or ["markdown"],
        }
        # Support both v0 and v1 API
        api_url = f"{self._url}/v1/scrape"

        try:
            req = urllib.request.Request(
                api_url,
                data=json.dumps(body).encode("utf-8"),
                headers=self._headers(),
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout or self._timeout) as resp:
                data = json.loads(resp.read(20_000_000).decode("utf-8"))
        except urllib.error.HTTPError as e:
            # Fall back to v0 API
            if e.code == 404:
                return self._scrape_v0(url, timeout=timeout)
            raise RuntimeError(f"Firecrawl error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Firecrawl connection error: {e.reason}")

        # v1 response format
        if data.get("success"):
            result = data.get("data", {})
            return result.get("markdown") or result.get("content") or ""

        raise RuntimeError(f"Firecrawl scrape failed: {data.get('error', 'unknown error')}")

    def _scrape_v0(self, url: str, *, timeout: Optional[int] = None) -> str:
        """Fallback: Firecrawl v0 API format."""
        body = {"url": url, "pageOptions": {"onlyMainContent": True}}
        api_url = f"{self._url}/v0/scrape"

        req = urllib.request.Request(
            api_url,
            data=json.dumps(body).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout or self._timeout) as resp:
                data = json.loads(resp.read(20_000_000).decode("utf-8"))
        except Exception as e:
            raise RuntimeError(f"Firecrawl v0 error: {e}")

        return (data.get("data", {}).get("markdown")
                or data.get("data", {}).get("content")
                or "")

    def crawl(
        self,
        url: str,
        *,
        max_pages: int = 10,
        timeout: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """Crawl a site and return list of {url, markdown} dicts.

        Args:
            url: Starting URL.
            max_pages: Maximum number of pages to crawl.
            timeout: Override default timeout (seconds per page).

        Returns:
            List of {"url": ..., "markdown": ...} dicts.
        """
        self._require_configured()

        body = {"url": url, "limit": max_pages, "formats": ["markdown"]}
        api_url = f"{self._url}/v1/crawl"

        try:
            req = urllib.request.Request(
                api_url,
                data=json.dumps(body).encode("utf-8"),
                headers=self._headers(),
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=(timeout or self._timeout) * max_pages) as resp:
                data = json.loads(resp.read(50_000_000).decode("utf-8"))
        except Exception as e:
            raise RuntimeError(f"Firecrawl crawl error: {e}")

        if not data.get("success"):
            raise RuntimeError(f"Firecrawl crawl failed: {data.get('error', 'unknown')}")

        results = []
        for page in data.get("data", []):
            results.append({
                "url": page.get("metadata", {}).get("sourceURL", url),
                "markdown": page.get("markdown", ""),
            })
        return results


def _log(msg: str):
    print(f"[fleet_gateway.scrape] {msg}", file=sys.stderr, flush=True)
