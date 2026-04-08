---
status: pending
priority: p2
issue_id: "072"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 072 — Python quality bundle: get_event_loop deprecated, Optional[...] x47, auth.py legacy types, raise...from e

## Problem Statement

Four Python quality issues spanning `server.py` and `auth.py`:

1. `asyncio.get_event_loop()` in `_get_token` is deprecated since Python 3.10+ and raises `RuntimeError` in Python 3.12+ from inside a running coroutine — the project's stated minimum is 3.10.
2. `server.py` uses `Optional[X]` from `typing` in 47 tool function signatures — the rest of the codebase uses `X | None` (Python 3.10+ union syntax). This is the largest surviving legacy typing inconsistency.
3. `auth.py` uses `Dict`, `List`, `Optional` from `typing` throughout all method annotations.
4. `raise AuthError(...)` in `auth.py` and `raise AzureADError(...)` in `azure_ad_api.py` do not chain the original exception (`from e`), losing the original traceback.

## Findings

### 1. `asyncio.get_event_loop()` deprecated (server.py ~line 147)
```python
loop = asyncio.get_event_loop()  # deprecated 3.10, RuntimeError in 3.12+
result = await loop.run_in_executor(None, lambda: app.acquire_token_for_client(...))
```
Fix: `loop = asyncio.get_running_loop()` — one word change, always correct inside `async def`.

### 2. `Optional[...]` in server.py (server.py ~line 11, then pervasively)
```python
from typing import Any, Optional  # line 11
# 47 occurrences of Optional[str], Optional[dict], Optional[int] in tool signatures
```
All other scripts in the PR use `str | None`, `dict | None`. `Optional` import should be removed from server.py.

### 3. `auth.py` legacy types (auth.py ~line 29)
```python
from typing import Optional, Dict, Any
# All method annotations: Dict[str, Any], Optional[str], etc.
```
`Dict` deprecated since Python 3.9. `Optional` deprecated since 3.10. All should be `dict[str, Any]`, `str | None`, etc.

### 4. `raise ... from e` missing (auth.py ~lines 95, 259; azure_ad_api.py ~lines 164–171)
```python
except Exception as e:
    raise AuthError(f"Failed to load config: {e}")  # original traceback lost
```
Python convention: `raise AuthError(...) from e` preserves the original `PermissionError`, `OSError`, etc. for debugging. Without `from e`, the traceback shows only the `AuthError`.

## Proposed Solutions

**Option A (Recommended):**
1. One-word fix: `asyncio.get_event_loop()` → `asyncio.get_running_loop()` on server.py line 147.
2. Global replace in server.py: remove `Optional` from imports, replace all `Optional[X]` with `X | None`.
3. `auth.py`: replace `Dict[str, Any]` → `dict[str, Any]`, `Optional[str]` → `str | None`, remove `Dict` from imports.
4. Add `from e` to all `raise XxxError(...)` in exception handlers in `auth.py` and `azure_ad_api.py`.
- Effort: Small (items 1, 3, 4) to Medium (item 2 — 47 replacements in server.py). Risk: Zero (purely typing/syntax changes).

## Acceptance Criteria

- [ ] `asyncio.get_event_loop()` replaced with `asyncio.get_running_loop()` in `_get_token`
- [ ] `Optional` removed from `server.py` imports; all 47 usages replaced with `X | None`
- [ ] `auth.py` uses `dict`, `str | None` throughout; `Dict`/`Optional` imports removed
- [ ] `raise AuthError(...) from e` (and analogous patterns) in `auth.py` and `azure_ad_api.py`

## Work Log

- 2026-04-08: Identified by kieran-python-reviewer (FINDING-5/6/7/8), architecture-strategist (FINDING-3), security-sentinel (FINDING-07) in 5th review pass
