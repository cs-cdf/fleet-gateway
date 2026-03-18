"""
fleet_gateway.mcp — MCP (Model Context Protocol) server for Claude Code.

Exposes fleet-gateway capabilities as Claude Code tools:
  - llm_call    — Call any LLM model or capability
  - llm_search  — Search the web via SearXNG
  - llm_scrape  — Scrape a URL via Firecrawl
  - llm_models  — List available models
  - llm_health  — Check gateway health

Usage (add to Claude Code settings.json):
  {
    "mcpServers": {
      "fleet": {
        "command": "python",
        "args": ["-m", "fleet_gateway.mcp"],
        "env": {
          "GROQ_API_KEY": "...",
          "CEREBRAS_API_KEY": "...",
          "SEARXNG_URL": "http://localhost:8888"
        }
      }
    }
  }

Requires: pip install fleet-gateway[mcp]
"""

from __future__ import annotations

import json
import sys

# Graceful import — mcp is optional
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, CallToolResult
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False


def _check_mcp():
    if not _MCP_AVAILABLE:
        print(
            "ERROR: 'mcp' package not installed. Run: pip install fleet-gateway[mcp]",
            file=sys.stderr,
        )
        sys.exit(1)


async def _serve():
    from fleet_gateway import Fleet

    fleet = Fleet()
    server = Server("fleet-gateway")

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="llm_call",
                description=(
                    "Call an LLM model or capability alias. "
                    "Capability aliases: coding, general, reasoning, translate, proofread, "
                    "summarize, creative, fast, italian, vision. "
                    "Or use a direct reference: 'groq/llama-3.3-70b-versatile'."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model": {
                            "type": "string",
                            "description": "Model or capability alias (e.g. 'coding', 'general', 'groq/llama-3.3-70b-versatile')",
                        },
                        "prompt": {
                            "type": "string",
                            "description": "The user message / prompt",
                        },
                        "system": {
                            "type": "string",
                            "description": "Optional system prompt",
                        },
                        "max_tokens": {
                            "type": "integer",
                            "default": 2048,
                            "description": "Max tokens in response",
                        },
                        "temperature": {
                            "type": "number",
                            "default": 0.7,
                            "description": "Sampling temperature (0=deterministic, 1=creative)",
                        },
                    },
                    "required": ["model", "prompt"],
                },
            ),
            Tool(
                name="llm_search",
                description=(
                    "Search the web via SearXNG (self-hosted, privacy-respecting). "
                    "Returns list of results with title, URL, and snippet. "
                    "Requires SEARXNG_URL env var or configured in config.yaml."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "num_results": {"type": "integer", "default": 10, "description": "Max results"},
                        "language": {"type": "string", "description": "Language code (e.g. 'en', 'it')"},
                        "categories": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Categories: general, news, images, videos, science, ...",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="llm_scrape",
                description=(
                    "Scrape a URL and return its content as clean Markdown using Firecrawl. "
                    "Handles JS-rendered pages, paywalls, and PDFs. "
                    "Requires FIRECRAWL_URL env var or configured in config.yaml."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to scrape"},
                    },
                    "required": ["url"],
                },
            ),
            Tool(
                name="llm_models",
                description="List all configured LLM models and their availability status.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="llm_health",
                description="Check the health status of fleet-gateway and its backends.",
                inputSchema={"type": "object", "properties": {}},
            ),
            # ── Multi-model patterns ──────────────────────────────
            Tool(
                name="llm_consensus",
                description=(
                    "Ask multiple LLMs the same question and get a synthesized consensus answer. "
                    "Runs N models in parallel, then synthesizes into one response. "
                    "Better than a single model for questions where multiple perspectives matter."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "Question to ask all models"},
                        "n": {"type": "integer", "default": 3, "description": "Number of models to use"},
                        "synthesize": {"type": "boolean", "default": True, "description": "Synthesize into one answer"},
                    },
                    "required": ["question"],
                },
            ),
            Tool(
                name="llm_review",
                description=(
                    "Get a multi-model review of code, text, or a document. "
                    "Multiple models review in parallel, then produce a synthesized report. "
                    "content_type: 'code', 'text', 'document', 'plan', 'essay'"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Content to review"},
                        "content_type": {"type": "string", "default": "code", "description": "code | text | document | plan | essay"},
                        "n": {"type": "integer", "default": 3, "description": "Number of reviewer models"},
                    },
                    "required": ["content"],
                },
            ),
            Tool(
                name="llm_challenge",
                description=(
                    "Devil's advocate: stress-test an idea, decision, or plan. "
                    "Finds counterarguments, hidden assumptions, risks, and better alternatives. "
                    "depth: 'quick' (3 weaknesses), 'thorough' (full analysis), 'deep' (red team)"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "idea": {"type": "string", "description": "Idea, claim, or decision to challenge"},
                        "depth": {"type": "string", "default": "thorough", "description": "quick | thorough | deep"},
                    },
                    "required": ["idea"],
                },
            ),
            Tool(
                name="llm_loop",
                description=(
                    "Iterative refinement: generate → critique → improve, repeated N times. "
                    "Each iteration feeds the previous response as context and asks for improvement. "
                    "Good for: writing, code, plans — anything that benefits from multiple passes."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "Initial task or question"},
                        "iterations": {"type": "integer", "default": 3, "description": "Number of refinement cycles (2-5 recommended)"},
                    },
                    "required": ["prompt"],
                },
            ),
            Tool(
                name="llm_brainstorm",
                description=(
                    "Multi-model brainstorming: generate diverse ideas from multiple LLMs in parallel. "
                    "Models use different 'mindsets' (conventional, creative, technical), "
                    "then ideas are deduplicated and ranked."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "What to brainstorm about"},
                        "n": {"type": "integer", "default": 3, "description": "Number of models to use"},
                    },
                    "required": ["topic"],
                },
            ),
            Tool(
                name="llm_swot",
                description=(
                    "SWOT analysis: Strengths, Weaknesses, Opportunities, Threats. "
                    "Returns a structured analysis with strategic implications."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string", "description": "What to analyze (product, decision, technology, etc.)"},
                        "context": {"type": "string", "description": "Optional additional context"},
                    },
                    "required": ["subject"],
                },
            ),
            Tool(
                name="llm_perspectives",
                description=(
                    "Get multiple expert viewpoints on a topic. "
                    "Each model is assigned a different expert persona (pragmatist, critic, strategist, specialist). "
                    "Returns individual perspectives plus a synthesis."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "Topic or question to analyze"},
                        "viewpoints": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Custom expert roles (optional). Default: pragmatist, skeptic, strategist",
                        },
                    },
                    "required": ["topic"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> CallToolResult:
        try:
            if name == "llm_call":
                result = fleet.call(
                    arguments["model"],
                    arguments["prompt"],
                    system=arguments.get("system"),
                    max_tokens=arguments.get("max_tokens", 2048),
                    temperature=arguments.get("temperature", 0.7),
                )
                text = result or "(no response)"
                return CallToolResult(content=[TextContent(type="text", text=text)])

            elif name == "llm_search":
                results = fleet.search(
                    arguments["query"],
                    num_results=arguments.get("num_results", 10),
                    language=arguments.get("language"),
                    categories=arguments.get("categories"),
                )
                text = json.dumps(results, indent=2, ensure_ascii=False)
                return CallToolResult(content=[TextContent(type="text", text=text)])

            elif name == "llm_scrape":
                content = fleet.scrape(arguments["url"])
                return CallToolResult(content=[TextContent(type="text", text=content)])

            elif name == "llm_models":
                models = fleet.models()
                text = json.dumps(models, indent=2, ensure_ascii=False)
                return CallToolResult(content=[TextContent(type="text", text=text)])

            elif name == "llm_health":
                health = fleet.health()
                text = json.dumps(health, indent=2, ensure_ascii=False)
                return CallToolResult(content=[TextContent(type="text", text=text)])

            elif name == "llm_consensus":
                result = fleet.patterns.consensus(
                    arguments["question"],
                    n=arguments.get("n", 3),
                    synthesize=arguments.get("synthesize", True),
                )
                text = json.dumps(result, indent=2, ensure_ascii=False)
                return CallToolResult(content=[TextContent(type="text", text=text)])

            elif name == "llm_review":
                result = fleet.patterns.review(
                    arguments["content"],
                    content_type=arguments.get("content_type", "code"),
                    n=arguments.get("n", 3),
                )
                text = result.get("synthesis") or json.dumps(result, indent=2, ensure_ascii=False)
                return CallToolResult(content=[TextContent(type="text", text=text)])

            elif name == "llm_challenge":
                result = fleet.patterns.challenge(
                    arguments["idea"],
                    depth=arguments.get("depth", "thorough"),
                )
                text = result.get("challenge") or "(no response)"
                return CallToolResult(content=[TextContent(type="text", text=text)])

            elif name == "llm_loop":
                result = fleet.patterns.loop(
                    arguments["prompt"],
                    iterations=arguments.get("iterations", 3),
                )
                text = result.get("final") or "(no response)"
                return CallToolResult(content=[TextContent(type="text", text=text)])

            elif name == "llm_brainstorm":
                result = fleet.patterns.brainstorm(
                    arguments["topic"],
                    n=arguments.get("n", 3),
                )
                text = result.get("synthesis") or json.dumps(result.get("raw_ideas", {}), indent=2, ensure_ascii=False)
                return CallToolResult(content=[TextContent(type="text", text=text)])

            elif name == "llm_swot":
                result = fleet.patterns.swot(
                    arguments["subject"],
                    context=arguments.get("context", ""),
                )
                text = result.get("analysis") or "(no response)"
                return CallToolResult(content=[TextContent(type="text", text=text)])

            elif name == "llm_perspectives":
                result = fleet.patterns.perspectives(
                    arguments["topic"],
                    viewpoints=arguments.get("viewpoints"),
                )
                text = result.get("synthesis") or json.dumps(result.get("perspectives", {}), indent=2, ensure_ascii=False)
                return CallToolResult(content=[TextContent(type="text", text=text)])

            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                    isError=True,
                )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {e}")],
                isError=True,
            )

    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


def main():
    _check_mcp()
    import asyncio
    asyncio.run(_serve())


if __name__ == "__main__":
    main()
