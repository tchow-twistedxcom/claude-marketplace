---
status: complete
priority: p1
issue_id: "013"
tags: [code-review, bug, azure-ad, sweep]
dependencies: []
---

# 013 — sweep.py crashes on import: missing build_time_filter and security_* methods

## Problem Statement

`sweep.py` imports `build_time_filter` from `azure_ad_api` and calls `api.security_sign_ins()`, `api.security_risk_detections()`, `api.security_audit_logs()`, and `api.security_auth_methods()` — none of which exist in `azure_ad_api.py`. The script crashes with `ImportError` before executing a single line. An agent or user running `python3 sweep.py --hours 48` gets an immediate failure.

## Findings

- **File**: `plugins/m365-skills/skills/azure-ad/scripts/sweep.py`, lines 30-31 and throughout `run_sweep()`
- **Agent**: agent-native-reviewer (CRITICAL)

```python
# sweep.py line 30-31 — build_time_filter does not exist in azure_ad_api.py
from azure_ad_api import AzureADAPI, build_time_filter

# Called in run_sweep() but none of these methods exist on AzureADAPI:
api.security_sign_ins(top=500, filter_query=f, all_pages=True)  # no such method
api.security_risk_detections(top=500, ...)                       # no such method
api.security_audit_logs(top=100, ...)                            # no such method
api.security_auth_methods(upn)                                   # no such method
```

`azure_ad_api.py` only has: `users_*`, `groups_*`, `devices_*`, `directory_*` methods.

## Proposed Solutions

### Option A: Add missing methods to azure_ad_api.py (Recommended)
Implement `security_sign_ins`, `security_risk_detections`, `security_audit_logs`, `security_auth_methods`, and `build_time_filter` in `azure_ad_api.py`. This matches the CLI structure documented in `security_api.md`.

The DXT extension `server.py` already implements all of these as async httpx calls — the implementations can be adapted to the synchronous requests-based `AzureADAPI` class.

- **Effort**: Medium (4 methods + build_time_filter helper)
- **Risk**: Low

### Option B: Rewrite sweep.py to call the DXT extension via subprocess
Instead of importing from `azure_ad_api`, invoke the DXT server tools via the MCP client pattern. Less practical for a local CLI script.

- **Effort**: Large
- **Risk**: Medium

### Option C: Stub the missing methods with direct Graph API calls in sweep.py
Implement the API calls inline in `sweep.py` using `requests` directly, without depending on `azure_ad_api`.

- **Effort**: Medium
- **Risk**: Low (but increases duplication)

## Recommended Action

Option A: add the missing methods to `azure_ad_api.py` alongside the existing `users_list`, `groups_list` etc. This also satisfies the `security_api.md` CLI documentation (see todo #018).

## Technical Details

- **Affected files**:
  - `plugins/m365-skills/skills/azure-ad/scripts/sweep.py` (imports)
  - `plugins/m365-skills/skills/azure-ad/scripts/azure_ad_api.py` (add methods)
- **Methods needed**:
  - `build_time_filter(hours, since)` — constructs `createdDateTime ge TIMESTAMP` filter
  - `AzureADAPI.security_sign_ins(top, filter_query, all_pages)` → `GET /auditLogs/signIns`
  - `AzureADAPI.security_risk_detections(top, filter_query)` → `GET /identityProtection/riskDetections`
  - `AzureADAPI.security_audit_logs(top, filter_query)` → `GET /auditLogs/directoryAudits`
  - `AzureADAPI.security_auth_methods(upn)` → `GET /users/{upn}/authentication/methods`

## Acceptance Criteria

- [ ] `python3 sweep.py --hours 48` runs without ImportError
- [ ] All 6 detection vectors produce output (or empty results) for a real tenant
- [ ] `build_time_filter` is importable from `azure_ad_api`

## Work Log

- 2026-04-07: Identified by agent-native-reviewer as critical (sweep.py crashes on import)
