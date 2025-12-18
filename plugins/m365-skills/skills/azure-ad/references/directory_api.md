# Directory API Reference

Azure AD Directory operations via Microsoft Graph API.

## Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get organization | GET | `/organization` |
| List domains | GET | `/domains` |
| List licenses | GET | `/subscribedSkus` |
| Get license details | GET | `/subscribedSkus/{id}` |
| List directory roles | GET | `/directoryRoles` |
| List role members | GET | `/directoryRoles/{id}/members` |
| List deleted users | GET | `/directory/deletedItems/microsoft.graph.user` |
| Restore deleted user | POST | `/directory/deletedItems/{id}/restore` |

## CLI Commands

### Organization

```bash
# Get organization info
python3 azure_ad_api.py directory organization

# Output as JSON
python3 azure_ad_api.py --format json directory organization
```

### Domains

```bash
# List all verified domains
python3 azure_ad_api.py directory domains

# Output as JSON
python3 azure_ad_api.py --format json directory domains
```

### Licenses

```bash
# List all available licenses (subscribed SKUs)
python3 azure_ad_api.py directory licenses

# Get details for specific license
python3 azure_ad_api.py directory license-details SKU_ID

# Output as JSON for scripting
python3 azure_ad_api.py --format json directory licenses
```

### Directory Roles

```bash
# List all activated directory roles
python3 azure_ad_api.py directory roles

# List members of a specific role
python3 azure_ad_api.py directory role-members ROLE_ID
```

### Deleted Users

```bash
# List recently deleted users
python3 azure_ad_api.py directory deleted-users

# List with custom page size
python3 azure_ad_api.py directory deleted-users --top 50

# Restore a deleted user (requires confirmation)
python3 azure_ad_api.py directory restore-user USER_ID --confirm
```

## Organization Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Tenant ID |
| `displayName` | String | Organization name |
| `verifiedDomains` | Array | Verified domains |
| `city` | String | City |
| `state` | String | State/Province |
| `country` | String | Country |
| `countryLetterCode` | String | Country code |
| `postalCode` | String | Postal code |
| `street` | String | Street address |
| `technicalNotificationMails` | Array | Technical contact emails |
| `securityComplianceNotificationMails` | Array | Security contact emails |
| `tenantType` | String | Tenant type |
| `createdDateTime` | DateTime | Tenant creation date |

## Domain Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Domain name |
| `authenticationType` | String | Managed or Federated |
| `isDefault` | Boolean | Default domain |
| `isInitial` | Boolean | Initial .onmicrosoft.com domain |
| `isRoot` | Boolean | Root domain |
| `isVerified` | Boolean | Verification status |
| `supportedServices` | Array | Services using domain |

## License (SubscribedSku) Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | SKU ID (GUID) |
| `skuId` | String | SKU identifier |
| `skuPartNumber` | String | SKU name (e.g., ENTERPRISEPACK) |
| `capabilityStatus` | String | Status (Enabled, Warning, Suspended) |
| `consumedUnits` | Integer | Licenses in use |
| `prepaidUnits` | Object | Available license units |
| `prepaidUnits.enabled` | Integer | Enabled licenses |
| `prepaidUnits.suspended` | Integer | Suspended licenses |
| `prepaidUnits.warning` | Integer | Warning state licenses |
| `servicePlans` | Array | Included service plans |

## Common License SKU Part Numbers

| SKU Part Number | Product Name |
|-----------------|--------------|
| `ENTERPRISEPACK` | Office 365 E3 |
| `ENTERPRISEPREMIUM` | Office 365 E5 |
| `SPE_E3` | Microsoft 365 E3 |
| `SPE_E5` | Microsoft 365 E5 |
| `EXCHANGESTANDARD` | Exchange Online (Plan 1) |
| `EXCHANGEENTERPRISE` | Exchange Online (Plan 2) |
| `POWER_BI_STANDARD` | Power BI (free) |
| `POWER_BI_PRO` | Power BI Pro |
| `PROJECTPREMIUM` | Project Plan 5 |
| `VISIOCLIENT` | Visio Plan 2 |
| `TEAMS_EXPLORATORY` | Teams Exploratory |
| `AAD_PREMIUM` | Azure AD Premium P1 |
| `AAD_PREMIUM_P2` | Azure AD Premium P2 |
| `EMS` | Enterprise Mobility + Security E3 |
| `EMSPREMIUM` | Enterprise Mobility + Security E5 |

## Directory Roles

| Role | Description |
|------|-------------|
| Global Administrator | Full access to all features |
| User Administrator | Manage users and groups |
| Helpdesk Administrator | Reset passwords, manage service requests |
| Exchange Administrator | Manage Exchange Online |
| SharePoint Administrator | Manage SharePoint Online |
| Teams Administrator | Manage Microsoft Teams |
| Security Administrator | Manage security features |
| Compliance Administrator | Manage compliance features |
| Intune Administrator | Manage Intune devices |
| Billing Administrator | Manage billing and subscriptions |
| License Administrator | Manage license assignments |

## Use Cases

### License Usage Report

```bash
# Get all licenses with usage
python3 azure_ad_api.py --format json directory licenses | \
  jq '.value[] | {sku: .skuPartNumber, used: .consumedUnits, total: .prepaidUnits.enabled}'
```

### Find Global Admins

```bash
# First, list roles to find Global Administrator role ID
python3 azure_ad_api.py directory roles

# Then list members of that role
python3 azure_ad_api.py directory role-members GLOBAL_ADMIN_ROLE_ID
```

### Domain Verification Status

```bash
# Check all domains and their verification status
python3 azure_ad_api.py --format json directory domains | \
  jq '.value[] | {domain: .id, verified: .isVerified, default: .isDefault}'
```

### Audit Deleted Users

```bash
# List all deleted users (recoverable within 30 days)
python3 azure_ad_api.py directory deleted-users --top 100

# Restore a specific user
python3 azure_ad_api.py directory restore-user USER_ID --confirm
```

### Tenant Information

```bash
# Get comprehensive tenant info
python3 azure_ad_api.py --format json directory organization
```

## Required Permissions

| Operation | Permission |
|-----------|------------|
| Organization info | `Organization.Read.All` |
| List domains | `Domain.Read.All` or `Directory.Read.All` |
| List licenses | `Organization.Read.All` or `Directory.Read.All` |
| List roles | `RoleManagement.Read.Directory` or `Directory.Read.All` |
| Role members | `RoleManagement.Read.Directory` or `Directory.Read.All` |
| Deleted users | `User.Read.All` or `Directory.Read.All` |
| Restore user | `User.ReadWrite.All` |
