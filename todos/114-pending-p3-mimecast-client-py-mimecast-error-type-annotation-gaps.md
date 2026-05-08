---
status: pending
priority: p3
issue_id: "114"
tags: [code-review, quality, mimecast-skills, type-hints]
dependencies: [102]
---

# 114 — `mimecast_client.py` `MimecastError` type annotation gaps: bare `int = None`, missing `-> str`

## Problem Statement

`MimecastError.__init__` has parameters annotated as `int = None` and `str = None` — these are incorrect: the type is `int` but the default is `None`, so the annotation should be `int | None = None` and `str | None = None`. Additionally, `__str__` is missing `-> str`, and `_add_tokens`/`wait` are missing `-> None`. These are annotation correctness issues separate from the broader modernization in todo 102 (which covers the full-file Dict/List/Optional pass); these specific gaps are in the class definition signature.

Note: This todo depends on 102 being completed first, as the full modernization pass may resolve some of these as part of that work.

## Findings

- **`MimecastError.__init__`**: `status_code: int = None` should be `status_code: int | None = None`
- **`MimecastError.__init__`**: `request_id: str = None` should be `request_id: str | None = None`
- **Line 76**: `def __str__(self):` missing `-> str`
- **Lines 36, 56**: `_add_tokens`, `wait` missing `-> None`
- Flagged by: kieran-python-reviewer (7th review pass)

## Proposed Solutions

### Option A: Fix as part of todo 102's full modernization pass

These annotation gaps should be addressed as part of the broader `mimecast_client.py` modernization. Mark this as a subset of 102.

- **Effort**: Trivial (part of 102) | **Risk**: None

## Acceptance Criteria

- [ ] `MimecastError.__init__` parameters use `int | None = None` / `str | None = None`
- [ ] `__str__` annotated with `-> str`
- [ ] `_add_tokens`, `wait` annotated with `-> None`

## Work Log

- 2026-04-08: Identified in 7th code review pass (kieran-python-reviewer) — annotation correctness gaps in MimecastError
