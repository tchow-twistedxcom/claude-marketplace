---
status: pending
priority: p1
issue_id: "068"
tags: [code-review, azure-ad, agent-native]
dependencies: []
---

# 068 — Agent-native P1 docstring errors: sign_ins 50199 wrong, email_events shape mismatch, directory_roles wrong xref, advanced_hunt wrong sentinel

## Problem Statement

Four errors in tool docstrings/return shapes that will cause agents to fail or take wrong actions during incident response workflows:

1. `azure_ad_sign_ins` documents error code 50199 as "device code pending" — it is actually the MFA fatigue / AiTM phishing indicator (same code used by `azure_ad_incident_triage` internally). An agent filtering for MFA fatigue attacks will get misleading guidance.
2. `azure_ad_email_events` docstring describes raw Defender row fields (`Timestamp`, `RecipientEmailAddress`, etc.) but the tool returns an aggregated `{totalRows, totalMessages, messages: [{time, subject, sender, recipients: [...]}]}` envelope. Code expecting row fields will fail.
3. `azure_ad_directory_roles` instructs: "Call `azure_ad_group_members` with role ID to see who holds a role." This is wrong — directory roles use `/directoryRoles/{id}/members`, not `/groups/{id}/members`. Every such call returns 404.
4. `azure_ad_advanced_hunt` returns `{"status": "dry_run", ...}` when `confirm=False`, while every other guarded tool returns `{"confirm": False, ...}`. Callers checking for the standard `"confirm": False` sentinel will miss this tool's dry-run response.

## Findings

### 1. `azure_ad_sign_ins` error code 50199 wrong (server.py ~line 566)
```python
# Docstring says:
# 50199 = device code pending
```
`azure_ad_incident_triage` (line 1981) flags the same code as `MFA_FATIGUE`. Microsoft documentation: 50199 = "The token is not valid. User sign-in is required" — appears in adversary-in-the-middle phishing and repeated MFA push scenarios. An agent reading `azure_ad_sign_ins` docstring may dismiss MFA fatigue alerts as benign device auth.

### 2. `azure_ad_email_events` return shape mismatch (server.py ~lines 1473–1522)
Docstring: `Returns rows with: Timestamp, SenderFromAddress, RecipientEmailAddress, Subject, NetworkMessageId, DeliveryStatus, LatestDeliveryAction, ThreatTypes.`
Actual: aggregated by `NetworkMessageId` into `messages` objects with `time`, `subject`, `sender`, `direction`, `deliveryStatus`, `threatTypes`, `recipients: [...]`. `LatestDeliveryAction` and raw row structure are gone from the output.

### 3. `azure_ad_directory_roles` wrong cross-reference (server.py ~line 537)
Docstring: `"Call azure_ad_group_members with role ID to see who holds a role."`
Reality: `azure_ad_group_members` calls `/groups/{group_id}/members`. Directory role objects are not in the `/groups` collection — this returns 404.

### 4. `azure_ad_advanced_hunt` wrong sentinel (server.py ~line 1431)
All other guarded tools: `return json.dumps({"confirm": False, "would_revoke_sessions_for": ..., ...})`
`azure_ad_advanced_hunt`: `return _fmt({"status": "dry_run", "message": "...", "query_preview": ...})`
Any script checking `"confirm" in response` or `response.get("confirm") == False` will miss this tool's dry-run state.

## Proposed Solutions

**Option A (Recommended):**
1. `azure_ad_sign_ins`: change docstring line to `50199 = MFA interrupted / MFA fatigue indicator (used in AiTM phishing — repeated push denial). See azure_ad_incident_triage.`
2. `azure_ad_email_events`: replace the Returns section describing raw row fields with the actual aggregated envelope shape.
3. `azure_ad_directory_roles`: replace cross-reference with: "No direct role-members tool exists — use `azure_ad_role_changes` to see recent role assignments, or `azure_ad_audit_logs` with `category eq 'RoleManagement'`."
4. `azure_ad_advanced_hunt` dry-run response: change return to `{"confirm": False, "message": "...", "query_preview": ...}` to match all other guarded tools.
- Effort: Small. Risk: Low.

## Acceptance Criteria

- [ ] `azure_ad_sign_ins` docstring: 50199 described as MFA fatigue / AiTM indicator
- [ ] `azure_ad_email_events` docstring: Returns section describes `{totalRows, totalMessages, messages: [{time, subject, sender, direction, deliveryStatus, threatTypes, recipients}]}`
- [ ] `azure_ad_directory_roles` docstring: removes incorrect `azure_ad_group_members` cross-reference
- [ ] `azure_ad_advanced_hunt` dry-run response changed from `{"status": "dry_run"}` to `{"confirm": False, ...}`

## Work Log

- 2026-04-08: Identified by agent-native-reviewer (FINDING-1/2/3) and pattern-recognition-specialist (FINDING-1) in 5th review pass
