# Contributing to fleet-gateway

Thank you for your interest in contributing!

## Getting Started

```bash
git clone https://github.com/3p4dm4/fleet-gateway.git
cd fleet-gateway
pip install -e ".[all]"
cp .env.example .env   # add at least one API key
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Adding a New Backend

1. Optionally create a new file in `fleet_gateway/backends/` (if the backend is not OpenAI-compatible)
2. Or add it to the auto-discovery table in `fleet_gateway/config.py` (`_AUTO_BACKENDS`)
3. Add it to `config.example.yaml` under `backends:`
4. Update `README.md` Provider Details section
5. Add tests in `tests/`

Most providers use the OpenAI-compatible format — check `config.py` for examples.

## Adding a New Pattern

Patterns live in `fleet_gateway/patterns.py`. Each pattern:
- Takes a prompt/content as first argument
- Optionally takes `models`, `n`, `timeout`, `max_tokens`
- Returns a dict with a clear structure
- Gets a module-level shortcut in `__init__.py`
- Gets an MCP tool in `mcp.py`
- Gets a Claude Code skill in `.claude/commands/`
- Gets a prompt template in `templates/`

## Code Style

- stdlib only for core modules (no external deps unless in `[extras]`)
- Type hints everywhere
- Docstrings with Args/Returns
- No print() in library code — use `_log()` to stderr

## Pull Requests

- Keep PRs focused on one thing
- Include tests for new features
- Update README if you add/change user-facing behavior
- Describe what the PR does and why in the description
