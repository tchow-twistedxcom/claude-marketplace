---
status: pending
priority: p1
issue_id: "101"
tags: [code-review, quality, azure-ad, auth]
dependencies: []
---

# 101 — `auth.py` atomic write: `NameError` if `mkstemp` fails — `tmp_path` referenced before assignment

## Problem Statement

Todo 084 added an atomic cache-write using `mkstemp → os.fchmod → fdopen → os.replace`. The outer `try` block wraps `mkstemp` itself. If `mkstemp` raises (e.g., no temp-dir space, permission denied), `tmp_path` is never assigned, yet the `except` block calls `os.unlink(tmp_path)` — raising a secondary `NameError` that masks the original error. This is a code-correctness bug introduced by the fix itself.

## Findings

- **`plugins/m365-skills/skills/azure-ad/scripts/auth.py`**: `tmp_fd, tmp_path = mkstemp(...)` inside outer `try`; if this line raises, `tmp_path` is undefined
- The inner `except` block calls `os.unlink(tmp_path)` → `NameError: name 'tmp_path' is not defined`
- The real exception (e.g., `OSError: no space left on device`) is lost
- Flagged by: kieran-python-reviewer (7th review pass)

## Proposed Solutions

### Option A: Initialize `tmp_path` to `None` before the try block (recommended)

```python
tmp_fd, tmp_path = None, None
try:
    tmp_fd, tmp_path = mkstemp(dir=str(path.parent), prefix=".tmp_token_")
    ...
except Exception:
    if tmp_path is not None:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
    raise
```

- **Effort**: Trivial | **Risk**: None

### Option B: Move try block to start after mkstemp

Let `mkstemp` failure propagate naturally; only wrap the write+replace in try:
```python
tmp_fd, tmp_path = mkstemp(dir=str(path.parent), prefix=".tmp_token_")
try:
    ...
except Exception:
    with contextlib.suppress(OSError):
        os.unlink(tmp_path)
    raise
```

- **Effort**: Trivial | **Risk**: None (mkstemp failure propagates as OSError)

## Acceptance Criteria

- [ ] `tmp_path` is never referenced in the cleanup `except` block when it may be unassigned
- [ ] If `mkstemp` fails, the original error propagates cleanly without a secondary `NameError`

## Work Log

- 2026-04-08: Identified in 7th code review pass (kieran-python-reviewer) — NameError introduced by 084 atomic write fix
