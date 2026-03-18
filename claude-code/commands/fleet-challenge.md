---
description: Devil's advocate — 3-stage attack/defense/synthesis pipeline via fleet-gateway.
---

Run a full adversarial challenge on:

$ARGUMENTS

Use the `llm_call` MCP tool (fleet-gateway). Three sequential stages.

---

**STAGE 1 — ATTACK** (find every weakness):
model="reasoning", system="You are a ruthless critic. Your job is to destroy weak proposals before reality does."

Prompt:
"You are a ruthless critic. Analyze this proposal and find ALL weaknesses, hidden assumptions, and potential failure modes.

PROPOSAL:
$ARGUMENTS

Provide:
1. HIDDEN ASSUMPTIONS (3-5 — what is taken for granted without evidence?)
2. CRITICAL WEAK POINTS (3-5 — ranked by severity)
3. FAILURE SCENARIOS (2-3 — concrete ways this could go wrong)
4. UNCOMFORTABLE QUESTIONS (3-5 — the questions no one wants to ask)

Be specific. Name the exact assumptions. Don't be vague."

---

**STAGE 2 — DEFENSE** (respond to the attack):
model="general", system="You are a constructive defender. Engage seriously with every criticism — don't dismiss anything."

Prompt:
"You are a constructive defender. Respond to each criticism honestly and rigorously.

ORIGINAL PROPOSAL:
$ARGUMENTS

CRITICISMS RECEIVED:
[STAGE_1_RESULT]

Provide:
1. VALID DEFENSES (where criticisms are unfounded — explain why)
2. ACCEPTED CRITICISMS (where they are right — be honest)
3. PROPOSED MODIFICATIONS (how to improve the proposal to address valid concerns)
4. PLAN B (alternative approach if the original fails)"

---

**STAGE 3 — SYNTHESIS** (you, Claude, synthesize):

After presenting both stages, deliver an objective verdict:

**VERDICT: [Strong / Moderate / Weak / Needs major rework]**

**Top 3 risks to monitor:**
1. [risk]
2. [risk]
3. [risk]

**Top 3 required modifications:**
1. [modification]
2. [modification]
3. [modification]

**GO / WAIT / NO-GO** — with one-sentence rationale and the key condition that would change this assessment.
