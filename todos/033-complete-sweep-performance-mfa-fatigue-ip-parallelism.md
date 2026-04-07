---
status: complete
priority: p3
issue_id: "033"
tags: [code-review, performance, azure-ad, sweep]
dependencies: []
---

# 033 — sweep.py performance: O(n²) MFA fatigue detection + sequential IP sweep API calls

## Problem Statement

Two performance issues in `sweep.py` that degrade severely at scale:

**Issue 1 — O(n) re-scan per UPN in MFA fatigue loop** (lines 88-130): `user_failures = [s for s in failures if s.get('userPrincipalName') == upn]` scans the full failures list for every unique UPN. At 500 failures across 50 UPNs = 25,000 comparisons per sweep run.

**Issue 2 — Sequential API calls per UPN**: One `security_sign_ins` call per UPN with failures. At 50 affected UPNs × 300ms = 15s sequential wait.

**Issue 3 — Sequential IP sweep calls** (lines 208-218, 249-259): Both Vector 1 and Vector 4 iterate IPs sequentially. 10 IPs × 500ms = 5s when they could run in parallel.

## Findings

- **File**: `plugins/m365-skills/skills/azure-ad/scripts/sweep.py`, lines 88-130, 208-218, 249-259
- **Agent**: performance-oracle

```python
# O(n) re-scan per UPN — should be pre-grouped
for upn in upns_with_failures:
    user_failures = [s for s in failures if s.get('userPrincipalName') == upn]
```

## Proposed Solutions

### Option A: Pre-group failures by UPN dict + ThreadPoolExecutor for IP sweeps (Recommended)
```python
# Pre-group once (O(n)) instead of O(n) per UPN
from collections import defaultdict
failures_by_upn = defaultdict(list)
for s in failures:
    upn = s.get('userPrincipalName', '')
    if upn:
        failures_by_upn[upn].append(s)

# Parallel IP sweeps
from concurrent.futures import ThreadPoolExecutor, as_completed
with ThreadPoolExecutor(max_workers=min(len(suspect_ips), 10)) as executor:
    futures = {executor.submit(collect_sign_ins_by_ip, api, ip, filter_base): ip
               for ip in suspect_ips}
```

## Recommended Action

Option A — standard Python optimizations, no new dependencies required.

## Acceptance Criteria

- [x] `failures_by_upn` pre-grouped before the MFA fatigue loop
- [x] Vector 1 and Vector 4 IP sweep calls parallelized with `ThreadPoolExecutor`

## Work Log

- 2026-04-07: Identified by performance-oracle
- 2026-04-07: Fixed — (1) Added `failures_by_upn: dict = defaultdict(list)` pre-grouping in `collect_mfa_fatigue_victims()` before the UPN loop, replacing the O(n) per-UPN list comprehension with an O(1) dict lookup. (2) Added `from concurrent.futures import ThreadPoolExecutor, as_completed` import. (3) Vector 1 IP sweep (`run_sweep()` lines ~215-235) now uses `ThreadPoolExecutor(max_workers=min(len(suspect_ips), 10))` to fire all IP queries in parallel. (4) Vector 4 cross-reference sweep (~265-285) similarly parallelized with `ThreadPoolExecutor`. Both use `as_completed()` for result collection with per-IP error handling to stderr. Committed in 94b6d3c as part of fix(sweep) commit covering todos 032 and 033.
