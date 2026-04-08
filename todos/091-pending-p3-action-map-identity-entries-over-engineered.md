---
status: pending
priority: p3
issue_id: "091"
tags: [code-review, simplicity, azure-ad]
dependencies: []
---

# 091 — `_action_map` dict with identity mappings is over-engineered

## Problem Statement

`_action_map` (server.py lines 1374-1378) is a dict with 3 entries that map action strings to themselves (identity mappings). This adds indirection without transformation. The dict can be replaced with a direct lookup or a set check.

## Findings

- **server.py lines 1374-1378**: `_action_map = {"block": "block", "unblock": "unblock", "enable": "enable"}` (approximately) — 3 identity mappings
- A dict with identity mappings is equivalent to `action in {"block", "unblock", "enable"}`
- Flagged by: code-simplicity-reviewer

## Proposed Solutions

### Option A: Replace with set membership check
```python
VALID_ACTIONS = {"block", "unblock", "enable"}
if action not in VALID_ACTIONS:
    raise ValueError(f"Invalid action: {action!r}")
```
- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria
- [ ] `_action_map` replaced with a set or direct validation
- [ ] Behavior identical — invalid actions still raise errors

## Work Log
- 2026-04-08: Identified in 6th code review pass (code-simplicity-reviewer)
