---
status: pending
priority: p2
issue_id: "102"
tags: [code-review, quality, mimecast-skills, type-hints]
dependencies: []
---

# 102 — `mimecast_client.py` entire file missed `Optional[X]→X|None` / `Dict/List→dict/list` modernization

## Problem Statement

A previous pass modernized type annotations across `server.py`, `sweep.py`, `auth.py`, and `azure_ad_api.py`. `mimecast_client.py` was skipped entirely. It still uses `Optional[X]`, `Dict[K,V]`, `List[T]`, incorrect bare `int = None` / `str = None` parameter annotations, and is missing `-> None` / `-> str` return type hints on several methods. This is a blocking quality issue since the same reviewers who flagged it in other files already reviewed this one.

## Findings

- **`MimecastError.__init__`**: parameters typed as `int = None`, `str = None` — should be `int | None = None`, `str | None = None`
- **Line 76**: `__str__` missing `-> str` return annotation
- **Lines 36, 56**: `_add_tokens`, `wait` missing `-> None`
- All `Optional[X]` usages should be `X | None` (Python 3.10+)
- All `Dict[K,V]` / `List[T]` should be `dict[k,v]` / `list[t]` (lowercase built-ins, PEP 585)
- Flagged by: kieran-python-reviewer (7th review pass) as BLOCKING

## Proposed Solutions

### Option A: Full modernization pass on mimecast_client.py (recommended)

- Replace `Optional[X]` → `X | None` throughout
- Replace `Dict[K, V]` → `dict[K, V]` and `List[T]` → `list[T]`
- Fix `MimecastError.__init__` parameter annotations
- Add missing `-> str` and `-> None` return annotations
- Remove `from typing import Optional, Dict, List` imports if no longer needed

- **Effort**: Small | **Risk**: Low (annotation-only changes, no runtime behavior)

## Acceptance Criteria

- [ ] No `Optional[`, `Dict[`, `List[` in `mimecast_client.py`
- [ ] `MimecastError.__init__` parameters use `int | None = None` / `str | None = None`
- [ ] `__str__`, `_add_tokens`, `wait` have correct return type annotations
- [ ] `from typing import ...` reduced to only what's still needed

## Work Log

- 2026-04-08: Identified in 7th code review pass (kieran-python-reviewer) — entire file missed in previous modernization passes
