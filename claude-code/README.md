# fleet-gateway — Claude Code Integration

This directory contains everything needed to integrate fleet-gateway with Claude Code.

## Structure

```
claude-code/
├── README.md              # this file
├── settings_snippet.json  # MCP server config — add to ~/.claude/settings.json
├── commands/              # Claude Code skills (slash commands)
│   ├── fleet-review.md       # /fleet-review — multi-model code/text review
│   ├── fleet-consensus.md    # /fleet-consensus — multi-model consensus answer
│   ├── fleet-loop.md         # /fleet-loop — iterative refinement (generate→critique→improve)
│   ├── fleet-challenge.md    # /fleet-challenge — devil's advocate analysis
│   ├── fleet-brainstorm.md   # /fleet-brainstorm — multi-model brainstorming
│   ├── fleet-swot.md         # /fleet-swot — SWOT analysis
│   ├── fleet-perspectives.md # /fleet-perspectives — multi-expert viewpoints
│   └── fleet-adversarial.md  # /fleet-adversarial — structured attacker vs defender
└── hooks/
    └── README.md             # Claude Code hooks examples
```

## Quick Setup

### 1. Add the MCP server

Copy the contents of `settings_snippet.json` into your `~/.claude/settings.json`
under the `mcpServers` key:

```json
{
  "mcpServers": {
    "fleet": {
      "command": "python",
      "args": ["-m", "fleet_gateway.mcp"],
      "env": {
        "GROQ_API_KEY": "your_key_here",
        "CEREBRAS_API_KEY": "your_key_here"
      }
    }
  }
}
```

### 2. Install with MCP support

```bash
pip install fleet-gateway[mcp]
```

### 3. Add the skills

Copy the skill files to your Claude Code commands directory:

```bash
# Global (available in all projects)
cp claude-code/commands/*.md ~/.claude/commands/

# Project-local (available only in this project)
mkdir -p .claude/commands
cp claude-code/commands/*.md .claude/commands/
```

### 4. Verify

In Claude Code, type `/` to see available commands. You should see:
- `/fleet-review`
- `/fleet-consensus`
- `/fleet-loop`
- `/fleet-challenge`
- `/fleet-brainstorm`
- `/fleet-swot`
- `/fleet-perspectives`
- `/fleet-adversarial`

---

## Available Skills

### `/fleet-review [file or code]`
Multi-model code or text review. Calls 3 models in parallel, synthesizes their feedback.

```
/fleet-review src/main.py
/fleet-review the authentication logic above
/fleet-review document: review my proposal for X
```

### `/fleet-consensus [question]`
Ask multiple models the same question, get a synthesized consensus answer.

```
/fleet-consensus Is Rust better than Go for CLI tools?
/fleet-consensus What are the tradeoffs of event sourcing?
```

### `/fleet-loop [task]`
Iterative refinement: generate → critique → improve, 3 cycles.

```
/fleet-loop Write a Python quicksort with good error handling
/fleet-loop Draft an email declining a partnership offer professionally
```

### `/fleet-challenge [idea or decision]`
Devil's advocate: stress-test an idea, decision, or plan.

```
/fleet-challenge We should rewrite everything in microservices
/fleet-challenge Our pricing model should be freemium
```

### `/fleet-brainstorm [topic]`
Multi-model idea generation with deduplication and ranking.

```
/fleet-brainstorm Product names for a developer productivity tool
/fleet-brainstorm Ways to reduce onboarding time for new engineers
```

### `/fleet-swot [subject]`
Full SWOT analysis with strategic implications.

```
/fleet-swot Adopting Rust for our backend services
/fleet-swot Switching from REST to GraphQL
```

### `/fleet-perspectives [topic]`
Multi-expert viewpoints: pragmatist, critic, strategist, specialist.

```
/fleet-perspectives Remote-first vs office-first teams
/fleet-perspectives Using LLMs for customer support
```

### `/fleet-adversarial [claim or plan]`
Structured attacker vs defender debate, 2 rounds, with verdict.

```
/fleet-adversarial We should deprecate our REST API and use GraphQL only
/fleet-adversarial AI will replace most software developers within 5 years
```

---

## MCP Tools (available directly in Claude)

When the MCP server is configured, these tools are available to Claude automatically:

| Tool | Description |
|------|-------------|
| `llm_call` | Call any model or capability alias |
| `llm_search` | Web search via SearXNG |
| `llm_scrape` | Scrape a URL via Firecrawl |
| `llm_models` | List available models |
| `llm_health` | Check gateway health |
| `llm_consensus` | Multi-model consensus |
| `llm_review` | Multi-model review |
| `llm_challenge` | Devil's advocate |
| `llm_loop` | Iterative refinement |
| `llm_brainstorm` | Multi-model brainstorming |
| `llm_swot` | SWOT analysis |
| `llm_perspectives` | Multi-expert viewpoints |

---

## Integrating with Existing Skills

If you already have custom Claude Code skills that call local models directly
(e.g. hardcoded endpoints like `http://localhost:8080`), you can run them alongside
fleet-gateway skills without conflict.

fleet-gateway skills use **capability aliases** (`coding`, `reasoning`, `general`)
instead of specific model names or endpoints. This means:

- They work with any backend configured in fleet-gateway (cloud or local)
- No hardcoded IPs or model names — everything is resolved at runtime
- You can swap backends in `config.yaml` without touching the skills

To point a fleet-gateway skill at a specific local model, just configure it
as a backend in `config.yaml` and update the routing for the relevant capability.
