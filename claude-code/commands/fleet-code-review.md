---
description: Deep file-aware code review — pass files directly to fleet-gateway, 3 models in parallel. Works with any file type; auto-routes images to vision models.
---

Review the following file(s) using fleet-gateway's multi-model pipeline:

$ARGUMENTS

## Instructions

If $ARGUMENTS contains file paths (e.g. `src/auth.py`, `./router.py`):
- Use the `llm_analyze_files` MCP tool with `files=[$ARGUMENTS]` — do NOT read the files yourself
- fleet-gateway handles encoding and routing automatically
- For code files, model is auto-set to "coding"; for images, "vision"

If $ARGUMENTS is a description or topic (no file path):
- Fall back to reading relevant code from context and use `llm_call` with model="coding"

Run all 3 reviewers in parallel using `llm_call` or `llm_analyze_files`:

---

**REVIEWER 1 — Security & correctness** (`model="coding"`)

```
system: "You are a senior security engineer and Python expert. Be direct and specific."

prompt: "Review this code for:
1. SECURITY — injection, path traversal, credential exposure, input validation gaps
2. CORRECTNESS — logic errors, edge cases, off-by-ones, exception handling gaps
3. THREAD SAFETY — race conditions, shared mutable state, missing locks

For each issue: severity (Critical/High/Medium/Low), exact location, and concrete fix.
If nothing to report in a section, say 'None found.'"
```

---

**REVIEWER 2 — Architecture & design** (`model="reasoning"`)

```
system: "You are a software architect focused on maintainability and scalability."

prompt: "Review this code for:
1. DESIGN — does the abstraction make sense? coupling, cohesion, SRP violations
2. MAINTAINABILITY — what will be hard to change in 6 months? hidden complexity?
3. MISSING PIECES — error handling, logging, observability, testability
4. TOP 3 IMPROVEMENTS ranked by long-term impact"
```

---

**REVIEWER 3 — Clarity & completeness** (`model="general"`)

```
system: "You are a senior engineer focused on code quality and documentation."

prompt: "Review this code for:
1. READABILITY — naming, structure, self-documenting vs. needs comments
2. API DESIGN — is the public interface intuitive? surprising behavior?
3. STRENGTHS — what is done particularly well?
4. ONE-PARAGRAPH VERDICT — overall quality and the single most impactful change"
```

---

**Synthesize** into a final report:

```markdown
## Code Review: [filename(s)]

**Reviewers:** coding (security), reasoning (architecture), general (clarity)
**Date:** [today]

### 🔴 Critical Issues
(raised by any reviewer at Critical/High severity — fix before merge)
- [issue] — [file:line if known] — raised by: [reviewer(s)]

### 🟡 Warnings
(Medium severity or raised by 1 reviewer — worth addressing)
- [issue] — raised by: [reviewer]

### 🟢 Strengths
- [what works well]

### Top Improvements (by impact)
1. [improvement] — [rationale]
2. [improvement] — [rationale]
3. [improvement] — [rationale]

### Verdict
**[Production-ready / Needs work / Major issues]** — [one sentence]

<details>
<summary>Full individual reviews</summary>

**Reviewer 1 (coding/security):**
[full text]

**Reviewer 2 (reasoning/architecture):**
[full text]

**Reviewer 3 (general/clarity):**
[full text]
</details>
```
