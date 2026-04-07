---
status: complete
priority: p2
issue_id: "015"
tags: [code-review, security, azure-ad, dxt, agent-native]
dependencies: []
---

# 015 — Destructive security operations have no dry-run or confirmation gate

## Problem Statement

`azure_ad_revoke_sessions`, `azure_ad_confirm_compromised`, and `azure_ad_delete_ca_policy` in `server.py` execute irreversible operations immediately with no confirmation step. `confirmCompromised` sets a user's risk state permanently — if Conditional Access blocks high-risk users, this immediately locks out the employee. An LLM calling these tools on the wrong account causes a production outage.

## Findings

- **File**: `extensions/azure-ad/src/server.py`, lines 700-738, 1222-1230
- **Agent**: security-sentinel (HIGH-3)

```python
# Line 713 — immediately revokes ALL sessions, no dry-run
result = await _graph("POST", f"/users/{user_id}/revokeSignInSessions")

# Lines 733-737 — sets confirmed-compromised (irreversible via API, locks account)
result = await _graph(
    "POST",
    "/identityProtection/riskyUsers/confirmCompromised",
    data={"userIds": user_ids},
)

# Lines 1222-1230 — permanently deletes CA policy, no confirmation
result = await _graph("DELETE", f"/identity/conditionalAccessPolicies/{policy_id}")
```

## Proposed Solutions

### Option A: Add dry_run parameter + confirm flag (Recommended)

```python
@mcp.tool()
async def azure_ad_revoke_sessions(
    user: str,
    dry_run: bool = True,  # default safe
) -> dict:
    if dry_run:
        return {"dry_run": True, "would_revoke": user, "message": "Pass dry_run=False to execute"}
    # ... actual revocation

@mcp.tool()
async def azure_ad_confirm_compromised(
    users: list[str],
    confirm: bool = False,  # must explicitly opt in
) -> dict:
    if not confirm:
        return {"confirm": False, "would_flag": users, "message": "Pass confirm=True to execute"}
    # ... actual flagging
```

- **Effort**: Small
- **Risk**: Low

### Option B: Log-only mode
Add structured logging to stderr for all destructive operations with timestamp and target, without adding dry_run. Lets humans audit what the LLM did.

- **Effort**: Tiny
- **Risk**: Doesn't prevent mistakes

### Option C: Separate permission tier
Move destructive tools behind a `ALLOW_DESTRUCTIVE_OPERATIONS=true` env var check. Tools return an error unless the env var is explicitly set.

- **Effort**: Small
- **Risk**: Low

## Recommended Action

Option A (dry_run + confirm) for all three tools. This is the standard agent-safe pattern for destructive operations.

## Technical Details

- **Affected tools**: `azure_ad_revoke_sessions` (line 700), `azure_ad_confirm_compromised` (line 717), `azure_ad_delete_ca_policy` (line 1222)

## Acceptance Criteria

- [ ] `azure_ad_revoke_sessions` defaults to `dry_run=True`
- [ ] `azure_ad_confirm_compromised` requires explicit `confirm=True`
- [ ] `azure_ad_delete_ca_policy` has a confirmation mechanism
- [ ] All three tools log their invocations to stderr with timestamp

## Work Log

- 2026-04-07: Identified by security-sentinel as HIGH-3
