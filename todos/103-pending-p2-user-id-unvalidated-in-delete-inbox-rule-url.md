---
status: pending
priority: p2
issue_id: "103"
tags: [code-review, security, azure-ad]
dependencies: []
---

# 103 — `user_id` not validated before insertion into DELETE URL in `azure_ad_delete_inbox_rule`

## Problem Statement

`azure_ad_delete_inbox_rule` constructs a Graph API DELETE URL using `user_id` directly without validation. A caller passing a malicious `user_id` containing path separators (`/`, `..`) or encoded sequences could manipulate the URL path. Todo 095 addressed `rule_id` validation; `user_id` was not updated in the same pass. Both parameters are caller-supplied and both appear in the URL path.

## Findings

- **`extensions/azure-ad/src/server.py`** `azure_ad_delete_inbox_rule`: builds URL like `f"{GRAPH_BASE}/users/{user_id}/mailFolders/inbox/messageRules/{rule_id}"`
- `rule_id` was validated/sanitized in 095
- `user_id` is not validated — accepts arbitrary strings including `/`, `%2F`, `..`, etc.
- Consistent with how `user_id` is validated in other tools (e.g., `azure_ad_list_inbox_rules`) — the same guard should apply here
- Flagged by: security-sentinel (7th review pass)

## Proposed Solutions

### Option A: Add UPN/GUID validation for `user_id` (recommended)

Reuse the same `user_id` guard already applied elsewhere (email format or GUID pattern):
```python
if not re.match(r'^[a-zA-Z0-9@._-]+$', user_id):
    raise ValueError(f"Invalid user_id: {user_id!r}")
```

- **Effort**: Trivial | **Risk**: None

### Option B: URL-encode `user_id`

Use `urllib.parse.quote(user_id, safe='@')` before URL construction to neutralize path traversal. Less strict than validation but still safe.

- **Effort**: Trivial | **Risk**: Low

## Acceptance Criteria

- [ ] `user_id` validated before URL insertion in `azure_ad_delete_inbox_rule`
- [ ] Validation matches the pattern used for `user_id` in other tools in `server.py`

## Work Log

- 2026-04-08: Identified in 7th code review pass (security-sentinel) — user_id missed when 095 addressed rule_id validation
