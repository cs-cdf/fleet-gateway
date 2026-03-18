---
description: Structured adversarial debate — 2 rounds of attack/defense + verdict via fleet-gateway.
---

Run a structured adversarial debate on:

$ARGUMENTS

Use the `llm_call` MCP tool (fleet-gateway). Sequential rounds.

---

**ROUND 1 — ATTACK:**
model="reasoning", system="You are an adversarial critic. Find the single most devastating flaw. Be specific, cite evidence, be merciless. Do not hedge."

Prompt:
"Attack this claim or plan — find its fatal flaw:

$ARGUMENTS

Provide:
1. THE FATAL FLAW — the single most devastating problem (be specific)
2. EVIDENCE — concrete reasons why this is a real problem, not hypothetical
3. KNOCK-ON EFFECTS — what else breaks as a result of this flaw?
4. WHY DEFENDERS MISS IT — why people typically don't see this coming"

---

**ROUND 1 — DEFENSE:**
model="general", system="You are a rigorous defender. Engage directly with every attack. Acknowledge valid points — do not dismiss anything without evidence."

Prompt:
"Defend this claim against the following attack:

ORIGINAL CLAIM: $ARGUMENTS
ATTACK: [ROUND_1_ATTACK]

Provide:
1. DIRECT REBUTTAL — address the fatal flaw point by point
2. ACKNOWLEDGED WEAKNESSES — where the attacker is right (be honest)
3. MITIGATIONS — how to address the valid criticisms
4. STRENGTHENED POSITION — revised version of the claim after incorporating feedback"

---

**ROUND 2 — ATTACK (escalated):**
model="reasoning"

Prompt:
"The defender responded to your attack:
DEFENSE: [ROUND_1_DEFENSE]

Now find a new, stronger attack that:
- Addresses their defense directly (don't repeat Round 1)
- Targets the weaknesses they acknowledged
- Challenges the mitigations they proposed

Be more specific and harder to dismiss than Round 1."

---

**ROUND 2 — DEFENSE (final position):**
model="general"

Prompt:
"New escalated attack: [ROUND_2_ATTACK]
Your previous defense: [ROUND_1_DEFENSE]

Strengthen your position:
1. Address the new attack directly
2. Refine your mitigations based on this second challenge
3. State your final, battle-tested position in 2-3 sentences"

---

**VERDICT** (you, Claude, synthesize objectively):

```
## ADVERSARIAL DEBATE: $ARGUMENTS

### ROUND 1
**ATTACK:**
[round_1_attack]

**DEFENSE:**
[round_1_defense]

---

### ROUND 2
**ATTACK (escalated):**
[round_2_attack]

**DEFENSE (final position):**
[round_2_defense]

---

## VERDICT

**Claim survived scrutiny?** Strong / Weakened / Refuted

**Most valid criticisms** (that weren't fully defended):
1. [criticism]
2. [criticism]

**Strongest defense points:**
1. [point]
2. [point]

**Recommended modifications** to strengthen the original position:
1. [modification]
2. [modification]

**Final recommendation: Proceed / Modify / Abandon**
Rationale: [one sentence]
Key condition that would change this assessment: [one sentence]
```
