# Applications API Reference

App registrations, service principals (enterprise apps), and OAuth consent grants via Microsoft
Graph API. This surface is the primary tool for detecting illicit-consent-grant attacks, malicious
app registrations, and attacker-added application credentials (backdoor persistence that survives
password resets and session revocation).

## Endpoints

| Operation | Method | Endpoint | Permission |
|-----------|--------|----------|------------|
| List app registrations | GET | `/applications` | `Application.Read.All` or `Directory.Read.All` |
| Get application | GET | `/applications/{id}` | `Application.Read.All` |
| App credentials | GET | `/applications/{id}?$select=keyCredentials,passwordCredentials` | `Application.Read.All` |
| List service principals | GET | `/servicePrincipals` | `Application.Read.All` |
| Get service principal | GET | `/servicePrincipals/{id}` | `Application.Read.All` |
| App roles assigned to an SP | GET | `/servicePrincipals/{id}/appRoleAssignedTo` | `Application.Read.All` |
| Tenant OAuth2 grants | GET | `/oauth2PermissionGrants` | `Directory.Read.All` |
| Disable service principal | PATCH | `/servicePrincipals/{id}` `{accountEnabled:false}` | `Application.ReadWrite.All` |
| Remove app password | POST | `/applications/{id}/removePassword` `{keyId}` | `Application.ReadWrite.All` |
| Remove app key | PATCH | `/applications/{id}` `{keyCredentials:[...]}` | `Application.ReadWrite.All` |

All endpoints are Graph v1.0 and support app-only (client-credentials) auth.

## CLI Commands

### Reads

```bash
# List app registrations
python3 azure_ad_api.py applications apps-list --top 50
python3 azure_ad_api.py applications apps-list --all

# Include credentials in the listing (detect backdoor secrets/certs)
python3 azure_ad_api.py applications apps-list --include-credentials

# Get one application
python3 azure_ad_api.py applications apps-get APP_OBJECT_ID

# Inspect credentials with an "added N days ago" flag for each
python3 azure_ad_api.py applications apps-credentials APP_OBJECT_ID

# List service principals (enterprise apps)
python3 azure_ad_api.py applications sp-list --top 50
python3 azure_ad_api.py applications sp-get SP_OBJECT_ID

# App-role assignments granted TO a service principal
python3 azure_ad_api.py applications sp-app-roles SP_OBJECT_ID

# Tenant-wide OAuth2 permission grants (illicit consent detection)
python3 azure_ad_api.py applications oauth-grants --all
```

### Guarded writes (incident response)

```bash
# Neutralize a malicious enterprise app by disabling its service principal
python3 azure_ad_api.py applications sp-disable SP_OBJECT_ID --confirm

# Re-enable (undo)
python3 azure_ad_api.py applications sp-enable SP_OBJECT_ID --confirm

# Remove an attacker-added client secret (by keyId from apps-credentials)
python3 azure_ad_api.py applications apps-remove-password APP_OBJECT_ID --key-id KEY_ID --confirm

# Remove an attacker-added certificate (key credential)
python3 azure_ad_api.py applications apps-remove-key APP_OBJECT_ID --key-id KEY_ID --confirm
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `azure_ad_list_applications` | List app registrations (`include_credentials=True` to surface keys/secrets) |
| `azure_ad_get_application` | Get a single application |
| `azure_ad_app_credentials` | Credentials with `addedDaysAgo` for backdoor detection |
| `azure_ad_list_service_principals` | List service principals (enterprise apps) |
| `azure_ad_get_service_principal` | Get a single service principal |
| `azure_ad_sp_app_role_assignments` | App roles granted to a service principal |
| `azure_ad_oauth_grants_tenant` | Tenant-wide OAuth2 grants, enriched with app names |
| `azure_ad_disable_service_principal` | Disable a malicious SP (`confirm=True`) |
| `azure_ad_enable_service_principal` | Re-enable an SP (`confirm=True`) |
| `azure_ad_remove_app_password` | Remove a client secret by keyId (`confirm=True`) |
| `azure_ad_remove_app_key` | Remove a certificate by keyId (`confirm=True`) |

## Caveats

- The public key blob on `keyCredentials` is **omitted by default** on `GET /applications`. The CLI
  `apps-list --include-credentials` and `apps-credentials` add an explicit `$select` to retrieve it.
  There is a throttling limit of about **150 requests/min/tenant** when selecting `keyCredentials`.
- `passwordCredentials` never returns the secret value itself, only metadata (hint, keyId, start
  and end dates). That metadata is sufficient to detect recently-added secrets.
- `oauth2PermissionGrants` and `appRoleAssignedTo` are subject to **replication delay**; filter by
  `clientId` to reduce it.
- A single-page `oauth-grants` call can return an **empty first page with a `nextLink`** (a Graph
  pagination quirk for this collection). Use `--all` (CLI) or `all_pages=True` (MCP) to get the real
  data; tenants commonly have hundreds of grants.
- Disabling a service principal (`accountEnabled=false`) immediately blocks the enterprise app from
  authenticating. It is reversible with `sp-enable`. Removing app credentials is **not** reversible.

## Incident Response Notes

OAuth grants and added app credentials are the two most common attacker-persistence mechanisms that
survive password resets and session revocation. A typical post-compromise check:

1. `oauth-grants` (tenant) and `azure_ad_user_oauth_grants` (per victim) to find consented apps.
2. `apps-credentials` / `apps-list --include-credentials` to find secrets or certs added near the
   compromise window (`addedDaysAgo`).
3. If malicious: `sp-disable` the enterprise app, then `apps-remove-password` / `apps-remove-key`
   to strip the attacker credential.
