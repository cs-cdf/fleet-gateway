# Routing Logic

How `Router.call()` resolves a `model_or_capability` string to an actual backend call, with rate limiting and fallback.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#1a1a2e',
  'primaryTextColor': '#ffffff',
  'primaryBorderColor': '#4ecca3',
  'lineColor': '#4ecca3',
  'secondaryColor': '#16213e',
  'tertiaryColor': '#0f3460',
  'edgeLabelBackground': '#1a1a2e',
  'fontFamily': 'Inter, sans-serif',
  'fontSize': '13px'
}}}%%
flowchart TD
    IN(["📥 call(model_or_capability, messages)"])

    IN --> CAP{Capability alias?<br/><small>e.g. 'coding', 'general'</small>}

    CAP -->|yes| CHAIN["📋 Load routing chain<br/>from config / fleet.yaml<br/><small>['groq/llama-3.3-70b', 'gemini/...', ...]</small>"]
    CAP -->|no — direct ref or bare ID| DIRECT["🎯 Single-entry chain<br/><small>'groq/model' or 'model-id'</small>"]
    DIRECT --> CHAIN

    CHAIN --> NEXT{More entries?}
    NEXT -->|no — chain exhausted| FAIL(["❌ return None<br/>503 to HTTP client"])

    NEXT -->|yes| SLASH{Contains '/'?}

    SLASH -->|yes<br/>'backend/model'| SPLIT["Split on first '/'<br/>backend_name, model_id"]
    SLASH -->|no — bare model ID| INDEX["🔍 O(1) model index lookup<br/><small>self._model_index[entry]</small>"]

    INDEX --> FOUND{Found?}
    FOUND -->|no| NEXT
    FOUND -->|yes| SPLIT

    SPLIT --> AVAIL{Backend available?<br/><small>_get_backend() + is_available()</small>}
    AVAIL -->|no| NEXT

    AVAIL -->|yes| RL{Rate limit OK?<br/><small>acquire_nowait()</small>}
    RL -->|no — at capacity| NEXT
    RL -->|yes — slot acquired| CALL["📡 backend.call(<br/>  model_id, messages,<br/>  max_tokens, temperature, ...)<br/>"]

    CALL --> RES{Response?}
    RES -->|None — backend error| NEXT
    RES -->|content string| COT["🧠 CoT normalization<br/><small>extract content → strip think tags</small>"]
    COT --> OK(["✅ return response"])

    style IN   fill:#4ecca3,stroke:#1a1a2e,color:#1a1a2e
    style OK   fill:#2a9d8f,stroke:#1a1a2e,color:#fff
    style FAIL fill:#e63946,stroke:#1a1a2e,color:#fff
    style CAP  fill:#16213e,stroke:#4ecca3,color:#fff
    style SLASH fill:#16213e,stroke:#4ecca3,color:#fff
    style FOUND fill:#16213e,stroke:#4ecca3,color:#fff
    style AVAIL fill:#16213e,stroke:#4ecca3,color:#fff
    style RL    fill:#16213e,stroke:#4ecca3,color:#fff
    style RES   fill:#16213e,stroke:#4ecca3,color:#fff
    style NEXT  fill:#0f3460,stroke:#4ecca3,color:#fff
    style INDEX fill:#1a1a2e,stroke:#4ecca3,color:#4ecca3
```

## Routing Chain Format

| Input | Interpretation |
|-------|---------------|
| `"coding"` | Capability alias → load chain from `routing:` config |
| `"groq/llama-3.3-70b"` | Explicit `backend/model_id` — skip index lookup |
| `"llama-3.3-70b"` | Bare model ID — O(1) lookup in `_model_index` |

## Config Example

```yaml
routing:
  coding:
    - groq/llama-3.3-70b-versatile   # primary
    - gemini/gemini-2.0-flash         # fallback 1
    - anthropic/claude-haiku-4-5      # fallback 2

backends:
  groq:
    rate_limit: 30   # req/min — slots managed by RateLimiter
    models:
      - id: llama-3.3-70b-versatile
        capabilities: [coding, general]
```
