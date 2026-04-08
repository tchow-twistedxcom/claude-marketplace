---
status: pending
priority: p3
issue_id: "094"
tags: [code-review, quality, azure-ad, consistency]
dependencies: []
---

# 094 — `azure_ad_revoke_sessions` and `azure_ad_confirm_compromised` dry-run use `json.dumps()` not `_fmt()`

## Problem Statement

The two older confirm-guarded tools (`azure_ad_revoke_sessions` line 836, `azure_ad_confirm_compromised` line 872) return their dry-run preview using `json.dumps()`. The newer tools added in this PR (`azure_ad_delete_inbox_rule`, `azure_ad_dismiss_risky_users`) correctly use `_fmt()`. All confirm-guarded tools should use the same return path for consistency.

## Findings

- **server.py line 836** (`azure_ad_revoke_sessions` dry-run): `return json.dumps({...}, indent=2)`
- **server.py line 872** (`azure_ad_confirm_compromised` dry-run): `return json.dumps({...}, indent=2)`
- **server.py newer tools**: use `return _fmt({...})` — consistent with rest of codebase
- `_fmt()` handles edge cases (serialization, encoding) that `json.dumps()` may not handle
- Flagged by: pattern-recognition-specialist

## Proposed Solutions

### Option A: Replace `json.dumps()` with `_fmt()` in both old tools
```python
# Before:
return json.dumps({"confirm": False, "preview": ...}, indent=2)
# After:
return _fmt({"confirm": False, "preview": ...})
```
- **Effort**: Trivial | **Risk**: None (same effective output for simple dicts)

## Acceptance Criteria
- [ ] All 6 confirm-guarded tools use `_fmt()` for their dry-run return path
- [ ] No `json.dumps()` in confirm-guard dry-run paths

## Work Log
- 2026-04-08: Identified in 6th code review pass (pattern-recognition-specialist)
