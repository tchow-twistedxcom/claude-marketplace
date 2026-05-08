---
status: pending
priority: p1
issue_id: "039"
tags: [code-review, security, azure-ad]
dependencies: []
---

# 039 — KQL injection in `azure_ad_advanced_hunt` — raw query passed to Defender API

## Problem Statement

`extensions/azure-ad/src/server.py` `azure_ad_advanced_hunt()` accepts a `query` parameter and passes it directly to the Microsoft Defender Threat Hunting API (Advanced Hunting) without sanitization. Any caller (agent or human) can pass arbitrary KQL, including queries that use `let` statements to exfiltrate data from unintended tables, call `external_data()` or `union` across unintended schemas, or use newlines/backticks to escape the intended query context.

The existing KQL blocklist (`BLOCKED_KQL`) at lines around 965–975 does not block newlines (`\n`), backtick (`` ` ``), or `union` keyword variations (e.g., `UNION`, `Union`). The blocklist approach is inherently incomplete.

## Findings

- `azure_ad_advanced_hunt` passes the `query` parameter to the Defender Advanced Hunting API with only a partial blocklist check.
- `BLOCKED_KQL` is case-sensitive — `UNION`, `Union`, `uNiOn` all bypass the check.
- Newline characters (`\n`) allow multi-statement KQL injection that bypasses single-line pattern checks.
- Backtick (`` ` ``) is a KQL string delimiter that can be used to break out of intended filter contexts.
- `external_data()` and `externaldata()` are KQL operators that fetch data from attacker-controlled URIs — neither is in the current blocklist.
- The tool is exposed as an MCP tool callable by any connected agent without additional authorization.

## Proposed Solutions

**Option A (Recommended):**
- Wrap `azure_ad_advanced_hunt` in a schema allowlist: only permit queries that begin with `DeviceLogonEvents`, `EmailEvents`, `AlertInfo`, `IdentityLogonEvents` or other approved table names
- Add `\n` and `` ` `` to `BLOCKED_KQL`
- Add case-insensitive matching to existing blocklist checks (use `query.upper()` or `re.search(..., re.IGNORECASE)`)
- Effort: Small, Risk: Low

**Option B:**
- Treat `azure_ad_advanced_hunt` as privileged/admin-only: add `confirm: bool = False` guard like destructive operations, requiring explicit `confirm=True`
- Document that arbitrary KQL is intentionally allowed for authorized security analysts
- Effort: Small, Risk: Low

**Option C:**
- Remove `azure_ad_advanced_hunt` from the public MCP tool surface and only expose curated hunt queries
- Effort: Large, Risk: Medium

## Acceptance Criteria

- [ ] `BLOCKED_KQL` includes `\n`, `` ` ``, and uses case-insensitive matching
- [ ] Either: table allowlist restricts queries to approved schemas; OR `confirm=False` guard requires explicit opt-in
- [ ] Threat model decision documented in tool docstring

## Work Log

- 2026-04-08: Identified in 3rd review pass
