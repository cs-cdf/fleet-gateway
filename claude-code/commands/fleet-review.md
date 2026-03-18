---
description: Multi-model code/text review — 3 reviewers in parallel, synthesized report via fleet-gateway.
---

Run a multi-model review of:

$ARGUMENTS

If $ARGUMENTS is a file path, read the file first. If it's a description, use the relevant code or text from context.

Use the `llm_call` MCP tool (fleet-gateway). Call all 3 reviewers in parallel (or as fast as possible).

---

**REVIEWER 1 — Technical precision:**
model="coding", system="You are a senior software engineer specializing in code quality, security, and architecture."

Prompt:
"Review the following [code/text]:

[CONTENT]

Provide:
1. CRITICAL ISSUES — bugs, security vulnerabilities, logic errors (rank by severity: Critical / High / Medium / Low)
2. ARCHITECTURE & DESIGN — structural issues, design pattern violations, scalability concerns
3. SPECIFIC LINE-LEVEL IMPROVEMENTS — reference exact lines or sections
4. VERDICT — production-ready / needs work / major issues"

---

**REVIEWER 2 — Reasoning and correctness:**
model="reasoning", system="You are a rigorous analyst focused on correctness, edge cases, and logical soundness."

Prompt:
"Review the following [code/text]:

[CONTENT]

Provide:
1. LOGICAL ERRORS & EDGE CASES — what scenarios aren't handled?
2. HIDDEN COMPLEXITY — what will be hard to maintain or debug in 6 months?
3. MISSING PIECES — what's conspicuously absent?
4. TOP 3 IMPROVEMENTS ranked by impact"

---

**REVIEWER 3 — General quality:**
model="general", system="You are a thoughtful senior reviewer focused on clarity, maintainability, and overall quality."

Prompt:
"Review the following [code/text]:

[CONTENT]

Provide:
1. STRENGTHS — what works well and why
2. CLARITY & READABILITY — is this easy to understand and maintain?
3. DOCUMENTATION & NAMING — are conventions clear and consistent?
4. OVERALL ASSESSMENT — one paragraph summary"

---

**Synthesize** the three reviews:

```
## CODE REVIEW: [filename or description]

**Reviewers:** coding, reasoning, general

### Critical Issues (fix before shipping)
(issues raised by 2+ models — high confidence)
- [issue + severity + which models flagged it]

### Warnings (should fix)
(issues raised by 1 model — worth investigating)
- [issue + which model raised it]

### Strengths
- [strength]

### Top Improvements (ranked by impact)
1. [improvement + rationale]
2. [improvement + rationale]
3. [improvement + rationale]

### Verdict
**[Production-ready / Needs work / Major issues]** — [one sentence rationale]

---

<details>
<summary>Individual reviews</summary>

**Reviewer 1 (coding):**
[full response]

**Reviewer 2 (reasoning):**
[full response]

**Reviewer 3 (general):**
[full response]
</details>
```
