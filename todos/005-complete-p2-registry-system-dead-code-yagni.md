---
status: complete
priority: p2
issue_id: "005"
tags: [code-review, architecture, mimecast, yagni, simplicity]
dependencies: []
---

# 005 — Registry system in `domains/base.py` is dead code (YAGNI)

## Problem Statement

`plugins/mimecast-skills/scripts/domains/base.py` implements a full registry system:
- `_REGISTRY: dict[str, type[BaseDomain]]`
- `@register_domain("name")` decorator
- `get_registry()` public accessor

`domains/awareness_training.py` decorates with `@register_domain("awareness")`, which populates `_REGISTRY`.

**However**, `mimecast_api.py`'s `main()` never calls `get_registry()`. It imports `AwarenessTrainingDomain` directly:

```python
from domains.awareness_training import AwarenessTrainingDomain
_pre_domains = [AwarenessTrainingDomain(None)]
```

`_REGISTRY` is populated but **never consumed**. The registry is pure dead code at runtime. This violates YAGNI — the future auto-discovery vision is speculative.

## Findings

- **Agent**: code-simplicity-reviewer (P1), architecture-strategist (P1)
- **Files**: `domains/base.py` (registry defined), `mimecast_api.py` (bypasses it)

## Proposed Solutions

### Option A: Delete registry, keep plain BaseDomain ABC
Remove `_REGISTRY`, `@register_domain`, `get_registry()`. Keep only `BaseDomain`, `DomainT`, and shared helpers.

Domains are imported directly in `mimecast_api.py` — simple and explicit.

- **Pros**: Eliminates dead code, removes mutable global state, simpler base.py
- **Cons**: When more domains are added, each needs a manual import in main()
- **Effort**: Small
- **Risk**: Very low

### Option B: Actually use the registry in main()
Replace the explicit import/instantiation lists with `get_registry()`:

```python
from domains import *  # trigger all @register_domain decorators
_pre_domains = [cls(None) for cls in get_registry().values()]
```

- **Pros**: Registry becomes useful; adding new domain = just create the file
- **Cons**: `import *` is ugly; ordering becomes non-deterministic; still need each domain file to be imported
- **Effort**: Small
- **Risk**: Low

### Option C: Hybrid — remove registry, use explicit domain list in __init__.py
Move the domain list to `domains/__init__.py`:

```python
from .awareness_training import AwarenessTrainingDomain
DOMAIN_CLASSES = [AwarenessTrainingDomain]
```

`main()` imports `DOMAIN_CLASSES`. Adding a domain = edit `__init__.py`.

- **Pros**: Explicit, no magic, single place to add domains, no dead code
- **Cons**: One extra file to update per domain
- **Effort**: Small
- **Risk**: Very low

### Recommended
**Option C** — explicit domain list in `__init__.py`. Cleaner than both extremes.

## Technical Details

- **Affected files**: `domains/base.py`, `domains/awareness_training.py`, `domains/__init__.py`, `mimecast_api.py`

## Acceptance Criteria

- [ ] No dead code in base.py (either registry is used or removed)
- [ ] Adding a second domain requires changes in exactly 1 file
- [ ] All existing awareness training commands still work

## Work Log

- 2026-04-04: Created by code review (code-simplicity-reviewer + architecture-strategist)
