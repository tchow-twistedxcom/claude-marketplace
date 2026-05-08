---
status: complete
priority: p3
issue_id: "097"
tags: [code-review, agent-native, azure-ad, documentation]
dependencies: []
---

# 097 — `azure_ad_create_ca_policy` missing Returns docstring section

## Problem Statement

`azure_ad_create_ca_policy` lacks a Returns section in its docstring. The tool returns the created policy object including an `id` field that is required for subsequent `azure_ad_update_ca_policy` or `azure_ad_delete_ca_policy` calls. Without documenting the return shape, an agent cannot know how to extract the ID for chaining.

## Findings

- **server.py lines 1352-1407**: `azure_ad_create_ca_policy` — no Returns section
- Function ends with `return _fmt(result)` where `result` is the Graph API response (standard CA policy object)
- Key chaining fields: `id`, `displayName`, `state`
- Compare: `azure_ad_list_ca_policies` documents its return shape explicitly
- Flagged by: agent-native-reviewer (observation)

## Proposed Solutions

### Option A: Add Returns section to docstring
```
Returns:
    Created CA policy object including:
    - id: Policy GUID — use with azure_ad_update_ca_policy or azure_ad_delete_ca_policy
    - displayName: Policy name
    - state: "enabled", "disabled", or "enabledForReportingButNotEnforced"
    - conditions, grantControls: as specified in the request
```
- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria
- [ ] `azure_ad_create_ca_policy` has a Returns section documenting `id` and key fields
- [ ] Downstream chaining tools referenced in the Returns description

## Work Log
- 2026-04-08: Identified in 6th code review pass (agent-native-reviewer)
- 2026-04-08: Fixed — added Returns section to azure_ad_create_ca_policy docstring documenting id (GUID for chaining), displayName, and state fields. Commit: fix(azure-ad): resolve 6th review todos 077-098a in server.py
