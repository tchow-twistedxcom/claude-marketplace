---
status: pending
priority: p1
issue_id: "036"
tags: [code-review, security, azure-ad]
dependencies: []
---

# 036 — SSRF in server.py `_get_all_pages` — nextLink host validation missing

## Problem Statement

`extensions/azure-ad/src/server.py` has its own `_get_all_pages()` function (around line 199–201) that follows `@odata.nextLink` pagination. Unlike `azure_ad_api.py` (which was fixed in todo 023), the server.py version does NOT validate that `nextLink` URLs belong to `graph.microsoft.com`. An attacker who controls a Graph API response could return a `@odata.nextLink` pointing to an internal service (e.g., `http://169.254.169.254/latest/meta-data/`), causing the MCP server to make SSRF requests. The fix was only applied to the CLI, not the server.

## Findings

- `azure_ad_api.py` received the SSRF fix in todo 023: validates that `nextLink` starts with `https://graph.microsoft.com/` before following.
- `server.py` contains a separate, independent `_get_all_pages()` implementation that was not updated in todo 023.
- The server.py version fetches `nextLink` values directly without any host validation.
- This affects all paginated MCP tools that call `_get_all_pages()`, including user/group enumeration tools.
- The MCP server runs with service principal credentials that have broad read access, making SSRF especially impactful.

## Proposed Solutions

**Option A (Recommended):**
- Add the same `GRAPH_BASE = "https://graph.microsoft.com/"` constant and host validation already added to `azure_ad_api.py`
- In `_get_all_pages()`: `if not next_link.startswith(GRAPH_BASE): raise ValueError(f"Rejected non-Graph nextLink: {next_link}")`
- Effort: Small, Risk: Low

**Option B:**
- Extract shared pagination logic into a module imported by both CLI and server
- Effort: Large, Risk: Medium

## Acceptance Criteria

- [ ] `_get_all_pages()` in server.py validates nextLink starts with `https://graph.microsoft.com/`
- [ ] Malicious nextLink values raise ValueError and do not result in outbound requests
- [ ] Fix mirrors the pattern already applied in `azure_ad_api.py`

## Work Log

- 2026-04-08: Identified in 3rd review pass
