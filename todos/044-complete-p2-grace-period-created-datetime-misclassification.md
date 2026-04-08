---
status: pending
priority: p2
issue_id: "044"
tags: [code-review, architecture, mimecast]
dependencies: []
---

# 044 — Grace period buckets use `createdDateTime` — misclassifies long-tenured recently-disabled users

## Problem Statement

The grace period logic in `audit_m365_sync.py` uses `createdDateTime` (account creation date) as a proxy for "when was this account disabled" to determine if a recently-offboarded user is within the grace window. This misclassifies users who were created years ago but disabled last week — they will never appear in the grace bucket even though they were just terminated. The result is false-positive orphan reports for legitimate recently-offboarded employees.

## Findings

- `createdDateTime` is the account creation date, not the disable date.
- Azure AD does not provide a native `disabledDateTime` field.
- A user created 3 years ago and disabled last week will have `createdDateTime` well outside the grace window and will appear as a definitive orphan rather than a grace-period case.
- Conversely, a newly-created contractor account that was never properly linked may falsely land in the grace bucket.
- The correct signal for "recently offboarded" is either `signInActivity.lastSignInDateTime` or a custom attribute set by the offboarding workflow.

## Proposed Solutions

### Option A — Switch to `lastSignInDateTime` heuristic (Recommended)

Switch to `signInActivity.lastSignInDateTime` from the Graph API `?$select=signInActivity` endpoint as the grace cutoff heuristic. A user who is disabled AND had a last sign-in within 30 days is likely recently offboarded.

- Effort: Medium, Risk: Low

### Option B — Document the limitation

Accept `createdDateTime` as an acknowledged limitation. Add a comment in code and a note in SKILL.md that the grace period is imprecise for long-tenured accounts, with a recommendation to manually verify the grace bucket.

- Effort: Small, Risk: None (documentation only)

### Option C — Configurable reference field

Add an optional `--grace-reference-field` parameter to let callers choose between `createdDateTime` and `lastSignInDateTime`.

- Effort: Medium, Risk: Low

## Acceptance Criteria

- [ ] Either grace period uses a more accurate "recently disabled" heuristic
- [ ] OR code comments explicitly document the limitation and what it means for audit results
- [ ] SKILL.md notes the limitation if Option B is chosen

## Work Log

- 2026-04-08: Identified in 3rd review pass
