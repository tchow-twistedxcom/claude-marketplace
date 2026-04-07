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
  - Compromise sweep, account compromise, MFA fatigue, suspicious sign-ins
  - Risk detections, Identity Protection, risky users
  - Security audit logs, sign-in logs, authentication methods
  - Incident response, breach investigation, attacker IP sweep
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

### Security Domain (Compromise Sweep)
- **Sign-in logs**: Query Azure AD sign-in audit logs with time/user/IP filters
- **Risk detections**: Identity Protection risk events
- **Risky users**: Accounts flagged by Identity Protection
- **Directory audit logs**: All admin/user changes
- **Auth methods**: MFA enrollment per user
- **Compromise sweep**: 6-vector detection (IP sweep, MFA fatigue, risk events, audit anomalies, auth methods)

## MCP Server (48 Agent-Native Tools)

The `azure-ad` MCP server exposes 48 tools including `azure_ad_incident_triage`, email forensics
(`azure_ad_sent_emails`, `azure_ad_email_events`), Defender Advanced Hunting (`azure_ad_advanced_hunt`),
CA policy management, and OAuth grant detection. These tools are registered automatically when
`m365-skills` is installed via the plugin system.

### Method 1: Environment Variables (Plugin Auto-Registration)

Set credentials as environment variables before starting Claude Code:

```bash
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
```

The MCP server is defined in `plugins/m365-skills/.mcp.json` and registered via `plugin.json`
`mcpServers`. Once env vars are set, the `azure-ad` MCP server starts automatically.

### Method 2: DXT Extension (Interactive Credential Setup)

The `extensions/azure-ad.dxt` bundle can be installed directly via Claude Code's extension
installer, which prompts for credentials and stores them securely:

```bash
# In Claude Code, install the extension from the local bundle:
/extension install extensions/azure-ad.dxt
```

The DXT installer handles `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, and `AZURE_CLIENT_SECRET`
interactively. Use this method if you prefer not to set environment variables manually.

The DXT manifest is at `extensions/azure-ad/manifest.json`. The server entry point is
`extensions/azure-ad/src/server.py`.

## Quick Start (CLI Interface)

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
    ├── directory_api.md
    └── security_api.md     # Security operations, incident response playbook
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
