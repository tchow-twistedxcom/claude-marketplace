---
status: complete
priority: p1
issue_id: "002"
tags: [code-review, security, mimecast, injection]
dependencies: []
---

# 002 — URL injection via `policy_type` in server.py:547

## Problem Statement

In `extensions/mimecast/src/server.py` at line ~547, the MCP tool that retrieves policies constructs an API endpoint URL by interpolating a user-controlled `policy_type` parameter:

```python
uri = endpoint_map.get(policy_type, f"/api/policy/{policy_type}/get-policy")
```

When `policy_type` is not in `endpoint_map`, the fallback uses the raw user input directly in the URL path. A malicious caller could supply a crafted `policy_type` like `../../admin/something` to hit unintended endpoints on the Mimecast API server.

## Findings

- **File**: `extensions/mimecast/src/server.py`, line ~547
- **Agent**: security-sentinel (P2 in their ranking, elevated to P1 given this is user-controlled API routing)
- **Pre-existing**: This was NOT introduced in PR #3 — it exists in the original codebase. However the PR is still the right place to fix it.

## Proposed Solutions

### Option A: Allowlist validation — reject unknown types
Raise a `ValueError` if `policy_type` is not in `endpoint_map` instead of using the fallback.

```python
if policy_type not in endpoint_map:
    raise ValueError(f"Unknown policy type: {policy_type!r}. Valid: {list(endpoint_map)}")
uri = endpoint_map[policy_type]
```

- **Pros**: Eliminates the injection surface entirely. Strict API.
- **Cons**: Breaks forward-compat if Mimecast adds new policy types
- **Effort**: Small
- **Risk**: Very low

### Option B: Allowlist + sanitize fallback
Keep fallback but validate `policy_type` matches `[a-z0-9-_]+`.

```python
import re
if policy_type not in endpoint_map:
    if not re.fullmatch(r'[a-z0-9_-]+', policy_type):
        raise ValueError(f"Invalid policy_type: {policy_type!r}")
    uri = f"/api/policy/{policy_type}/get-policy"
```

- **Pros**: Allows forward-compat while blocking path traversal
- **Cons**: Still uses dynamic URL (lower risk, but not eliminated)
- **Effort**: Small
- **Risk**: Low

### Recommended
**Option A** — strict allowlist. MCP tools should never route to unknown Mimecast endpoints.

## Technical Details

- **Affected files**: `extensions/mimecast/src/server.py`
- **Vulnerability class**: URL path injection / SSRF-lite (attacker controls path on trusted server)

## Acceptance Criteria

- [ ] `policy_type` values not in `endpoint_map` raise `ValueError` with helpful message
- [ ] No path traversal sequences (`../`, `//`, etc.) can reach server.py via `policy_type`

## Work Log

- 2026-04-04: Created by code review (security-sentinel finding)
