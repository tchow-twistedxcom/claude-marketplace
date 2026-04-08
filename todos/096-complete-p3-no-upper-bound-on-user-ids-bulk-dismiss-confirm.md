---
status: complete
priority: p3
issue_id: "096"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 096 — No upper bound on `user_ids` list for `dismiss` and `confirm_compromised` bulk API calls

## Problem Statement

`azure_ad_dismiss_risky_users` and `azure_ad_confirm_compromised` both accept `list[str]` inputs with no upper bound check. The Graph API limits bulk operations on `riskyUsers/dismiss` and `riskyUsers/confirmCompromised` to 60 IDs per call. Passing more than 60 produces a Graph API error rather than a helpful validation message from the tool.

## Findings

- **server.py lines 1956**: `data={"userIds": user_ids}` — no `len()` guard
- **server.py line 879** (`confirm_compromised`): similar pattern
- Microsoft Graph docs specify max 60 IDs per `confirmCompromised` and `dismiss` call
- Flagged by: security-sentinel (low severity)

## Proposed Solutions

### Option A: Add length guard before API call
```python
if len(user_ids) > 60:
    raise ValueError(f"Graph API limit: max 60 user IDs per call, got {len(user_ids)}")
```
- Add to both `azure_ad_dismiss_risky_users` and `azure_ad_confirm_compromised`
- **Effort**: Trivial | **Risk**: None

### Option B: Auto-batch into 60-ID chunks
Process in batches of 60 automatically, collecting results
- More user-friendly but adds complexity
- **Effort**: Small | **Risk**: Low

## Acceptance Criteria
- [ ] Both bulk tools validate `len(user_ids) <= 60` before API call
- [ ] Clear error message when limit exceeded
- [ ] Limit documented in tool docstring

## Work Log
- 2026-04-08: Identified in 6th code review pass (security-sentinel)
- 2026-04-08: Fixed — added len(user_ids/users) > 60 guard with clear ValueError message in both azure_ad_confirm_compromised and azure_ad_dismiss_risky_users, placed after confirm check, before Graph API call. Commit: fix(azure-ad): resolve 6th review todos 077-098a in server.py
