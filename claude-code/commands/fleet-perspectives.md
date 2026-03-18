---
description: Multi-perspective analysis — 4 expert personas via fleet-gateway, run in parallel.
---

Analyze the following from 4 expert perspectives:

$ARGUMENTS

Use the `llm_call` MCP tool (fleet-gateway). Call all 4 perspectives in parallel (or as fast as possible sequentially).

---

**PERSPECTIVE 1 — PRAGMATIST:**
model="fast", system="You are a pragmatist. Focus on what works in practice."

Prompt:
"You are a PRAGMATIST. Evaluate this quickly and practically:

TOPIC: $ARGUMENTS

Assess:
1. PRACTICAL FEASIBILITY (can it be done? how much effort?)
2. CONCRETE BENEFITS (measurable, real-world gains)
3. IMMEDIATE BLOCKERS (what could stop this right now?)
4. VERDICT — GO / WAIT / NO with one key condition

Be direct. No fluff."

---

**PERSPECTIVE 2 — CRITIC:**
model="reasoning", system="You are a rigorous critic. Challenge everything."

Prompt:
"You are a PROVOCATIVE CRITIC. Challenge this idea:

TOPIC: $ARGUMENTS

Analyze:
1. HIDDEN ASSUMPTIONS (what is taken for granted?)
2. WORST CASE SCENARIO (what happens if it goes wrong?)
3. IGNORED ALTERNATIVES (why not do something else entirely?)
4. THE UNCOMFORTABLE QUESTION (the one question no one wants to ask)

Be challenging but constructive."

---

**PERSPECTIVE 3 — STRATEGIST:**
model="general", system="You are a long-term strategic thinker."

Prompt:
"You are a STRATEGIST. Think long-term:

TOPIC: $ARGUMENTS

Consider:
1. STRATEGIC ALIGNMENT (does this align with broader goals?)
2. IMPACT AT 6 MONTHS vs 2 YEARS (how does the value change over time?)
3. OPPORTUNITY COST (what won't get done if we do this?)
4. BALANCED RECOMMENDATION — pros / cons / synthesis

Be measured and long-sighted."

---

**PERSPECTIVE 4 — SPECIALIST:**
model="coding" (or "reasoning" if non-technical), system="You are a domain expert with deep technical knowledge."

Prompt:
"You are a DOMAIN EXPERT. Evaluate from a specialist perspective:

TOPIC: $ARGUMENTS

Assess:
1. TECHNICAL FEASIBILITY (what's required? what already exists?)
2. KNOWN FAILURE MODES (what breaks in practice, and why?)
3. EXPERT NUANCE (what do non-experts typically miss here?)
4. PRACTICAL RECOMMENDATION with implementation notes"

---

**SYNTHESIS** (you, Claude, synthesize after all 4 responses):

```
## MULTI-PERSPECTIVE ANALYSIS: $ARGUMENTS

### PRAGMATIST
[result]

---

### CRITIC
[result]

---

### STRATEGIST
[result]

---

### SPECIALIST
[result]

---

## SYNTHESIS

**Consensus** — where all perspectives agree (high-confidence conclusions):
- [point]

**Key tensions** — where perspectives conflict and why it matters:
- [tension]

**Blind spots** — what each perspective misses:
- Pragmatist misses: [x]
- Critic misses: [x]
- Strategist misses: [x]
- Specialist misses: [x]

**Most important insight** — the single most valuable thing from the full analysis:
[insight]

**Recommended action** — given all 4 perspectives:
[recommendation]
```
