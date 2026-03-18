# Claude Code Hooks for fleet-gateway

Claude Code hooks let you run scripts automatically on tool events.
These examples show how to integrate fleet-gateway into your Claude Code workflow.

## Setup

Add hooks to `~/.claude/settings.json` under the `hooks` key.

## Example: Auto-review on file write

Automatically get an LLM review every time Claude writes a Python file:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "python -c \"\nimport sys, json, subprocess\nresult = json.loads(sys.stdin.read())\npath = result.get('tool_input', {}).get('file_path', '')\nif path.endswith('.py'):\n    code = open(path).read()\n    import fleet_gateway\n    review = fleet_gateway.call('coding', f'Quick review of this Python file (3 bullet points max):\\n{code[:2000]}')\n    if review: print(f'[fleet-gateway review] {review[:500]}')\n\""
          }
        ]
      }
    ]
  }
}
```

## Example: Summarize long tool output

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python -c \"\nimport sys, json\nresult = json.loads(sys.stdin.read())\noutput = result.get('tool_response', '')\nif len(str(output)) > 3000:\n    import fleet_gateway\n    summary = fleet_gateway.call('summarize', f'Summarize this command output in 2 sentences:\\n{str(output)[:3000]}')\n    if summary: print(f'[summary] {summary}')\n\""
          }
        ]
      }
    ]
  }
}
```

## Notes

- Keep hooks fast — long-running hooks block the Claude Code UI
- Use `fleet_gateway.call("fast", ...)` for hooks — it routes to the fastest available model
- Hooks receive tool input/output via stdin as JSON
- Print to stdout to show output in Claude Code
