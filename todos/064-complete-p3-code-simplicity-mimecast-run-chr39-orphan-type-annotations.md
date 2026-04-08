---
status: complete
priority: p3
issue_id: "064"
tags: [code-review, quality]
dependencies: []
---

# 064 — Code simplicity — `_mimecast_run` simplification, `chr(39)` noise, orphan-append collapse, defensive getattr, type annotations

## Problem Statement

Five minor code quality issues across the PR, each small but collectively adding noise:

1. `audit_m365_sync.py` `_mimecast_run` (lines 277-302): 26-line function is a near-duplicate of `run_cli`. The only difference is a hardcoded command prefix. Could reduce to 1-2 lines.

2. `server.py` `chr(39)` usage (lines 583, 589, 644, 727, 729): `app.replace(chr(39), chr(39)*2)` appears 5× instead of the clearer `app.replace("'", "''")`

3. `audit_m365_sync.py` dual orphan-append (lines 475-487): Two nearly identical `results["orphaned"].append(...)` blocks differing only in `note` value. Can collapse to one.

4. `sweep.py` defensive `getattr` (lines 222-233): `getattr(args, 'hours', None)` used on a fixed argparse namespace where `args.hours`, `args.days`, `args.since` always exist (defaulting to `None` from argparse).

5. Type annotation gaps in `audit_m365_sync.py`:
   - `run_cli(cmd: list, ...)` → `cmd: list[str]`
   - `_mimecast_run(cmd: list, ...)` → `cmd: list[str]`
   - `_mc_data` misleadingly named (suggests Mimecast data but handles Graph API responses) → rename to `_unwrap_graph_list` or `_extract_list`

## Findings

- `audit_m365_sync.py` line 68: `def run_cli(cmd: list, ...)` — missing `[str]`
- `audit_m365_sync.py` line 277-302: 26 lines duplicating `run_cli`
- `audit_m365_sync.py` lines 475-487: two `.append({...})` with identical structure, differ only in `note`
- `server.py` line 583: `app.replace(chr(39), chr(39)*2)` — should be `app.replace("'", "''")`
- `sweep.py` lines 222-233: `getattr(args, 'hours', None)` — argparse always sets these

## Proposed Solutions

Option A (Recommended):
1. Replace `_mimecast_run` body with: `return run_cli([MIMECAST_CLI, "--profile", profile, "--output", "json"] + cmd, verbose)` — delegates all error handling to `run_cli`. Remove the 24 inner lines.
2. Replace 5× `chr(39)` with `"'"` literal.
3. Collapse dual orphan-append: `note = "Account deleted..." if email in deleted_emails else "No matching..."; results["orphaned"].append({..., "note": note})`
4. Replace `getattr(args, 'hours', None)` with `args.hours` (×3 calls)
5. `run_cli`: `cmd: list` → `cmd: list[str]`; Rename `_mc_data` → `_unwrap_graph_list`
- Effort: Small. Risk: Low.

## Acceptance Criteria

- [x] `_mimecast_run` body reduced to delegating call to `run_cli`
- [ ] All 5 `chr(39)` uses in server.py replaced with `"'"` — NOT in scope for this task (server.py item)
- [x] Dual orphan-append collapsed to single append with conditional `note`
- [ ] `getattr(args, ...)` with defaults removed from sweep.py — NOT in scope for this task (sweep.py item)
- [x] `cmd: list` → `cmd: list[str]` in `_mimecast_run` (run_cli was already list[str])
- [x] `_mc_data` renamed to `_unwrap_graph_list` (all 3 call sites updated: fetch_azure_users, fetch_azure_deleted_users, fetch_azure_domains)

Note: server.py chr(39) and sweep.py getattr items are NOT in audit_m365_sync.py — those remain for a separate pass on server.py / sweep.py.

## Work Log

- 2026-04-08: Found by code-simplicity-reviewer, kieran-python-reviewer, pattern-recognition-specialist in 4th review pass
- 2026-04-08: audit_m365_sync.py items resolved: _mimecast_run collapsed to 1-line delegation,
  dual orphan-append collapsed to single conditional-note append, _mc_data renamed to
  _unwrap_graph_list across 3 call sites, cmd: list[str] annotation on _mimecast_run.
  server.py chr(39) and sweep.py getattr fixes remain pending (different files).
