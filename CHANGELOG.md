# Changelog

All notable changes to fleet-gateway are documented here.

Format: [Semantic Versioning](https://semver.org/) — `MAJOR.MINOR.PATCH`

---

## [0.2.0] — 2026-03-18

### File Attachment Support (Phase 1)

**New module: `fleet_gateway.files`**
- `load_file(path)` — load a local file and return an OpenAI-compatible content block
  - Images (PNG, JPEG, GIF, WEBP) → `image_url` block with base64 data URI
  - Text/code (50+ extensions) → `text` block prefixed with filename
  - PDF → extracted text via `pypdf` (optional); placeholder if not installed
  - Unknown binary → `[binary file: name, N bytes]` placeholder
- `files_to_blocks(files)` — convert a list of paths; skips missing files with a warning
- `inject_files(messages, files)` — inject blocks into the last user message; returns a new list (no mutation)
- `suggest_capability(files)` — auto-select `vision` / `coding` / `general` by file type

**`Fleet.call()` — new `files=` parameter**
```python
fleet.call("vision", "Describe this diagram", files=["arch.png"])
fleet.call("coding", "Review for security issues", files=["src/auth.py"])
fleet.call("general", "Summarize these", files=["report.pdf", "notes.md"])
```

**`backends/anthropic.py` — transparent format conversion**
- `_to_anthropic_content()`: converts OpenAI `image_url` blocks to Anthropic `image/source` format automatically — callers use the same API regardless of backend

**`mcp.py` — Claude Code MCP tools**
- `llm_call`: new `files` parameter — pass file paths instead of reading file content yourself
- `llm_analyze_files` (new tool): auto-routes to `vision`/`coding`/`general` based on file types when `model="auto"`

**Public API exports** — importable from `fleet_gateway` directly:
```python
from fleet_gateway import load_file, files_to_blocks, inject_files, suggest_capability
```

---

## [0.1.0] — 2026-03-18

### Initial release

**Core**
- OpenAI-compatible HTTP gateway server (`python -m fleet_gateway.server`)
- Capability-based routing: `coding`, `general`, `reasoning`, `translate`, `proofread`, `summarize`, `creative`, `fast`, `italian`, `vision`
- Fallback chains: tries next backend on failure, automatically
- Zero mandatory dependencies (stdlib-only core)
- Progressive config: env vars → config.yaml → auto-discovery
- YAML config support (PyYAML optional, fallback minimal parser included)

**Backends**
- `openai_compat` — works with: local llama.cpp, vLLM, Ollama, LM Studio, Groq, Cerebras, SambaNova, Mistral, NVIDIA NIM, OpenRouter, OpenAI, Gemini (OpenAI compat), and any `/v1/chat/completions` endpoint
- `anthropic` — native Anthropic Messages API (handles format translation)
- Auto-discovery from env vars: GROQ, CEREBRAS, SAMBANOVA, MISTRAL, GEMINI, OPENAI, ANTHROPIC, OPENROUTER, NVIDIA

**Web Tools**
- SearXNG integration: `fleet.search()`, `POST /v1/search`
- Firecrawl integration: `fleet.scrape()`, `POST /v1/scrape` (v0 and v1 API)

**Multi-model Patterns** (`fleet.patterns.*`)
- `consensus` — ask N models, synthesize answer
- `loop` — iterative generate→critique→improve refinement
- `review` — multi-model structured review (code, text, document, plan, essay)
- `challenge` — devil's advocate (quick / thorough / deep)
- `brainstorm` — multi-model idea generation with deduplication
- `swot` — SWOT analysis with section parsing
- `perspectives` — expert viewpoints with assignable roles
- `adversarial` — structured attacker vs defender debate

**Claude Code Integration**
- MCP server: `llm_call`, `llm_search`, `llm_scrape`, `llm_models`, `llm_health`, pattern tools
- Skills: `/fleet-review`, `/fleet-consensus`, `/fleet-loop`, `/fleet-challenge`, `/fleet-brainstorm`, `/fleet-swot`, `/fleet-perspectives`, `/fleet-adversarial`
- Prompt templates for each pattern in `templates/`

**Infrastructure**
- Docker-compose: gateway + SearXNG + Firecrawl + Redis
- `config.example.yaml` with all providers documented
- `.env.example` with signup links and free tier info
- `pyproject.toml` with optional extras: `[yaml]`, `[mcp]`, `[server]`, `[all]`

---

[0.2.0]: https://github.com/cs-cdf/fleet-gateway/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/cs-cdf/fleet-gateway/releases/tag/v0.1.0
