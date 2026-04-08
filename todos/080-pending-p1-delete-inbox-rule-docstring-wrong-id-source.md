---
status: pending
priority: p1
issue_id: "080"
tags: [code-review, agent-native, azure-ad, documentation]
dependencies: []
---

# 080 — `azure_ad_delete_inbox_rule` docstring incorrectly claims rule IDs come from `azure_ad_ual_inbox_rules`

## Problem Statement

The docstring for `azure_ad_delete_inbox_rule` (server.py line 1910) instructs agents: "Use rule IDs from `azure_ad_ual_inbox_rules`". However, `azure_ad_ual_inbox_rules` returns UAL audit log events with fields `{time, operation, user, clientIP, userAgent, ruleName, sessionId, rawParameters}` — there is no `id` field. Rule Graph IDs (needed for the DELETE call) only appear in `azure_ad_incident_triage` output (`maliciousRules[].id`), which comes from a separate `GET /messageRules` call. An agent following the documented workflow will look at UAL output, find no `id`, and be unable to complete the deletion.

## Findings

- **server.py line 1910**: Docstring says "Get rule IDs from `azure_ad_ual_inbox_rules`"
- **server.py lines 1012-1021** (`azure_ad_ual_inbox_rules` return shape): `{time, operation, user, clientIP, userAgent, ruleName, sessionId, rawParameters}` — no `id` field
- **server.py line 2152** (`azure_ad_incident_triage` output): `maliciousRules[].id` — this is the correct source of rule Graph IDs
- **SKILL.md line 85**: Same misleading claim — "rule IDs from `azure_ad_ual_inbox_rules`"
- Flagged by: agent-native-reviewer (critical/agent-blocking severity)

## Proposed Solutions

### Option A: Update docstring and SKILL.md (Recommended)
Change the docstring instruction to:
> "Get rule ID from `azure_ad_incident_triage` output (`maliciousRules[].id`) or by listing rules directly via `GET /users/{user}/mailFolders/inbox/messageRules`. `azure_ad_ual_inbox_rules` provides forensic attribution (creator IP, timestamp) but NOT the Graph rule ID needed for deletion."

Update SKILL.md line 85 with the same correction.
- **Effort**: Small | **Risk**: None

### Option B: Add `id` field to `azure_ad_ual_inbox_rules` output
- The UAL audit log doesn't contain the Graph rule ID — this would require a cross-reference lookup against `GET /messageRules` to match by `ruleName`
- More complex and potentially fragile (rules with duplicate names)
- **Effort**: Medium | **Risk**: Medium

## Acceptance Criteria
- [ ] `azure_ad_delete_inbox_rule` docstring accurately describes where to get rule IDs
- [ ] SKILL.md IR workflow section updated to match
- [ ] No mention of `azure_ad_ual_inbox_rules` as ID source in delete tool docs
- [ ] The correct source (`azure_ad_incident_triage` `maliciousRules[].id`) is clearly documented

## Work Log
- 2026-04-08: Identified in 6th code review pass (agent-native-reviewer, agent-blocking)
