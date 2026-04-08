---
status: pending
priority: p2
issue_id: "060"
tags: [code-review, performance, azure-ad]
dependencies: []
---

# 060 — Performance bundle — MFA fatigue parallelism, fetch_sync_health, user_devices gather, CLI timeout

## Problem Statement
Four remaining performance issues after previous parallelism fixes:

1. `sweep.py` `collect_mfa_fatigue_victims` success-query loop (~lines 104-150): Sequential `for upn in upns_with_failures: api.security_sign_ins(...)` makes one HTTPS call per victim, totaling 10-25s for 50+ victims.
2. `audit_m365_sync.py` ~line 1073: `fetch_mimecast_config` and `fetch_sync_health` run sequentially, despite being fully independent.
3. `server.py` ~line 359: `azure_ad_user_devices` makes two sequential Graph calls (`/ownedDevices`, `/registeredDevices`) that should use `asyncio.gather`.
4. `azure_ad_api.py` `_get_all_pages` nextLink uses 30s timeout vs server.py's 60s httpx client timeout — CLI may fail on large paginated exports that the MCP server handles.

## Findings
- sweep.py success queries: `for upn in upns_with_failures: succ_result = api.security_sign_ins(...)` — sequential network calls
- audit_m365_sync.py: `config = fetch_mimecast_config(...)` then `sync_health = fetch_sync_health(...)` — sequential
- server.py: `owned = await _graph("GET", f"/users/{user_id}/ownedDevices")` then `registered = await _graph(...)` — two awaits
- azure_ad_api.py `_get_all_pages` timeout: `self.config.get('defaults', {}).get('timeout', 30)` — 30s fallback vs server.py 60s

## Proposed Solutions
Option A (Recommended):
1. Extract `_query_success_signs(api, upn, f_success)` helper and use `ThreadPoolExecutor(max_workers=10)` in `collect_mfa_fatigue_victims`, matching the Vector 5 pattern established at lines 203-214
2. Wrap `fetch_mimecast_config` + `fetch_sync_health` in a `ThreadPoolExecutor(max_workers=2)` block
3. Change `azure_ad_user_devices` to `owned, registered = await asyncio.gather(_graph(...), _graph(...))`
4. Change `_get_all_pages` nextLink timeout default from `30` to `60` to match server.py
- Effort: Small per item. Risk: Low.

## Acceptance Criteria
- [ ] `collect_mfa_fatigue_victims` success queries parallelized with ThreadPoolExecutor
- [ ] `fetch_mimecast_config` and `fetch_sync_health` run concurrently
- [x] `azure_ad_user_devices` uses `asyncio.gather` for the two device calls
- [ ] `_get_all_pages` nextLink timeout default is 60s

## Work Log
- 2026-04-08: Found by performance-oracle in 4th review pass
- 2026-04-08: server.py asyncio.gather fix applied by pr-comment-resolver. In azure_ad_user_devices, the two sequential awaits for /ownedDevices and /registeredDevices are now replaced with asyncio.gather. Committed in: fix(azure-ad): standardize confirm param, events return key, asyncio.gather for user_devices. Remaining items (sweep.py mfa fatigue parallelism, audit_m365_sync.py sequential fetch, azure_ad_api.py timeout default) handled by other agents.
