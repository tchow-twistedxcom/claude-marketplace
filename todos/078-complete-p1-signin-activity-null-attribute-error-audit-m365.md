---
status: complete
priority: p1
issue_id: "078"
tags: [code-review, bug, mimecast-audit]
dependencies: []
---

# 078 — `audit_m365_sync.py` line 509: `signInActivity: null` causes AttributeError

## Problem Statement

When Microsoft Graph API returns `"signInActivity": null` (explicitly null, not absent), the expression `az_user.get("signInActivity", {}).get("lastSignInDateTime")` raises `AttributeError: 'NoneType' object has no attribute 'get'`. The `.get("signInActivity", {})` default only applies when the key is absent — if the key is present with a null value, it returns `None`. This crashes the orphan-user analysis for any tenant where sign-in activity is null.

## Findings

- **audit_m365_sync.py line 509**: `last_sign_in = az_user.get("signInActivity", {}).get("lastSignInDateTime")`
- Graph API returns `"signInActivity": null` for users with no recorded sign-in (e.g., service accounts, newly created users, or when signInActivity reporting is disabled)
- `.get("signInActivity", {})` returns `None` when key exists with null value → `None.get(...)` → `AttributeError`
- The dict default `{}` only activates when the key is **missing** from the dict entirely
- Flagged by: kieran-python-reviewer (blocking severity)

## Proposed Solutions

### Option A: Use `or {}` pattern (Recommended)
```python
last_sign_in = (az_user.get("signInActivity") or {}).get("lastSignInDateTime")
```
- `or {}` coerces both `None` and absent-key `None` to `{}` before calling `.get()`
- One-line fix, idiomatic Python
- **Effort**: Small | **Risk**: None

### Option B: Explicit None check
```python
sign_in_activity = az_user.get("signInActivity")
last_sign_in = sign_in_activity.get("lastSignInDateTime") if sign_in_activity else None
```
- More explicit but verbose
- **Effort**: Small | **Risk**: None

## Acceptance Criteria
- [ ] No AttributeError when Graph returns `"signInActivity": null`
- [ ] Users with null signInActivity are treated as having no last sign-in date (same as absent)
- [ ] Scan the rest of `audit_m365_sync.py` for any other `.get(key, {}).get(...)` chains on Graph fields that may return null

## Work Log
- 2026-04-08: Identified in 6th code review pass (kieran-python-reviewer, blocking severity)
- 2026-04-08: Fixed in commit c4f4f21 — changed `.get("signInActivity", {}).get(...)` to `(az_user.get("signInActivity") or {}).get(...)`. Scanned entire file; no other `az_user.get(..., {}).get(...)` chains found. Single-line fix, no behavior change for absent keys.
