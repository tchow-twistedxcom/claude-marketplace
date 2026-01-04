# Mimecast Skills Plugin

Mimecast email security integration via Python CLI with 28 operations for TTP protection, user management, policy management, and security reporting.

## Features

- **Email Security**: Message tracking, held message management, TTP URL/attachment/impersonation logs
- **User Management**: CRUD operations for internal users and groups
- **Policy Management**: Block/permit sender policies, anti-spoofing
- **Reporting**: Audit events, SIEM integration, threat intelligence

## Quick Start

### 1. Configure Credentials

```bash
cd plugins/mimecast-skills/config
cp mimecast_config.template.json mimecast_config.json
# Edit mimecast_config.json with your credentials
```

### 2. Get Mimecast API Credentials

1. Log in to Mimecast Admin Console
2. Navigate to **Administration → Services → API and Platform Integrations**
3. Create or select an application
4. Generate: App ID, App Key, Access Key, Secret Key

### 3. Test Authentication

```bash
python3 scripts/mimecast_auth.py --test
```

### 4. Run CLI Commands

```bash
# Account info
python3 scripts/mimecast_api.py account info

# List users
python3 scripts/mimecast_api.py users list

# Search messages
python3 scripts/mimecast_api.py messages search --from sender@example.com

# Get TTP URL logs
python3 scripts/mimecast_api.py ttp urls --start 2024-01-01

# Block a sender
python3 scripts/mimecast_api.py policies block-sender --email spam@malicious.com
```

## CLI Operations (28 Total)

| Resource | Operations |
|----------|------------|
| `account` | info |
| `messages` | search, held, release, info |
| `ttp` | urls, attachments, impersonation |
| `archive` | search |
| `users` | list, create, update, delete |
| `groups` | list, create, add-member, remove-member |
| `policies` | list, block-sender, permit-sender, definitions |
| `reports` | audit, siem, stats, threat-intel |

## Output Formats

```bash
# Table format (default)
python3 scripts/mimecast_api.py users list

# JSON format
python3 scripts/mimecast_api.py users list --output json
```

## Regional Endpoints

| Region | Base URL |
|--------|----------|
| US | `https://us-api.mimecast.com` |
| EU | `https://eu-api.mimecast.com` |
| UK | `https://uk-api.mimecast.com` |
| DE | `https://de-api.mimecast.com` |
| AU | `https://au-api.mimecast.com` |

## Commands

- `/mimecast-setup` - Initial configuration wizard
- `/mimecast-manage` - CLI operations reference

## Skill

- `mimecast-api` - Execute Mimecast operations via Python CLI

## Reference Documentation

- [Authentication](skills/mimecast-api/references/mimecast-authentication.md)
- [Email Security](skills/mimecast-api/references/mimecast-email-security.md)
- [User Management](skills/mimecast-api/references/mimecast-user-management.md)
- [Policy Management](skills/mimecast-api/references/mimecast-policy-management.md)
- [Reporting](skills/mimecast-api/references/mimecast-reporting.md)
