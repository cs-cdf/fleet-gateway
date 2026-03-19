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
        INIT["fleet_gateway.__init__<br>Fleet · call · load_file<br>inject_files · suggest_capability"]
    end

    subgraph Core["⚙ Core"]
        ROUTER["router.py<br>Router · _model_index<br>_backend_cache · _cache_lock"]
        CONFIG["config.py<br>Config · backends · routing<br>auto-discovery"]
        RATELIMIT["ratelimit.py<br>RateLimiter<br>sliding window · stdlib only"]
        SERVER["server.py<br>WSGI server<br>POST /v1/chat/completions"]
    end

    subgraph Backends["🔌 Backends"]
        OAI["openai_compat.py<br>OpenAICompatBackend<br>CoT extraction · deprecation"]
        ANTHRO["anthropic.py<br>AnthropicBackend<br>native API · image conversion"]
    end

    subgraph Extensions["🧩 Extensions"]
        FILES["files.py<br>load_file · inject_files<br>path traversal guard"]
        PATTERNS["patterns.py<br>consensus · loop · review<br>challenge · brainstorm · swot"]
        MCP["mcp.py<br>llm_call · llm_analyze_files<br>llm_search · llm_health"]
        SEARCH["search.py<br>SearXNG integration"]
        SCRAPE["scrape.py<br>Firecrawl integration"]
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

    style Public     fill:#4ecca3,stroke:#1a1a2e,stroke-width:2px,color:#1a1a2e
    style Core       fill:#1a1a2e,stroke:#4ecca3,stroke-width:2px,color:#fff
    style Backends   fill:#0f3460,stroke:#4ecca3,stroke-width:2px,color:#fff
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
