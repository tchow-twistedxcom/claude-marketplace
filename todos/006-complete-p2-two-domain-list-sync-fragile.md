---
status: complete
priority: p2
issue_id: "006"
tags: [code-review, architecture, mimecast, maintainability]
dependencies: [005]
---

# 006 — Two-domain-list sync in `main()` silently breaks when domains are added

## Problem Statement

In `mimecast_api.py`'s `main()`, domains appear in **two separate lists** that must be kept in sync:

```python
# List 1 — parser registration (before arg parsing, client=None)
_pre_domains = [AwarenessTrainingDomain(None)]
for _domain in _pre_domains:
    _domain.register_parsers(subparsers, make_common_parser)

# ... 200 lines later ...

# List 2 — cmd_map building (after API auth, client=live)
for _domain in [AwarenessTrainingDomain(api.client)]:
    cmd_map.update(_domain.get_cmd_map())
```

Adding a second domain requires updating **both lists**. If a developer updates only one list, the domain either gets no subparsers (args fail) or no cmd_map entries (dispatch fails) — both silently produce confusing errors.

## Findings

- **Agent**: architecture-strategist (P1)
- **Files**: `mimecast_api.py` — `main()` function

## Proposed Solutions

### Option A: Single domain class list, instantiate twice inline

```python
DOMAIN_CLASSES = [AwarenessTrainingDomain]  # single source of truth

# Before parsing:
for cls in DOMAIN_CLASSES:
    cls(None).register_parsers(subparsers, make_common_parser)

# After auth:
for cls in DOMAIN_CLASSES:
    cmd_map.update(cls(api.client).get_cmd_map())
```

- **Pros**: One list to update, obvious pattern
- **Cons**: Still instantiates twice per domain
- **Effort**: Small
- **Risk**: Very low

### Option B: `register_parsers` as `@classmethod`
Make `register_parsers` a classmethod that doesn't need a client:

```python
@classmethod
def register_parsers(cls, subparsers, make_common_parser): ...
```

Then in main():
```python
DOMAIN_CLASSES = [AwarenessTrainingDomain]
for cls in DOMAIN_CLASSES:
    cls.register_parsers(subparsers, make_common_parser)
# ... later ...
for cls in DOMAIN_CLASSES:
    cmd_map.update(cls(api.client).get_cmd_map())
```

- **Pros**: Cleanest API; no dummy `None` client; addresses architecture-strategist's classmethod suggestion
- **Cons**: Requires updating BaseDomain ABC and AwarenessTrainingDomain
- **Effort**: Small-Medium
- **Risk**: Low

### Recommended
**Option B** — `@classmethod` for `register_parsers`. Cleaner design, single `DOMAIN_CLASSES` list. Resolves todo #005's explicit list pattern too.

## Technical Details

- **Affected files**: `domains/base.py`, `domains/awareness_training.py`, `mimecast_api.py`

## Acceptance Criteria

- [ ] Adding a new domain requires editing exactly one list/location in `main()`
- [ ] No `(None)` dummy instantiation for parser registration
- [ ] All existing awareness training subcommands still parse correctly

## Work Log

- 2026-04-04: Created by code review (architecture-strategist finding)
