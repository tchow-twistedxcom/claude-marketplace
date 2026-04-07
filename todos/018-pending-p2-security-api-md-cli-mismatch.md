---
status: pending
priority: p2
issue_id: "018"
tags: [code-review, agent-native, azure-ad, documentation]
dependencies: [013]
---

# 018 — security_api.md references CLI commands that don't exist in azure_ad_api.py

## Problem Statement

`security_api.md` documents `python3 azure_ad_api.py security sign-ins`, `python3 azure_ad_api.py security risky-users`, etc. — but `azure_ad_api.py` has no `security` subparser. Every command in the reference doc will fail with `unrecognized arguments`. Additionally, `security_api.md` is not listed in the `azure-ad/SKILL.md` files section, so agents don't know it exists.

## Findings

- **File**: `plugins/m365-skills/skills/azure-ad/references/security_api.md` — documents security CLI subcommand
- **File**: `plugins/m365-skills/skills/azure-ad/scripts/azure_ad_api.py` — no `security` subparser in `create_parser()`
- **File**: `plugins/m365-skills/skills/azure-ad/SKILL.md` — lists `users_api.md`, `groups_api.md`, `devices_api.md`, `directory_api.md` but not `security_api.md`
- **Agent**: agent-native-reviewer

## Proposed Solutions

### Option A: Add security subcommand to azure_ad_api.py (Recommended, synergistic with #013)
Implement the `security` subparser in `azure_ad_api.py` with the operations documented in `security_api.md`:
- `security sign-ins` → `GET /auditLogs/signIns`
- `security risky-users` → `GET /identityProtection/riskyUsers`
- `security risk-detections` → `GET /identityProtection/riskDetections`
- `security audit-logs` → `GET /auditLogs/directoryAudits`
- `security auth-methods` → `GET /users/{upn}/authentication/methods`

This satisfies both `security_api.md` documentation AND `sweep.py` import needs (#013).

- **Effort**: Medium
- **Risk**: Low

### Option B: Update security_api.md to document DXT tools instead
Rewrite `security_api.md` to document the DXT extension tools (`azure_ad_sign_ins`, `azure_ad_risk_detections`, etc.) instead of the CLI. Mark CLI path as "DXT required".

- **Effort**: Small
- **Risk**: Low (but leaves CLI gap)

### Option C: Add only the SKILL.md reference link (minimal)
Add `security_api.md` to the SKILL.md files section so agents at least know it exists, with a note that CLI commands are coming soon.

- **Effort**: Tiny
- **Risk**: Low

## Recommended Action

Option A combined with #013 — one effort to add security methods to `azure_ad_api.py` satisfies both todos. Option C as a quick win regardless.

## Technical Details

- **Files to modify**:
  - `plugins/m365-skills/skills/azure-ad/scripts/azure_ad_api.py` (add security subparser + methods)
  - `plugins/m365-skills/skills/azure-ad/SKILL.md` (add security_api.md to files section)

## Acceptance Criteria

- [ ] `python3 azure_ad_api.py security sign-ins --hours 24` runs without error
- [ ] `security_api.md` is listed in `azure-ad/SKILL.md` files section
- [ ] All 5 security operations documented in `security_api.md` work against actual CLI

## Work Log

- 2026-04-07: Identified by agent-native-reviewer
