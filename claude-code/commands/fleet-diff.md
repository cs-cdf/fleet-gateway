---
description: Review staged or recent git changes — pass the diff to fleet-gateway for multi-model analysis before committing or opening a PR.
---

Review the current git diff using fleet-gateway:

$ARGUMENTS

## Instructions

**Step 1 — Get the diff:**

- If $ARGUMENTS is empty or "staged": run `git diff --staged` (changes staged for commit)
- If $ARGUMENTS is "unstaged" or "working": run `git diff` (unstaged working tree changes)
- If $ARGUMENTS is a commit/range (e.g. `HEAD~1`, `main..feature`): run `git diff $ARGUMENTS`
- If $ARGUMENTS is a file path: run `git diff -- $ARGUMENTS`

If the diff is empty, tell the user and stop.

Cap the diff at ~8000 tokens if very large (summarise skipped sections).

**Step 2 — Run 2 reviewers in parallel via `llm_call`:**

**REVIEWER 1 — Correctness & security** (`model="coding"`)

```
system: "You are a senior engineer doing a pre-commit diff review. Be precise."

prompt: "Review this git diff:

[DIFF]

Focus on:
1. BUGS introduced — logic errors, off-by-ones, null dereferences
2. SECURITY — any new attack surface, hardcoded secrets, input not validated
3. REGRESSIONS — does this break existing behaviour or contracts?
4. MISSING — tests, error handling, edge cases not covered

For each issue: file + line number from the diff, severity (Critical/High/Medium/Low), fix suggestion.
If the diff looks clean in a category, say 'Clean.'"
```

**REVIEWER 2 — Design & completeness** (`model="general"`)

```
system: "You are a thoughtful code reviewer focused on overall quality."

prompt: "Review this git diff:

[DIFF]

Provide:
1. DESIGN — does the approach make sense? better alternatives?
2. READABILITY — naming, structure, comment quality
3. COMMIT HYGIENE — is this diff focused? should it be split?
4. READY TO MERGE? — yes / needs changes / needs discussion

One paragraph summary."
```

**Step 3 — Synthesize:**

```markdown
## Diff Review: [branch or description]

**Scope:** [N files changed, +X/-Y lines]

### 🔴 Must Fix Before Commit
- [issue] — [file:line] — [fix]

### 🟡 Should Address
- [issue] — [file:line]

### ✅ Looks Good
- [what was done well]

### Merge Readiness
**[Ready / Needs changes / Needs discussion]** — [rationale]

<details>
<summary>Full reviews</summary>

**Reviewer 1 (correctness/security):**
[full text]

**Reviewer 2 (design/completeness):**
[full text]
</details>
```
