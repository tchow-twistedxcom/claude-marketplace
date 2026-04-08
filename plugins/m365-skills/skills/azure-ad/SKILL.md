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
  - Incident triage, full compromise triage, orchestrated security investigation
  - Email forensics, sent mail analysis, phishing investigation, SaveToSentItems
  - Inbox rules, forwarding rules, attacker-created rules, auto-forward detection
  - Unified Audit Log, UAL, Office 365 Management Activity API
  - Defender hunting, KQL, Advanced Hunting, EmailEvents, threat hunting
  - OAuth persistence, OAuth app grants, app consent, token persistence
  - Conditional Access policy management, CA policy, named locations, trusted IPs
  - SharePoint forensics, OneDrive exfiltration, Teams forensics
  - MFA changes, auth method registration, privilege escalation, role changes
---

# Azure AD / Entra ID Skill

Comprehensive Azure AD operations using Microsoft Graph API.

## Capabilities

> **Note: User lifecycle operations (create/update/delete), licensing, and device management are
> CLI-only via `azure_ad_api.py` — no MCP tools exist for these operations.** MCP tools cover
> read-only directory/security queries plus session revocation, compromised-user marking, inbox
> rule deletion, risky-user dismissal, and Conditional Access policy operations (all with
> `confirm` guards).

### Users Domain (MCP: read-only; write ops: CLI-only)
- **List/Search**: Query all users with OData filters (MCP)
- **Get Details**: Retrieve specific user by ID or UPN (MCP)
- **Create/Update/Delete**: Full user lifecycle management — **CLI-only (`azure_ad_api.py`)**
- **Relationships**: Manager, direct reports, group memberships (MCP)
- **Devices**: Owned and registered devices (MCP)
- **Licensing**: Assign and revoke licenses — **CLI-only (`azure_ad_api.py`)**

### Groups Domain (MCP: read-only)
- **List/Search**: Query all groups with filters (MCP)
- **Get Details**: Retrieve specific group information (MCP)
- **Create/Update/Delete**: Full group lifecycle — **CLI-only (`azure_ad_api.py`)**
- **Members**: List group members (MCP); add/remove members — **CLI-only**
- **Owners**: List group owners (MCP)
- **Nesting**: Get parent group memberships (MCP)

### Devices Domain (MCP: read-only)
- **List/Search**: Query all registered devices (MCP)
- **Get Details**: Device properties and status (MCP)
- **Update/Delete**: Device management — **CLI-only (`azure_ad_api.py`)**
- **Owners/Users**: Registered owners and users (MCP)
- **Memberships**: Device group memberships (MCP)

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

### MCP Extension Tools (Agent-Native)

These tools are exposed by the `azure-ad` MCP server and are available to agents when the server
is running. They require the MCP server to be configured — either via `plugins/m365-skills/.mcp.json`
(auto-registered by the plugin system) or by manually installing `extensions/azure-ad.dxt`.

#### Incident Response

- **`azure_ad_delete_inbox_rule`** — Delete a specific malicious inbox rule from a user's mailbox.
  Use rule IDs returned by `azure_ad_ual_inbox_rules` or `azure_ad_incident_triage`. Requires
  `confirm=True` to execute; returns preview when `confirm=False`.

- **`azure_ad_dismiss_risky_users`** — Dismiss the Identity Protection risk state for one or more
  users after full remediation (password reset + sessions revoked + MFA re-enrolled). Calls
  `POST /identityProtection/riskyUsers/dismiss`. Requires `confirm=True` to execute; returns
  preview when `confirm=False`.

- **`azure_ad_incident_triage`** — Orchestrates a complete compromise triage in one call: sign-in
  analysis, inbox rule inspection, sent mail forensics (via Defender EmailEvents), auth method
  review, UAL forensics, mailbox forwarding check, and OAuth grant review. Returns a structured
  report per user with a HIGH/MEDIUM/CLEAN risk summary. Top-level output fields include:
  `account`, `riskSummary`, `suspiciousSignIns`, `maliciousRules`, `suspiciousSentMail`,
  `authMethods`, `ualFindings`, `forwardingAddress`, `oauthGrants`, `sentMailSource`,
  `cloudAppFindings`. Start here for any account compromise investigation.

#### Email Forensics

- **`azure_ad_sent_emails`** — List emails sent from a user's mailbox in a time window; identifies
  phishing/spam sent via stolen tokens. Use `include_body=True` to see message content.
- **`azure_ad_search_mail`** — Search a mailbox folder by subject keyword or sender address using
  OData `$filter`; supports `from:address` prefix syntax.
- **`azure_ad_get_email`** — Get full detail of a specific email message (complete body, all
  headers, attachments flag) by message ID from `azure_ad_sent_emails` results.

#### Unified Audit Log (UAL) Forensics

These tools query the Office 365 Management Activity API and require the `ActivityFeed.Read`
permission (Office 365 Management APIs scope) with admin consent.

- **`azure_ad_ual_inbox_rules`** — Query UAL for inbox rule creation and modification events;
  returns forensic attribution (creator IP, timestamp, user agent, rule parameters) to prove
  attacker-created rules.
- **`azure_ad_ual_mailbox_access`** — Query UAL for mailbox access events (MailItemsAccessed,
  MessageBind, FolderBind, SendAs) to identify if an attacker read mailbox contents after token
  theft.
- **`azure_ad_ual_search`** — Search the UAL for any Exchange or Azure AD operations; supports
  arbitrary operation filter and content type (`Audit.Exchange`, `Audit.AzureActiveDirectory`,
  `Audit.General`).
