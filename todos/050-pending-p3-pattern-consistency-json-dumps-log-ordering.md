---
status: pending
priority: p3
issue_id: "050"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 050 — Pattern consistency — json.dumps vs _fmt(), log-before-API, azure_status dead weight

## Problem Statement

Three minor pattern inconsistencies across `server.py` and `audit_m365_sync.py` that reduce code quality, create misleading audit trails, and add noise to output data.

## Findings

1. **`json.dumps()` in dry-run paths** (`server.py`): Dry-run returns (e.g., in `azure_ad_create_ca_policy`, `azure_ad_update_ca_policy`, `azure_ad_delete_ca_policy`) use `json.dumps(payload, indent=2)` directly instead of the project's `_fmt()` helper. Inconsistent with other return paths.

2. **Destructive ops log before API call**: Some destructive operations log "performing action X" before the Graph API call succeeds, meaning the log entry appears even if the call fails. Should log after success to avoid misleading audit trails.

3. **`azure_status` dead weight in grace entries** (`audit_m365_sync.py`): Grace period bucket entries include `azure_status` field but this field is always the same value (disabled) for all grace entries — it's noise.

## Proposed Solutions

Option A (Recommended):
- Replace `json.dumps(payload, indent=2)` in dry-run returns with `_fmt(payload)`
- Move success log entries to after the API call returns
- Remove `azure_status` from grace bucket entries or move to a summary-level field
- Effort: Small, Risk: Low

## Acceptance Criteria

- [ ] All dry-run return paths use `_fmt()` not `json.dumps()`
- [ ] Destructive operation logs appear after successful API calls
- [ ] `azure_status` removed from per-entry grace records (or documented as intentional)

## Work Log

- 2026-04-08: Identified in 3rd review pass
