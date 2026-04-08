---
status: pending
priority: p2
issue_id: "081"
tags: [code-review, architecture, azure-ad, ual]
dependencies: []
---

# 081 — `_ual_fetch_blobs` `incomplete` flag discarded by 4 of 5 callers

## Problem Statement

`_ual_fetch_blobs` returns `tuple[list, bool]` where the bool is an `incomplete` flag signaling that the blob cursor was exhausted before all events were retrieved (paginator hit the per-run limit). 4 of 5 callers unpack only the first element, silently discarding the flag. Incident response tools return results without warning the analyst that coverage is incomplete.

## Findings

- **server.py line 994** (`azure_ad_ual_exchange`): `events, _ = await _ual_fetch_blobs(...)`
- **server.py line 1059** (`azure_ad_ual_aad`): `events, _ = await _ual_fetch_blobs(...)`
- **server.py line 1098** (`azure_ad_ual_general`): `events, _ = await _ual_fetch_blobs(...)`
- **server.py line 1860** (`azure_ad_ual_sharepoint`): result unpacked via `results[0]` from gather — incomplete flag in `results[0][1]` is never checked
- Only `azure_ad_ual_all` propagates the flag correctly
- Callers do not set `ualDataIncomplete: true` in returned dicts when flag is True
- Flagged by: architecture-strategist (medium), performance-oracle (medium)

## Proposed Solutions

### Option A: Propagate flag in each UAL tool's return dict (Recommended)
For each of the 4 callers, unpack the tuple and add `ualDataIncomplete` to the response:
```python
events, incomplete = await _ual_fetch_blobs(...)
result = {"events": [...], "total": len(events)}
if incomplete:
    result["ualDataIncomplete"] = True
    result["warning"] = "Blob cursor limit reached; results may be truncated"
return _fmt(result)
```
- **Effort**: Small | **Risk**: Low

### Option B: Wrap all 5 callers in a shared helper
Extract a `_ual_fetch_with_incomplete_flag(content_type, ...)` helper that always returns a consistent dict shape including `ualDataIncomplete`
- **Effort**: Medium | **Risk**: Low

## Acceptance Criteria
- [ ] All 5 UAL tool callers propagate the incomplete flag to their return dict
- [ ] When `ualDataIncomplete: true`, a `warning` field explains coverage gap
- [ ] No change to existing return structure when `incomplete` is False

## Work Log
- 2026-04-08: Identified in 6th code review pass (architecture-strategist, performance-oracle)
