---
status: pending
priority: p2
issue_id: "014"
tags: [code-review, security, injection, azure-ad, dxt]
dependencies: []
---

# 014 — OData filter injection and KQL injection in azure-ad MCP server

## Problem Statement

`extensions/azure-ad/src/server.py` passes caller-controlled strings directly into OData `$filter` expressions and KQL queries without sanitization. Multiple MCP tools are affected. An attacker (or misconfigured LLM) providing crafted input can bypass scope restrictions and exfiltrate more data than intended from the authorized tenant.

## Findings

- **File**: `extensions/azure-ad/src/server.py`
- **Agent**: security-sentinel (HIGH-1, HIGH-2)

**OData injection (HIGH-1):**
```python
# Line 169-170 — raw passthrough of caller input
if filter_query:
    params["$filter"] = filter_query  # no sanitization

# Lines 484, 640 — unsanitized interpolation
filters.append(f"userPrincipalName eq '{user}'")  # user is caller-controlled
filters.append(f"initiatedBy/user/userPrincipalName eq '{user}'")

# Lines 320, 398 — device/group name interpolated
params = {"$filter": f"displayName eq '{group_id}'"}
params = {"$filter": f"displayName eq '{device_id}'"}
```

**KQL injection (HIGH-2):**
```python
# Lines 1260-1263 — no validation on raw KQL
result = await _graph("POST", "/security/runHuntingQuery", data={"Query": q})

# Lines 1697, 1703 — upn interpolated into KQL
cloud_kql = f"CloudAppEvents | where AccountUpn =~ '{upn}' ..."
```

The `| limit` check at line 1261 is not a security control — it's easily bypassed with a comment or string literal containing the word "limit".

## Proposed Solutions

### Option A: Input validation + single-quote escaping (Recommended)
Validate typed parameters (email, IP, UPN) with format checks before interpolation:

```python
import re

EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
IP_RE = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')

def _safe_email(value: str) -> str:
    if not EMAIL_RE.match(value):
        raise ValueError(f"Invalid email format: {value!r}")
    return value.replace("'", "''")  # OData single-quote escape

def _safe_kql_string(value: str) -> str:
    """Reject KQL metacharacters in user-supplied values."""
    if any(c in value for c in ("|", ";", "//", "'", '"')):
        raise ValueError(f"Invalid characters in value: {value!r}")
    return value
```

- **Effort**: Medium
- **Risk**: Low

### Option B: Document filter_query as trusted-caller only
Add a docstring note to `filter_query` parameters stating they are not sanitized and intended for admin/trusted use. Add a `_ALLOW_RAW_FILTER` constant that defaults to `False`.

- **Effort**: Small
- **Risk**: Medium (doesn't fix injection, just documents it)

### Option C: Remove raw filter_query passthrough, keep typed parameters only
Remove the `filter_query` open-ended passthrough from `azure_ad_list_users` and require callers to use structured parameters (`user`, `department`, `enabled_only`).

- **Effort**: Medium
- **Risk**: Low (breaks some flexibility but hardens the surface)

## Recommended Action

Option A for interpolated values (email, UPN, IP, group/device names). Option B for `filter_query` since it's intended for power users — document and scope it clearly.

## Technical Details

- **Affected tools**: `azure_ad_list_users` (line 169), `azure_ad_sign_ins` (line 484), `azure_ad_audit_logs` (line 640), `azure_ad_list_groups` (line 320), `azure_ad_list_devices` (line 398), `azure_ad_advanced_hunt` (lines 1260-1264), `azure_ad_email_events` (line 1697)

## Acceptance Criteria

- [ ] Email/UPN parameters validated with regex before OData interpolation
- [ ] Single-quote escaping applied to all interpolated string values
- [ ] `filter_query` passthrough documented as admin-only or removed
- [ ] KQL metacharacters rejected from `user`/`upn` parameters

## Work Log

- 2026-04-07: Identified by security-sentinel as HIGH-1 and HIGH-2
