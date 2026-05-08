---
status: complete
priority: p2
issue_id: "059"
tags: [code-review, security, quality, azure-ad]
dependencies: []
---

# 059 — `auth.py` error_description leaks tenant/client IDs + server.py UAL exception handling silent failures

## Problem Statement
Two exception handling issues:

1. `auth.py` line 224-225: MSAL `error_description` included verbatim in `AuthError` message. Microsoft's error_description frequently contains `"AADSTS700016: Application with identifier 'b068503f-...' was not found in directory 'ede4fe1e-...'"` — leaking tenant ID and client ID. The same fix was applied to `server.py` (line 152-153) but `auth.py` was missed.

2. `server.py` lines 918-921: `except Exception: pass` in UAL blob download loop silently swallows `json.JSONDecodeError` and `TypeError`, creating invisible forensic data gaps with no warning to the caller. The `azure_ad_incident_triage` UAL fetch (lines 1846-1849) also uses bare `except Exception:` without logging.

## Findings
```python
# auth.py lines 224-225
error_desc = result.get('error_description', 'No description')
raise AuthError(f"Failed to acquire token: {error} - {error_desc}")  # LEAKS tenant/client IDs

# server.py lines 918-921
try:
    all_events.extend(resp.json())
except Exception:
    pass  # SILENT: audit gap created with no warning

# server.py lines 1846-1849
try:
    ual_events = await _ual_fetch_blobs("Audit.Exchange", ual_start, ual_end)
except Exception:
    ual_events = []  # SILENT: no logging of what went wrong
```

## Proposed Solutions
Option A (Recommended):
1. `auth.py`: Remove `error_description` from AuthError. Only include `error` (short AADSTS code): `raise AuthError(f"Failed to acquire token: {error}")`
2. `server.py` UAL blob loop: Replace bare `pass` with typed exception handling:
   ```python
   except json.JSONDecodeError as e:
       print(f"WARNING: UAL blob parse failed: {e}", file=sys.stderr)
   except TypeError as e:
       print(f"WARNING: UAL blob unexpected shape: {e}", file=sys.stderr)
   ```
3. `server.py` triage UAL fetch: Add logging: `except Exception as e: print(f"WARNING: UAL fetch failed for triage: {e}", file=sys.stderr); ual_events = []`
- Effort: Small. Risk: Low.

## Acceptance Criteria
- [x] `auth.py` AuthError does not include `error_description` in message
- [x] `server.py` UAL blob `except Exception: pass` replaced with typed exception handlers that log to stderr
- [x] `server.py` `_triage_one` UAL fetch exception includes `as e` and logs warning to stderr

## Work Log
- 2026-04-08: Found by security-sentinel (auth.py) and kieran-python-reviewer (server.py) in 4th review pass
- 2026-04-08: Fixed in commit a13663a — removed error_description from auth.py AuthError, replaced bare except-pass in UAL blob loop with typed json.JSONDecodeError/TypeError handlers logging to stderr, added as-e logging to _triage_one UAL fetch exception
