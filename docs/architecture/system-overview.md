# System Overview

High-level map of every major component in fleet-gateway and how they connect.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#1a1a2e',
  'primaryTextColor': '#ffffff',
  'primaryBorderColor': '#4ecca3',
  'lineColor': '#4ecca3',
  'secondaryColor': '#16213e',
  'tertiaryColor': '#0f3460',
  'fontFamily': 'Inter, sans-serif',
  'fontSize': '14px'
}}}%%
graph TB
    subgraph Clients["Clients"]
        PY["🐍 Python API<br>fleet.call() / call()"]
        HTTP["🌐 HTTP Client<br>curl / OpenAI SDK"]
        MCP["🤖 Claude Code<br>llm_call / llm_analyze_files"]
    end

    subgraph GW["fleet-gateway core"]
        direction TB
        SERVER["🚪 Gateway Server<br>POST /v1/chat/completions"]
        ROUTER["🔄 Router<br>capability → routing chain<br>O(1) model index"]
        RL["⏱ RateLimiter<br>sliding window per-backend<br>thread-safe · stdlib only"]
        FILES["📎 Files<br>images · text · PDF<br>path traversal guard"]
        PATTERNS["🧩 Patterns<br>consensus · loop · review<br>challenge · brainstorm · swot"]
    end

    subgraph Backends["Backends"]
        LOCAL["🏠 Local<br>llama.cpp · vLLM<br>Ollama · LM Studio"]
        CLOUD["☁ OpenAI-compat<br>Groq · Gemini · Cerebras<br>SambaNova · Mistral · NVIDIA"]
        ANTHRO["🦜 Anthropic<br>native Messages API<br>auto format conversion"]
    end

    subgraph Web["Web Tools (optional)"]
        SEARCH["🔍 SearXNG<br>self-hosted search"]
        SCRAPE["🕷 Firecrawl<br>web scraping"]
    end

    PY   -->|fleet.call| SERVER
    HTTP -->|POST /v1| SERVER
    MCP  -->|MCP tools| SERVER

    SERVER --> ROUTER
    ROUTER --> RL
    RL --> LOCAL
    RL --> CLOUD
    RL --> ANTHRO

    SERVER -.-> FILES
    SERVER -.-> PATTERNS
    SERVER -.-> SEARCH
    SERVER -.-> SCRAPE

    style Clients  fill:#e8f4f8,stroke:#1a1a2e,stroke-width:2px,color:#1a1a2e
    style GW       fill:#1a1a2e,stroke:#4ecca3,stroke-width:2px,color:#fff
    style Backends fill:#0f3460,stroke:#4ecca3,stroke-width:2px,color:#fff
    style Web      fill:#16213e,stroke:#4ecca3,stroke-width:2px,color:#fff
```

> Solid arrows = primary request path. Dashed arrows = optional/auxiliary features.

## Component Descriptions

| Component | File | Purpose |
|-----------|------|---------|
| Gateway Server | `server.py` | WSGI HTTP server, OpenAI-compatible API surface |
| Router | `router.py` | Capability resolution, fallback chain, O(1) model index, thread-safe caching |
| RateLimiter | `ratelimit.py` | Sliding-window rate limiter, one instance per backend, no external deps |
| Files | `files.py` | Load images/text/PDF into OpenAI content blocks, path traversal guard, size limits |
| Patterns | `patterns.py` | Multi-model patterns: consensus, loop, review, challenge, brainstorm, swot, perspectives, adversarial |
| OpenAI-compat backend | `backends/openai_compat.py` | Works with any `/v1/chat/completions` endpoint; CoT extraction, deprecation detection |
| Anthropic backend | `backends/anthropic.py` | Native Messages API; auto-converts OpenAI image blocks to Anthropic format |
| MCP server | `mcp.py` | Exposes all capabilities as Claude Code MCP tools |
