---
description: Iterative refinement loop — 3-pass surface/deep/synthesis via fleet-gateway.
---

Run a 3-pass iterative refinement loop for:

$ARGUMENTS

Use the `llm_call` MCP tool (fleet-gateway) for each pass sequentially.

---

**PASS 1 — Surface analysis:**
model="fast", system="You are a fast, practical analyst. Be concise and direct."

Prompt:
"Quick surface analysis of: $ARGUMENTS

Provide:
1. KEY STRENGTHS (3 bullet points)
2. IMMEDIATE CONCERNS (3 bullet points)
3. QUESTIONS TO EXPLORE DEEPER (3 bullet points)
4. SUMMARY (2 lines max)"

---

**PASS 2 — Deep analysis:**
model="reasoning", system="You are a deep critical thinker. Question everything."

Prompt:
"Deep analysis of: $ARGUMENTS

Surface analysis from Pass 1:
[PASS_1_RESULT]

Go deeper:
1. HIDDEN ASSUMPTIONS (what is being taken for granted?)
2. NON-OBVIOUS CONNECTIONS (what links to what, and how?)
3. ROOT CAUSE ANALYSIS (why do the problems actually exist?)
4. ALTERNATIVE PERSPECTIVES (how would a harsh critic see this? A naive optimist?)
5. SYNTHESIS (2-3 lines)"

---

**PASS 3 — Synthesis and refined conclusions:**
model="general", system="You are a strategic synthesizer integrating multiple analytical passes."

Prompt:
"Final synthesis for: $ARGUMENTS

Pass 1 (Surface):
[PASS_1_RESULT]

Pass 2 (Deep):
[PASS_2_RESULT]

Integrate everything into:
1. REFINED UNDERSTANDING (what do we now truly understand that we didn't before?)
2. REQUIRED CHANGES — Must / Should / Could (3 levels of priority)
3. KEY INSIGHTS (top 3 — one sentence each)
4. RECOMMENDED ACTIONS — Immediate / Short-term / Long-term
5. CONFIDENCE LEVEL — High / Medium / Low, and why"

---

Present all 3 passes with clear headers, then close with an **Evolution Summary** table:

| Aspect | Pass 1 | Pass 2 | Pass 3 |
|--------|--------|--------|--------|
| Clarity | Superficial | Deeper | Integrated |
| Key finding | [P1 key point] | [P2 key point] | [final insight] |
| Open questions | [from P1] | [from P2] | Resolved/Remaining |

**What changed between Pass 1 and Pass 3, and why it matters.**
