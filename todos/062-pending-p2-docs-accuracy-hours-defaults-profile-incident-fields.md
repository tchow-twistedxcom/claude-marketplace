---
status: pending
priority: p2
issue_id: "062"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 062 — Docs accuracy bundle — hours defaults, profile default, revoke-sessions hint, tool count, incident_triage fields

## Problem Statement
Six documentation accuracy issues found across SKILL.md files, docstrings, and sweep.py output. Several cause agents to receive less data than expected or fail CLI invocations.

## Findings
1. `server.py` `azure_ad_ual_mailbox_access` (line 1042): docstring says "default 72" but `hours: int = 6`
2. `server.py` `azure_ad_ual_search` (line 1005): docstring says "default 24" but `hours: int = 6`
3. `mimecast-audit SKILL.md` line 34: documents `--mimecast-profile default` but `argparse` default is `"production"` (audit_m365_sync.py line 989)
4. `sweep.py` line 434: `print_report()` next-steps hints reference `security revoke-sessions` CLI subcommand which doesn't exist (only available as MCP tool `azure_ad_revoke_sessions`)
5. `azure-ad SKILL.md` line 153: says "These 26 tools are available" but table has 27 entries
6. `azure-ad SKILL.md` `azure_ad_incident_triage` description: doesn't list output fields `forwardingAddress`, `oauthGrants`, `sentMailSource`, `cloudAppFindings` — agents miss EMAIL_FORWARDING_ACTIVE findings
7. `azure-ad SKILL.md` `azure_ad_advanced_hunt` description: doesn't mention `confirm=True` requirement, causing unnecessary dry-run round-trip

## Proposed Solutions
Option A (Recommended): Fix all 7 documentation issues:
1. `azure_ad_ual_mailbox_access` docstring: `"default 72"` → `"default 6h, max 24h per API limit"`
2. `azure_ad_ual_search` docstring: `"default 24"` → `"default 6h, max 24h per API limit"`
3. SKILL.md `--mimecast-profile default` → either update to `"production"` or change the argparse default to `"default"` (whichever is correct for the actual environment)
4. `sweep.py` revoke-sessions hint: replace with `python3 ${AZURE_AD_CLI} users update <UPN> --data '{"accountEnabled": false}'` or note it requires the MCP tool
5. SKILL.md "26 tools" → "27 tools"
6. SKILL.md incident_triage bullet: add `forwardingAddress`, `oauthGrants`, `sentMailSource`, `cloudAppFindings` to output field listing
7. SKILL.md advanced_hunt: add note "(requires `confirm=True` to execute — defaults to dry-run for safety)"
- Effort: Small. Risk: Low.

## Acceptance Criteria
- [ ] `azure_ad_ual_mailbox_access` docstring correctly says "default 6h"
- [ ] `azure_ad_ual_search` docstring correctly says "default 6h"
- [ ] mimecast-audit SKILL.md profile default matches argparse default
- [ ] `sweep.py` revoke-sessions next-steps hint replaced with accurate command
- [ ] azure-ad SKILL.md basic ops count is correct
- [ ] `azure_ad_incident_triage` SKILL.md entry lists all top-level output fields
- [ ] `azure_ad_advanced_hunt` SKILL.md mentions `confirm=True` requirement

## Work Log
- 2026-04-08: Found by agent-native-reviewer and pattern-recognition-specialist in 4th review pass
