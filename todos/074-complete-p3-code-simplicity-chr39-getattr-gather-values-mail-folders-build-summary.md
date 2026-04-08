---
status: complete
priority: p3
issue_id: "074"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 074 — Code simplicity: chr(39)/chr(10) in server.py, getattr in sweep.py, _gather_values helper, VALID_MAIL_FOLDERS, _build_summary

## Problem Statement

Several simplicity issues remaining after previous cleanup passes. Two items (`chr(39)` and `getattr`) were flagged in todo 064 but left unfixed in `server.py` and `sweep.py` respectively. New items: 7 repeated `isinstance(Exception)` guards in `_triage_one`, `VALID_MAIL_FOLDERS` inside function body, `_build_summary` as module-level function when it belongs as a `@staticmethod`.

## Findings

### 1. `chr(39)` and `chr(10)` in server.py (lines ~583, 589, 644, 727, 729, 1490) — NOT fixed by todo 064
```python
# 5 occurrences:
app.replace(chr(39), chr(39)*2)   # means: app.replace("'", "''")
# 1 occurrence:
f"| where {chr(10) + '    and '.join(filters)}\n"  # means: "\n    "
```
`chr(39)` = single quote `'`. `chr(10)` = newline `\n`. These are obfuscated character codes. Should be literal strings.

### 2. `getattr(args, ...)` in sweep.py (lines ~252–260, 268, 320) — NOT fixed by todo 064
```python
hours=getattr(args, 'hours', None),
days=getattr(args, 'days', None),
since=getattr(args, 'since', None),
ips=getattr(args, 'ips', None),
```
`args` always comes from `argparse.parse_args()` where all these attributes are defined. The `getattr(..., None)` default is defensive coding for a case that cannot occur. Should be direct attribute access: `hours=args.hours`.

### 3. `_gather_values` helper missing — 7 copies of isinstance/Exception guard in `_triage_one` (server.py ~lines 1947–2073)
```python
# Pattern repeated 7 times:
(data.get("value", []) if isinstance(data, dict) else []) if not isinstance(data, Exception) else []
```
A single `_gather_values(result) -> list` helper collapses all 7 into one-line calls:
```python
def _gather_values(result) -> list:
    if isinstance(result, Exception): return []
    return result.get("value", []) if isinstance(result, dict) else []
```

### 4. `VALID_MAIL_FOLDERS` inside function body (server.py ~line 1153)
```python
async def azure_ad_search_mail(...):
    VALID_MAIL_FOLDERS = {"inbox", "sentitems", "drafts", ...}  # recreated every call
```
Should be at module scope alongside the other allowlists (`VALID_RISK_LEVELS`, `VALID_CA_STATES`).

### 5. `_build_summary` in `human_risk.py` is not a `@staticmethod` (line ~199)
`_build_summary(users)` is a module-level function used only by `HumanRiskDomain.cmd_summary`. It has no `self`/`cls` dependency. Should be `@staticmethod` on `HumanRiskDomain`. Was flagged in todo 034 and deferred.

### 6. `params or None` anti-pattern (server.py ~line 285)
```python
result = await _graph("GET", f"/users/{user_id}", params=params or None)
```
`params = {}` two lines above. httpx treats empty dict identical to `None` for query params. `or None` guard is solving a non-problem.

## Proposed Solutions

1. Replace all 6 `chr(39)`/`chr(10)` occurrences with literal `"'"` and `"\n"`.
2. Replace 6 `getattr(args, 'x', None)` with `args.x` in `run_sweep`.
3. Extract `_gather_values` at module level in `server.py`; replace 7 occurrences in `_triage_one`.
4. Move `VALID_MAIL_FOLDERS` to module scope.
5. Promote `_build_summary` to `@staticmethod` on `HumanRiskDomain`.
6. Remove `or None` from `azure_ad_get_user` params call.
- Effort: Small. Risk: Zero.

## Acceptance Criteria

- [ ] No `chr(39)` or `chr(10)` in server.py — all replaced with literal strings
- [ ] No `getattr(args, ...)` in `run_sweep`/`_process_victim` — direct `args.x` access
- [ ] `_gather_values(result) -> list` helper extracted; 7 occurrences in `_triage_one` replaced
- [ ] `VALID_MAIL_FOLDERS` at module scope
- [ ] `_build_summary` is `@staticmethod` on `HumanRiskDomain`
- [ ] `params or None` removed from `azure_ad_get_user`

## Work Log

- 2026-04-08: Identified by code-simplicity-reviewer in 5th review pass. Items 1 and 2 were originally in todo 064 but scope was limited to audit_m365_sync.py.
- 2026-04-08: Resolved. chr(39)/chr(10) were not present in server.py (already clean). _gather_values helper extracted to module scope; 5 isinstance/Exception guard patterns replaced in _triage_one. VALID_MAIL_FOLDERS moved to module scope. params or None removed from azure_ad_get_user. getattr(args, ...) replaced with direct args.x in sweep.py. _build_summary promoted to @staticmethod on HumanRiskDomain. Commit: a8c2a30.
