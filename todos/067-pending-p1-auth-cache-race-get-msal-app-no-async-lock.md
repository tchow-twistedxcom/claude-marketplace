---
status: pending
priority: p1
issue_id: "067"
tags: [code-review, security, performance, azure-ad]
dependencies: []
---

# 067 — Token cache TOCTOU race: `_get_token` and `_get_msal_app` have no async lock

## Problem Statement

`server.py` correctly protects the httpx client singleton with `_http_client_lock` (added in todo 055), but applies no equivalent locking to `_get_token()` and `_get_msal_app()`. Under `asyncio.gather` with concurrent callers (e.g., `_triage_one` fires 9 concurrent `_graph()` calls), all coroutines can simultaneously pass the cache-miss check, make redundant MSAL `acquire_token_for_client` calls, and write back to `_token_cache` independently. `_get_msal_app()` has the same pattern for `_msal_app` initialization.

## Findings

### `_get_token()` cache TOCTOU (server.py ~lines 138–156)
```python
cached = _token_cache.get(cache_key)   # 1. cache read — no lock
if cached and not _is_token_expired(cached):
    return cached["access_token"]
# ... await loop.run_in_executor(...)  # 2. releases event loop — other coroutines run
_token_cache[cache_key] = token_data   # 3. cache write — no lock
```
Two concurrent coroutines can both see a cache miss, both call `acquire_token_for_client`, both write to `_token_cache`. In `azure_ad_incident_triage` which fires `asyncio.gather(*[_triage_one(upn) for upn in users])`, each `_triage_one` fires 9 inner `_graph()` calls. With 5 users under triage, all 45 concurrent calls hit an expired token simultaneously → 45 redundant MSAL token acquisitions.

### `_get_msal_app()` TOCTOU (server.py ~lines 124–135)
```python
if _msal_app is None:
    # ... _msal_app = ConfidentialClientApplication(...)
```
Not protected. Two concurrent callers can both see `None` and create two independent MSAL app instances with separate internal token caches.

### Token-cache write with no lock (security-sentinel FINDING-08)
Doubles unnecessary network calls to `login.microsoftonline.com` and can mask token acquisition errors. MSAL quota burns proportionally to concurrent callers.

## Proposed Solutions

**Option A (Recommended):**
Add a module-level `_token_lock: asyncio.Lock = asyncio.Lock()` alongside the existing `_http_client_lock`. Wrap the check-and-refresh cycle in `_get_token()`:
```python
async with _token_lock:
    cached = _token_cache.get(cache_key)
    if cached and not _is_token_expired(cached):
        return cached["access_token"]
    # acquire + cache write inside lock
```
Extend the same pattern to `_get_msal_app()`.
- Effort: Small. Risk: Low.

**Option B:**
Use a per-scope lock dict (`_token_locks: dict[str, asyncio.Lock]`) to allow concurrent refreshes for different scopes (Graph vs UAL). More complex, not needed currently.

## Acceptance Criteria

- [ ] `_token_lock: asyncio.Lock = asyncio.Lock()` added at module level
- [ ] `_get_token()` wraps cache read + MSAL call + cache write in `async with _token_lock`
- [ ] `_get_msal_app()` protected from concurrent double-initialization
- [ ] Concurrent calls to `_get_token()` with an expired cache produce exactly one MSAL network call

## Work Log

- 2026-04-08: Identified by performance-oracle (P1) and security-sentinel (P2 FINDING-08) in 5th review pass
