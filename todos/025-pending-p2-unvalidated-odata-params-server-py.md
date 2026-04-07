---
status: pending
priority: p2
issue_id: "025"
tags: [code-review, security, injection, azure-ad]
dependencies: [014]
---

# 025 — Remaining unvalidated OData parameters in server.py (app, country, risk_level, etc.)

## Problem Statement

Todo 014 added `_validate_email`, `_validate_ip`, `_validate_safe_name`, `_validate_kql_value` helpers and applied them to email/IP fields. However, several string parameters in 4 tools are still embedded directly in OData filter strings without any validation:

- `azure_ad_sign_ins`: `app`, `risk_level`, `country` (lines 533, 537, 539)
- `azure_ad_risk_detections`: `risk_level`, `risk_event_type` (lines 592, 594)
- `azure_ad_risky_users`: `risk_level`, `risk_state` (lines 624, 626)
- `azure_ad_audit_logs`: `activity`, `category`, `result_filter` (lines 677, 679, 681)

A value like `risk_level = "low' or 1 eq 1 or riskLevel eq 'high"` bypasses the intended filter restriction.

## Findings

- **File**: `extensions/azure-ad/src/server.py`, lines 533-681
- **Agent**: security-sentinel (H1 — HIGH)

Also: `azure_ad_search_mail` extracts `from:` sender from query string but doesn't escape the sender value (line 1110), while the subject branch correctly does `query.replace("'", "''")`. Inconsistency.

## Proposed Solutions

### Option A: Add allowlist validators for enum-style params (Recommended)
```python
VALID_RISK_LEVELS = {"low", "medium", "high", "none", "hidden", "unknownFutureValue"}
VALID_RISK_STATES = {"atRisk", "confirmedCompromised", "remediated", "dismissed", "none"}
VALID_RESULT_FILTERS = {"success", "failure", "timeout"}

def _validate_enum(value: str, valid_set: set, field: str) -> str:
    if value.lower() not in valid_set:
        raise ValueError(f"Invalid {field} value: {value!r}")
    return value
```

Apply to risk_level, risk_state, result_filter. For free-text fields (app, country, activity, category), apply `_validate_safe_name` or single-quote escaping.

### Option B: Single-quote escape only (minimal)
For all remaining unvalidated string params, apply `.replace("'", "''")` as a minimum OData injection defense.

### Option C: Accept risk for admin-only tool
These are admin tools that require Azure AD credentials to call. Document as admin-only context and accept the risk.

## Recommended Action

Option B immediately (minimal fix), Option A for enum-constrained fields as a follow-up. Also fix the `from:` sender in `azure_ad_search_mail` with one-line `.replace("'", "''")`.

## Acceptance Criteria

- [ ] All string params embedded in OData `$filter` strings in `azure_ad_sign_ins`, `azure_ad_risk_detections`, `azure_ad_risky_users`, `azure_ad_audit_logs` are either escaped or allowlist-validated
- [ ] `azure_ad_search_mail` `from:` sender value is escaped

## Work Log

- 2026-04-07: Identified by security-sentinel as H1 (HIGH) — partial fix from todo 014
