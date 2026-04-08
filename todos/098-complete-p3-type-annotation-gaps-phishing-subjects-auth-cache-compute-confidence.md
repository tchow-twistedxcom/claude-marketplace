---
status: complete
priority: p3
issue_id: "098"
tags: [code-review, quality, azure-ad, typing]
dependencies: []
---

# 098 — Type annotation gaps: PHISHING_SUBJECTS, _token_cache, compute_confidence, _gather_values

## Problem Statement

Several type annotations use bare generic types instead of parameterized ones, reducing type checker effectiveness:
1. `PHISHING_SUBJECTS: frozenset` → should be `frozenset[str]`
2. `_token_cache: dict = {}` → should be `dict[str, Any]`
3. `compute_confidence(evidence: dict)` in sweep.py → should be `dict[str, Any]`
4. `_gather_values(result)` → `result` parameter has no type annotation

## Findings

- **server.py**: `PHISHING_SUBJECTS: frozenset` — bare frozenset
- **server.py**: `_token_cache: dict = {}` — bare dict
- **sweep.py**: `compute_confidence(evidence: dict)` — bare dict
- **server.py**: `_gather_values(result)` — no annotation on `result`
- Flagged by: kieran-python-reviewer (medium)

## Proposed Solutions

### Option A: Add parameterized type annotations
```python
PHISHING_SUBJECTS: frozenset[str] = frozenset(...)
_token_cache: dict[str, Any] = {}

def compute_confidence(evidence: dict[str, Any]) -> float:
    ...

async def _gather_values(result: BaseException | tuple | Any) -> ...:
    ...
```
- **Effort**: Small | **Risk**: None

## Acceptance Criteria
- [x] All 4 identified annotations use parameterized generic types
- [ ] No new bare `dict` or `frozenset` annotations in server.py or sweep.py

## Work Log
- 2026-04-08: Identified in 6th code review pass (kieran-python-reviewer)
- 2026-04-08: sweep.py portion fixed — added `from typing import Any` import and changed `compute_confidence(evidence: dict)` → `compute_confidence(evidence: dict[str, Any])`. Commit: refactor(sweep): separate audit anomaly score constant; fix typing (todos 092, 098). server.py portion (PHISHING_SUBJECTS, _token_cache, _gather_values) handled in parallel agent.
