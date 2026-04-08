---
status: pending
priority: p2
issue_id: "073"
tags: [code-review, azure-ad, agent-native, quality]
dependencies: []
---

# 073 — Manifest/docs/IR bundle: confirm guards missing from 4 manifests, SKILL.md stale fields, missing Returns, IR capability gaps

## Problem Statement

Several documentation gaps that degrade agent usability during time-sensitive IR workflows, plus two missing IR capability tools:

1. **4 manifest descriptions omit `confirm=True` requirement** — agents call expecting action, get dry-run dict, waste a round-trip.
2. **SKILL.md documents wrong field names** for `azure_ad_incident_triage` output (signIns/inboxRules/sentMail/ualEvents — all wrong).
3. **SKILL.md "capabilities" section** lists Create/Update/Delete/License/Group management — these are CLI-only, not MCP tools.
4. **3 tools missing Returns sections** in their docstrings.
5. **IR completion gap**: no `azure_ad_delete_inbox_rule` tool (triage detects rule IDs, agents cannot remediate).
6. **IR completion gap**: no `azure_ad_dismiss_risky_users` tool (agents cannot close risk records after remediation).
7. **Top cap undocumented** in `azure_ad_advanced_hunt` and `azure_ad_email_events`.

## Findings

### 1. Manifest confirm guard omissions (manifest.json)
- `azure_ad_advanced_hunt`: description says nothing about `confirm=True` — agent calls, gets `{"status": "dry_run", ...}`, has to infer
- `azure_ad_revoke_sessions`: "Revoke all active sign-in sessions" — does NOT revoke until `confirm=True`
- `azure_ad_confirm_compromised`: "triggers remediation" — may immediately lock user; `confirm=True` required
- `azure_ad_delete_ca_policy`: "Delete a Conditional Access policy" — irreversible, `confirm=True` required

### 2. SKILL.md stale field names for `azure_ad_incident_triage`
Documented: `signIns, inboxRules, sentMail, ualEvents`
Actual output keys: `suspiciousSignIns, maliciousRules, suspiciousSentMail, ualFindings`
Also undocumented: `account`, `riskSummary`

### 3. SKILL.md misleading capabilities section
Lists "Create/Update/Delete: Full user lifecycle management", "Licensing", "Devices / Update/Delete" as MCP capabilities. These are CLI (`azure_ad_api.py`) operations only — no MCP tools exist for them.

### 4. Missing Returns sections in docstrings
- `azure_ad_sent_emails` — returns `{"user", "count", "messages": [{sentDateTime, subject, to, cc, hasAttachments, messageId}]}`
- `azure_ad_get_email` — returns `{sentDateTime, subject, from, to, cc, hasAttachments, bodyPreview, body[:5000]}`
- `azure_ad_list_ca_policies` — returns `{"count", "policies": [{id, displayName, state, includeUsers, includeGroups, grantControls}]}`

### 5. IR gap: no `azure_ad_delete_inbox_rule`
`azure_ad_incident_triage` and `azure_ad_ual_inbox_rules` detect malicious rules and return their IDs. No tool to delete them — agents must ask operator to manually remove via Exchange Admin Center.

### 6. IR gap: no `azure_ad_dismiss_risky_users`
`azure_ad_confirm_compromised` marks users compromised. After remediation (password reset + sessions revoked + MFA re-enrolled), risk state persists at `confirmedCompromised` indefinitely. No tool to call `POST /identityProtection/riskyUsers/dismiss`.

### 7. Top cap undocumented
`azure_ad_advanced_hunt` and `azure_ad_email_events` have hard cap `min(top, 10000)` — not mentioned in docstrings. Callers passing values above 10,000 will be silently truncated.

## Proposed Solutions

**Option A (Recommended):**
1. Append to each of the 4 manifest descriptions: `"Requires confirm=True to execute — previews action by default."` (tailor message for each tool).
2. Update SKILL.md `azure_ad_incident_triage` output fields to actual key names; add `account`, `riskSummary`.
3. Split or re-label SKILL.md "capabilities" section to distinguish MCP tools from CLI-only operations.
4. Add Returns sections to the 3 tool docstrings.
5. Add `azure_ad_delete_inbox_rule(user_id, rule_id, confirm=False)` tool wrapping `DELETE /users/{user_id}/mailFolders/inbox/messageRules/{rule_id}`.
6. Add `azure_ad_dismiss_risky_users(user_ids, confirm=False)` tool wrapping `POST /identityProtection/riskyUsers/dismiss`.
7. Document 10,000 cap in `top` parameter docstrings.
- Effort: Small (1–4, 7); Medium (5, 6 — new tools). Risk: Low.

## Acceptance Criteria

- [ ] 4 manifest descriptions include `confirm=True` requirement and what happens without it
- [ ] SKILL.md `azure_ad_incident_triage` output fields match actual keys
- [ ] SKILL.md capabilities section distinguishes MCP from CLI
- [ ] Returns sections added to `azure_ad_sent_emails`, `azure_ad_get_email`, `azure_ad_list_ca_policies`
- [ ] `azure_ad_delete_inbox_rule` tool added (optional — if out of scope, document the gap in SKILL.md)
- [ ] `azure_ad_dismiss_risky_users` tool added (optional — if out of scope, document in SKILL.md)
- [ ] Top cap documented in `azure_ad_advanced_hunt` and `azure_ad_email_events` `top` param descriptions

## Work Log

- 2026-04-08: Identified by agent-native-reviewer (FINDING-4/5/6/7/8/9/10/11/12/13/14) and pattern-recognition-specialist (FINDING-7/8/9/10) in 5th review pass
