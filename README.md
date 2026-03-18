# fleet-gateway

> Part of the **[FlowState](https://github.com/claudiosesto2021)** ecosystem — a personal productivity and AI system designed and built by [Claudio Sesto](https://github.com/claudiosesto2021).
> FlowState is a comprehensive framework integrating LLM infrastructure, knowledge management (Zettelkasten), multi-agent reasoning patterns, Claude Code tooling, and production-grade AI workflows.
> fleet-gateway is its open-sourced LLM routing layer, extracted and generalized for anyone to use.

---

Lightweight OpenAI-compatible LLM gateway with smart routing, fallback chains, and optional web tools.

**No local hardware required.** Start with free cloud APIs, add local models when you're ready.

> **New here?** → See **[QUICKSTART.md](./QUICKSTART.md)** for a step-by-step setup guide.
> **Note:** To run any LLM calls you need at least one API key from a supported provider.
> Several offer generous free tiers — no credit card required. The setup wizard handles this:
> ```bash
> pip install fleet-gateway
> python -m fleet_gateway setup
> ```

```
        You / Your App
             │
             │  OpenAI-compatible API
             ▼
      fleet-gateway :4000
             │
     ┌───────┴───────┐
     │   Routing     │  "coding" → try Cerebras first, then Groq, then Mistral...
     └───────┬───────┘
             │
    ┌────────┼────────┬────────┐
    ▼        ▼        ▼        ▼
  Groq    Cerebras  Mistral  (your local GPU)
  (free)  (free)    (free)
```

---

## Features

- **OpenAI-compatible API** — drop-in for any tool that uses OpenAI
- **Capability routing** — `"coding"`, `"general"`, `"translate"` auto-select the best available model
- **Fallback chains** — if a backend fails, tries the next one automatically
- **Progressive setup** — works with just env vars, no config file needed
- **Zero mandatory deps** — stdlib-only core, optional extras for specific features
- **Web search** — optional SearXNG integration (self-hosted, no API key)
- **Web scraping** — optional Firecrawl integration (self-hosted or cloud)
- **Claude Code MCP** — expose all capabilities as MCP tools
- **Docker-compose** — full stack in one command

---

## Provider Details

Detailed breakdown of what you get with each provider.

### Cerebras — Best for speed
- **Sign up**: https://cloud.cerebras.ai
- **Free tier**: 1,000,000 tokens/day — no credit card needed
- **Key env var**: `CEREBRAS_API_KEY`
- **Models available**:
  - `qwen-3-235b-a22b-instruct-2507` — 235B MoE, ~2600 t/s (!), best quality, 8192 ctx
  - `llama3.1-8b` — fast, lightweight, 8192 ctx
- **Best for**: any task where speed matters; hooks, classification, summaries
- **Limits**: 1M tok/day, 30 req/min
- **Notes**: Cerebras uses custom silicon (wafer-scale), not GPUs — hence extraordinary speed

### Groq — Best free general model
- **Sign up**: https://console.groq.com
- **Free tier**: 30 req/min on most models — no credit card needed
- **Key env var**: `GROQ_API_KEY`
- **Models available**:
  - `llama-3.3-70b-versatile` — 70B, 128K ctx, best quality on Groq
  - `llama3-70b-8192` — 70B, 8K ctx, slightly faster
  - `llama3-8b-8192` — 8B, very fast
  - `gemma2-9b-it` — Google Gemma 9B
  - `mixtral-8x7b-32768` — Mixtral 8x7B, 32K ctx
- **Best for**: general tasks, translation, summarization
- **Limits**: 6,000 tok/min on free tier, 30 req/min
- **Notes**: Very stable API, good Italian capability with Llama 3.3

### SambaNova — Best quality/free ratio
- **Sign up**: https://cloud.sambanova.ai
- **Free tier**: 10 req/min — no credit card needed
- **Key env var**: `SAMBANOVA_API_KEY`
- **Models available**:
  - `Qwen3-235B` — 235B MoE, excellent quality, 8192 ctx
  - `DeepSeek-V3.2` — 671B MoE, 65K ctx, strong coder
  - `Meta-Llama-3.3-70B-Instruct` — 70B, 32K ctx
  - `Qwen3-32B` — 32B dense, strong reasoning
- **Best for**: quality tasks where you can tolerate 10 req/min limit
- **Limits**: 10 req/min
- **Notes**: SambaNova RDU hardware, comparable to Cerebras for quality at different model sizes

### Mistral — Best for European languages
- **Sign up**: https://console.mistral.ai
- **Free tier**: "Experiment" plan — 2 req/min, 1B tok/month — no credit card
- **Key env var**: `MISTRAL_API_KEY`
- **Models available** (all included in Experiment plan):
  - `mistral-large-latest` — 123B, 128K ctx, excellent Italian/French/Spanish
  - `codestral-latest` — 22B dedicated coding model, 256K ctx
  - `mistral-small-latest` — 22B balanced, fast
  - `mistral-ocr-latest` — state-of-the-art document OCR
- **Best for**: Italian proofreading, multilingual, code generation
- **Limits**: 2 req/min on free tier (upgrade for more); data may be used for training on free plan
- **Notes**: Best-in-class for Italian and French text quality

### Google Gemini — Best for multimodal + long context
- **Sign up (AI Studio, free)**: https://aistudio.google.com → "Get API key"
- **Sign up (Vertex AI, paid/enterprise)**: https://console.cloud.google.com
- **Free tier (AI Studio)**: 15 req/min, 1M tok/day — no credit card for basic tier
- **Key env var**: `GEMINI_API_KEY`
- **Models available**:
  - `gemini-2.5-flash` — fast, multimodal, 1M ctx, vision+audio+video
  - `gemini-2.5-pro` — best quality, 2M ctx, complex reasoning (limited free tier)
  - `gemini-2.0-flash` — fast, multimodal
- **Best for**: long documents, vision tasks, audio transcription, complex reasoning
- **Limits**: 15 req/min free (Flash), 2 req/min free (Pro); generous paid tier
- **Google Workspace / Business**: Use the same `GEMINI_API_KEY` from AI Studio, or set up a GCP project for Vertex AI access with better SLAs and data residency controls
- **Notes**: Only model with 2M context window; native multimodal (images, audio, video)

### OpenRouter — Access to many models through one key
- **Sign up**: https://openrouter.ai
- **Free tier**: 50 req/day (free models), 20 req/min — no credit card for free models
- **Key env var**: `OPENROUTER_API_KEY`
- **Free models available** (`:free` suffix):
  - `qwen/qwen3-coder:free` — 480B MoE, strongest free coder, 262K ctx
  - `nousresearch/hermes-3-llama-3.1-405b:free` — 405B dense, excellent all-rounder
  - `mistralai/mistral-small-3.1-24b-instruct:free` — 24B, strong Italian/multilingual
  - `meta-llama/llama-3.3-70b-instruct:free` — 70B versatile
  - `deepseek/deepseek-r1:free` — 671B reasoning model
  - `google/gemma-3-27b-it:free` — 27B, vision, good Italian
- **Paid models** (add credits): Mistral Large ($0.50/M), Qwen3.5-Flash ($0.10/M)
- **Best for**: accessing free versions of large models; fallback chain
- **Limits**: 50 req/day free; 1000 req/day with ≥$10 credits

### NVIDIA NIM — High-quality models with generous free tier
- **Sign up**: https://build.nvidia.com → "Get API Key"
- **Free tier**: 1000 API calls/month — no credit card
- **Key env var**: `NVIDIA_API_KEY`
- **Models available**:
  - `nvidia/nemotron-3-super-120b-a12b` — 120B, thinking model, 131K ctx
  - `qwen/qwen3.5-122b-a10b` — 122B MoE, thinking model, 131K ctx
  - `nvidia/llama-3.3-nemotron-super-49b-v1` — 49B, strong reasoning+tools
  - `nvidia/llama-3.1-nemotron-70b-instruct` — 70B instruct, high quality
- **Best for**: complex reasoning, agentic tasks; using up free quota for heavy tasks
- **Limits**: 1000 calls/month total (use wisely — save for complex tasks)
- **Notes**: Thinking models require `enable_thinking` parameter via `extra_body`

### OpenAI (paid)
- **Sign up**: https://platform.openai.com → API keys
- **Free credits**: $5 on signup (expires after 3 months)
- **Key env var**: `OPENAI_API_KEY`
- **Models**: GPT-4o ($5/$15 MTok), GPT-4o-mini ($0.15/$0.6 MTok), o1, o3-mini
- **Best for**: vision, function calling, widest ecosystem compatibility

### Anthropic Claude (paid)
- **Sign up**: https://console.anthropic.com → API keys
- **Key env var**: `ANTHROPIC_API_KEY`
- **Models**: Claude Sonnet 4.6 ($3/$15 MTok), Claude Haiku 4.5 ($1/$5 MTok), Claude Opus 4.6 ($5/$25 MTok)
- **Best for**: complex reasoning, editorial work, long documents (200K ctx)
- **Notes**: Uses a different API format (handled transparently by fleet-gateway)

---

## Quickstart (5 minutes)

### 1. Get a free API key

Pick any one (or more). All services below have free tiers — no credit card required to start.

#### Free Tier Providers

| Provider | Sign-up | Free Quota | Best Models | Best For |
|----------|---------|------------|-------------|----------|
| **Cerebras** | [cloud.cerebras.ai](https://cloud.cerebras.ai) | 1M tok/day | Qwen3-235B (2600 t/s!) | Fastest inference, coding, reasoning |
| **Groq** | [console.groq.com](https://console.groq.com) | 30 req/min | Llama 3.3 70B | Fast general-purpose |
| **SambaNova** | [cloud.sambanova.ai](https://cloud.sambanova.ai) | 10 req/min | Qwen3-235B, DeepSeek V3.2 | Quality tasks, reasoning |
| **Mistral** | [console.mistral.ai](https://console.mistral.ai) | 2 req/min, 1B tok/month | Mistral Large, Codestral | Italian, French, coding |
| **Google AI Studio (Gemini)** | [aistudio.google.com](https://aistudio.google.com) | 15 req/min, 1M tok/day | Gemini 2.5 Flash, Gemini 2.5 Pro | Multimodal, long context, vision |
| **OpenRouter** | [openrouter.ai](https://openrouter.ai) | 50 req/day free | Qwen3-Coder, Hermes 405B, Mistral | Access to many free models |
| **NVIDIA NIM** | [build.nvidia.com](https://build.nvidia.com) | 1000 API calls/month | Nemotron 120B, Qwen3.5-122B | Top-tier reasoning, coding |

#### Paid Providers (optional)

| Provider | Sign-up | Pricing | Best Models | Best For |
|----------|---------|---------|-------------|----------|
| **Google Gemini** (Business) | [console.cloud.google.com](https://console.cloud.google.com) | Pay-per-use | Gemini 2.5 Pro/Flash | Long context, multimodal, Google Workspace integration |
| **OpenAI** | [platform.openai.com](https://platform.openai.com) | Pay-per-use | GPT-4o, GPT-4o-mini | General excellence |
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com) | Pay-per-use | Claude Sonnet/Haiku/Opus | Code, analysis, editorial |

#### Google Workspace / Google for Business

If you already have Google Workspace, you get access to Gemini via:
1. **AI Studio** (personal): [aistudio.google.com](https://aistudio.google.com) → API Keys → Create key
2. **Vertex AI** (enterprise, GCP): more control, SLAs, data residency → use `GEMINI_API_KEY` from GCP project
3. **Gemini for Workspace**: integrated in Gmail/Docs/Sheets — separate from the API

For programmatic access, use **AI Studio** (easiest) or **Vertex AI** (production).
The `GEMINI_API_KEY` from AI Studio works directly with fleet-gateway.

### 2. Install

```bash
pip install fleet-gateway
```

### 3. Use it

**Option A — Module-level functions (simplest)**

```python
import os
os.environ["GROQ_API_KEY"] = "your_key_here"

from fleet_gateway import call

# Call by capability — tries the best available model automatically
response = call("coding", "Write a Python hello world")
print(response)

# Or use a specific model
response = call("groq/llama-3.3-70b-versatile", "What is 2+2?")
```

**Option B — Fleet instance**

```python
from fleet_gateway import Fleet

fleet = Fleet()  # reads from env vars or config.yaml

response = fleet.call("general", "Explain async programming in Python")
print(response)
```

**Option C — Start the gateway server, use with any OpenAI client**

```bash
export GROQ_API_KEY=your_key_here
python -m fleet_gateway.server
```

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:4000/v1", api_key="dummy")
response = client.chat.completions.create(
    model="coding",   # capability alias → routes to best available
    messages=[{"role": "user", "content": "Write a Python hello world"}]
)
print(response.choices[0].message.content)
```

```bash
# Or with curl
curl http://localhost:4000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"general","messages":[{"role":"user","content":"What is 2+2?"}]}'
```

---

## Configuration

### Env-vars only (no config file)

Set API keys as env vars. The gateway auto-discovers available backends:

```bash
export GROQ_API_KEY=...
export CEREBRAS_API_KEY=...
export MISTRAL_API_KEY=...
export GEMINI_API_KEY=...
# etc.

python -m fleet_gateway.server
```

### Config file

For custom routing, models, or tool URLs, create a `config.yaml`:

```yaml
# config.yaml
backends:
  groq:
    type: openai_compat
    url: https://api.groq.com/openai/v1
    api_key_env: GROQ_API_KEY
    models:
      - id: llama-3.3-70b-versatile
        capabilities: [general, translate, summarize]

  # Your local Ollama instance
  ollama:
    type: openai_compat
    url: http://localhost:11434/v1
    api_key: ollama
    models:
      - id: llama3.1
        capabilities: [general, coding]

routing:
  coding:
    - ollama/llama3.1        # prefer local
    - groq/llama-3.3-70b-versatile  # fallback to cloud
```

```python
from fleet_gateway import Fleet
fleet = Fleet("config.yaml")
response = fleet.call("coding", "Write a hello world")
```

See `config.example.yaml` for the full reference with all supported providers.

---

## Capability Aliases

| Alias | Description |
|-------|-------------|
| `coding` | Code generation, debugging, code review |
| `general` | General-purpose Q&A |
| `reasoning` | Step-by-step reasoning, math, logic |
| `translate` | Text translation |
| `proofread` | Grammar, style, Italian proofreading |
| `summarize` | Text summarization |
| `creative` | Creative writing, brainstorming |
| `fast` | Quick tasks, classification |
| `italian` | Italian-language tasks |
| `vision` | Image understanding (requires multimodal model) |

---

## Supported Backends

### Free Cloud APIs (no hardware needed)

| Provider | Type | Key |
|----------|------|-----|
| Groq | openai_compat | `GROQ_API_KEY` |
| Cerebras | openai_compat | `CEREBRAS_API_KEY` |
| SambaNova | openai_compat | `SAMBANOVA_API_KEY` |
| Mistral | openai_compat | `MISTRAL_API_KEY` |
| Gemini | openai_compat | `GEMINI_API_KEY` |
| OpenRouter | openai_compat | `OPENROUTER_API_KEY` |
| NVIDIA NIM | openai_compat | `NVIDIA_API_KEY` |

### Paid Cloud APIs

| Provider | Type | Key |
|----------|------|-----|
| OpenAI | openai_compat | `OPENAI_API_KEY` |
| Anthropic Claude | anthropic | `ANTHROPIC_API_KEY` |

### Local Models (when you have hardware)

Any OpenAI-compatible local server works:

```yaml
backends:
  ollama:
    type: openai_compat
    url: http://localhost:11434/v1
    api_key: ollama

  llama_cpp:
    type: openai_compat
    url: http://localhost:8080/v1

  lm_studio:
    type: openai_compat
    url: http://localhost:1234/v1
    api_key: lm-studio

  vllm:
    type: openai_compat
    url: http://my-gpu-server:8000/v1
```

---

## Web Tools (Optional)

### SearXNG — Web Search

Self-hosted privacy search. No API key. Aggregates 80+ search engines.

```bash
# Start SearXNG
docker run -d -p 8888:8080 searxng/searxng

# Set env var
export SEARXNG_URL=http://localhost:8888
```

```python
from fleet_gateway import Fleet, search

fleet = Fleet()
results = fleet.search("Python async best practices", num_results=5)
for r in results:
    print(r["title"], r["url"])

# Or module-level:
results = search("latest AI news")
```

### Firecrawl — Web Scraping

Converts any URL to clean Markdown. Handles JS, PDFs, paywalls.

```bash
# Self-hosted (no API key needed)
cd docker && docker compose up firecrawl-api redis -d

# Or use cloud (free tier at firecrawl.dev)
export FIRECRAWL_URL=https://api.firecrawl.dev
export FIRECRAWL_API_KEY=your_key
```

```python
from fleet_gateway import Fleet, scrape

fleet = Fleet()
content = fleet.scrape("https://docs.python.org/3/library/asyncio.html")
print(content[:500])  # Clean markdown

# Or module-level:
content = scrape("https://example.com")
```

---

## Full Stack with Docker

Starts gateway + SearXNG + Firecrawl in one command:

```bash
cd docker
cp .env.example .env
# Edit .env: add at least one API key
docker compose up -d

# Verify
curl http://localhost:4000/health
```

Services:
- `http://localhost:4000` — fleet-gateway (OpenAI-compatible)
- `http://localhost:8888` — SearXNG (web search)
- `http://localhost:3002` — Firecrawl (web scraping)

---

## Claude Code Integration

fleet-gateway ships with a full Claude Code integration package in the [`claude-code/`](./claude-code/) directory:

```
claude-code/
├── README.md                  # full setup instructions
├── settings_snippet.json      # paste into ~/.claude/settings.json
├── commands/                  # slash commands (skills)
│   ├── fleet-review.md        # /fleet-review
│   ├── fleet-consensus.md     # /fleet-consensus
│   ├── fleet-loop.md          # /fleet-loop
│   ├── fleet-challenge.md     # /fleet-challenge
│   ├── fleet-brainstorm.md    # /fleet-brainstorm
│   ├── fleet-swot.md          # /fleet-swot
│   ├── fleet-perspectives.md  # /fleet-perspectives
│   └── fleet-adversarial.md   # /fleet-adversarial
└── hooks/
    └── README.md              # PostToolUse hook examples
```

### MCP Server

Add fleet-gateway as an MCP server to get all capabilities directly in Claude Code.

Add to your `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "fleet": {
      "command": "python",
      "args": ["-m", "fleet_gateway.mcp"],
      "env": {
        "GROQ_API_KEY": "your_key_here",
        "CEREBRAS_API_KEY": "your_key_here",
        "SEARXNG_URL": "http://localhost:8888"
      }
    }
  }
}
```

Install with MCP support:
```bash
pip install fleet-gateway[mcp]
```

**Available MCP tools in Claude Code:**

| Tool | Description |
|------|-------------|
| `llm_call` | Call any model or capability alias |
| `llm_search` | Web search via SearXNG |
| `llm_scrape` | Scrape URLs via Firecrawl |
| `llm_models` | List available models and status |
| `llm_health` | Check gateway health |
| `llm_consensus` | Multi-model consensus answer |
| `llm_review` | Multi-model structured review |
| `llm_challenge` | Devil's advocate analysis |
| `llm_loop` | Iterative generate→critique→improve |
| `llm_brainstorm` | Multi-model idea generation |
| `llm_swot` | SWOT analysis |
| `llm_perspectives` | Multi-expert viewpoints |

### Slash Commands (Skills)

Copy the skills to your Claude Code commands directory:

```bash
# Global — available in all projects
cp claude-code/commands/*.md ~/.claude/commands/

# Project-local — available only in this project
mkdir -p .claude/commands
cp claude-code/commands/*.md .claude/commands/
```

Then type `/fleet-` in Claude Code to see all available commands:

| Command | Description |
|---------|-------------|
| `/fleet-review [file or code]` | 3 models review in parallel → synthesized report |
| `/fleet-consensus [question]` | Same question to N models → consensus answer |
| `/fleet-loop [task]` | Generate → critique → improve × 3 cycles |
| `/fleet-challenge [idea]` | Devil's advocate: stress-test an idea or plan |
| `/fleet-brainstorm [topic]` | Multi-model ideation with deduplication and ranking |
| `/fleet-swot [subject]` | Full SWOT analysis with strategic implications |
| `/fleet-perspectives [topic]` | Pragmatist / critic / strategist / specialist viewpoints |
| `/fleet-adversarial [claim]` | Structured attacker vs defender debate with verdict |

**Example usage:**

```
/fleet-review src/auth.py
/fleet-consensus Is Rust better than Go for CLI tools?
/fleet-loop Write a Python quicksort with good error handling
/fleet-challenge We should rewrite everything in microservices
/fleet-brainstorm Ways to reduce onboarding time for new engineers
/fleet-swot Adopting Rust for our backend services
/fleet-perspectives Remote-first vs office-first teams
/fleet-adversarial AI will replace most software developers within 5 years
```

All commands use **capability aliases** (`coding`, `reasoning`, `general`) — no hardcoded endpoints or model names. Swap backends in `config.yaml` without touching any skill file.

See [`claude-code/README.md`](./claude-code/README.md) for full setup and customization instructions.

---

## Prompt Templates

The [`templates/`](./templates/) directory contains ready-to-use prompt templates for all multi-model patterns. These can be customized and used directly in your own applications or scripts.

| Template | Use case |
|----------|----------|
| [`consensus.md`](./templates/consensus.md) | Ask N models the same question, synthesize answers |
| [`loop_refine.md`](./templates/loop_refine.md) | Iterative generation + critique + improvement |
| [`review_code.md`](./templates/review_code.md) | Structured code review: bugs, style, security, perf |
| [`review_text.md`](./templates/review_text.md) | Document/text review: clarity, structure, completeness |
| [`challenge.md`](./templates/challenge.md) | Devil's advocate: find flaws in a plan or argument |
| [`brainstorm.md`](./templates/brainstorm.md) | Divergent ideation with deduplication and ranking |
| [`swot.md`](./templates/swot.md) | Full SWOT with strategic implications |
| [`perspectives.md`](./templates/perspectives.md) | Multiple expert personas analyzing the same topic |
| [`adversarial.md`](./templates/adversarial.md) | Structured attacker vs defender, 2 rounds + verdict |

Each template includes the system prompt, user prompt structure, and instructions for customization.

---

## Progressive Setup Guide

Start simple, add capabilities as needed:

### Stage 1 — Cloud only (0 hardware, 5 min setup)

```bash
pip install fleet-gateway
export GROQ_API_KEY=...        # free at https://console.groq.com
export CEREBRAS_API_KEY=...    # free at https://cloud.cerebras.ai
python -c "from fleet_gateway import call; print(call('general', 'Hello!'))"
```

### Stage 2 — Add web search (10 min)

```bash
docker run -d -p 8888:8080 searxng/searxng
export SEARXNG_URL=http://localhost:8888
python -c "from fleet_gateway import search; print(search('Python tips'))"
```

### Stage 3 — Add web scraping (15 min)

```bash
cd docker && docker compose up firecrawl-api redis -d
export FIRECRAWL_URL=http://localhost:3002
python -c "from fleet_gateway import scrape; print(scrape('https://example.com')[:200])"
```

### Stage 4 — Run as a server (20 min)

```bash
python -m fleet_gateway.server
# Now any OpenAI-compatible tool can use it
```

### Stage 5 — Add local models (when you have a GPU)

Install Ollama, pull a model, add to config.yaml:

```bash
ollama pull llama3.1
```

```yaml
# config.yaml
backends:
  ollama:
    type: openai_compat
    url: http://localhost:11434/v1
    api_key: ollama
    models:
      - id: llama3.1
        capabilities: [general, coding]

routing:
  coding:
    - ollama/llama3.1        # local first
    - cerebras/qwen3-235b   # cloud fallback
```

### Stage 6 — Claude Code MCP

```bash
pip install fleet-gateway[mcp]
# Add to ~/.claude/settings.json (see above)
```

---

## API Reference

### Python API

```python
from fleet_gateway import Fleet, call, search, scrape, models, capabilities

# Fleet instance (more control)
fleet = Fleet()
fleet = Fleet("config.yaml")
fleet = Fleet({"backends": {...}, "routing": {...}})

# LLM calls
response = fleet.call("coding", "Write hello world")
response = fleet.call("general", [{"role": "user", "content": "What is 2+2?"}])
response = fleet.call("groq/llama-3.3-70b-versatile", "Hello")
response = fleet.call("coding", "...", system="You are a senior Python developer")
response = fleet.call("coding", "...", max_tokens=4096, temperature=0.2)

# Web tools
results = fleet.search("query", num_results=5)
content = fleet.scrape("https://example.com")

# Introspection
models_list = fleet.models()    # [{id, backend, capabilities, available}, ...]
caps = fleet.capabilities()     # {"coding": ["groq/...", "cerebras/..."], ...}
health = fleet.health()         # {status, models_available, searxng, firecrawl}

# Module-level shortcuts (use default Fleet from env vars)
response = call("coding", "hello world")
results  = search("python tips")
content  = scrape("https://example.com")
```

### HTTP API

```
POST /v1/chat/completions     — OpenAI-compatible LLM call
GET  /v1/models               — List configured models and capabilities
GET  /v1/capabilities         — Show routing table
GET  /health                  — Gateway health check
POST /v1/search               — Web search (SearXNG)
POST /v1/scrape               — Web scraping (Firecrawl)
```

**Search request:**
```json
POST /v1/search
{"query": "Python async tips", "num_results": 5}
```

**Scrape request:**
```json
POST /v1/scrape
{"url": "https://docs.python.org/3/library/asyncio.html"}
```

### Multi-Model Patterns API

```python
from fleet_gateway import Fleet

fleet = Fleet()

# Consensus — ask N models, get synthesized answer
result = fleet.consensus("Is GraphQL worth the complexity?", n=3)
print(result["synthesis"])

# Loop — iterative refinement
result = fleet.loop("Write a Python quicksort", iterations=3)
print(result["final"])

# Review — structured multi-model review
result = fleet.review(code_string, content_type="code", n=3)
print(result["synthesis"])   # synthesized report
print(result["reviews"])     # individual model reviews

# Challenge — devil's advocate
result = fleet.challenge("We should migrate to microservices", depth="thorough")
print(result["challenge"])

# Brainstorm — multi-model idea generation
result = fleet.brainstorm("New features for a developer CLI", n=3)
print(result["synthesis"])   # deduplicated + ranked ideas
print(result["raw_ideas"])   # per-model raw output

# SWOT analysis
result = fleet.swot("Adopting Rust for our backend", context="We are a 5-person startup")
print(result["analysis"])
print(result["swot"])   # {"strengths": ..., "weaknesses": ..., ...}

# Perspectives — multi-expert viewpoints
result = fleet.perspectives("Remote-first vs office-first", viewpoints=["pragmatist", "skeptic", "strategist"])
print(result["synthesis"])
print(result["perspectives"])   # per-viewpoint responses

# Adversarial — attacker vs defender debate
result = fleet.adversarial("AI will replace most software developers within 5 years")
print(result["verdict"])
print(result["rounds"])   # full debate transcript
```

All patterns are also available as module-level shortcuts:
```python
from fleet_gateway import consensus, loop, review, challenge, brainstorm, swot, perspectives, adversarial
```

---

## Installation Options

```bash
# Core (no external deps)
pip install fleet-gateway

# With YAML config file support
pip install fleet-gateway[yaml]

# With MCP server (Claude Code integration)
pip install fleet-gateway[mcp]

# Everything
pip install fleet-gateway[all]
```

---

## License

MIT
