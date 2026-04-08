---
status: pending
priority: p1
issue_id: "054"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 054 — `sweep.py` MFA fatigue outer `break` exits victim loop too early

## Problem Statement

In `sweep.py` `collect_mfa_fatigue_victims()` (line 146), the outer `for fail in user_failures` loop has a stray `break` that exits after checking only the first failure per user. If the first failure has no matching success within the time window but a later failure does, the victim is missed entirely.

## Findings

```python
# sweep.py lines 140-148
for fail in user_failures:
    f_success = f"userPrincipalName eq '{safe_upn}' and status/errorCode eq 0 ..."
    succ_result = api.security_sign_ins(...)
    for s in successes:
        if ...:
            evidence.append(...)
            break  # inner break: correct — stop checking successes once confirmed
    if evidence:
        break  # OUTER break: WRONG — exits after first failure checked, misses later failures
```

The outer `break` was likely intended as "stop early once we have enough evidence". But since `evidence` is appended incrementally during the loop, the break means: if the first failure produces no evidence, we exit the loop entirely without checking remaining failures for that user. Real MFA fatigue victims are silently missed.

## Proposed Solutions

Option A (Recommended): Remove the outer `break` at line 146. The loop should always check all failures. The inner `break` already short-circuits the success scan correctly.
- Effort: Trivial (remove 1 line). Risk: Low.

Option B: Replace `break` with `continue` — but this still does not make sense semantically. Remove is correct.

## Acceptance Criteria

- [ ] Outer `break` on line 146 of `sweep.py` removed
- [ ] MFA fatigue victim collection checks all failures per user, not just the first

## Work Log

- 2026-04-08: Found by kieran-python-reviewer in 4th review pass
