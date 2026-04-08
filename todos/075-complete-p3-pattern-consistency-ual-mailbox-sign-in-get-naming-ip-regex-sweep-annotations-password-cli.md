---
status: complete
priority: p3
issue_id: "075"
tags: [code-review, quality, azure-ad, security]
dependencies: []
---

# 075 — Pattern consistency + minor security: ual_mailbox required users, sign_in_get naming, IP regex, --password in argv, sweep annotations

## Problem Statement

Several pattern consistency issues and minor security improvements across `server.py`, `sweep.py`, and `azure_ad_api.py`:

1. `azure_ad_ual_mailbox_access` — `users` is required string while all 3 sibling UAL tools have it `Optional`.
2. `azure_ad_sign_in_get` naming reversed — should be `azure_ad_get_sign_in` to match `get_` prefix convention.
3. `azure_ad_user_devices` return shape has no `count` key and uses `ownedDevices`/`registeredDevices` — unique across all list tools.
4. IP validation in `sweep.py` uses permissive regex `r'^[\d.:/\[\]a-fA-F%]+'` — should use `ipaddress.ip_address()` like `server.py` already does.
5. `--password` accepted as CLI argument in `azure_ad_api.py` — visible in process table on shared systems.
6. `run_sweep` missing `argparse.Namespace` type annotation on `args`; `_process_victim` return is `tuple` instead of `tuple[str, list[dict], list[dict]]`.
7. `compute_confidence` in `sweep.py` has undocumented magic numbers for scoring weights.
8. `fetch_sync_health` hardcodes `--days 2` for sync history — doesn't scale with `--grace-days`.
9. `.find("spoof") >= 0` idiom in `audit_m365_sync.py` — should be `"spoof" in ...`.
10. `getattr(args, "output", "table")` defensive pattern in domain modules — output is always present after `make_common_parser()`.

## Findings

### 1. ual_mailbox_access required users (server.py ~line 1031)
All UAL siblings: `users: Optional[str] = None`. `azure_ad_ual_mailbox_access`: `users: str` (required). Forces callers to provide a value even for tenant-wide sweeps.

### 2. sign_in_get naming reversed (server.py ~line 606)
All single-entity tools: `azure_ad_get_user`, `azure_ad_get_group`, `azure_ad_get_device`, `azure_ad_get_email`. Only outlier: `azure_ad_sign_in_get`.

### 3. user_devices return shape (server.py ~line 362)
Returns `{"ownedDevices": [...], "registeredDevices": [...]}` — no `count` key, no `value` key. Every other list tool has at least `count`. Diverges from sibling tool return contracts.

### 4. IP regex in sweep.py (lines ~62–65)
```python
if not re.match(r'^[\d.:/\[\]a-fA-F%]+$', ip):
```
Allows `%` (IPv6 zone IDs), `/`, `[`, `]`. Should use `ipaddress.ip_address()` from stdlib like `server.py`'s `_validate_ip()` already does. The `%` character could be used in percent-encoding attacks.

### 5. --password in process table (azure_ad_api.py ~line 610)
```python
users_create.add_argument('--password', required=True, help='Initial password')
```
Password appears in `ps aux` / `/proc/pid/cmdline` on Linux during process lifetime. Standard fix: `getpass.getpass()` prompt or env var fallback.

### 6. Annotation gaps in sweep.py
- `run_sweep(api, args)` — `args` should be `args: argparse.Namespace`
- `_process_victim` returns `tuple` — should be `tuple[str, list[dict], list[dict]]`
- `_values(response)` — `response` has no type annotation

### 7. compute_confidence magic numbers (sweep.py ~lines 375–390)
Scoring weights `3` (MFA fatigue), `2` (risk detection), `1` (IP/audit) and thresholds `3` (HIGH), `2` (MEDIUM) are inline magic numbers. Should be named module-level constants.

### 8. fetch_sync_health --days 2 hardcoded (audit_m365_sync.py ~line 325)
Sync history always checked for last 2 days regardless of `--grace-days` value.

### 9. .find >= 0 idiom (audit_m365_sync.py ~line 573)
```python
.find("spoof") >= 0  # should be: "spoof" in ...lower()
```

### 10. getattr(args, "output", "table") in domain modules (directory_sync.py ~lines 63, 101; human_risk.py ~lines 61, 92–95)
`output` attribute always present via `make_common_parser()`. Defensive `getattr` unnecessary (9 occurrences).

## Proposed Solutions

1. `azure_ad_ual_mailbox_access`: change `users: str` → `users: Optional[str] = None`; update body to handle `None` case (skip UPN filter or require at least one).
2. Rename `azure_ad_sign_in_get` → `azure_ad_get_sign_in` in server.py, manifest.json, SKILL.md.
3. `azure_ad_user_devices`: add `"count": len(owned.get("value", [])) + len(registered.get("value", []))` to return dict.
4. Replace IP regex in sweep.py with `ipaddress.ip_address(ip)` try/except (like server.py).
5. `azure_ad_api.py`: accept `--password` from `getpass.getpass()` when flag absent, or env var `AZURE_INITIAL_PASSWORD`.
6. Add annotations to `run_sweep`, `_process_victim`, `_values` in sweep.py.
7. Extract `_SCORE_*` and `_THRESHOLD_*` constants above `compute_confidence`.
8. Accept `--sync-history-days` arg in `main()`, pass to `fetch_sync_health`.
9. Replace `.find("spoof") >= 0` with `"spoof" in ...lower()`.
10. Replace all `getattr(args, "output", "table")` with `args.output` in domain modules.
- Effort: Small per item. Risk: Low.

## Acceptance Criteria

- [ ] `azure_ad_ual_mailbox_access` `users` parameter is Optional with `None` default
- [ ] Tool renamed to `azure_ad_get_sign_in` in server.py, manifest.json, SKILL.md
- [ ] `azure_ad_user_devices` returns `count` key
- [ ] sweep.py IP validation uses `ipaddress.ip_address()` try/except
- [ ] `azure_ad_api.py` `--password` replaced with getpass or env var
- [ ] `run_sweep`, `_process_victim`, `_values` have complete type annotations
- [ ] `compute_confidence` scoring weights are named constants
- [ ] Sync history days parameterized
- [ ] `.find("spoof") >= 0` → `"spoof" in ...`
- [ ] `getattr(args, "output", ...)` → `args.output` in domain modules (9 occurrences)

## Work Log

- 2026-04-08: Identified by pattern-recognition-specialist (FINDING-3/5/6/10), security-sentinel (FINDING-09/06), kieran-python-reviewer (FINDING-3/4/10), code-simplicity-reviewer in 5th review pass
- 2026-04-08: Resolved — all 9 items implemented: ual_mailbox users Optional, sign_in_get renamed, user_devices count key, IP regex → ipaddress stdlib, getpass for --password, sweep type annotations, compute_confidence named constants, spoof idiom fix, getattr(output) → args.output. Committed a4290c2.
