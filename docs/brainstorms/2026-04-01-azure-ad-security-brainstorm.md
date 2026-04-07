# Brainstorm: Azure AD Security & Incident Response Extension

**Date:** 2026-04-01
**Status:** Implemented (v1.1.0)
**Plugin:** m365-skills:azure-ad

---

## What We're Building

An extension to the existing `azure-ad` skill that adds a `security` domain covering the full incident response lifecycle for compromised user accounts in Microsoft Entra ID (Azure AD).

The existing skill handled identity/directory operations well but lacked all the security-focused APIs needed to actually triage a compromise — sign-in logs, risk detections, audit trails, session revocation, and MFA inspection.

## Why This Approach

We added a single new `security` domain (rather than splitting into multiple domains like `identity-protection`, `audit`, etc.) because:

1. **Triage is a workflow** — all 13 operations are typically used together during an incident. Grouping them under one domain keeps `security sign-ins`, `security risky-users`, `security revoke-sessions` etc. logically coherent.
2. **CLI simplicity** — analysts can type `security -h` to see all incident response tools in one place.
3. **Minimal change surface** — only `azure_ad_api.py` and `formatters.py` needed modification; `auth.py` and config required no changes.

## Key Decisions

### Time-range convenience flags
Added `--hours`, `--days`, `--since` to sign-ins, risk-detections, and audit-logs. During a live incident, "show me the last 2 hours" is far faster than constructing OData datetime filters manually. These auto-compose into `$filter` strings and combine with any explicit `--filter`.

### Filter composition
The dispatch logic collects convenience flags (e.g., `--user`, `--status failure`, `--hours 24`) into a `filters` list and joins them with `' and '`. This allows the raw `--filter` escape hatch to coexist with the convenience flags.

### Formatter ordering fix
The new security entity detections were inserted **before** the existing `user` check in `get_default_fields()`. This is critical because `riskyUser` and `riskDetection` objects both contain `userPrincipalName`, which would cause them to match the generic user pattern and show wrong columns.

### No auth.py changes
The existing `https://graph.microsoft.com/.default` scope already acquires all app-granted permissions. Adding new permissions only requires Azure portal changes (grant admin consent) — zero code change.

### All v1.0 endpoints
All 13 new endpoints are in Graph API v1.0 (not beta). No need for a second `BASE_URL`.

### Write actions require `--confirm`
`revoke-sessions`, `confirm-compromised`, and `dismiss-risk` follow the existing pattern from `users delete` / `groups delete` — requiring `--confirm` prevents accidental execution.

## Operations Added (13)

| Category | Operations |
|---|---|
| Sign-in logs | sign-ins, sign-in-get |
| Identity Protection | risk-detections, risky-users, risky-user-history |
| Audit | audit-logs |
| Auth | auth-methods |
| Conditional Access | ca-policies, ca-policy-get, named-locations |
| Containment | revoke-sessions, confirm-compromised, dismiss-risk |

## Permissions Required (Azure Portal)

| Permission | Covers | License |
|---|---|---|
| `AuditLog.Read.All` | sign-ins, audit-logs | P1+ |
| `IdentityRiskEvent.Read.All` | risk-detections | P1+ |
| `IdentityRiskyUser.ReadWrite.All` | risky-users, confirm/dismiss | P2 |
| `User.RevokeSessions.All` | revoke-sessions | Any |
| `UserAuthenticationMethod.Read.All` | auth-methods | Any |
| `Policy.Read.All` | ca-policies, named-locations | Any |

## Incident Response Workflow

```
1. Detect:    security sign-ins --hours 24 --risk high
              security risky-users --state atRisk
2. Triage:    security sign-ins --user X --hours 48
              security auth-methods X (check for new MFA)
              security risky-user-history OBJECT_ID
              security audit-logs --filter "initiatedBy/user/id eq 'ID'"
3. Contain:   security revoke-sessions X --confirm
              security confirm-compromised ID --confirm
              users update X --data '{"accountEnabled": false}'
4. Remediate: security dismiss-risk ID --confirm
              users update X --data '{"accountEnabled": true}'
```

## Files Changed

- `scripts/azure_ad_api.py` — utilities + 12 API methods + CLI parser + dispatch
- `scripts/formatters.py` — 7 new entity detection cases
- `references/security_api.md` — new reference doc with playbook
- `SKILL.md` — updated triggers and capabilities
- `README.md` — updated permissions table and command reference
- `plugin.json` — version 1.1.0 + security keywords
- `../../.claude-plugin/marketplace.json` — version 1.1.0
