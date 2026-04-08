---
status: pending
priority: p2
issue_id: "085"
tags: [code-review, agent-native, azure-ad, documentation]
dependencies: []
---

# 085 — `azure_ad_dismiss_risky_users` docstring doesn't warn that UPNs cause 400 errors

## Problem Statement

`azure_ad_dismiss_risky_users` requires Azure AD object IDs (GUIDs), not UPNs, in the `user_ids` list. The Graph API endpoint `/identityProtection/riskyUsers/dismiss` returns HTTP 400 if a UPN is passed. The current docstring says "Get IDs from `azure_ad_risky_users` or `azure_ad_get_user`" but doesn't clarify which field to use or warn about the UPN failure mode. An agent might pass UPNs (which appear throughout other tool outputs) and receive a silent 400.

## Findings

- **server.py lines 1941-1942**: Docstring mentions ID source but not the UPN rejection behavior
- **server.py line 1956**: `data={"userIds": user_ids}` — Graph API requires object IDs here
- `azure_ad_risky_users` output includes `id` (object ID) and `userPrincipalName` fields — agent must know to use `id`
- Contrast: `azure_ad_confirm_compromised` docstring (line 863-865) is more explicit about ID requirements
- Flagged by: agent-native-reviewer (warning severity)

## Proposed Solutions

### Option A: Update docstring with explicit UPN warning (Recommended)
Add to the docstring:
> "**Object IDs (GUIDs) required** — UPNs are not accepted and will return HTTP 400 from the Graph API. Use the `id` field from `azure_ad_risky_users` output, not `userPrincipalName`."

Also update the `confirm=False` preview message to remind agents which field to use.
- **Effort**: Trivial | **Risk**: None

### Option B: Add UPN-to-ID resolution inside the tool
Auto-detect UPNs and call `GET /users/{upn}?$select=id` to resolve before dismissing
- More forgiving but adds Graph calls and complexity
- **Effort**: Medium | **Risk**: Low

## Acceptance Criteria
- [ ] Docstring explicitly states "object IDs required, UPNs return HTTP 400"
- [ ] Docstring identifies `id` field from `azure_ad_risky_users` as the correct source
- [ ] `confirm=False` preview message reinforces this constraint

## Work Log
- 2026-04-08: Identified in 6th code review pass (agent-native-reviewer)
