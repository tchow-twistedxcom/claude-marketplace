---
status: complete
priority: p2
issue_id: "049"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 049 — CLI coverage gaps — sign-ins/risky-users missing filter flags + docstring accuracy

## Problem Statement

Three CLI usability gaps in `azure_ad_api.py` (or the equivalent CLI entry points). Agents and users relying on the CLI for filtering must resort to manual JSON post-processing, and a misleading docstring will cause agents to underestimate the time window of UAL inbox rule data.

## Findings

### 1. `azure_ad_sign_ins` CLI missing filter flags

The CLI `sign-ins` command does not expose `--app`, `--error-code`, `--country`, `--risk-level` filtering options that the Graph API supports via `$filter`. Users must fetch all sign-ins and filter manually in the shell. These are high-value filters for incident response (e.g., "show only failed sign-ins from Russia for this user").

### 2. `azure_ad_risky_users` CLI missing `--risk-state` filter

The `risky-users` command does not expose `--risk-state` (values: `atRisk`, `confirmedCompromised`, `remediated`, `dismissed`). This filter is essential for narrowing to actionable users. Without it, the command returns all risky users regardless of state, requiring the caller to filter after the fact.

### 3. `azure_ad_ual_inbox_rules` docstring wrong default

The docstring says "default 72h" but the actual Python default is `hours: int = 6`. An agent relying on this docstring will expect 72 hours of inbox rule change data but only receive 6 hours. This causes false negatives during incident response: an attacker who set a forwarding rule 10 hours ago would not appear in the results.

## Proposed Solutions

### Option A — Add filter flags and fix docstring (Recommended)

- Add `--app`, `--error-code`, `--country`, `--risk-level` to the `sign-ins` CLI subcommand with corresponding Graph `$filter` construction (append conditions with `and`).
- Add `--risk-state` to the `risky-users` CLI subcommand with `$filter=riskState eq '{value}'` construction.
- Fix docstring in `azure_ad_ual_inbox_rules`: change "default 72h" to "default 6h". Consider whether the default itself should also be changed to 72h for incident response use cases.
- Effort: Small per item, Risk: Low

## Acceptance Criteria

- [x] `sign-ins` CLI command accepts `--app`, `--error-code`, `--country`, `--risk-level` filter flags
- [x] `risky-users` CLI command accepts `--risk-state` filter flag
- [x] `azure_ad_ual_inbox_rules` docstring shows the correct default (6h not 72h)

## Work Log

- 2026-04-08: Identified in 3rd review pass
- 2026-04-08: All 3 items resolved by Agent B (azure_ad_api.py commit e5e06d2) and Agent A (server.py docstring in commit bb936ce).
