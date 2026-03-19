# Changelog

All notable changes to fleet-gateway are documented here.

Format: [Semantic Versioning](https://semver.org/) — `MAJOR.MINOR.PATCH`

---

## [0.3.3] — 2026-03-19

### Reliability — Thread safety, O(1) routing, deep copy fix, standard logging

**`router.py`**
- Add `_cache_lock` (`threading.Lock`) protecting `_backend_cache` and `_limiters` dict
  writes; uses double-checked locking — eliminates race condition under concurrent load
- Pre-build `_model_index` (`{model_id: backend_name}`) at init time: bare model-ID
  lookup is now O(1) instead of O(N×M) per request
- Replace `_log` / `print(sys.stderr)` with `logging.getLogger(__name__)` — messages are
  filterable via standard Python logging infrastructure

**`files.py`**
- `inject_files`: replace `[dict(msg) for msg in messages]` shallow copy with
  `copy.deepcopy(messages)` — prevents nested `content` list mutations bleeding back
  into the caller's messages

**`tests/test_basic.py`** — 34 tests total (+4 new)
- `test_model_index_built_at_init`, `test_cache_lock_exists`,
  `test_concurrent_get_backend_no_crash`, `test_inject_files_deep_copy_no_mutation`

### Documentation — Architecture folder

**`docs/architecture/`** (new)
- `README.md` — architecture landing page
- `system-overview.md` — styled component map with Mermaid theming (dark navy/teal)
- `request-flow.md` — autonumbered sequence diagram showing rate limiting, fallback
  chain, and CoT normalization
- `routing-logic.md` — color-coded flowchart including O(1) model index step
- `module-map.md` — Python module dependency graph with public API contracts

**`README.md`**
- Architecture section replaced with compact inline diagram + link table to `docs/architecture/`
- Added Documentation index table at end of file

---

## [0.3.2] — 2026-03-19

### New Features — Cloud model deprecation detection

**`backends/openai_compat.py` — inline deprecation check**
- When a cloud request fails with HTTP 404/410 or a body matching deprecation patterns
  (e.g. "deprecated", "no longer available", "invalid model"), a background thread
  automatically runs `fleet_model_checker.run_check()` for that provider
- Check is debounced per provider (at most once per hour) to avoid hammering the API
- Sends a Telegram alert if issues are found (requires `TELEGRAM_BOT_TOKEN` + `TELEGRAM_ADMIN_CHAT_ID`)
- Graceful degradation: if `fleet_model_checker` is not importable, the feature is silently skipped

---

## [0.3.1] — 2026-03-19

### Bug Fixes — CoT (Chain-of-Thought) extraction

**`backends/openai_compat.py` — `_extract_content()` priority fix**
- Old code: `text = content or reasoning_content or reasoning` — wrong priority caused raw
  thinking to leak as the answer when `content` was empty (e.g. deepseek model hit `max_tokens`
  mid-reasoning)
- New priority: `content` → `reasoning` (vLLM clean answer field) → `reasoning_content`
  (Cogito/Apriel answer, or deepseek raw thinking as last resort)
- This matches vLLM's `--reasoning-parser qwen3` behavior: thinking goes to `reasoning`,
  clean answer goes to `content`; when `content` is null vLLM puts the answer in `reasoning`

**`_strip_think_tags()` — unclosed tag handling**
- Old code: only stripped complete `<think>...</think>` blocks; an unclosed `<think>` (model
  truncated mid-reasoning) would leak raw thinking verbatim
- New code: if a `<think>` has no matching `</think>`, everything from the tag onward is
  discarded — raw thinking never appears in the output

**`tests/test_basic.py` — extended CoT coverage**
- Added 11 new `TestExtractContent` cases covering: vLLM `reasoning` field, content priority,
  think-tag stripping, unclosed tags, deepseek empty-content pattern

---

## [0.3.0] — 2026-03-18

### Reliability & Security

**Rate limiting — per-provider sliding window**
- New module `fleet_gateway/ratelimit.py` — thread-safe sliding-window `RateLimiter`
- Configured per backend via `rate_limit: <req/min>` in `config.yaml`:
  ```yaml
  backends:
    groq:
      rate_limit: 30   # free tier: 30 req/min
    gemini:
      rate_limit: 15
    mistral:
      rate_limit: 2    # Free Experiment plan
  ```
- When a backend is at capacity the router skips it immediately (non-blocking) and tries the next fallback — no request stall

**Path traversal fix + size guards (`fleet_gateway/files.py`)**
- `load_file()` now calls `Path(path).resolve()` — eliminates `../` traversal and symlink escapes before any file is opened
- Size guards: images capped at 50 MB, text/code at 10 MB; raises `ValueError` on violation

**CI/CD — GitHub Actions**
- `.github/workflows/test.yml`: runs `pytest` on every push/PR across Python 3.9, 3.10, 3.11, 3.12

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

[0.3.0]: https://github.com/cs-cdf/fleet-gateway/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/cs-cdf/fleet-gateway/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/cs-cdf/fleet-gateway/releases/tag/v0.1.0
