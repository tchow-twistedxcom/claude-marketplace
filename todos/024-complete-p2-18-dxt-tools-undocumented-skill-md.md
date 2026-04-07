---
status: complete
priority: p2
issue_id: "024"
tags: [code-review, agent-native, documentation, m365-skills]
dependencies: [021]
completed: 2026-04-07
---

# 024 — 18 new DXT tools undocumented in SKILL.md (incident triage, email forensics, Defender hunting invisible to agents)

## Problem Statement

`server.py` adds 18 tools that have no equivalent in the CLI and are not mentioned anywhere in `SKILL.md` or `security_api.md`. The highest-value new tool — `azure_ad_incident_triage` — can orchestrate a complete compromise investigation in a single call. An agent reading SKILL.md will never discover this capability.

Missing from SKILL.md / security_api.md:
- `azure_ad_incident_triage` — full orchestrated compromise triage
- `azure_ad_sent_emails`, `azure_ad_search_mail`, `azure_ad_get_email` — email forensics
- `azure_ad_ual_inbox_rules`, `azure_ad_ual_mailbox_access`, `azure_ad_ual_search`, `azure_ad_ual_sharepoint` — UAL forensics
- `azure_ad_advanced_hunt`, `azure_ad_email_events`, `azure_ad_email_attachments` — Defender hunting
- `azure_ad_user_oauth_grants`, `azure_ad_mailbox_settings`, `azure_ad_mfa_changes`, `azure_ad_role_changes` — post-compromise persistence
- `azure_ad_list_ca_policies`, `azure_ad_create_named_location`, `azure_ad_create_ca_policy`, `azure_ad_update_ca_policy`

The SKILL.md frontmatter also lacks activation keywords: "email forensics", "inbox rules", "forwarding rules", "OAuth persistence", "Defender hunting", "KQL", "incident triage".

## Findings

- **File**: `plugins/m365-skills/skills/azure-ad/SKILL.md` — no DXT tools section
- **File**: `plugins/m365-skills/skills/azure-ad/references/security_api.md` — no DXT tools section
- **Agent**: agent-native-reviewer (CRITICAL)

SKILL.md coverage: 12/30 distinct capabilities are discoverable. 18 capabilities are completely invisible to agents.

## Proposed Solutions

### Option A: Add DXT Extension section to SKILL.md (Recommended)
Add a `### DXT Extension Tools (MCP Server)` section after Security Domain listing all 18+ tools with one-line descriptions, grouped by category. Also add activation keywords to frontmatter description.

### Option B: Add DXT section to security_api.md
Move the DXT documentation to `security_api.md` (already referenced from SKILL.md) and update SKILL.md description frontmatter keywords.

## Recommended Action

Option A — add to SKILL.md. The file already has a Capabilities section with domain subsections; add a DXT Extension subsection.

## Acceptance Criteria

- [ ] `azure_ad_incident_triage` is discoverable via SKILL.md
- [ ] Email forensics tools are mentioned in SKILL.md
- [ ] Defender hunting tools are mentioned in SKILL.md
- [ ] SKILL.md frontmatter description includes: "email forensics", "incident triage", "Defender hunting", "inbox rules", "OAuth persistence"

## Work Log

- 2026-04-07: Identified by agent-native-reviewer (CRITICAL — 18/48 tools invisible)
- 2026-04-07: Resolved. Updated `plugins/m365-skills/skills/azure-ad/SKILL.md`:
  - Added 9 new activation keyword lines to frontmatter description (incident triage, email
    forensics, UAL, KQL/Defender hunting, OAuth persistence, forwarding rules, CA policy,
    SharePoint forensics, MFA/role changes)
  - Added `### MCP Extension Tools (Agent-Native)` section under Capabilities with 5 categories:
    Incident Response (1 tool), Email Forensics (3 tools), UAL Forensics (4 tools),
    Defender/KQL Hunting (3 tools), Post-Compromise Persistence (4 tools),
    CA Policy Management (5 tools) — 20 tools total documented (19 from the todo list + delete)
  - Each tool entry has a one-line description drawn from server.py docstrings
  - Added note that tools require MCP server configured via .mcp.json or DXT install
  - Committed as: `docs(skill): document 18 DXT MCP extension tools in SKILL.md (todo 024)`