- **`azure_ad_ual_sharepoint`** — Query UAL for SharePoint, OneDrive, and Teams forensics;
  detects post-compromise data exfiltration via file downloads, anonymous link creation, external
  sharing, and Teams session activity.

#### Defender / Advanced Hunting (KQL)

These tools require `ThreatHunting.Read.All` permission with admin consent and Microsoft 365
Defender Plan 1/2 (included in M365 E3/E5/Business Premium).

- **`azure_ad_advanced_hunt`** — Run an arbitrary KQL query against Microsoft 365 Defender
  Advanced Hunting; covers EmailEvents, EmailAttachmentInfo, EmailUrlInfo, IdentityLogonEvents,
  DeviceLogonEvents, CloudAppEvents. The ONLY way to see emails sent with
  `SaveToSentItems=false`. Requires `confirm=True` to execute — defaults to dry-run for safety.
- **`azure_ad_email_events`** — Query the Defender `EmailEvents` table for complete email
  forensics; captures all sends including `SaveToSentItems=false` (invisible to Graph Mail API,
  UAL, and Mimecast). Returns message-level summary grouped by NetworkMessageId.
- **`azure_ad_email_attachments`** — Query the Defender `EmailAttachmentInfo` table; returns
  file names, types, SHA256 hashes, malware family tags, and NetworkMessageId for correlation.
  Captures attachments from `SaveToSentItems=false` emails.

#### Post-Compromise Persistence Detection

- **`azure_ad_user_oauth_grants`** — List OAuth delegated permission grants for a user; detects
  attacker persistence via malicious app consent (OAuth grants survive password resets and session
  revocations).
- **`azure_ad_mailbox_settings`** — Get mailbox-level settings including SMTP forwarding address
  and auto-reply config; detects forwarding exfiltration that survives inbox rule deletion.
- **`azure_ad_mfa_changes`** — Query audit logs for MFA and authentication method changes;
  detects unauthorized MFA registrations (attacker adds their own authenticator or phone number).
- **`azure_ad_role_changes`** — Query audit logs for directory role assignment changes; detects
  privilege escalation (attacker adding themselves to Global Admin or other privileged roles).

#### Conditional Access Policy Management

- **`azure_ad_list_ca_policies`** — List all Conditional Access policies with state, conditions
  summary (users, locations, grant controls).
- **`azure_ad_create_ca_policy`** — Create a Conditional Access policy (block or require MFA from
  non-trusted locations); takes user list, excluded Named Location IDs, and action.
- **`azure_ad_update_ca_policy`** — Enable, disable, or rename an existing CA policy by ID.
- **`azure_ad_delete_ca_policy`** — Permanently delete a CA policy; requires `confirm=True` for
  safety.
- **`azure_ad_create_named_location`** — Create an IP-based Named Location (trusted CIDR ranges)
  for use as a CA policy exclusion (e.g., block-except-corporate-IP pattern).

### Basic Operations MCP Tools

These tools are available but not individually documented above. Use them for general directory queries and investigation:

| Tool | Purpose |
|------|---------|
| `azure_ad_list_users` | List all users in the tenant |
| `azure_ad_get_user` | Get a single user by ID or UPN |
| `azure_ad_search_users` | Search users by name, UPN, or email |
| `azure_ad_user_member_of` | List groups a user is a member of |
| `azure_ad_user_manager` | Get a user's manager |
| `azure_ad_user_direct_reports` | Get a user's direct reports |
| `azure_ad_user_devices` | Get devices registered to a user |
| `azure_ad_list_groups` | List all groups |
| `azure_ad_get_group` | Get a group by ID or name |
| `azure_ad_group_members` | List members of a group |
| `azure_ad_group_owners` | List owners of a group |
| `azure_ad_list_devices` | List all registered devices |
| `azure_ad_get_device` | Get a device by ID |
| `azure_ad_organization` | Get tenant/organization info |
| `azure_ad_domains` | List verified domains |
| `azure_ad_licenses` | List assigned license plans |
| `azure_ad_directory_roles` | List directory roles and members |
| `azure_ad_sign_ins` | Query sign-in logs |
| `azure_ad_sign_in_get` | Get a specific sign-in by ID |
| `azure_ad_risk_detections` | Query risk detection events |
| `azure_ad_risky_users` | List risky users |
| `azure_ad_risky_user_history` | Get risk history for a user |
| `azure_ad_audit_logs` | Query Azure AD audit logs |
| `azure_ad_auth_methods` | List a user's authentication methods |
| `azure_ad_named_locations` | List Conditional Access named locations |
| `azure_ad_revoke_sessions` | **Revoke all sessions for a user (dry_run=True default)** |
| `azure_ad_confirm_compromised` | **Mark users as confirmed compromised (confirm=False default)** |

## MCP Server (49 Agent-Native Tools)

The `azure-ad` MCP server exposes 49 tools including `azure_ad_incident_triage`, email forensics
(`azure_ad_sent_emails`, `azure_ad_email_events`), Defender Advanced Hunting (`azure_ad_advanced_hunt`),
CA policy management, OAuth grant detection, inbox rule deletion, and risky user dismissal. These
tools are registered automatically when `m365-skills` is installed via the plugin system.

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

## MCP Tools vs CLI Scripts

If the `azure-ad` MCP server is connected (test by calling `azure_ad_list_users` — if it responds, the server is up), **prefer MCP tools**:
- No `cwd` setup required
- Return structured JSON directly
- Cover all 47 operations
- Support concurrent tool calls

Use `scripts/azure_ad_api.py` CLI only when:
- The MCP server is not available
- You need CSV/table output for human-readable reports
- You're running from a script that can't use MCP

**Quick test**: Call `azure_ad_list_users` with no arguments. If it works, use MCP.

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
