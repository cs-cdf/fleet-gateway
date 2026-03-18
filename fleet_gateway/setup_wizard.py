"""
fleet-gateway setup wizard and doctor.

Guides new users through:
  1. Selecting providers
  2. Getting API keys (with signup links)
  3. Writing a .env file
  4. Testing connectivity
  5. Running a first call

Zero external dependencies (stdlib only).
"""
from __future__ import annotations

import os
import sys
import urllib.request
import urllib.error
import json
from pathlib import Path


# ── Provider catalogue ────────────────────────────────────────────────────────

PROVIDERS = [
    {
        "key": "groq",
        "env": "GROQ_API_KEY",
        "name": "Groq",
        "url": "https://api.groq.com/openai/v1",
        "signup": "https://console.groq.com",
        "free": True,
        "quota": "30 req/min, no credit card",
        "best_for": "fast general-purpose, best starting point",
        "test_model": "llama-3.3-70b-versatile",
    },
    {
        "key": "cerebras",
        "env": "CEREBRAS_API_KEY",
        "name": "Cerebras",
        "url": "https://api.cerebras.ai/v1",
        "signup": "https://cloud.cerebras.ai",
        "free": True,
        "quota": "1M tokens/day, no credit card",
        "best_for": "fastest inference (~2600 t/s), coding and reasoning",
        "test_model": "llama3.1-8b",
    },
    {
        "key": "sambanova",
        "env": "SAMBANOVA_API_KEY",
        "name": "SambaNova",
        "url": "https://api.sambanova.ai/v1",
        "signup": "https://cloud.sambanova.ai",
        "free": True,
        "quota": "10 req/min, no credit card",
        "best_for": "highest quality free models (Qwen3-235B, DeepSeek V3)",
        "test_model": "Meta-Llama-3.3-70B-Instruct",
    },
    {
        "key": "mistral",
        "env": "MISTRAL_API_KEY",
        "name": "Mistral",
        "url": "https://api.mistral.ai/v1",
        "signup": "https://console.mistral.ai",
        "free": True,
        "quota": "2 req/min, 1B tok/month, no credit card",
        "best_for": "Italian/French/Spanish, code (Codestral)",
        "test_model": "mistral-small-latest",
    },
    {
        "key": "gemini",
        "env": "GEMINI_API_KEY",
        "name": "Google Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "signup": "https://aistudio.google.com",
        "free": True,
        "quota": "15 req/min, 1M tok/day, no credit card",
        "best_for": "long context (2M tokens), vision, multimodal",
        "test_model": "gemini-2.0-flash",
    },
    {
        "key": "openrouter",
        "env": "OPENROUTER_API_KEY",
        "name": "OpenRouter",
        "url": "https://openrouter.ai/api/v1",
        "signup": "https://openrouter.ai",
        "free": True,
        "quota": "50 req/day free models, no credit card",
        "best_for": "access to many free large models via one key",
        "test_model": "meta-llama/llama-3.3-70b-instruct:free",
    },
    {
        "key": "nvidia",
        "env": "NVIDIA_API_KEY",
        "name": "NVIDIA NIM",
        "url": "https://integrate.api.nvidia.com/v1",
        "signup": "https://build.nvidia.com",
        "free": True,
        "quota": "1000 API calls/month, no credit card",
        "best_for": "complex reasoning, Nemotron thinking models",
        "test_model": "nvidia/llama-3.3-nemotron-super-49b-v1",
    },
    {
        "key": "openai",
        "env": "OPENAI_API_KEY",
        "name": "OpenAI",
        "url": "https://api.openai.com/v1",
        "signup": "https://platform.openai.com",
        "free": False,
        "quota": "$5 free credits on signup (expires 3 months)",
        "best_for": "GPT-4o, vision, widest ecosystem compatibility",
        "test_model": "gpt-4o-mini",
    },
    {
        "key": "anthropic",
        "env": "ANTHROPIC_API_KEY",
        "name": "Anthropic Claude",
        "url": None,  # native API
        "signup": "https://console.anthropic.com",
        "free": False,
        "quota": "Pay-per-use only",
        "best_for": "Claude models, complex reasoning, 200K context",
        "test_model": None,  # native API, skip simple test
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _print(msg: str = "", color: str = ""):
    codes = {"green": "\033[32m", "red": "\033[31m", "yellow": "\033[33m",
             "cyan": "\033[36m", "bold": "\033[1m", "reset": "\033[0m"}
    if color and sys.stdout.isatty():
        print(f"{codes.get(color, '')}{msg}{codes['reset']}")
    else:
        print(msg)


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"{prompt}{suffix}: ").strip()
        return val or default
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)


