---
status: pending
priority: p3
issue_id: "063"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 063 — Pattern consistency — `dry_run` vs `confirm`, `user` vs `user_id`, return key shapes

## Problem Statement

Three naming/pattern inconsistencies in server.py that increase cognitive overhead for agents and developers:

1. Safety gate naming: `azure_ad_revoke_sessions` uses `dry_run: bool = True` (inverted logic — True=safe) while all other 3 destructive tools use `confirm: bool = False` (False=safe). An agent generalizing the pattern will use the wrong parameter on revoke_sessions.

2. Single-user parameter name: 12 tools use `user_id`, 6 tools use `user` — both accepting UPN or object ID with no semantic distinction. `azure_ad_auth_methods` takes `user_id` while closely related `azure_ad_mfa_changes` takes `user`.

3. Return key inconsistency: `azure_ad_mfa_changes` and `azure_ad_role_changes` return `{"count": N, "value": items[:top]}` while peer audit log tools (`azure_ad_ual_inbox_rules`, etc.) return `{"count": N, "events": [...]}`. The `mfa_changes`/`role_changes` also apply `items[:top]` as a post-fetch slice rather than using Graph `$top`.

## Findings

```python
# server.py line 778 — OUTLIER: uses dry_run (inverted)
async def azure_ad_revoke_sessions(user: str, dry_run: bool = True) -> str:
    if dry_run:
        return json.dumps({"dry_run": True, ...})

# Canonical pattern for 3 other destructive tools:
async def azure_ad_confirm_compromised(users: list[str], confirm: bool = False) -> str:
async def azure_ad_delete_ca_policy(policy_id: str, confirm: bool = False) -> str:
async def azure_ad_advanced_hunt(query: str, top: int = 1000, confirm: bool = False) -> str:

# server.py lines 1651, 1688 — inverted key order + post-fetch slice
return _fmt({"count": len(items), "value": items[:top]})  # mfa_changes, role_changes
# vs. all other tools:
return _fmt({"value": items, "count": len(items)})  # sign_ins, audit_logs, etc.
```

## Proposed Solutions

Option A (Recommended):
1. Rename `dry_run` → `confirm` on `azure_ad_revoke_sessions`, invert logic: `if not confirm: return dry-run response`. Update docstring and SKILL.md.
2. Standardize `user`→`user_id` (or vice versa) across all single-user-lookup tools. `user_id` is more descriptive; rename the 6 `user` params to `user_id`. Update all docstrings.
3. Change `mfa_changes`/`role_changes` return to `{"value": items[:top], "count": len(items)}` (consistent key order) and rename `"value"` to `"events"` to match the UAL tool family.
- Effort: Small. Risk: Low (non-breaking for MCP callers that use named params).

## Acceptance Criteria

- [ ] `azure_ad_revoke_sessions` uses `confirm: bool = False` (not `dry_run: bool = True`)
- [ ] All single-user tools use consistent param name (`user_id` recommended)
- [ ] `azure_ad_mfa_changes` and `azure_ad_role_changes` use `"events"` key with consistent key ordering

## Work Log

- 2026-04-08: Found by pattern-recognition-specialist in 4th review pass
