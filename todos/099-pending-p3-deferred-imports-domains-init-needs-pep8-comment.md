---
status: pending
priority: p3
issue_id: "099"
tags: [code-review, quality, mimecast-skills]
dependencies: []
---

# 099 — Deferred imports at bottom of `domains/__init__.py` need clarifying PEP 8 comment

## Problem Statement

`domains/__init__.py` has deferred imports after the `register_domain` decorator function definition (to avoid circular imports). PEP 8 requires imports at the top of the file. Placing them after function definitions without explanation looks like an error to readers unfamiliar with the module structure. A brief comment explaining the necessity prevents future developers from "fixing" this by moving the imports to the top (which would break circular import resolution).

## Findings

- **domains/__init__.py**: Imports of domain classes appear after function definitions
- Standard Python convention is all imports at top of file
- Deferred placement is necessary because domain modules import from `__init__.py` (circular dependency)
- No comment explaining why imports are deferred
- Flagged by: kieran-python-reviewer

## Proposed Solutions

### Option A: Add clarifying comment before deferred imports
```python
# Deferred imports: domain modules import `register_domain` from this package,
# so they must be imported AFTER the decorator is defined to avoid circular imports.
from .awareness_training import AwarenessTrainingDomain  # noqa: E402
from .directory_sync import DirectorySyncDomain           # noqa: E402
from .human_risk import HumanRiskDomain                   # noqa: E402
```
- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria
- [ ] Comment above deferred imports explains the circular import necessity
- [ ] `# noqa: E402` added to suppress linting warnings about import position

## Work Log
- 2026-04-08: Identified in 6th code review pass (kieran-python-reviewer)
