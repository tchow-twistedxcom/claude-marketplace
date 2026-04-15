---
status: pending
priority: p1
issue_id: "100"
tags: [code-review, quality, azure-ad, manifest]
dependencies: []
---

# 100 — `manifest.json` `azure_ad_delete_inbox_rule` still says wrong rule-ID source (regression from 080)

## Problem Statement

Todo 080 fixed the `azure_ad_delete_inbox_rule` docstring in `server.py` and `SKILL.md` to remove the false claim that rule IDs come from `azure_ad_ual_inbox_rules`. However, `manifest.json` was not updated — it still says "Use rule IDs from azure_ad_ual_inbox_rules or azure_ad_incident_triage". This is a P1 regression: the MCP manifest is the authoritative source consumers read to understand tool parameters, so the stale description will mislead any agent or developer building on this tool.

## Findings

- **`extensions/azure-ad/manifest.json` line 256**: `azure_ad_delete_inbox_rule` `rule_id` parameter description still reads "Use rule IDs from azure_ad_ual_inbox_rules or azure_ad_incident_triage"
- The correct source is `azure_ad_list_inbox_rules` (the new dedicated listing tool added in this PR)
- `server.py` docstring was corrected in 080; `SKILL.md` was corrected in 093; manifest was overlooked
- Flagged by: agent-native-reviewer (7th review pass)

## Proposed Solutions

### Option A: Update manifest.json parameter description (recommended)

Find and replace the stale description in `manifest.json`:
```json
"description": "Inbox rule ID to delete. Obtain from azure_ad_list_inbox_rules."
```

- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria

- [ ] `manifest.json` `azure_ad_delete_inbox_rule` `rule_id` parameter description updated to reference `azure_ad_list_inbox_rules`
- [ ] Description matches what `server.py` docstring and `SKILL.md` now say

## Work Log

- 2026-04-08: Identified in 7th code review pass (agent-native-reviewer) — regression from 080 fix that only updated server.py + SKILL.md
