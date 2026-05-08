---
status: pending
priority: p1
issue_id: "035"
tags: [code-review, security, performance, azure-ad]
dependencies: []
---

# 035 — Async critical bugs — blocking sync call in async context + TOCTOU race in httpx singleton

## Problem Statement

`extensions/azure-ad/src/server.py` has two critical async correctness bugs:

1. `_get_token()` at lines 162, 848 is a synchronous MSAL call inside an async FastMCP handler. When `azure_ad_incident_triage` calls `asyncio.gather()` for 9+ concurrent users, each gather task blocks the event loop waiting for MSAL token acquisition. This causes timeout cascades under moderate load.
2. `_get_http_client()` at lines 74–83 has a classic TOCTOU race: `if _http_client is None: _http_client = httpx.AsyncClient(...)`. Under concurrent `asyncio.gather`, two coroutines can both pass the `is None` check before either sets the global, creating duplicate singletons and leaking connections.

## Findings

- `_get_token()` calls `msal_app.acquire_token_silently()` synchronously from an async context. This is a blocking I/O call that holds the event loop.
- `azure_ad_incident_triage` uses `asyncio.gather()` to fan out across 9+ users concurrently. Each gather task calls `_get_token()` which blocks the loop, serializing what should be parallel execution.
- `_get_http_client()` uses a module-level `_http_client` global with a bare `if _http_client is None:` guard — no locking. Two coroutines racing on first call both pass the check, both instantiate `httpx.AsyncClient`, and the first one's client is silently leaked.
- The leaked `AsyncClient` holds open connection pool resources and will not be closed cleanly on shutdown.

## Proposed Solutions

**Option A (Recommended):**
- Wrap `_get_token()` with `asyncio.get_event_loop().run_in_executor(None, msal_app.acquire_token_silently, ...)` to push blocking call to thread pool
- Add `asyncio.Lock` for `_get_http_client()` singleton: `_http_client_lock = asyncio.Lock()` then `async with _http_client_lock: if _http_client is None: ...`
- Effort: Medium, Risk: Low

**Option B:**
- Use `msal.aio.ConfidentialClientApplication` (MSAL async variant) for non-blocking token acquisition
- Effort: Medium, Risk: Medium (MSAL async API is newer)

**Option C:**
- Cache token at module load and refresh periodically with a background task
- Does not address TOCTOU for httpx
- Effort: Large, Risk: High

## Acceptance Criteria

- [ ] `_get_token()` does not block event loop in async context
- [ ] `_get_http_client()` is concurrency-safe (tested with `asyncio.gather` of 10 calls)
- [ ] No new client instances created under concurrent access

## Work Log

- 2026-04-08: Identified in 3rd review pass
