---
status: pending
priority: p3
issue_id: "095"
tags: [code-review, security, azure-ad]
dependencies: []
---

# 095 — `rule_id` path segment unvalidated before DELETE URL construction

## Problem Statement

`azure_ad_delete_inbox_rule` interpolates `rule_id` directly into the URL path at server.py line 1925 with no format validation. While `httpx` URL-encodes path segments (mitigating classic traversal), the lack of explicit format validation is inconsistent with how other ID parameters are handled (e.g., GUID validation for `group_id`). A crafted `rule_id` with unexpected characters could produce unexpected API behavior.

## Findings

- **server.py line 1925**: `await _graph("DELETE", f"/users/{user_id}/mailFolders/inbox/messageRules/{rule_id}")` — no validation on `rule_id`
- Graph API inbox rule IDs are opaque base64url strings (e.g., `AAAAAGRVLlQAAAEJ...`)
- No explicit allowlist or pattern check before path construction
- Contrast: `group_id` GUID validation pattern elsewhere in the file
- Flagged by: security-sentinel (low severity)

## Proposed Solutions

### Option A: Add regex format check for rule_id
```python
import re
if not re.match(r'^[A-Za-z0-9+/=_\-]{4,500}$', rule_id):
    raise ValueError(f"Invalid rule_id format: {rule_id!r}")
```
- Allows base64url characters + standard padding, rejects path separators and query chars
- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria
- [ ] `rule_id` is validated against a safe character set before use in URL
- [ ] Invalid `rule_id` raises `ValueError` with clear message

## Work Log
- 2026-04-08: Identified in 6th code review pass (security-sentinel)
