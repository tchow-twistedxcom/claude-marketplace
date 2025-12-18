---
name: azure-ad
description: |
  Azure AD / Entra ID operations via Microsoft Graph API. Use when user mentions:
  - Azure AD, Entra ID, AAD, Azure Active Directory
  - Microsoft 365 users, groups, devices
  - Graph API user/group/device operations
  - Tenant users, directory operations
  - License management, role assignments
  - User provisioning, group memberships
---

# Azure AD / Entra ID Skill

Comprehensive Azure AD operations using Microsoft Graph API.

## Capabilities

### Users Domain
- **List/Search**: Query all users with OData filters
- **Get Details**: Retrieve specific user by ID or UPN
- **Create/Update/Delete**: Full user lifecycle management
- **Relationships**: Manager, direct reports, group memberships
- **Devices**: Owned and registered devices
- **Licensing**: Assign and revoke licenses

### Groups Domain
- **List/Search**: Query all groups with filters
- **Get Details**: Retrieve specific group information
- **Create/Update/Delete**: Full group lifecycle
- **Members**: List, add, remove group members
- **Owners**: Manage group owners
- **Nesting**: Get parent group memberships

### Devices Domain
- **List/Search**: Query all registered devices
- **Get Details**: Device properties and status
- **Update/Delete**: Device management
- **Owners/Users**: Registered owners and users
- **Memberships**: Device group memberships

### Directory Domain
- **Organization**: Tenant information
- **Domains**: Verified domain list
- **Licenses**: Available SKUs and assignments
- **Roles**: Directory roles and members
- **Deleted Items**: Restore deleted users

## Quick Start

```bash
# Setup
cd skills/azure-ad/config
cp azure_config.template.json azure_config.json
# Edit with your Azure credentials

# Test connection
python3 scripts/auth.py --test

# Basic operations
python3 scripts/azure_ad_api.py users list
python3 scripts/azure_ad_api.py users get "user@domain.com"
python3 scripts/azure_ad_api.py groups list
python3 scripts/azure_ad_api.py devices list
python3 scripts/azure_ad_api.py directory organization
```

## Authentication

Uses OAuth 2.0 Client Credentials flow via MSAL:
- App-only authentication (no user context)
- Automatic token caching and refresh
- Multi-tenant support with aliases

## Required Permissions

Minimum read-only permissions:
- `User.Read.All`
- `Group.Read.All`
- `Device.Read.All`
- `Directory.Read.All`

For write operations add:
- `User.ReadWrite.All`
- `Group.ReadWrite.All`

## Files

```
azure-ad/
├── SKILL.md                    # This file
├── README.md                   # Setup guide
├── config/
│   ├── azure_config.template.json  # Config template
│   ├── azure_config.json           # Your config (gitignored)
│   └── .azure_tokens.json          # Token cache (gitignored)
├── scripts/
│   ├── auth.py                     # MSAL authentication
│   ├── azure_ad_api.py             # Main CLI (45+ operations)
│   └── formatters.py               # Output formatting
└── references/
    ├── users_api.md
    ├── groups_api.md
    ├── devices_api.md
    └── directory_api.md
```

## Output Formats

- **table**: Human-readable formatted tables (default)
- **json**: Raw JSON for scripting
- **csv**: CSV export for spreadsheets

## Examples

```bash
# Multi-tenant support
python3 azure_ad_api.py -t prod users list
python3 azure_ad_api.py --tenant staging groups list

# Output formats
python3 azure_ad_api.py --format json users list > users.json
python3 azure_ad_api.py --format csv users list > users.csv

# Filtering
python3 azure_ad_api.py users list --filter "department eq 'Engineering'"
python3 azure_ad_api.py devices list --filter "operatingSystem eq 'Windows'"

# Pagination
python3 azure_ad_api.py users list --all  # Get all pages
python3 azure_ad_api.py groups list --top 500
```
