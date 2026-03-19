# Architecture Documentation

Technical diagrams and design documentation for fleet-gateway.

| Document | Description |
|----------|-------------|
| [System Overview](system-overview.md) | High-level component map: clients, gateway, backends |
| [Request Flow](request-flow.md) | Sequence diagram: rate limiting, circuit breaker, fallback chain |
| [Routing Logic](routing-logic.md) | Flowchart: capability resolution → model index → fallback |
| [Module Map](module-map.md) | Python module dependencies and public API surface |

## Quick Summary

```
Clients  ──►  Gateway (Router → RateLimiter → CircuitBreaker)  ──►  Backends
              └─ capability alias   └─ sliding window/provider  └─ local / cloud
              └─ fallback chain     └─ O(1) model index         └─ openai-compat / anthropic
```

See [README.md](../../README.md) for installation and usage.
