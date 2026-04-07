---
status: complete
priority: p2
issue_id: "026"
tags: [code-review, bug, correctness, azure-ad]
dependencies: []
---

# 026 — _get_all_pages silently truncates at max_pages with no warning — audit correctness bug

## Problem Statement

Both `server.py` and `azure_ad_api.py` implement `_get_all_pages()` with a `max_pages` cap (50 and 100 respectively). When the cap is hit, the function returns a silently truncated list. For the audit use case, a tenant with 5,000+ users would hit this cap and the audit would report false orphan findings (users visible in Azure but not in the truncated list would appear as Mimecast-only orphans).

The two implementations also have divergent caps: server.py caps at 50 pages, azure_ad_api.py at 100. A call that returns 51 pages via the MCP tool is truncated while the same call via CLI is not.

## Findings

- **File**: `extensions/azure-ad/src/server.py`, lines 157-167 — `max_pages=50`
- **File**: `plugins/m365-skills/skills/azure-ad/scripts/azure_ad_api.py`, lines 134-165 — `max_pages=100`
- **Agents**: kieran-python-reviewer (Critical/High), performance-oracle

At 200 users/page: server.py truncates at 10,000 users, azure_ad_api.py at 20,000. Large enterprise tenants easily exceed this.

## Proposed Solutions

### Option A: Warn to stderr on truncation (Recommended, minimal)
```python
if page >= max_pages and endpoint:
    print(f"⚠ WARNING: _get_all_pages hit max_pages={max_pages} limit — results are TRUNCATED. "
          f"Use --top with a higher value or increase max_pages for full coverage.", file=sys.stderr)
```

### Option B: Raise an exception on truncation (strict mode)
Raise `RuntimeError("Result truncated at max_pages")` if the loop exits due to the cap rather than `nextLink` being absent. Callers must explicitly handle this.

### Option C: Make max_pages configurable with a high default
Change defaults: `max_pages=500` (effectively unlimited for most tenants). At 200/page this covers 100k users.

### Option D: Align the two implementations
Both `server.py` and `azure_ad_api.py` should use the same default cap and document the limitation identically.

## Recommended Action

Options A + C + D — warn to stderr, increase default to 500, align the two implementations. Tiny changes, high correctness value.

## Acceptance Criteria

- [x] A warning is printed to stderr when `_get_all_pages` hits `max_pages` and more pages exist
- [x] Both implementations use the same `max_pages` default (both now 500)
- [x] The `azure_ad_list_users --all` path in the audit is not silently truncated for tenants with 10k+ users

## Work Log

- 2026-04-07: Identified by kieran-python-reviewer (Critical) and performance-oracle
- 2026-04-07: Fixed `azure_ad_api.py` portion. Increased `max_pages` default from 100 to 500 (covers 100k users at 200/page). Added post-loop stderr warning when the cap is hit and `@odata.nextLink` is still present. The `server.py` divergent cap (`max_pages=50`) is a separate file and was handled in a separate work item. Committed as `65f3544` (`fix(azure-ad-api): SSRF nextLink validation + truncation warning in _get_all_pages (todos 023,026)`).
- 2026-04-07: Fixed `server.py` portion (commit 25d965c). Increased max_pages default from 50 to 500 (now aligned with azure_ad_api.py). Added stderr WARNING when cap is hit and @odata.nextLink is still present. Both acceptance criteria for server.py now satisfied.
