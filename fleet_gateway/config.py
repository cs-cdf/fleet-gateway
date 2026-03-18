"""
fleet_gateway.config — Progressive configuration loader.

Priority (highest → lowest):
  1. Explicit dict passed to Fleet()
  2. FLEET_GATEWAY_CONFIG env var (path to YAML file)
  3. ./config.yaml in current directory
  4. Auto-discovery from API key env vars (no file needed)

Zero external dependencies unless PyYAML is installed.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────────────────────
# Auto-discovery: env var → backend config
# ─────────────────────────────────────────────────────────────

_AUTO_BACKENDS: Dict[str, dict] = {
    "GROQ_API_KEY": {
        "name": "groq",
        "type": "openai_compat",
        "url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "models": [
            {"id": "llama-3.3-70b-versatile", "capabilities": ["general", "translate", "summarize"]},
            {"id": "llama3-70b-8192", "capabilities": ["general", "coding"]},
        ],
    },
    "CEREBRAS_API_KEY": {
        "name": "cerebras",
        "type": "openai_compat",
        "url": "https://api.cerebras.ai/v1",
        "api_key_env": "CEREBRAS_API_KEY",
        "models": [
            {"id": "qwen3-235b", "model_id": "qwen-3-235b-a22b-instruct-2507", "capabilities": ["general", "coding", "reasoning"]},
            {"id": "llama3.1-8b", "model_id": "llama3.1-8b", "capabilities": ["fast", "summarize"]},
        ],
    },
    "SAMBANOVA_API_KEY": {
        "name": "sambanova",
        "type": "openai_compat",
        "url": "https://api.sambanova.ai/v1",
        "api_key_env": "SAMBANOVA_API_KEY",
        "models": [
            {"id": "qwen3-235b-sn", "model_id": "Qwen3-235B", "capabilities": ["reasoning", "coding", "creative"]},
            {"id": "deepseek-v3", "model_id": "DeepSeek-V3.2", "capabilities": ["coding", "general"]},
        ],
    },
    "MISTRAL_API_KEY": {
        "name": "mistral",
        "type": "openai_compat",
        "url": "https://api.mistral.ai/v1",
        "api_key_env": "MISTRAL_API_KEY",
        "models": [
            {"id": "mistral-large", "capabilities": ["italian", "proofread", "creative"]},
            {"id": "codestral", "capabilities": ["coding"]},
        ],
    },
    "GEMINI_API_KEY": {
        "name": "gemini",
        "type": "openai_compat",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key_env": "GEMINI_API_KEY",
        "models": [
            {"id": "gemini-2.5-flash", "capabilities": ["fast", "general", "vision"]},
            {"id": "gemini-2.5-pro", "capabilities": ["reasoning", "long_context", "coding"]},
        ],
    },
    "OPENAI_API_KEY": {
        "name": "openai",
        "type": "openai_compat",
        "url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "models": [
            {"id": "gpt-4o", "capabilities": ["general", "coding", "vision"]},
            {"id": "gpt-4o-mini", "capabilities": ["fast", "general"]},
        ],
    },
    "ANTHROPIC_API_KEY": {
        "name": "anthropic",
        "type": "anthropic",
        "api_key_env": "ANTHROPIC_API_KEY",
        "models": [
            {"id": "claude-sonnet-4-6", "model_id": "claude-sonnet-4-6", "capabilities": ["reasoning", "coding", "editorial"]},
            {"id": "claude-haiku-4-5", "model_id": "claude-haiku-4-5-20251001", "capabilities": ["fast", "classification"]},
        ],
    },
    "OPENROUTER_API_KEY": {
        "name": "openrouter",
        "type": "openai_compat",
        "url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "models": [
            {"id": "qwen3-coder-free", "model_id": "qwen/qwen3-coder:free", "capabilities": ["coding"]},
            {"id": "hermes-405b-free", "model_id": "nousresearch/hermes-3-llama-3.1-405b:free", "capabilities": ["general", "creative"]},
        ],
    },
    "NVIDIA_API_KEY": {
        "name": "nvidia",
        "type": "openai_compat",
        "url": "https://integrate.api.nvidia.com/v1",
        "api_key_env": "NVIDIA_API_KEY",
        "models": [
            {"id": "nemotron-super-120b", "model_id": "nvidia/nemotron-3-super-120b-a12b", "capabilities": ["reasoning", "coding"]},
            {"id": "qwen3.5-122b-nv", "model_id": "qwen/qwen3.5-122b-a10b", "capabilities": ["reasoning", "coding", "creative"]},
        ],
    },
}

# Default routing chains using auto-discovered backends
_DEFAULT_ROUTING: Dict[str, List[str]] = {
    "coding":    ["cerebras/qwen3-235b", "sambanova/deepseek-v3", "openrouter/qwen3-coder-free", "mistral/codestral", "groq/llama3-70b-8192"],
    "general":   ["cerebras/qwen3-235b", "groq/llama-3.3-70b-versatile", "sambanova/qwen3-235b-sn", "gemini/gemini-2.5-flash"],
    "reasoning": ["sambanova/qwen3-235b-sn", "sambanova/deepseek-v3", "cerebras/qwen3-235b", "gemini/gemini-2.5-pro"],
    "translate": ["groq/llama-3.3-70b-versatile", "mistral/mistral-large", "cerebras/qwen3-235b"],
    "proofread": ["mistral/mistral-large", "gemini/gemini-2.5-flash", "groq/llama-3.3-70b-versatile"],
    "summarize": ["groq/llama-3.3-70b-versatile", "cerebras/llama3.1-8b", "gemini/gemini-2.5-flash"],
    "creative":  ["sambanova/qwen3-235b-sn", "cerebras/qwen3-235b", "openrouter/hermes-405b-free", "gemini/gemini-2.5-pro"],
    "fast":      ["cerebras/llama3.1-8b", "groq/llama-3.3-70b-versatile", "gemini/gemini-2.5-flash"],
    "italian":   ["mistral/mistral-large", "cerebras/qwen3-235b", "groq/llama-3.3-70b-versatile"],
    "vision":    ["gemini/gemini-2.5-flash", "openai/gpt-4o"],
}


# ─────────────────────────────────────────────────────────────
# YAML loader (no PyYAML required)
# ─────────────────────────────────────────────────────────────

def _load_yaml(path: Path) -> dict:
    """Load YAML file. Uses PyYAML if available, else minimal parser."""
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except ImportError:
        pass
    return _minimal_yaml(text)


def _minimal_yaml(text: str) -> dict:
    """Minimal YAML parser sufficient for config.yaml (no PyYAML dep).
    Handles: mappings, block lists, inline lists, scalars, quoted strings, #comments.
    Does NOT handle anchors, multi-line strings, or complex flow blocks.
    """
    def _scalar(v: str):
        v = v.strip()
        if not v or v in ("~", "null", "Null"): return None
        if v in ("true", "True", "yes"): return True
        if v in ("false", "False", "no"): return False
        if v.startswith(('"', "'")) and v[-1] == v[0]: return v[1:-1]
        try:
            return int(v)
        except ValueError:
            pass
        try:
            return float(v)
        except ValueError:
            pass
        return v

    def _strip_comment(s: str) -> str:
        if s.startswith(('"', "'")): return s
        i = s.find("  #")
        return s[:i].strip() if i > 0 else s

    def _split_csv(s: str) -> list:
        parts, cur, depth, q = [], "", 0, None
        for ch in s:
            if ch in ('"', "'") and q is None: q = ch; cur += ch
            elif ch == q: q = None; cur += ch
            elif q: cur += ch
            elif ch in ("[", "{"): depth += 1; cur += ch
            elif ch in ("]", "}"): depth -= 1; cur += ch
            elif ch == "," and depth == 0: parts.append(cur.strip()); cur = ""
            else: cur += ch
        if cur.strip(): parts.append(cur.strip())
        return parts

    def _flow(s: str):
        s = s.strip()
        if s.startswith("[") and s.endswith("]"):
            inner = s[1:-1].strip()
            return [_scalar(x) for x in _split_csv(inner)] if inner else []
        if s.startswith("{") and s.endswith("}"):
            inner = s[1:-1].strip()
            if not inner: return {}
            r = {}
            for p in _split_csv(inner):
                if ":" in p:
                    k, v = p.split(":", 1)
                    r[k.strip().strip('"').strip("'")] = _scalar(v.strip())
            return r
        return _scalar(s)

    entries = []
    for raw in text.splitlines():
        s = raw.strip()
        if s and not s.startswith("#"):
            entries.append((len(raw) - len(raw.lstrip()), s))

    def _parse(start: int, min_indent: int):
        if start >= len(entries): return None, start
        fi = entries[start][0]
        if fi < min_indent: return None, start
        if entries[start][1].startswith("- "):
            result, i = [], start
            while i < len(entries):
                ind, content = entries[i]
                if ind < fi: break
                if ind == fi and content.startswith("- "):
                    item = content[2:].strip()
                    if not item:
                        i += 1; child, i = _parse(i, fi + 1); result.append(child)
                    else:
                        result.append(_flow(item)); i += 1
                elif ind > fi: i += 1
                else: break
            return result, i
        result, i = {}, start
        while i < len(entries):
            ind, content = entries[i]
            if ind < fi: break
            if ind > fi: i += 1; continue
            cp = content.find(":")
            if cp < 0: i += 1; continue
            key = content[:cp].strip().strip('"').strip("'")
            val_str = _strip_comment(content[cp+1:].strip())
            if val_str:
                result[key] = _flow(val_str); i += 1
            else:
                i += 1
                if i < len(entries) and entries[i][0] > fi:
                    child, i = _parse(i, fi + 1); result[key] = child
                else:
                    result[key] = None
        return result, i

    val, _ = _parse(0, 0)
    return val if isinstance(val, dict) else {}


# ─────────────────────────────────────────────────────────────
# Main config loader
# ─────────────────────────────────────────────────────────────

class Config:
    """Resolved configuration for fleet-gateway.

    Backends, routing, server settings, and tool URLs are available
    as simple dicts after loading.
    """

    def __init__(self, raw: dict):
        self._raw = raw
        # Resolved backends dict: name → backend config dict
        self.backends: Dict[str, dict] = {}
        self.routing: Dict[str, List[str]] = {}
        self.server: dict = {}
        self.tools: dict = {}
        self._resolve()

    def _resolve(self):
        raw = self._raw

        # Backends
        for name, cfg in (raw.get("backends") or {}).items():
            if isinstance(cfg, dict):
                cfg = dict(cfg)
                cfg.setdefault("name", name)
                cfg.setdefault("api_key", os.environ.get(cfg.get("api_key_env") or "", ""))
                self.backends[name] = cfg

        # Routing
        self.routing = dict(raw.get("routing") or _DEFAULT_ROUTING)

        # Server
        srv = raw.get("server") or {}
        self.server = {
            "host": srv.get("host", "0.0.0.0"),
            "port": int(srv.get("port", 4000)),
            "max_concurrent": int(srv.get("max_concurrent", 4)),
            "timeout": float(srv.get("timeout", 120)),
            "log_level": srv.get("log_level", "INFO"),
        }

        # Tools
        tools = raw.get("tools") or {}
        self.tools = {
            "searxng": {
                "enabled": tools.get("searxng", {}).get("enabled", False),
                "url": tools.get("searxng", {}).get("url", os.environ.get("SEARXNG_URL", "")),
                "default_language": tools.get("searxng", {}).get("default_language", "en"),
                "default_categories": tools.get("searxng", {}).get("default_categories", ["general"]),
                "max_results": int(tools.get("searxng", {}).get("max_results", 10)),
            },
            "firecrawl": {
                "enabled": tools.get("firecrawl", {}).get("enabled", False),
                "url": tools.get("firecrawl", {}).get("url", os.environ.get("FIRECRAWL_URL", "")),
                "api_key": os.environ.get(tools.get("firecrawl", {}).get("api_key_env") or "FIRECRAWL_API_KEY", ""),
                "timeout": int(tools.get("firecrawl", {}).get("timeout", 30)),
            },
        }

    def get_backend(self, name: str) -> Optional[dict]:
        return self.backends.get(name)

    def get_routing_chain(self, capability: str) -> List[str]:
        """Return routing chain for a capability. Falls back to 'general'."""
        return self.routing.get(capability) or self.routing.get("general") or []


def _auto_config() -> dict:
    """Build config dict from environment variables only."""
    backends = {}
    for env_var, backend_def in _AUTO_BACKENDS.items():
        if os.environ.get(env_var):
            name = backend_def["name"]
            backends[name] = dict(backend_def)

    # Also check for SEARXNG_URL / FIRECRAWL_URL
    tools: dict = {}
    if os.environ.get("SEARXNG_URL"):
        tools["searxng"] = {"enabled": True, "url": os.environ["SEARXNG_URL"]}
    if os.environ.get("FIRECRAWL_URL"):
        tools["firecrawl"] = {
            "enabled": True,
            "url": os.environ["FIRECRAWL_URL"],
            "api_key_env": "FIRECRAWL_API_KEY",
        }

    return {
        "backends": backends,
        "routing": _DEFAULT_ROUTING,
        "tools": tools,
    }


def load_config(config_dict: Optional[dict] = None) -> Config:
    """Load configuration with progressive fallback.

    1. Explicit dict passed by caller
    2. FLEET_GATEWAY_CONFIG env var pointing to a YAML file
    3. config.yaml in current directory
    4. Auto-discovery from API key env vars
    """
    if config_dict is not None:
        raw = config_dict
    elif os.environ.get("FLEET_GATEWAY_CONFIG"):
        path = Path(os.environ["FLEET_GATEWAY_CONFIG"])
        raw = _load_yaml(path)
        _merge_env_keys(raw)
    else:
        candidates = [Path.cwd() / "config.yaml", Path.cwd() / "fleet_gateway.yaml"]
        for p in candidates:
            if p.exists():
                raw = _load_yaml(p)
                _merge_env_keys(raw)
                break
        else:
            raw = _auto_config()

    return Config(raw)


def _merge_env_keys(raw: dict):
    """Inject API keys from env vars into a loaded config dict."""
    for backend_cfg in (raw.get("backends") or {}).values():
        if not isinstance(backend_cfg, dict):
            continue
        env_var = backend_cfg.get("api_key_env")
        if env_var and not backend_cfg.get("api_key"):
            backend_cfg["api_key"] = os.environ.get(env_var, "")
