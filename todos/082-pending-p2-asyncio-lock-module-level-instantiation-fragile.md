---
status: pending
priority: p2
issue_id: "082"
tags: [code-review, quality, azure-ad, asyncio]
dependencies: []
---

# 082 — `asyncio.Lock()` module-level instantiation is fragile in test/import contexts

## Problem Statement

`server.py` lines 73-74 instantiate `_token_lock` and `_http_client_lock` at module import time:
```python
_token_lock: asyncio.Lock = asyncio.Lock()
_http_client_lock: asyncio.Lock = asyncio.Lock()
```
`asyncio.Lock()` attaches to the running event loop in some Python versions. Importing `server` in a test context (outside an async runner) or re-using it across multiple test event loops can cause `RuntimeError: no running event loop` or lock state corruption between tests.

## Findings

- **server.py lines 73-74**: Module-level `asyncio.Lock()` instantiation
- In Python 3.10+, `asyncio.Lock()` no longer binds to the event loop at creation, so this is less likely to error — but the pattern is still fragile if test isolation requires fresh locks per test
- The double-checked locking pattern using these locks (`_token_lock` in `_get_token()`, `_http_client_lock` in `_ensure_http_client()`) is correct; only the initialization site is the concern
- Flagged by: kieran-python-reviewer (medium severity)

## Proposed Solutions

### Option A: Lazy initialization (Recommended)
```python
_token_lock: asyncio.Lock | None = None
_http_client_lock: asyncio.Lock | None = None

async def _get_lock() -> asyncio.Lock:
    global _token_lock
    if _token_lock is None:
        _token_lock = asyncio.Lock()
    return _token_lock
```
Or use `asyncio.Lock()` created inside the first `lifespan` / startup handler.
- **Effort**: Small | **Risk**: Low

### Option B: Keep module-level but document the constraint
Add a comment explaining Python 3.10+ behavior and that the locks are safe in single-event-loop FastMCP usage
- Minimal risk for production use; only matters for test authors
- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria
- [ ] Lock instantiation does not cause errors when `server.py` is imported in a test context
- [ ] Or: comment documents why module-level locks are acceptable for this usage pattern
- [ ] If lazy init is used: lock is still correctly shared across all callers (no lock-per-call regression)

## Work Log
- 2026-04-08: Identified in 6th code review pass (kieran-python-reviewer)
