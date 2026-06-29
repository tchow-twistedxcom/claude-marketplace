# Policy API Reference

Tenant-wide identity and security policy reads via Microsoft Graph API. These describe the security
posture of the directory (consent settings, security defaults, allowed auth methods, guest and
cross-tenant access). All reads use `Policy.Read.All` (granted) and are Graph v1.0, app-only.

## Endpoints

| Operation | Method | Endpoint | Shape |
|-----------|--------|----------|-------|
| Authorization policy | GET | `/policies/authorizationPolicy` | single object |
| Security defaults | GET | `/policies/identitySecurityDefaultsEnforcementPolicy` | single object |
| Authentication methods policy | GET | `/policies/authenticationMethodsPolicy` | single object |
| Permission grant policies | GET | `/policies/permissionGrantPolicies` | collection |
| Cross-tenant access policy | GET | `/policies/crossTenantAccessPolicy` (+ `/default`) | single object |
| Admin consent request policy | GET | `/policies/adminConsentRequestPolicy` | single object |

## CLI Commands

```bash
python3 azure_ad_api.py policy authorization
python3 azure_ad_api.py policy security-defaults
python3 azure_ad_api.py policy authentication-methods
python3 azure_ad_api.py policy permission-grants
python3 azure_ad_api.py policy cross-tenant
python3 azure_ad_api.py policy admin-consent-request

# Aggregate posture check with flagged risky settings
python3 azure_ad_api.py policy posture
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `azure_ad_authorization_policy` | User consent + guest defaults |
| `azure_ad_security_defaults` | Whether security defaults are enforced |
| `azure_ad_authentication_methods_policy` | Which MFA methods are enabled |
| `azure_ad_permission_grant_policies` | App consent framework policies |
| `azure_ad_cross_tenant_access_policy` | B2B / cross-tenant access (incl. default) |
| `azure_ad_admin_consent_request_policy` | Admin consent request workflow config |
| `azure_ad_policy_posture` | Aggregate: fetches key policies and flags risky settings |

## Posture Findings (what `posture` flags)

| Finding | Source | Why it matters |
|---------|--------|----------------|
| Security defaults disabled | `identitySecurityDefaultsEnforcementPolicy.isEnabled == false` | Baseline MFA may not be enforced (acceptable only if Conditional Access covers it) |
| Users can register apps | `authorizationPolicy.defaultUserRolePermissions.allowedToCreateApps == true` | Enables rogue app registrations |
| Broad user consent | `authorizationPolicy.permissionGrantPoliciesAssigned` permits user consent | Enables illicit-consent-grant phishing |
| Broad guest access | `authorizationPolicy.guestUserRoleId` set to a permissive role | Guests can enumerate the directory |

## Caveats

- `authorizationPolicy` returns a single object at `/policies/authorizationPolicy` in v1.0.
- `permissionGrantPolicies` is a collection (`value[]`); the others are single objects.
- Cross-tenant access exposes basic properties under app-only with `Policy.Read.All`; some sensitive
  identity-synchronization sub-properties are role-gated for delegated callers but readable here.
