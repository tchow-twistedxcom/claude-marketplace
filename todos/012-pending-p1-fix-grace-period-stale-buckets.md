---
status: pending
priority: p1
issue_id: "012"
tags: [code-review, bug, audit, mimecast]
dependencies: []
---

# 012 — grace_period and stale_grace buckets never populated in cross_reference()

## Problem Statement

`audit_m365_sync.py` declares `grace_period` and `stale_grace` result categories in `cross_reference()`, renders full report sections for them, and counts them in `total_issues` — but both buckets are always empty. All disabled-Azure-AD users unconditionally go to `disabled_active`. The grace period date comparison is computed but never evaluated.

The PR description explicitly presents these as distinct severity categories with working classification logic. This is a functional bug that silently makes departed-but-still-active accounts look less urgent than they are.

## Findings

- **File**: `plugins/mimecast-skills/scripts/audit_m365_sync.py`
- **Lines**: 354-356 (grace_cutoff computed, never used), 391-392 (buckets created), 404-417 (no comparison made), 866-884 (report sections for always-empty buckets), 989-993 (total_issues includes stale_grace)
- **Agents**: kieran-python-reviewer (CRITICAL), code-simplicity-reviewer, pattern-recognition-specialist

```python
# Line 356: computed but never used
grace_cutoff = now - timedelta(days=grace_days)

# Lines 404-417: all disabled users go here unconditionally
elif email in azure_disabled:
    az_user = azure_disabled[email]
    created_str = az_user.get("createdDateTime", "")  # fetched but never used
    results["disabled_active"].append(disabled_entry)  # ALWAYS ends up here
    # grace_period and stale_grace are never appended to
```

## Proposed Solutions

### Option A: Implement the grace period classification logic (Recommended)
Wire up the existing `grace_cutoff` against the user's `createdDateTime` field.

```python
elif email in azure_disabled:
    az_user = azure_disabled[email]
    disabled_entry = {
        "email": email,
        "display_name": az_user.get("displayName", ""),
        "azure_status": "disabled",
    }
    # Parse the disable date (use createdDateTime as proxy if disabledDateTime unavailable)
    created_str = az_user.get("createdDateTime", "")
    if created_str:
        try:
            created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            if created_dt > grace_cutoff:
                results["grace_period"].append(disabled_entry)
            else:
                results["stale_grace"].append(disabled_entry)
        except ValueError:
            results["disabled_active"].append(disabled_entry)
    else:
        results["disabled_active"].append(disabled_entry)
```

Note: `createdDateTime` is the account creation date, not the disable date. For accurate grace period classification, the Azure AD audit log (sign-in activity or `lastSignInDateTime`) would give a better proxy. A comment should document this limitation.

- **Effort**: Small
- **Risk**: Low

### Option B: Remove the grace/stale categories entirely
Delete `grace_period`, `stale_grace`, `grace_cutoff`, `--grace-days`, and corresponding report sections (~47 lines). Document as a future enhancement.

- **Pros**: Removes dead code; the remaining `disabled_active` is accurate
- **Cons**: Removes the documented feature
- **Effort**: Small
- **Risk**: Low

## Recommended Action

Option A if the classification is meaningful for the organization. Option B if the `createdDateTime` proxy is too imprecise to be actionable.

## Technical Details

- **Affected file**: `plugins/mimecast-skills/scripts/audit_m365_sync.py`
- **Lines to fix**: 404-417 (add branch for grace/stale routing)

## Acceptance Criteria

- [ ] Disabled Azure AD users are correctly routed to `grace_period`, `stale_grace`, OR `disabled_active` based on account age
- [ ] Report sections for `grace_period` and `stale_grace` contain accurate counts
- [ ] OR: both categories and `--grace-days` are removed and report sections updated accordingly

## Work Log

- 2026-04-07: Identified as CRITICAL by kieran-python-reviewer and confirmed by simplicity-reviewer and pattern-recognition-specialist
