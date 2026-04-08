---
status: pending
priority: p3
issue_id: "051"
tags: [code-review, quality, azure-ad, mimecast]
dependencies: []
---

# 051 — Minor code quality — single-element tuple, getattr pattern, unguarded future.result, sweep _values helper

## Problem Statement

Four small code quality items across `audit_m365_sync.py`, `human_risk.py`, `azure_ad_api.py`, `sweep.py`, and related files that add noise, hide errors, or miss an opportunity for consistency.

## Findings

1. **Single-element tuple `("HIGH",)`** (`audit_m365_sync.py` or `human_risk.py`): A tuple with one element used as a membership test. Should be a set `{"HIGH"}` for clarity and consistency with other membership checks.

2. **`getattr(args, 'output', 'table')` vs `args.output`** (`azure_ad_api.py`): Some commands use `getattr` with a default for `args.output` when all subcommands already define `--output` with a default. The `getattr` is defensive code that's now redundant and adds noise.

3. **`future.result()` unguarded in ThreadPoolExecutor** (`sweep.py` or `audit_m365_sync.py`): `for future in as_completed(futures): result = future.result()` without try/except will propagate exceptions from workers and abort the entire gather. Should catch and log per-future exceptions.

4. **`sweep.py` needs `_values()` helper**: Similar to `_mc_data()`, `sweep.py` has repeated `isinstance(result, dict) and "value" in result` patterns that should be extracted to a helper.

## Proposed Solutions

Option A (Recommended):
- Replace `("HIGH",)` with `{"HIGH"}` (set literal)
- Replace `getattr(args, 'output', 'table')` with `args.output` where `--output` is always defined
- Wrap `future.result()` in `try/except Exception as e: logger.warning(...)`
- Add `_values(result)` helper to sweep.py (same pattern as `_mc_data`)
- Effort: Small, Risk: Low

## Acceptance Criteria

- [ ] Single-element tuples used as sets replaced with set literals
- [ ] Redundant `getattr` with default removed
- [ ] All `future.result()` calls guarded with try/except
- [ ] `_values()` helper added to sweep.py

## Work Log

- 2026-04-08: Identified in 3rd review pass
- 2026-04-08: Investigated `getattr(args, 'output', 'table')` in azure_ad_api.py — no instances found. Output format uses `args.format` (not `args.output`) throughout. Item 2 (getattr) is resolved for azure_ad_api.py. Items 1, 3, 4 remain pending (single-element tuple, unguarded future.result, sweep _values helper).
