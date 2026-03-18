# fleet-gateway — Quickstart for New Users

> **Before you start:** fleet-gateway routes calls to LLM providers. To actually run
> inference, you need at least one API key from a supported provider. Several offer
> generous **free tiers** — no credit card required.

---

## Step 1 — Get a free API key (2 minutes)

Pick **any one** of these. All are free, no credit card needed:

| Provider | Sign up | Free quota | Best for |
|----------|---------|------------|----------|
| **Groq** ← easiest start | [console.groq.com](https://console.groq.com) | 30 req/min | Fast, general |
| **Cerebras** | [cloud.cerebras.ai](https://cloud.cerebras.ai) | 1M tokens/day | Speed, coding |
| **SambaNova** | [cloud.sambanova.ai](https://cloud.sambanova.ai) | 10 req/min | Quality |
| **Mistral** | [console.mistral.ai](https://console.mistral.ai) | 2 req/min, 1B tok/month | Italian/French/Code |
| **Gemini** | [aistudio.google.com](https://aistudio.google.com) | 15 req/min, 1M tok/day | Vision, long context |
| **OpenRouter** | [openrouter.ai](https://openrouter.ai) | 50 req/day free | Many free models |

> You can add more providers later. Start with one.

---

## Step 2 — Install

```bash
pip install fleet-gateway
```

---

## Step 3 — Run the setup wizard

```bash
python -m fleet_gateway setup
```

The wizard will:
- Ask which provider(s) you have keys for
- Let you paste your keys
- Test connectivity
- Write a `.env` file
- Run a live test call

---

## Step 4 — Verify everything works

```bash
# Load your keys
source .env        # Linux / Mac
# or on Windows:
# set -a; . .env; set +a

# Check health
python -m fleet_gateway doctor
```

Expected output:
```
  Groq            ✓ connection OK
  Cerebras        ✓ connection OK

Routing table:
  coding          → cerebras/qwen3-235b, groq/llama3-70b-8192, ...
  general         → cerebras/qwen3-235b, groq/llama-3.3-70b-versatile, ...
  reasoning       → ...
```

---

## Step 5 — Make your first call

**Python:**
```python
import os
os.environ["GROQ_API_KEY"] = "your_key_here"  # or load from .env

from fleet_gateway import call

# Call by capability — routes to best available model automatically
response = call("general", "What is 2+2?")
print(response)
```

**CLI:**
```bash
python -m fleet_gateway call general "What is 2+2?"
```

**As a server (OpenAI-compatible endpoint):**
```bash
python -m fleet_gateway serve
# Now accessible at http://localhost:4000/v1/chat/completions
```

```bash
curl http://localhost:4000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"general","messages":[{"role":"user","content":"Hello!"}]}'
```

---

## Capability aliases

Instead of hardcoding model names, use capability aliases:

| Alias | What it does |
|-------|-------------|
| `general` | Best available general-purpose model |
| `coding` | Best available coding model |
| `reasoning` | Best available reasoning model |
| `fast` | Fastest available model |
| `creative` | Creative writing, brainstorming |
| `translate` | Translation tasks |
| `summarize` | Summarization |

fleet-gateway picks the best backend for each capability and falls back automatically if one is unavailable.

---

## Add more providers later

Edit `.env` and add more keys:

```bash
# .env
GROQ_API_KEY=...
CEREBRAS_API_KEY=...
MISTRAL_API_KEY=...
GEMINI_API_KEY=...
```

Then re-run `python -m fleet_gateway doctor` to verify.

---

## Troubleshooting

**"No response" or connection errors:**
- Check that your key is exported: `echo $GROQ_API_KEY`
- Re-run `python -m fleet_gateway doctor`
- Try a different provider

**"Module not found" errors:**
- Make sure fleet-gateway is installed: `pip install fleet-gateway`
- If using a virtualenv, activate it first

**Rate limit errors:**
- You've hit the free tier limit — wait a minute or switch to another provider
- fleet-gateway will automatically try the next backend in the fallback chain

---

## What's next?

- **Full README**: see [README.md](./README.md) for all features
- **Config file**: see [config.example.yaml](./config.example.yaml) for custom routing
- **Claude Code integration**: see [claude-code/README.md](./claude-code/README.md) for MCP server setup
- **Docker stack**: see [docker/](./docker/) to run gateway + SearXNG + Firecrawl in one command
