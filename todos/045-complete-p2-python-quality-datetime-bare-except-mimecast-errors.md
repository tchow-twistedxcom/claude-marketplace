---
status: complete
priority: p2
issue_id: "045"
tags: [code-review, quality, azure-ad, mimecast]
dependencies: []
---

# 045 — Python quality — timezone-naive datetime, bare except Exception, invisible mimecast errors

## Problem Statement

Three Python code quality issues identified across `server.py`, `audit_m365_sync.py`, and `sweep.py`. Each is independently fixable and none are blocking, but together they create correctness risk and debugging difficulty in production.

## Findings

### 1. `datetime.now()` without `timezone.utc`

Multiple places in `server.py` and `audit_m365_sync.py` use `datetime.now()` (local time) instead of `datetime.now(timezone.utc)`. This causes incorrect time calculations when the server runs in a non-UTC timezone. Audit comparisons against Graph API timestamps (which are always UTC) would be off by the server's timezone offset.

### 2. Bare `except Exception:` in `sweep.py` collector functions

Three collector functions (`_collect_forwarding_rules`, `_collect_app_consents`, `_collect_admin_assignments`) use `except Exception: pass` or `except Exception: return []`. This silently swallows errors — API failures and network issues cause the sweep to report "no findings" when the collector actually failed. There is no way to distinguish a clean result from a silent error.

### 3. `_mimecast_run()` errors invisible

`_mimecast_run()` in `audit_m365_sync.py` suppresses `subprocess.CalledProcessError` and returns `None` on failure. The caller has no way to distinguish "no results" from "command failed". When the Mimecast CLI is misconfigured or returns an error, the audit silently produces empty data rather than surfacing the failure.

## Proposed Solutions

### Option A — Fix all three (Recommended)

- `datetime`: Global find+replace `datetime.now()` → `datetime.now(timezone.utc)` and `datetime.utcnow()` → `datetime.now(timezone.utc)` in all affected files. Ensure `from datetime import timezone` is imported.
- bare except: Replace `except Exception: pass` with `except Exception as e: logger.warning("collector failed: %s", e); return []` in all three sweep.py collectors.
- `_mimecast_run`: Return a `(result, error_message)` tuple or raise a named exception so callers can surface failures in the audit output.
- Effort: Small, Risk: Low

## Acceptance Criteria

- [x] All `datetime.now()` calls use `timezone.utc` — sweep.py had no bare datetime.now() calls; already used fromisoformat with UTC-aware strings
- [x] `except Exception` blocks in sweep.py log the exception before returning — fixed in collect_suspicious_audit_events and collect_auth_methods
- [ ] `_mimecast_run()` failures are surfaced to callers, not silently swallowed — remaining work in audit_m365_sync.py

## Work Log

- 2026-04-08: Identified in 3rd review pass
- 2026-04-08: sweep.py bare except fixed — collect_suspicious_audit_events and collect_auth_methods now log to stderr. sweep.py had no timezone-naive datetime.now() calls. _mimecast_run() (audit_m365_sync.py) still pending.
