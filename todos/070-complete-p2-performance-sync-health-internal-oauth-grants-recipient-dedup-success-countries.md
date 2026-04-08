---
status: complete
priority: p2
issue_id: "070"
tags: [code-review, performance, azure-ad]
dependencies: []
---

# 070 — Performance bundle: fetch_sync_health sequential, oauth_grants unbounded gather, O(N) recipient dedup, success_countries triple-set

## Problem Statement

Five performance issues not caught by previous passes:

1. `fetch_sync_health` has two independent subprocess calls that run sequentially despite `fetch_mimecast_config` (its sibling) already demonstrating the parallel pattern.
2. `azure_ad_user_oauth_grants` uses unbounded `asyncio.gather` for service principal enrichment — can saturate the 20-connection httpx pool.
3. `azure_ad_email_events` and `_triage_one` use `list.append` + `not in` for recipient deduplication — O(N) per row; should be set-based.
4. `segment_mimecast_users` calls `_is_mimecast_infra` twice per candidate (once for `infra`, once for `real_users`) — double traversal.
5. `_triage_one` computes `set(success_countries)` three times in the same block instead of once.

## Findings

### 1. `fetch_sync_health` sequential subprocesses (audit_m365_sync.py ~lines 318–326)
```python
return {
    "connection": _mimecast_run(["sync", "status"], profile, verbose),
    "history":    _mimecast_run(["sync", "history", "--days", "2"], profile, verbose),
}
```
Two independent subprocess+API calls run strictly sequentially. `fetch_mimecast_config` at lines 293–315 already demonstrates the correct pattern with `ThreadPoolExecutor`. Cost: ~1–2s per audit run hidden inside the outer parallel worker.

### 2. Unbounded asyncio.gather in `azure_ad_user_oauth_grants` (server.py ~lines 1548–1558)
```python
sp_results = await asyncio.gather(
    *[_graph("GET", f"/servicePrincipals/{cid}", ...) for cid in client_ids],
    return_exceptions=True,
)
```
No concurrency cap. With 20+ OAuth grants (common on dev tenants), this fires 20+ concurrent httpx requests against a pool configured with `max_connections=20`. Causes queuing inside httpx that produces misleading latency or connection errors.

### 3. O(N) recipient dedup (server.py ~lines 1514–1516, 1941–1943)
```python
if recip and recip not in msg_map[mid]["recipients"]:
    msg_map[mid]["recipients"].append(recip)
```
`recipients` is a `list`. `not in` is O(len(recipients)) per row. For a blast to 385 recipients (385 rows from Defender), this is 74,000 string comparisons. Should be accumulated as a `set` and converted to `list` at output time.

### 4. `_is_mimecast_infra` called twice (audit_m365_sync.py ~lines 257–258)
```python
infra = [u for u in candidates if _is_mimecast_infra(u)]
real_users = [u for u in candidates if not _is_mimecast_infra(u)]
```
Two full O(N) scans. Should be a single-pass partition.

### 5. `set(success_countries)` computed 3× (server.py ~lines 1993–1997)
```python
if len(set(success_countries)) > 1:
    ...
    "countries": sorted(set(success_countries)),
    "note": f"... {len(set(success_countries))} countries ..."
```
Three `set()` constructions on the same list. Assign once: `unique_countries = set(success_countries)`.

## Proposed Solutions

**Option A (Recommended):**
1. `fetch_sync_health`: wrap both `_mimecast_run` calls in `ThreadPoolExecutor(max_workers=2)`, matching the `fetch_mimecast_config` pattern.
2. `azure_ad_user_oauth_grants`: cap the gather with an `asyncio.Semaphore(10)` wrapping each `_graph` call.
3. Recipient dedup: use `set` for `recipients` accumulation during loops; convert to `sorted(list(...))` at the output step.
4. `segment_mimecast_users`: replace double list comprehension with a single-pass `infra, real_users = [], []; for u in candidates: (infra if _is_mimecast_infra(u) else real_users).append(u)`.
5. `success_countries`: declare as `set`, use `.add()` instead of `.append()`, remove three `set()` calls.
- Effort: Small per item. Risk: Low.

## Acceptance Criteria

- [x] `fetch_sync_health` runs both subprocess calls concurrently via ThreadPoolExecutor
- [x] `azure_ad_user_oauth_grants` SP enrichment capped at ≤10 concurrent `_graph` calls
- [x] Recipient deduplication uses `set`-based accumulation in `azure_ad_email_events` and `_triage_one`
- [x] `segment_mimecast_users` uses single-pass partition (no double `_is_mimecast_infra` call)
- [x] `success_countries` declared as `set`, `set()` call removed from output block

## Work Log

- 2026-04-08: Identified by performance-oracle (5th review pass)
- 2026-04-08: All 5 changes implemented. Commit: 6032a48 on feat/mimecast-m365-audit.
