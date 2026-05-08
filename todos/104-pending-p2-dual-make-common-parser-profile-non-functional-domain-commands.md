---
status: pending
priority: p2
issue_id: "104"
tags: [code-review, architecture, mimecast-skills]
dependencies: []
---

# 104 — Dual `make_common_parser` implementations: `--profile` silently non-functional for domain commands

## Problem Statement

`make_common_parser` is defined in two places: `plugins/mimecast-skills/scripts/domains/utils.py` (includes `--profile`) and `plugins/mimecast-skills/scripts/mimecast_api.py` (does not). Domain command modules import the version from `mimecast_api.py`, which lacks `--profile`. When a user passes `--profile` to a domain command, the argument is silently ignored or causes an unrecognized-argument error — inconsistent with the documented interface and with direct CLI usage.

## Findings

- **`plugins/mimecast-skills/scripts/domains/utils.py`**: defines `make_common_parser` with `--profile` argument
- **`plugins/mimecast-skills/scripts/mimecast_api.py`**: defines `make_common_parser` without `--profile`
- Domain command modules (`awareness_training.py`, `directory_sync.py`, `human_risk.py`) import from `mimecast_api.py`
- `--profile` appears documented in `SKILL.md` but is unreachable for domain commands
- Flagged by: architecture-strategist (7th review pass)

## Proposed Solutions

### Option A: Consolidate to a single `make_common_parser` (recommended)

Move the canonical definition to `domains/utils.py` (which already has the more complete version) and update `mimecast_api.py` to import from there:
```python
# mimecast_api.py
from .domains.utils import make_common_parser
```

- **Effort**: Small | **Risk**: Low (single authoritative definition)

### Option B: Add `--profile` to `mimecast_api.py`'s version

Duplicate the `--profile` argument addition so both implementations match. Less clean but avoids import dependency restructuring.

- **Effort**: Trivial | **Risk**: Low

## Acceptance Criteria

- [ ] Single canonical `make_common_parser` definition (no duplication)
- [ ] `--profile` argument available to all domain commands
- [ ] Domain commands use the same parser factory as direct CLI commands

## Work Log

- 2026-04-08: Identified in 7th code review pass (architecture-strategist) — parser duplication causes silent --profile breakage for domain commands
