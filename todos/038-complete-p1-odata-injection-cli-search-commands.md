---
status: complete
priority: p1
issue_id: "038"
tags: [code-review, security, azure-ad]
dependencies: []
---

# 038 — OData injection in CLI `users_search`, `groups_search`, `devices_search`

## Problem Statement

`plugins/m365-skills/skills/azure-ad/scripts/azure_ad_api.py` has search commands (`users_search`, `groups_search`, `devices_search`) that directly interpolate user-supplied query strings into OData `$filter` expressions without escaping. Single quotes in the query value can break out of the filter and inject arbitrary OData operators. The `_validate_safe_name()` guard used in MCP `server.py` was NOT applied to the CLI. An attacker controlling the query value (e.g., via a shell alias or tool calling convention) can enumerate users, bypass filter predicates, or cause data disclosure beyond intended scope.

## Findings

- `server.py` received OData escaping fixes in todo 014 and todo 025: search functions apply `.replace("'", "''")` before interpolating user input into `$filter` strings.
- `azure_ad_api.py` CLI search functions (`users_search`, `groups_search`, `devices_search`) were not updated in those todos — they still interpolate raw user input.
- Example exploit: `query = "' or 1 eq 1 or startswith(displayName,'"` bypasses `startswith` predicates and returns all users.
- The CLI is invoked by MCP skills (via subprocess) and by direct shell calls, so this is an exploitable surface, not just a theoretical concern.
- The fix is already proven and present in `server.py` — this is a port-back task.

## Proposed Solutions

**Option A (Recommended):**
- Apply `.replace("'", "''")` OData escaping to all user-supplied query values before interpolation in azure_ad_api.py search functions
- Match the pattern already in server.py (e.g., `safe_query = query.replace("'", "''")`  )
- Effort: Small, Risk: Low

**Option B:**
- Add a shared `escape_odata_string()` utility in a common module imported by both azure_ad_api.py and server.py
- Effort: Small, Risk: Low

## Acceptance Criteria

- [x] `users_search`, `groups_search`, `devices_search` in azure_ad_api.py escape single quotes in query
- [x] `query = "' or 1 eq 1 or startswith(displayName,'"` does not break the OData filter
- [x] Matches escaping pattern already in server.py

## Work Log

- 2026-04-08: Identified in 3rd review pass
- 2026-04-08: Fixed — applied `safe_query = query.replace("'", "''")` in all three search methods (commit e5e06d2)
