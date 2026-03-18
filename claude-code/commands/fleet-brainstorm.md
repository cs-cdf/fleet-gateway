---
description: Multi-model brainstorming — 3 parallel mindsets (conventional/creative/technical), deduplication and ranking via fleet-gateway.
---

Brainstorm ideas for:

$ARGUMENTS

Use the `llm_call` MCP tool (fleet-gateway). Call all 3 models in parallel.

---

**MODEL 1 — Conventional mindset:**
model="general", system="You are a practical thinker who generates well-tested, proven ideas."

Prompt:
"Generate 8 concrete, practical ideas for: $ARGUMENTS

Include both obvious and non-obvious approaches.
For each idea: one sentence description + why it would work.
Number each idea 1-8."

---

**MODEL 2 — Creative/unconventional mindset:**
model="creative", system="You are a lateral thinker who challenges conventional solutions."

Prompt:
"Generate 8 creative and unconventional ideas for: $ARGUMENTS

Push beyond the obvious. Think from unexpected angles — different industries, opposite approaches, combining unrelated concepts.
For each idea: one sentence description + why it's different.
Number each idea 1-8."

---

**MODEL 3 — Technical/expert mindset:**
model="coding" (or "reasoning" if non-technical), system="You are a domain expert who generates technically grounded, implementable ideas."

Prompt:
"Generate 8 technically-grounded, implementable ideas for: $ARGUMENTS

Focus on what would actually work in practice. Consider constraints, resources, and real-world limitations.
For each idea: one sentence description + first concrete step.
Number each idea 1-8."

---

**Synthesis** (you, Claude, synthesize):

```
## BRAINSTORM: $ARGUMENTS

### From all 3 models — 24 raw ideas

[MODEL 1 - Conventional]
[responses]

[MODEL 2 - Creative]
[responses]

[MODEL 3 - Technical]
[responses]

---

## TOP 10 IDEAS (ranked: originality × feasibility × impact)

| Rank | Idea | Source | Why promising | First step |
|------|------|--------|---------------|------------|
| 1 | [idea] | [model] | [reason] | [action] |
| 2 | ... | ... | ... | ... |
...

## HIDDEN GEMS
Ideas that looked unconventional but deserve serious consideration:
- [idea]: [why it's actually worth exploring]

## QUICK WINS
Ideas implementable immediately with minimal resources:
- [idea]: [why it's fast/cheap]
```
