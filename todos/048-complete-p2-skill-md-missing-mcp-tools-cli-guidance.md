---
status: pending
priority: p2
issue_id: "048"
tags: [code-review, documentation, azure-ad, mimecast]
dependencies: []
---

# 048 — SKILL.md gaps — 26 of 47 MCP tools invisible to agents + no CLI vs MCP guidance + mimecast prerequisites

## Problem Statement

Three documentation gaps in `plugins/m365-skills/skills/azure-ad/SKILL.md` and the mimecast-audit SKILL.md that reduce agent usability. Agents loading the skill cannot discover the primary containment tool (`revoke_sessions`) from SKILL.md alone, default to CLI when MCP tools are available, and cannot verify prerequisites before running the audit.

## Findings

### 1. 26 of 47 MCP tools undocumented in SKILL.md

`plugins/m365-skills/skills/azure-ad/SKILL.md` documents 21 security/forensics tools in detail but omits all 26 foundational tools:

- Users: `list_users`, `get_user`, `search_users`, `user_member_of`, `user_manager`, `user_direct_reports`, `user_devices`
- Groups: `list_groups`, `get_group`, `group_members`, `group_owners`
- Devices: `list_devices`, `get_device`
- Directory: `organization`, `domains`, `licenses`, `directory_roles`
- Security: `sign_ins`, `sign_in_get`, `risk_detections`, `risky_users`, `risky_user_history`, `audit_logs`, `auth_methods`, `named_locations`
- Actions: `revoke_sessions`, `confirm_compromised`

An agent loading this skill cannot discover `revoke_sessions` (the primary containment tool) from SKILL.md alone.

### 2. No CLI vs MCP decision guidance

SKILL.md shows both CLI commands and MCP tool references but never explains when to prefer one over the other. Agents default to CLI (which requires cwd setup and subprocess overhead) when MCP tools are available and more convenient.

### 3. mimecast-audit prerequisites not agent-actionable

The prerequisites section says "configure both CLIs" but does not provide test commands for agents to verify configuration before running the audit. An agent cannot confirm readiness without trial-and-error.

## Proposed Solutions

### Option A — Full documentation update (Recommended)

- Add a compact "Basic Operations" table to SKILL.md listing all 26 undocumented tools with one-line descriptions.
- Add a "CLI vs MCP" decision box near the top of SKILL.md: "If the azure-ad MCP server is running (test: call `azure_ad_list_users`), prefer MCP tools — no cwd required, structured JSON, 47 operations. Use CLI only when MCP is unavailable."
- Expand mimecast-audit prerequisites to include test commands: `python3 scripts/mimecast_api.py users list --output json` and `python3 scripts/azure_ad_api.py users list --format json`.
- Effort: Small, Risk: None

## Acceptance Criteria

- [ ] SKILL.md lists all 47 MCP tools (either individually or in a compact table)
- [ ] SKILL.md has CLI vs MCP guidance near the top
- [ ] mimecast-audit SKILL.md prerequisites include test commands for both CLIs
- [ ] SKILL.md tool count updated to "47" in all places where the count is stated

## Work Log

- 2026-04-08: Identified in 3rd review pass
