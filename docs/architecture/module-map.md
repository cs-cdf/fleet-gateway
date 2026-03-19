# Module Map

Python module dependencies and public API surface of fleet-gateway.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#1a1a2e',
  'primaryTextColor': '#ffffff',
  'primaryBorderColor': '#4ecca3',
  'lineColor': '#4ecca3',
  'clusterBkg': '#16213e',
  'clusterBorder': '#4ecca3',
  'fontFamily': 'Inter, sans-serif',
  'fontSize': '13px'
}}}%%
flowchart TD
    subgraph Public["🌐 Public API"]
        INIT["fleet_gateway<br/><code>__init__.py</code><br/><small>Fleet · call() · load_file<br/>inject_files · suggest_capability</small>"]
    end

    subgraph Core["⚙ Core"]
        ROUTER["router.py<br/><small>Router · _model_index<br/>_backend_cache · _cache_lock<br/>RateLimiter integration</small>"]
        CONFIG["config.py<br/><small>Config · backends dict<br/>routing dict · auto-discovery</small>"]
        RATELIMIT["ratelimit.py<br/><small>RateLimiter<br/>sliding window · thread-safe<br/>stdlib only</small>"]
        SERVER["server.py<br/><small>WSGI HTTP server<br/>POST /v1/chat/completions<br/>GET /v1/models · health</small>"]
    end

    subgraph Backends["🔌 Backends"]
        OAI["backends/openai_compat.py<br/><small>OpenAICompatBackend<br/>CoT extraction · think-tag strip<br/>deprecation detection</small>"]
        ANTHRO["backends/anthropic.py<br/><small>AnthropicBackend<br/>native Messages API<br/>image block conversion</small>"]
    end

    subgraph Extensions["🧩 Extensions"]
        FILES["files.py<br/><small>load_file · inject_files<br/>suggest_capability<br/>path traversal guard</small>"]
        PATTERNS["patterns.py<br/><small>consensus · loop · review<br/>challenge · brainstorm<br/>swot · perspectives · adversarial</small>"]
        MCP["mcp.py<br/><small>llm_call · llm_analyze_files<br/>llm_search · llm_scrape<br/>llm_health · pattern tools</small>"]
        SEARCH["search.py<br/><small>SearXNG integration</small>"]
        SCRAPE["scrape.py<br/><small>Firecrawl integration</small>"]
    end

    INIT --> ROUTER
    INIT --> CONFIG
    INIT --> FILES
    INIT --> PATTERNS
    INIT --> MCP
    INIT --> SERVER

    ROUTER --> CONFIG
    ROUTER --> RATELIMIT
    ROUTER --> OAI
    ROUTER --> ANTHRO

    SERVER --> ROUTER
    SERVER --> CONFIG
    SERVER --> SEARCH
    SERVER --> SCRAPE

    MCP --> ROUTER
    MCP --> FILES
    MCP --> PATTERNS

    PATTERNS --> ROUTER

    OAI --> CONFIG
    ANTHRO --> CONFIG

    style Public    fill:#4ecca3,stroke:#1a1a2e,color:#1a1a2e
    style Core      fill:#1a1a2e,stroke:#4ecca3,stroke-width:2px,color:#fff
    style Backends  fill:#0f3460,stroke:#4ecca3,stroke-width:2px,color:#fff
    style Extensions fill:#16213e,stroke:#4ecca3,stroke-width:2px,color:#fff
```

## Public API Surface

```python
from fleet_gateway import (
    Fleet,             # main class
    call,              # shortcut: call("coding", messages)
    load_file,         # load a file → OpenAI content block
    files_to_blocks,   # list of paths → list of blocks
    inject_files,      # inject blocks into last user message
    suggest_capability # "vision" / "coding" / "general" by file type
)
```

## Key Internal Contracts

| Interface | Contract |
|-----------|---------|
| `Router.call()` | Returns `str` or `None`; never raises on backend errors |
| `RateLimiter.acquire(timeout)` | Returns `True` (slot acquired) or `False` (timed out) |
| `Backend.call()` | Returns `str` or `None`; all exceptions caught internally |
| `inject_files()` | Returns new list; input `messages` is **never mutated** |
| `load_file()` | Raises `FileNotFoundError` or `ValueError` on bad input; caller decides |
