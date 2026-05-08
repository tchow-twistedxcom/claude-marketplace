---
status: complete
priority: p3
issue_id: "034"
tags: [code-review, quality, cleanup, azure-ad, mimecast]
dependencies: []
---

# 034 — Code cleanup: dead code, duplication, and minor quality issues across new files

## Problem Statement

Several minor code quality issues identified across the new files. None are blocking, but they add noise and will accumulate.

## Findings

### server.py
- **Duplicate CA policy list tools**: `azure_ad_ca_policies` (line 717) and `azure_ad_list_ca_policies` (line 1169) both list CA policies with different signatures. One should be removed.
- **Dead dict construction in `azure_ad_create_ca_policy`** (lines 1252-1264): `conditions.users` is built with a redundant spread, then unconditionally overwritten 15 lines later. First construction is dead code.
- **`_validate_safe_name` unreachable escape** (line 47): `value.replace("'", "''")` is dead — the regex already blocks `'`.
- **`json.loads(_fmt(result))` roundtrip** (lines 776, 817): covered by todo 029.
- **UAL time window copy-pasted 5×**: 3-line `now/start/end` block across `azure_ad_ual_inbox_rules`, `azure_ad_ual_search`, `azure_ad_ual_sharepoint`. Extract `_ual_time_window(hours)` helper.

### audit_m365_sync.py
- **`_run` closure defined twice identically** (lines 283, 313): `fetch_mimecast_config` and `fetch_sync_health` each define the same `_run` closure. Extract to a module-level helper.
- **`_extract_graph_list()` missing**: 5-line `isinstance(data, dict) and "value" in data` boilerplate repeated in 3 fetch functions. Should be a one-liner helper.
- **`_is_mimecast_infra` misleading variable name** (line 224): `local_at` contains `local@` not just the local part — rename to `local_prefix`.
- **`employees` vs `real_users` key inconsistency**: Azure segments use `employees`, Mimecast uses `real_users` for the equivalent set.

### sweep.py
- **`audit_filter_base` is a duplicate of `risk_filter_base`** (lines 264-269): identical `build_time_filter` call with same args. Remove and use `risk_filter_base` directly.
- **Bare `except: continue`** (line 96): Should be `except Exception as e: print_warning(...)`. (Fixed by todo 033 commit 94b6d3c)

### azure_ad_api.py
- **Lazy `from datetime import ...` inside `build_time_filter`** (line 52): stdlib import — move to top of file.
- **Legacy type hints** `Dict`, `List`, `Optional` throughout: project is Python 3.10+, use `dict`, `list`, `str | None`.

### domains/directory_sync.py + human_risk.py
- **`import json` / `import re` inside methods**: Move to module-level imports.
- **`_build_summary` in human_risk.py** is a module-level function only used by one class method — should be a `@staticmethod`.
- **`fetch_sync_health` runs two subprocess calls sequentially** (lines 315-318): both independent, should use `ThreadPoolExecutor` like `fetch_mimecast_config`.

## Recommended Action

Address as a cleanup PR after merging the main feature. None of these are blocking or correctness issues.

## Acceptance Criteria

- [x] `azure_ad_ca_policies` removed from server.py (duplicate tool — kept `azure_ad_list_ca_policies` as the more complete one)
- [x] Dead dict construction in `azure_ad_create_ca_policy` removed (replaced with clean `users_condition` variable)
- [x] `_validate_safe_name` dead `.replace()` removed
- [x] `_ual_time_window(hours)` helper extracted; all 4 UAL tool functions updated to use it
- [x] `_run` closure deduplicated in audit_m365_sync.py (extracted `_mimecast_run` module-level helper)
- [x] `_extract_graph_list()` helper extracted in audit_m365_sync.py; replaces boilerplate in 3 fetch functions
- [x] `local_at` renamed to `local_prefix` in `_is_mimecast_infra`
- [x] `audit_filter_base` removed from sweep.py; replaced with `risk_filter_base` (identical call)
- [x] `from datetime import ...` moved from inside `build_time_filter` to module-level in azure_ad_api.py
- [x] Legacy type hints (`Dict`, `List`, `Optional`) replaced with Python 3.10+ builtins throughout azure_ad_api.py

## Work Log

- 2026-04-07: Identified by code-simplicity-reviewer, pattern-recognition-specialist, kieran-python-reviewer
- 2026-04-07: All 10 cleanup items completed (todo 034 commit). Notes:
  - `bare except: continue` in sweep.py was already fixed by todo 033 (commit 94b6d3c)
  - `json.loads(_fmt(result))` roundtrip in server.py was already fixed by todo 029 (commit 25d965c)
  - domains/directory_sync.py and human_risk.py items were out of scope for the scoped todo items
