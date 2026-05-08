---
status: pending
priority: p2
issue_id: "105"
tags: [code-review, architecture, azure-ad]
dependencies: []
---

# 105 — `_ual_fetch_blobs` call-site asymmetry: `return_exceptions=True` + isinstance guard only in sharepoint

## Problem Statement

`_ual_fetch_blobs` was updated to return a `(list, bool)` tuple with an incomplete flag. However, of its multiple call sites, only `azure_ad_ual_sharepoint` correctly uses `return_exceptions=True` with the isinstance guard for the gather call. The other callers (handling Exchange/AzureAD/General audit types) do not apply this pattern, meaning exceptions from blob downloads can propagate as unhandled errors rather than being collected into the incomplete flag. This creates inconsistent error handling across audit types.

## Findings

- **`server.py` `azure_ad_ual_sharepoint`**: correctly uses `return_exceptions=True` + `isinstance(resp, Exception)` guard
- **Other UAL callers** (Exchange, AzureAD, General audit types): do not apply `return_exceptions=True` — exceptions bubble up instead of being captured
- The incomplete-flag mechanism from todo 081 works only where `return_exceptions=True` is used
- Flagged by: architecture-strategist (7th review pass)

## Proposed Solutions

### Option A: Apply `return_exceptions=True` + isinstance guard at all call sites (recommended)

Update all `asyncio.gather(...)` calls for blob fetching to use:
```python
responses = await asyncio.gather(*tasks, return_exceptions=True)
events, incomplete = _ual_fetch_blobs(responses)
```

- **Effort**: Small | **Risk**: Low

### Option B: Move `return_exceptions=True` inside `_ual_fetch_blobs`

Refactor `_ual_fetch_blobs` to take the tasks list directly and internally call `asyncio.gather(*tasks, return_exceptions=True)`, ensuring consistent behavior regardless of call site.

- **Effort**: Small | **Risk**: Low (consolidates the pattern)

## Acceptance Criteria

- [ ] All UAL blob-fetching call sites handle exceptions consistently
- [ ] `ualDataIncomplete` flag propagated for all audit types (not just SharePoint)
- [ ] No call site can surface unhandled exceptions from blob download failures

## Work Log

- 2026-04-08: Identified in 7th code review pass (architecture-strategist) — asymmetric call sites after 081 fix
