---
status: pending
priority: p3
issue_id: "052"
tags: [code-review, documentation, azure-ad]
dependencies: []
---

# 052 — Agent-native docstring accuracy — CA policy GUID, confirm_compromised list syntax, ual_hours cap, sweep.md path

## Problem Statement

Four docstring and documentation accuracy issues across `server.py` and `commands/azure-ad-sweep.md` that would mislead agents into producing non-actionable errors or silently incorrect behavior.

## Findings

1. **`azure_ad_create_ca_policy` GUID requirement not stated** (`server.py`): The docstring says "Use `azure_ad_named_locations` to find IDs" but doesn't say the IDs are GUIDs (not display names). An agent passing display names gets a non-actionable 400 error. Fix: add "Named Location IDs are GUIDs — pass the `id` field, not the display name" and a usage example sequence.

2. **`azure_ad_confirm_compromised` missing list syntax example** (`server.py`): `users: list[str]` parameter has no example. An agent may pass a comma-separated string. Fix: add `users=["<object-id-1>", "<object-id-2>"]` example.

3. **`azure_ad_incident_triage` silent `ual_hours` cap** (`server.py`): When `ual_hours > 24`, the value is silently capped to 24. The return value includes `ualWindowHours` but doesn't flag the truncation. Fix: add note to docstring "Setting ual_hours > 24 is silently capped to 24" and consider adding `ualCoverageCapped: true` to return when truncation occurs.

4. **`azure-ad-sweep.md` relative path** (`commands/azure-ad-sweep.md`): The command uses `cd plugins/m365-skills/skills/azure-ad/scripts` (relative to repo root). If an agent's cwd is not the repo root, this fails. Fix: use absolute path or `PYTHONPATH` env var to make the command cwd-independent.

## Proposed Solutions

Option A (Recommended):
- Update all 4 docstrings/command files with the noted fixes
- All are documentation-only changes with no functional impact
- Effort: Small, Risk: None

## Acceptance Criteria

- [ ] `azure_ad_create_ca_policy` docstring includes "IDs are GUIDs, not display names" + example sequence
- [ ] `azure_ad_confirm_compromised` docstring includes list syntax example
- [ ] `azure_ad_incident_triage` docstring notes ual_hours cap; return includes `ualCoverageCapped` when applicable
- [ ] `azure-ad-sweep.md` command uses cwd-independent path invocation

## Work Log

- 2026-04-08: Identified in 3rd review pass
