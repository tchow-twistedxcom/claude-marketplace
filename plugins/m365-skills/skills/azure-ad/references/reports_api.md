# Reports API Reference

Microsoft 365 usage reports and the authentication-method (MFA) registration report via Microsoft
Graph API. Useful for security posture (who has not registered MFA) and activity baselining.

## Endpoints

| Operation | Method | Endpoint | Permission | Format |
|-----------|--------|----------|------------|--------|
| MFA / auth-method registration | GET | `/reports/authenticationMethods/userRegistrationDetails` | `AuditLog.Read.All` | JSON |
| O365 active users | GET | `/reports/getOffice365ActiveUserDetail(period='D7')` | `Reports.Read.All` | CSV (via 302) |
| Email activity | GET | `/reports/getEmailActivityUserDetail(period='D7')` | `Reports.Read.All` | CSV (via 302) |
| Mailbox usage | GET | `/reports/getMailboxUsageDetail(period='D7')` | `Reports.Read.All` | CSV (via 302) |

All endpoints are Graph v1.0 and support app-only auth.

> **Permission note:** the MFA registration report uses **`AuditLog.Read.All`**, NOT
> `Reports.Read.All`. Both are granted on the current app registration, so both work.

## CLI Commands

```bash
# MFA / auth-method registration report (JSON)
python3 azure_ad_api.py reports mfa-registration --top 100
python3 azure_ad_api.py reports mfa-registration --all

# Find everyone NOT registered for MFA
python3 azure_ad_api.py reports mfa-registration --filter "isMfaRegistered eq false" --all

# Usage reports (CSV, parsed to rows). period in {D7, D30, D90, D180}
python3 azure_ad_api.py reports usage --report office365-active --period D7
python3 azure_ad_api.py reports usage --report email-activity --period D30
python3 azure_ad_api.py reports usage --report mailbox-usage --period D7
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `azure_ad_mfa_registration_report` | Auth-method / MFA registration state per user (JSON) |
| `azure_ad_usage_report` | One of the 3 usage reports; CSV is fetched, followed, and parsed to rows |

## userRegistrationDetails Filterable Fields

| Field | Type | Meaning |
|-------|------|---------|
| `isMfaRegistered` | Boolean | User has registered an MFA method |
| `isMfaCapable` | Boolean | User can perform MFA (registered + method allowed by policy) |
| `isSsprRegistered` | Boolean | Registered for self-service password reset |
| `isSsprEnabled` | Boolean | SSPR enabled for the user |
| `isAdmin` | Boolean | User holds a privileged role |
| `methodsRegistered` | Array | Methods registered (e.g. microsoftAuthenticatorPush, fido2) |

## Caveats

- The three usage reports return **HTTP 302** redirecting to a short-lived, pre-authenticated
  download URL that serves **CSV**. The client follows the redirect automatically (the Authorization
  header is correctly dropped on the cross-host redirect because the target needs none). The CLI and
  MCP tools parse the CSV into row objects.
- `period` is an OData function parameter passed in single quotes: `(period='D7')`. Allowed values:
  `D7`, `D30`, `D90`, `D180`.
- If the M365 admin-center privacy setting "Display concealed user, group, and site names" is
  enabled, usage reports return **obfuscated** UPNs and display names, which breaks joins on UPN.
  The MFA registration report (Graph JSON) is not affected by that setting.
- `credentialUserRegistrationDetails` (the legacy SSPR report) is **not implemented**; it is beta
  and superseded by `userRegistrationDetails`.
