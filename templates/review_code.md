# Code Review Template
# Usage: call("coding", template.replace("{{CODE}}", code).replace("{{LANGUAGE}}", "python"))

Review the following {{LANGUAGE}} code as a senior engineer:

```{{LANGUAGE}}
{{CODE}}
```

Structure your review as:

## 🔴 Critical Issues
(bugs, security vulnerabilities, data loss risks — must fix before merging)

## 🟡 Warnings
(performance problems, bad practices, maintainability issues — fix soon)

## 🟢 Suggestions
(improvements, style, better approaches — nice to have)

## ✅ Strengths
(what the code does well — be specific)

## Summary
One paragraph: overall code quality assessment and the single most important change.

Be specific: cite line numbers or function names. Don't be vague.