def _test_key(provider: dict, key: str) -> tuple[bool, str]:
    """Quick connectivity test for a provider key."""
    url = provider.get("url")
    model = provider.get("test_model")
    if not url or not model:
        return True, "skipped (native API — verify manually)"

    # Use /v1/models as a lightweight check
    models_url = f"{url}/models"
    try:
        req = urllib.request.Request(
            models_url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status < 400:
                return True, "connection OK"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "invalid API key (401 Unauthorized)"
        if e.code == 404:
            # Some providers don't have /models — try a minimal chat call
            return _test_with_chat(url, key, model)
        return False, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return False, f"connection failed: {e.reason}"
    except Exception as e:
        return False, f"error: {e}"
    return True, "connection OK"


def _test_with_chat(base_url: str, key: str, model: str) -> tuple[bool, str]:
    """Minimal chat completions test."""
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 5,
    }).encode()
    try:
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status < 400, "connection OK"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "invalid API key (401)"
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, f"error: {e}"


def _write_env(keys: dict[str, str], path: Path):
    lines = [
        "# fleet-gateway API keys",
        "# Generated by: python -m fleet_gateway setup",
        "# Load with: source .env  (Linux/Mac)  or  set -a; . .env; set +a",
        "#            or use python-dotenv / direnv",
        "",
    ]
    for env_var, value in keys.items():
        lines.append(f"{env_var}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Setup wizard ──────────────────────────────────────────────────────────────

def run_setup():
    _print("\n╔══════════════════════════════════════════════════════╗", "bold")
    _print("║         fleet-gateway — Interactive Setup            ║", "bold")
    _print("╚══════════════════════════════════════════════════════╝\n", "bold")

    _print("fleet-gateway routes your LLM calls across multiple providers.", "cyan")
    _print("To use it, you need at least ONE API key from a supported provider.", "cyan")
    _print("Several providers offer generous FREE tiers — no credit card required.\n", "cyan")

    # Show free providers
    _print("FREE providers (recommended to start):", "bold")
    free = [p for p in PROVIDERS if p["free"]]
    for i, p in enumerate(free, 1):
        _print(f"  {i}. {p['name']:15s}  {p['quota']}")
        _print(f"     Best for: {p['best_for']}")
        _print(f"     Sign up:  {p['signup']}\n")

    _print("─" * 54)
    _print("\nWhich providers do you have (or want to get) keys for?", "bold")
    _print("(You can always add more later by editing .env)\n")

    all_providers = PROVIDERS
    collected: dict[str, str] = {}

    # Check for already-set env vars
    already_set = {}
    for p in all_providers:
        val = os.environ.get(p["env"], "")
        if val:
            already_set[p["env"]] = val

    if already_set:
        _print("Keys already found in your environment:", "yellow")
        for env_var in already_set:
            _print(f"  ✓ {env_var}", "green")
        _print()
        use_existing = _ask("Use these existing keys?", "yes")
        if use_existing.lower().startswith("y"):
            collected.update(already_set)

    # Ask for new keys
    for p in all_providers:
        if p["env"] in collected:
            continue
        tier = "FREE" if p["free"] else "PAID"
        _print(f"\n[{tier}] {p['name']}", "bold")
        _print(f"  Sign up: {p['signup']}")
        _print(f"  Best for: {p['best_for']}")
        key = _ask(f"  Paste your {p['env']} (or press Enter to skip)")
        if key:
            collected[p["env"]] = key

    if not collected:
        _print("\nNo keys entered. You need at least one key to use fleet-gateway.", "red")
        _print("Re-run this wizard after signing up for a free provider.", "yellow")
        _print("Fastest to get: Groq (https://console.groq.com) — takes ~1 minute.\n")
        sys.exit(1)

    # Test connectivity
    _print("\n── Testing API keys ─────────────────────────────────", "bold")
    valid = {}
    for p in all_providers:
        if p["env"] not in collected:
            continue
        key = collected[p["env"]]
        _print(f"  Testing {p['name']}... ", end="", flush=True)
        ok, msg = _test_key(p, key)
        if ok:
            _print(f"✓ {msg}", "green")
            valid[p["env"]] = key
        else:
            _print(f"✗ {msg}", "red")
            retry = _ask(f"  Keep this key anyway?", "no")
            if retry.lower().startswith("y"):
                valid[p["env"]] = key

    if not valid:
        _print("\nNo keys passed validation. Check your keys and try again.", "red")
        sys.exit(1)

    # Write .env
    env_path = Path(".env")
    if env_path.exists():
        overwrite = _ask("\n.env already exists. Overwrite?", "no")
        if not overwrite.lower().startswith("y"):
            env_path = Path(".env.fleet")
            _print(f"Writing to {env_path} instead.")

    _write_env(valid, env_path)
    _print(f"\n✓ Wrote {len(valid)} key(s) to {env_path}", "green")

    # Show what's available
    _print("\n── What you can do now ──────────────────────────────", "bold")
    _print("\n  Quick test:")
    _print("    python -m fleet_gateway doctor\n")
    _print("  Start the gateway server:")
    _print("    python -m fleet_gateway serve\n")
    _print("  Make a quick call:")
    _print("    python -m fleet_gateway call general 'What is 2+2?'\n")
    _print("  Or in Python:")
    _print("    from fleet_gateway import call")
    _print("    print(call('general', 'Hello!'))\n")

    # Offer a live test call
    live = _ask("Run a quick live test call now?", "yes")
    if live.lower().startswith("y"):
        _print("\nCalling 'general' capability...", "cyan")
        # Load keys into env
        for k, v in valid.items():
            os.environ[k] = v
        try:
            from fleet_gateway import call
            result = call("general", "Say hello in one sentence.")
            if result:
                _print(f"\n✓ Response: {result}", "green")
            else:
                _print("No response — check your keys or try another provider.", "red")
        except Exception as e:
            _print(f"Error: {e}", "red")

    _print("\n✓ Setup complete!", "green")
    _print(f"Load your keys before using fleet-gateway: source {env_path}\n")


# ── Doctor ────────────────────────────────────────────────────────────────────

def run_doctor():
    _print("\n╔══════════════════════════════════════════════════════╗", "bold")
    _print("║          fleet-gateway — Health Check                ║", "bold")
    _print("╚══════════════════════════════════════════════════════╝\n", "bold")

    found_any = False
    for p in PROVIDERS:
        key = os.environ.get(p["env"], "")
        if not key:
            continue
        found_any = True
        _print(f"  {p['name']:15s} ", end="")
        ok, msg = _test_key(p, key)
        if ok:
            _print(f"✓ {msg}", "green")
        else:
            _print(f"✗ {msg}", "red")

    if not found_any:
        _print("No API keys found in environment.", "red")
        _print("\nSet at least one key, e.g.:")
        _print("  export GROQ_API_KEY=your_key_here")
        _print("\nOr run the setup wizard:")
        _print("  python -m fleet_gateway setup\n")
        sys.exit(1)

    _print()
    # Show routing summary
    try:
        from fleet_gateway import Fleet
        fleet = Fleet()
        caps = fleet.capabilities()
        if caps:
            _print("Routing table:", "bold")
            for cap, chain in sorted(caps.items()):
                _print(f"  {cap:15s} → {', '.join(chain[:3])}" + (" ..." if len(chain) > 3 else ""))
    except Exception:
        pass

    _print()
