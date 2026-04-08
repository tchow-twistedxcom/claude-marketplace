---
status: pending
priority: p3
issue_id: "113"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 113 — `server.py` lines 2218/2281: redundant `not isinstance(x, Exception)` when already checking `isinstance(x, dict)`

## Problem Statement

Two locations in `server.py` have double isinstance guards where one check makes the other impossible:

- Line 2218: `if isinstance(mailbox_data, dict) and not isinstance(mailbox_data, Exception):`
- Line 2281: `if not isinstance(cloud_events_raw, Exception) and isinstance(cloud_events_raw, dict):`

A `dict` can never be an `Exception` instance. The `not isinstance(..., Exception)` check is logically dead — the `isinstance(..., dict)` check already excludes all Exception instances. These add reading noise without providing any safety.

## Findings

- **`server.py` line 2218**: dead `not isinstance(mailbox_data, Exception)` guard
- **`server.py` line 2281**: dead `not isinstance(cloud_events_raw, Exception)` guard
- Both can be simplified to just `isinstance(..., dict)`
- Flagged by: code-simplicity-reviewer (7th review pass)

## Proposed Solutions

### Option A: Remove the redundant `not isinstance(..., Exception)` checks

```python
# line 2218:
if isinstance(mailbox_data, dict):

# line 2281:
if isinstance(cloud_events_raw, dict):
```

- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria

- [ ] Lines 2218 and 2281 simplified to single `isinstance(..., dict)` check each

## Work Log

- 2026-04-08: Identified in 7th code review pass (code-simplicity-reviewer)
