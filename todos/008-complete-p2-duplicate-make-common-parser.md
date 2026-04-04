---
status: complete
priority: p2
issue_id: "008"
tags: [code-review, architecture, mimecast, duplication]
dependencies: []
---

# 008 — Duplicate `make_common_parser()` in `mimecast_api.py` and `utils.py`

## Problem Statement

`make_common_parser()` exists in two places with **divergent signatures**:

- `domains/utils.py`: returns `argparse.ArgumentParser` with `--output` (table/json/csv) and `--profile`
- `mimecast_api.py`: defined locally as a factory function with different behavior

The `csv` output choice in `utils.py` version is also non-functional — `format_output()` in `mimecast_formatter.py` has no `csv` handler and silently falls back to table output.

## Findings

- **Agent**: architecture-strategist (P2), code-simplicity-reviewer (P3)
- **Files**: `domains/utils.py`, `mimecast_api.py`

## Proposed Solutions

### Option A: Remove duplicate from `mimecast_api.py`, use `utils.py` version everywhere

Remove the local definition from `mimecast_api.py`. Import `make_common_parser` from `domains.utils`. Fix `csv` choice (either add handler or remove it).

- **Pros**: Single source of truth; eliminates divergence risk
- **Cons**: Need to verify all call sites use the utils.py signature
- **Effort**: Small
- **Risk**: Low

### Option B: Remove `csv` from output choices until implemented
In `utils.py`, change `choices=["table", "json", "csv"]` to `choices=["table", "json"]`. Add csv back when `format_output()` handles it.

- **Pros**: Removes the silent-fallback bug
- **Cons**: If csv was intentional placeholder, removes it prematurely
- **Effort**: Tiny
- **Risk**: Very low

### Recommended
**Option A + Option B together**: consolidate to one `make_common_parser`, remove `csv` until implemented.

## Technical Details

- **Affected files**: `mimecast_api.py`, `domains/utils.py`, `mimecast_formatter.py`

## Acceptance Criteria

- [ ] `make_common_parser()` exists in exactly one location
- [ ] `--output csv` either works correctly or is not an available choice
- [ ] `mimecast_api.py` imports from `domains.utils` (no local duplicate)

## Work Log

- 2026-04-04: Created by code review (architecture-strategist finding)
