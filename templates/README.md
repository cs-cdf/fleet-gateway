# fleet-gateway Prompt Templates

Ready-to-use prompt templates for each reasoning pattern.
Copy and adapt these for your use case.

## Usage in Python

```python
from fleet_gateway import call
from pathlib import Path

# Load a template
template = Path("templates/review_code.md").read_text()
prompt = template.replace("{{CONTENT}}", my_code).replace("{{LANGUAGE}}", "python")
result = call("coding", prompt)
```

## Templates

| File | Pattern | Use when |
|------|---------|----------|
| `consensus.md` | Consensus | You want multiple model opinions on one question |
| `loop_refine.md` | Loop | You want iterative improvement of a draft |
| `review_code.md` | Review | You want structured code review |
| `review_text.md` | Review | You want structured text/document review |
| `challenge.md` | Challenge | You want to stress-test an idea |
| `brainstorm.md` | Brainstorm | You want diverse creative ideas |
| `swot.md` | SWOT | You want a strategic analysis |
| `perspectives.md` | Perspectives | You want multiple expert viewpoints |
| `adversarial.md` | Adversarial | You want structured attack/defense |
