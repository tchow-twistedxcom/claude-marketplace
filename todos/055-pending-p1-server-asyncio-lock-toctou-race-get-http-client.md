---
status: pending
priority: p1
issue_id: "055"
tags: [code-review, security, azure-ad]
dependencies: []
---

# 055 — `server.py` `asyncio.Lock` TOCTOU race in `_get_http_client`

## Problem Statement

The `_get_http_client()` function initializes `asyncio.Lock` lazily with a `if _http_client_lock is None:` guard. This guard is itself a TOCTOU race: two concurrent callers can both observe `None` before either creates the lock, resulting in two separate Lock objects, one of which is silently discarded. The comment says "TOCTOU-safe initialization" but it is not.

## Findings

```python
# server.py lines 73-88
_http_client_lock: asyncio.Lock | None = None

async def _get_http_client() -> httpx.AsyncClient:
    global _http_client, _http_client_lock
    if _http_client_lock is None:
        _http_client_lock = asyncio.Lock()  # RACE: two callers can both enter here
    async with _http_client_lock:
        if _http_client is None:
            _http_client = httpx.AsyncClient(...)
    return _http_client
```

The correct fix is to initialize the Lock at module level where there is no concurrency, not lazily. Module-level `asyncio.Lock()` creation is safe in FastMCP servers since the event loop is set up before any tool invocations.

## Proposed Solutions

Option A (Recommended): Create the Lock at module level:
```python
_http_client_lock: asyncio.Lock = asyncio.Lock()  # module-level, safe
```
Remove the `if _http_client_lock is None:` branch entirely. Change type annotation from `asyncio.Lock | None` to `asyncio.Lock`. Remove the `global _http_client, _http_client_lock` declaration (only `_http_client` needs global).
- Effort: Small. Risk: Low.

Option B: Use `asyncio.ensure_future` or startup hook — more invasive and unnecessary.

## Acceptance Criteria

- [ ] `_http_client_lock` created at module level (not lazily)
- [ ] Type annotation changed from `asyncio.Lock | None` to `asyncio.Lock`
- [ ] `if _http_client_lock is None:` branch removed
- [ ] `_get_http_client` still correctly serializes client creation with the lock

## Work Log

- 2026-04-08: Found by kieran-python-reviewer in 4th review pass
