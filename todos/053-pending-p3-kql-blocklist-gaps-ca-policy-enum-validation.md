---
status: pending
priority: p3
issue_id: "053"
tags: [code-review, security, azure-ad]
dependencies: []
---

# 053 — KQL blocklist gaps (newlines, backticks) and CA policy state/action enum validation

## Problem Statement

Two minor security hardening gaps in `server.py`: the KQL injection blocklist has coverage holes, and CA policy parameters are passed to the Graph API without enum validation, producing non-actionable errors on invalid input.

## Findings

1. **KQL blocklist missing newlines and backticks** (`server.py` BLOCKED_KQL): The existing `BLOCKED_KQL` list blocks keywords like `DROP`, `DELETE`, `EXEC` etc. but does not block `\n` (newline), `\r` (carriage return), or `` ` `` (backtick). In KQL, newlines can be used to inject secondary statements, and backtick is used for variable references that could enable injection. The blocklist is also case-sensitive — `DROP` is blocked but `Drop` is not.

2. **CA policy `state` and `action` not validated** (`server.py`): `azure_ad_create_ca_policy` and `azure_ad_update_ca_policy` accept `state` (`enabled`, `disabled`, `enabledForReportingButNotEnforced`) and `action` (`block`, `mfa`, `compliant`) parameters that are interpolated into the Graph API payload without validation. Invalid values cause non-actionable 400 errors from Graph API.

## Proposed Solutions

Option A (Recommended):
- Add `"\n"`, `"\r"`, `` "`" `` to BLOCKED_KQL and make blocklist checks case-insensitive (`if keyword.upper() in query.upper()`)
- Add `VALID_CA_STATES = {"enabled", "disabled", "enabledForReportingButNotEnforced"}` and `VALID_CA_ACTIONS = {"block", "mfa", "compliantDevice", "compliantApplication"}` with validation before Graph API call
- Effort: Small, Risk: Low

## Acceptance Criteria

- [ ] BLOCKED_KQL checks are case-insensitive
- [ ] Newline and backtick blocked in KQL queries
- [ ] CA policy `state` validated against allowed set before API call
- [ ] CA policy `action` validated against allowed set before API call

## Work Log

- 2026-04-08: Identified in 3rd review pass
