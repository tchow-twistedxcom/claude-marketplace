---
status: complete
priority: p2
issue_id: "016"
tags: [code-review, performance, audit, mimecast]
dependencies: []
---

# 016 — 15 sequential subprocess calls in audit_m365_sync.py — 4-7x speedup available

## Problem Statement

`audit_m365_sync.py` makes 15 sequential subprocess calls — 4 data fetches + 9 Mimecast config checks + 2 sync health checks — all of which are independent. Current wall time is ~22s. All calls can run in parallel via `ThreadPoolExecutor` with ~0 code risk.

## Findings

- **File**: `plugins/mimecast-skills/scripts/audit_m365_sync.py`
- **Agent**: performance-oracle (Critical Issue #1)

```python
# main() — 4 sequential independent fetches
azure_users_raw = fetch_azure_users(...)      # ~1.5s
deleted_users = fetch_azure_deleted_users(...)  # ~1.5s
mimecast_raw = fetch_mimecast_users(...)        # ~2s
azure_domains = fetch_azure_domains(...)        # ~1s

# fetch_mimecast_config() — 9 more sequential calls
return {
    "dkim": _run(["dkim", "status"]),           # ~1s each
    "domains": _run(["domains", "list"]),
    "policies": _run(["policies", "list"]),
    # ... 6 more
}
```

Estimated wall time: 15 calls × ~1.5s avg = **~22s sequential** → **~3-5s parallel** (4-7x speedup)

## Proposed Solutions

### Option A: ThreadPoolExecutor for main() + fetch_mimecast_config() (Recommended)

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

# In main():
with ThreadPoolExecutor(max_workers=4) as ex:
    f_azure    = ex.submit(fetch_azure_users, args.azure_tenant, args.verbose)
    f_deleted  = ex.submit(fetch_azure_deleted_users, args.azure_tenant, args.verbose)
    f_mimecast = ex.submit(fetch_mimecast_users, args.mimecast_profile, args.verbose)
    f_domains  = ex.submit(fetch_azure_domains, args.azure_tenant, args.verbose)
    azure_users_raw = f_azure.result()
    deleted_users   = f_deleted.result()
    mimecast_raw    = f_mimecast.result()
    azure_domains   = f_domains.result()

# In fetch_mimecast_config():
checks = {"dkim": ["dkim", "status"], "domains": ["domains", "list"], ...}
with ThreadPoolExecutor(max_workers=9) as ex:
    futures = {ex.submit(_run, cmd): key for key, cmd in checks.items()}
    return {futures[f]: f.result() for f in as_completed(futures)}
```

- **Effort**: Small (ThreadPoolExecutor is stdlib, no new deps)
- **Risk**: Low (calls are independent, read-only)

### Option B: asyncio + subprocess async
Use `asyncio.create_subprocess_exec` for async subprocess calls.

- **Effort**: Medium (requires async refactor of main())
- **Risk**: Medium (more invasive change)

## Recommended Action

Option A — `ThreadPoolExecutor` is the minimal, safe change. Subprocess calls are I/O-bound (network + Python startup), so threading is appropriate.

## Technical Details

- **Affected file**: `plugins/mimecast-skills/scripts/audit_m365_sync.py`
- **Functions**: `main()` (lines 957-1002), `fetch_mimecast_config()` (lines 278-292)
- **Also**: Differentiate `run_cli` timeout: `TIMEOUT_FAST=30s` for config, `TIMEOUT_SLOW=180s` for paginated user lists

## Acceptance Criteria

- [ ] `fetch_mimecast_config` runs 9 config checks in parallel
- [ ] 4 top-level data fetches run in parallel
- [ ] Total audit wall time < 10s for a typical tenant
- [ ] Results are identical to sequential execution

## Work Log

- 2026-04-07: Identified by performance-oracle as Critical Issue #1 (~22s → ~3-5s)
