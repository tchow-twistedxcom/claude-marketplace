---
status: complete
priority: p1
issue_id: "056"
tags: [code-review, security, azure-ad]
dependencies: []
---

# 056 — `server.py` CA policy enum case mismatch + `compliantDevice`/`compliantApplication` silently maps to `"mfa"`

## Problem Statement

Two related bugs in `azure_ad_create_ca_policy`:

1. `VALID_CA_STATES` contains `"enabledForReportingButNotEnforced"` but `_validate_enum` does `value.lower()` before checking membership in the (mixed-case) set. Since `"enabledForReportingButNotEnforced".lower()` does not match the mixed-case set entry, this valid CA state is always rejected with a ValueError.

2. The grant construction only handles `"block"` vs everything-else-maps-to-`"mfa"`, silently creating an MFA policy when `"compliantDevice"` or `"compliantApplication"` is passed — despite these being in `VALID_CA_ACTIONS` and documented as valid.

## Findings

```python
# server.py lines 97-111
VALID_CA_STATES = {"enabled", "disabled", "enabledForReportingButNotEnforced"}

def _validate_enum(value: str, valid_set: set, field: str) -> str:
    if value.lower() not in valid_set:  # BUG: value.lower() won't match mixed-case entry
        raise ValueError(...)
    return value

# server.py lines 1309-1312
grant = {
    "operator": "OR",
    "builtInControls": ["block"] if action == "block" else ["mfa"],  # BUG: ignores compliantDevice, compliantApplication
}
```

## Proposed Solutions

Option A (Recommended):
- Fix 1: Change `VALID_CA_STATES` to all-lowercase: `{"enabled", "disabled", "enabledforreportingbutnotenforced"}`. Change `_validate_enum` to return `value` directly (callers pass canonical casing). OR: lowercase both sides: `{v.lower() for v in VALID_CA_STATES}` and `value.lower()`.
- Fix 2: Extend grant construction to handle all four action values:
```python
action_map = {"block": "block", "mfa": "mfa", "compliantDevice": "compliantDevice", "compliantApplication": "approvedApplication"}
grant = {"operator": "OR", "builtInControls": [action_map[action]]}
```
- Effort: Small. Risk: Low.

Option B: Remove `compliantDevice`/`compliantApplication` from `VALID_CA_ACTIONS` and docstring until properly implemented — explicitly tell callers these are not yet supported.

## Acceptance Criteria

- [x] `_validate_enum` correctly accepts `"enabledForReportingButNotEnforced"` (case-insensitive match)
- [x] `azure_ad_create_ca_policy` with `action="compliantDevice"` creates a compliant-device policy, not an MFA policy
- [x] `azure_ad_create_ca_policy` with `action="compliantApplication"` creates an approved-application policy, not an MFA policy
- [x] All 4 VALID_CA_ACTIONS values are handled in grant construction

## Work Log

- 2026-04-08: Found by kieran-python-reviewer and agent-native-reviewer in 4th review pass
- 2026-04-08: Fixed both bugs — (056a) `VALID_CA_STATES` changed to all-lowercase `enabledforreportingbutnotenforced` so `value.lower()` in `_validate_enum` matches correctly. (056b) Binary `["block"] if action == "block" else ["mfa"]` replaced with `_action_map` dict mapping all four `VALID_CA_ACTIONS` values to their correct Graph API `builtInControls` strings (`compliantApplication` maps to `approvedApplication` per MS Graph spec). Commit 9be9e78.
