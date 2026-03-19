# Request Flow

End-to-end sequence for a single `POST /v1/chat/completions` call, showing rate limiting, the fallback chain, and CoT normalization on success.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#1a1a2e',
  'primaryTextColor': '#ffffff',
  'lineColor': '#4ecca3',
  'fontFamily': 'Inter, sans-serif',
  'fontSize': '14px',
  'activationBorderColor': '#4ecca3',
  'activationBkgColor': '#16213e',
  'noteBkgColor': '#0f3460',
  'noteTextColor': '#ffffff'
}}}%%
sequenceDiagram
    autonumber

    participant Client  as 🌐 Client
    participant Gateway as 🚪 Gateway
    participant RL      as ⏱ RateLimiter
    participant Backend as ☁ Backend
    participant CoT     as 🧠 CoT

    Note over Client,Gateway: Incoming request
    Client->>Gateway: POST /v1/chat/completions { model: "coding" }
    Gateway->>Gateway: resolve capability to routing chain

    loop Fallback chain — try each entry until success

        Note over Gateway,RL: Rate limit check (non-blocking)
        Gateway->>RL: acquire_nowait(backend_name)

        alt Limit exceeded
            RL-->>Gateway: skip — try next
        else Slot available
            RL-->>Gateway: ok

            Note over Gateway,Backend: Backend call
            Gateway->>Backend: POST /v1/chat/completions

            alt Success
                Backend-->>Gateway: choices[0].message
                Note over Gateway,CoT: CoT normalization
                Gateway->>CoT: extract content
                CoT->>CoT: strip think tags
                CoT-->>Gateway: clean text
                Gateway-->>Client: 200 OK + response
            else Failure
                Backend-->>Gateway: error / timeout
                Gateway->>Gateway: try next in chain
            end
        end

    end

    Note over Client,Gateway: All backends exhausted
    Gateway-->>Client: 503 Service Unavailable
```

## Key Design Points

- **Non-blocking rate limiting** — `acquire_nowait()` returns immediately if a backend is at capacity; the router skips to the next entry rather than blocking.
- **No circuit breaker in package** — the production `fleet_gateway.py` in `_SHARED` has a per-backend `CircuitBreaker`; the open-source package uses only rate limiting + fallback.
- **CoT normalization priority** — `content` → `reasoning` (vLLM `--reasoning-parser`) → `reasoning_content` (Cogito/Apriel). Unclosed `<think>` tags are discarded entirely.
- **Thread safety** — `Router._backend_cache` and `_limiters` are protected by `_cache_lock` (double-checked locking). `RateLimiter` uses its own internal lock.
