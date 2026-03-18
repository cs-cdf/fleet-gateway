"""
fleet_gateway.server — OpenAI-compatible HTTP gateway server.

Exposes a single endpoint that:
  - Routes requests by model name / capability alias
  - Tries fallback chains if a backend fails
  - Returns OpenAI-format responses

Usage:
    python -m fleet_gateway.server              # port 4000
    python -m fleet_gateway.server --port 8080
    fleet-gateway --port 8080                   # if installed via pip

Then use with any OpenAI-compatible client:
    curl http://localhost:4000/v1/chat/completions \
      -H 'Content-Type: application/json' \
      -d '{"model":"coding","messages":[{"role":"user","content":"Write hello world"}]}'

    from openai import OpenAI
    client = OpenAI(base_url="http://localhost:4000/v1", api_key="dummy")
    response = client.chat.completions.create(model="coding", messages=[...])
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Semaphore
from typing import Any, Dict, List, Optional

from .config import load_config
from .router import Router
from .search import SearXNG
from .scrape import Firecrawl

_router: Optional[Router] = None
_searxng: Optional[SearXNG] = None
_firecrawl: Optional[Firecrawl] = None
_semaphore: Optional[Semaphore] = None
_config = None


def _init(config=None):
    global _router, _searxng, _firecrawl, _semaphore, _config
    _config = load_config(config)
    _router = Router(_config)
    _searxng = SearXNG(_config.tools.get("searxng", {}))
    _firecrawl = Firecrawl(_config.tools.get("firecrawl", {}))
    _semaphore = Semaphore(_config.server["max_concurrent"])


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Suppress default access log — we log ourselves
        pass

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, status: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: int, message: str):
        self._send_json(status, {"error": {"message": message, "type": "gateway_error"}})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")

        if path in ("/health", "/"):
            models_list = _router.available_models()
            available = sum(1 for m in models_list if m["available"])
            self._send_json(200, {
                "status": "ok" if available else "degraded",
                "version": "0.1.0",
                "models_available": available,
                "models_total": len(models_list),
                "searxng": _searxng.is_available(),
                "firecrawl": _firecrawl.is_available(),
            })

        elif path in ("/v1/models", "/models"):
            models_list = _router.available_models()
            self._send_json(200, {
                "object": "list",
                "data": [
                    {
                        "id": m["id"],
                        "object": "model",
                        "created": 0,
                        "owned_by": m["backend"],
                        "available": m["available"],
                        "capabilities": m["capabilities"],
                    }
                    for m in models_list
                ] + [
                    {"id": cap, "object": "model", "created": 0, "owned_by": "router",
                     "available": True, "type": "capability_alias"}
                    for cap in _router.available_capabilities()
                ],
            })

        elif path in ("/v1/capabilities", "/capabilities"):
            self._send_json(200, _router.available_capabilities())

        else:
            self._send_error(404, f"Unknown path: {self.path}")

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")

        if path in ("/v1/chat/completions", "/chat/completions"):
            self._handle_chat()
        elif path in ("/v1/search", "/search"):
            self._handle_search()
        elif path in ("/v1/scrape", "/scrape"):
            self._handle_scrape()
        else:
            self._send_error(404, f"Unknown path: {self.path}")

    def _handle_chat(self):
        try:
            body = self._read_body()
        except Exception:
            self._send_error(400, "Invalid JSON body")
            return

        model = body.get("model", "general")
        messages = body.get("messages", [])
        max_tokens = int(body.get("max_tokens", 2048))
        temperature = float(body.get("temperature", 0.7))
        timeout = float(_config.server.get("timeout", 120))

        if not messages:
            self._send_error(400, "messages is required")
            return

        with _semaphore:
            t0 = time.time()
            result = _router.call(
                model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )
            elapsed = time.time() - t0

        if result is None:
            self._send_error(503, f"All backends failed for model/capability: {model!r}")
            return

        # Return OpenAI-format response
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        resp = {
            "id": completion_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": result},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": -1,
                "completion_tokens": -1,
                "total_tokens": -1,
            },
            "system_fingerprint": None,
            "_gateway_elapsed_s": round(elapsed, 2),
        }
        _log(f"[chat] model={model!r} elapsed={elapsed:.1f}s")
        self._send_json(200, resp)

    def _handle_search(self):
        """POST /v1/search — SearXNG web search."""
        try:
            body = self._read_body()
        except Exception:
            self._send_error(400, "Invalid JSON body")
            return

        query = body.get("query", "")
        if not query:
            self._send_error(400, "'query' is required")
            return

        if not _searxng.is_available():
            self._send_error(503, "SearXNG not configured. Set SEARXNG_URL env var.")
            return

        try:
            results = _searxng.search(
                query,
                num_results=int(body.get("num_results", 10)),
                language=body.get("language"),
                categories=body.get("categories"),
            )
            self._send_json(200, {"query": query, "results": results})
        except Exception as e:
            self._send_error(500, str(e))

    def _handle_scrape(self):
        """POST /v1/scrape — Firecrawl web scraping."""
        try:
            body = self._read_body()
        except Exception:
            self._send_error(400, "Invalid JSON body")
            return

        url = body.get("url", "")
        if not url:
            self._send_error(400, "'url' is required")
            return

        if not _firecrawl.is_available():
            self._send_error(503, "Firecrawl not configured. Set FIRECRAWL_URL env var.")
            return

        try:
            content = _firecrawl.scrape(url)
            self._send_json(200, {"url": url, "markdown": content})
        except Exception as e:
            self._send_error(500, str(e))


def run(host: str = "0.0.0.0", port: int = 4000, config=None):
    """Start the gateway server (blocking)."""
    _init(config)
    server = HTTPServer((host, port), _Handler)
    _log(f"fleet-gateway listening on http://{host}:{port}")
    _log(f"  models: {len(_router.available_models())}")
    _log(f"  capabilities: {list(_router.available_capabilities().keys())}")
    _log(f"  searxng: {'enabled' if _searxng.is_available() else 'disabled'}")
    _log(f"  firecrawl: {'enabled' if _firecrawl.is_available() else 'disabled'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _log("Shutting down.")
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description="fleet-gateway — OpenAI-compatible LLM gateway")
    parser.add_argument("--host", default=os.environ.get("FLEET_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("FLEET_PORT", 4000)))
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    args = parser.parse_args()
    run(host=args.host, port=args.port, config=args.config)


def _log(msg: str):
    print(f"[fleet_gateway] {msg}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
