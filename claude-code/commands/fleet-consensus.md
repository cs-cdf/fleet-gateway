---
description: Multi-model consensus — ask 3 LLMs the same question, synthesize into one answer via fleet-gateway.
---

Get a multi-model consensus answer for:

$ARGUMENTS

Use the `llm_call` MCP tool (fleet-gateway). Call all 3 models in parallel (or as fast as possible sequentially).

---

**MODEL 1 — General:**
model="general"
Prompt: "$ARGUMENTS"

**MODEL 2 — Reasoning:**
model="reasoning"
Prompt: "$ARGUMENTS"

**MODEL 3 — Creative:**
model="creative"
Prompt: "$ARGUMENTS"

---

**Synthesize** the three responses into a consolidated answer:

```
## CONSENSUS ANSWER

[Your synthesis — merge overlapping points, resolve contradictions by picking
the stronger argument, preserve unique insights from any single model.]

---

**Confidence:** High / Medium / Low
**Models used:** general, reasoning, creative

### High-confidence points
(what all 3 models agreed on)
- [point]
- [point]

### Points of divergence
(where models differed — and why it matters)
- [divergence + explanation]

### Unique perspectives
(interesting points raised by only one model — worth considering)
- [model name]: [unique insight]

<details>
<summary>Individual model responses</summary>

**Model 1 (general):**
[response]

**Model 2 (reasoning):**
[response]

**Model 3 (creative):**
[response]
</details>
```

If a model fails or returns nothing: note it and synthesize from the remaining responses.
