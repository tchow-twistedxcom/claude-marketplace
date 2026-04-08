---
status: pending
priority: p2
issue_id: "086"
tags: [code-review, quality, mimecast-skills, typing]
dependencies: []
---

# 086 — `register_domain` decorator and `_DOMAIN_REGISTRY` lack type hints

## Problem Statement

`domains/__init__.py` introduced `@register_domain` decorator and `_DOMAIN_REGISTRY: list` but both lack type hints, making the type contract opaque. `register_domain` should be generic to preserve the decorated class's type, and `_DOMAIN_REGISTRY` should be `list[type]` to express intent. Without these annotations, type checkers cannot verify that only `BaseDomain` subclasses are registered or that `register_domain` returns the same type it receives.

## Findings

- **domains/__init__.py** `register_domain` function: no type hints on parameter or return value
- **domains/__init__.py** `_DOMAIN_REGISTRY: list` — bare `list` without element type
- Correct signature: `def register_domain[T](cls: type[T]) -> type[T]:` (Python 3.12+) or `def register_domain(cls: type[T]) -> type[T]:` with `TypeVar T = TypeVar('T')`
- **audit_m365_sync.py line 509** companion: `_DOMAIN_REGISTRY: list[type]` would allow `isinstance` checks with type safety
- Flagged by: kieran-python-reviewer (medium), architecture-strategist

## Proposed Solutions

### Option A: Add generic type hints (Recommended)
```python
from typing import TypeVar
T = TypeVar('T')

_DOMAIN_REGISTRY: list[type] = []

def register_domain(cls: type[T]) -> type[T]:
    _DOMAIN_REGISTRY.append(cls)
    return cls
```
- **Effort**: Small | **Risk**: None

### Option B: Use `type[BaseDomain]` constraint
```python
_DOMAIN_REGISTRY: list[type[BaseDomain]] = []

def register_domain(cls: type[BaseDomain]) -> type[BaseDomain]:
    ...
```
- Stricter — only allows BaseDomain subclasses to be registered
- **Effort**: Small | **Risk**: None (but requires BaseDomain import at top of file)

## Acceptance Criteria
- [ ] `register_domain` has typed parameter and return value
- [ ] `_DOMAIN_REGISTRY` has explicit element type annotation
- [ ] `DOMAIN_CLASSES` alias inherits the typed annotation

## Work Log
- 2026-04-08: Identified in 6th code review pass (kieran-python-reviewer, architecture-strategist)
