---
status: pending
priority: p2
issue_id: "029"
tags: [code-review, bug, azure-ad, server]
dependencies: [015]
---

# 029 — Destructive MCP tools return dict not str — json.loads(_fmt()) roundtrip throws JSONDecodeError

## Problem Statement

`azure_ad_revoke_sessions`, `azure_ad_confirm_compromised`, and `azure_ad_delete_ca_policy` in `server.py` declare `-> dict` return type and use `json.loads(_fmt(result))` on their execute paths. Every other `@mcp.tool` in the file returns `-> str` via `_fmt()`. Two problems:

1. `_fmt()` truncates output to 25,000 chars. `json.loads()` on a truncated JSON string raises `JSONDecodeError`, silently breaking the operation confirmation.
2. The dry-run paths return raw `dict` objects while execute paths go through `_fmt → json.loads` round-trip — inconsistent semantics within the same function.

## Findings

- **File**: `extensions/azure-ad/src/server.py`, lines 747 (`revoke_sessions`), 779 (`confirm_compromised`), 1301 (`delete_ca_policy`)
- **Agents**: pattern-recognition-specialist (HIGH), code-simplicity-reviewer

```python
# Execute path — truncation risk
return json.loads(_fmt(result))  # _fmt truncates at 25k chars then json.loads fails

# Dry-run path — raw dict (no truncation issue)
return {"dry_run": True, ...}
```

## Proposed Solutions

### Option A: Return -> str consistently, use _fmt() for both paths (Recommended)
Change return type to `-> str`. For dry-run path, return `json.dumps({"dry_run": True, ...})` or pass through `_fmt()`. For execute path, return `_fmt(result)` directly.

### Option B: Return -> dict consistently, skip _fmt() on execute path
Return `result` directly (the raw Graph API dict) on execute path. FastMCP will serialize it. This avoids the truncation issue but changes the response format.

## Recommended Action

Option A — consistent `-> str` return type matches all other tools.

## Acceptance Criteria

- [ ] `azure_ad_revoke_sessions`, `azure_ad_confirm_compromised`, `azure_ad_delete_ca_policy` all return `-> str`
- [ ] No `json.loads(_fmt(result))` roundtrip in any tool
- [ ] Dry-run paths return JSON strings, not raw dicts

## Work Log

- 2026-04-07: Identified by pattern-recognition-specialist and code-simplicity-reviewer
