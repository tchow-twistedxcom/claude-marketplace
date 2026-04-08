---
status: pending
priority: p2
issue_id: "043"
tags: [code-review, performance, azure-ad, mimecast]
dependencies: []
---

# 043 — Performance — sequential UAL blob downloads, double credential calls, Vector 5 processing

## Problem Statement

Three performance issues identified across `server.py` and `sweep.py`. None cause incorrect results but each introduces unnecessary latency in hot paths.

## Findings

### 1. `_ual_fetch_blobs` sequential downloads (`server.py`)

UAL blob downloads use `async for blob_url in blob_urls: response = await client.get(blob_url)` — sequential fetches. With 5–20 blobs per search, this is O(n) latency where each blob fetch waits for the previous to complete. Should use `asyncio.gather()`.

### 2. `_get_credentials()` called twice per request (`server.py`)

`_ual_request()` calls `_get_credentials()` to build headers and later calls `_get_token()` separately. Both invoke MSAL credential lookup. Should cache the token for the duration of a single request to avoid the double overhead.

### 3. Vector 5 (`sweep.py`) processes victims sequentially (`sweep.py`)

The mass-password-spray vector processes victim accounts one at a time using `for victim in victims: results = run_cli(...)`. With `ThreadPoolExecutor` already used for other vectors, this should use the same pattern for consistency and performance.

## Proposed Solutions

### Option A — Fix each independently (Recommended)

- `_ual_fetch_blobs`: Replace sequential loop with `tasks = [client.get(url) for url in blob_urls]; responses = await asyncio.gather(*tasks, return_exceptions=True)`. Handle per-item exceptions from `return_exceptions=True`.
- `_get_credentials()`: Accept optional cached token to avoid double lookup, or merge into `_get_token()` so a single MSAL call serves both needs.
- Vector 5: Use `executor.submit()` for victim processing, consistent with Vector 1/4 patterns already in `sweep.py`.
- Effort: Small per item, Risk: Low

## Acceptance Criteria

- [ ] `_ual_fetch_blobs` fetches blobs concurrently with `asyncio.gather`
- [ ] `_get_credentials()` is not called redundantly within a single request
- [ ] Vector 5 victim processing uses ThreadPoolExecutor consistent with other vectors

## Work Log

- 2026-04-08: Identified in 3rd review pass
