# Azure AD / Entra ID Skill

Azure Active Directory (now Microsoft Entra ID) operations via Microsoft Graph API.

## Features

- **45+ API Operations** across Users, Groups, Devices, and Directory domains
- **OAuth 2.0 Authentication** using MSAL with automatic token refresh
- **Multi-tenant Support** with aliases for easy switching
- **Multiple Output Formats**: table, JSON, CSV
- **OData Filtering** for powerful queries
- **Pagination Support** for large result sets

## Prerequisites

- Python 3.8+
- Azure AD tenant with admin access
- App registration with appropriate permissions

## Setup Guide

### Step 1: Create Azure App Registration

1. Log in to [Azure Portal](https://portal.azure.com)
2. Navigate to **Microsoft Entra ID** → **App registrations**
3. Click **New registration**
4. Configure:
   - **Name**: `Claude Code M365 Integration`
   - **Supported account types**: Accounts in this organizational directory only (Single tenant)
   - **Redirect URI**: Leave blank
5. Click **Register**
6. Note the **Application (client) ID** and **Directory (tenant) ID**

### Step 2: Configure API Permissions

1. In your app registration, go to **API permissions**
2. Click **Add a permission** → **Microsoft Graph** → **Application permissions**
3. Add these permissions:

   | Permission | Description |
   |------------|-------------|
   | `User.Read.All` | Read all users |
   | `Group.Read.All` | Read all groups |
   | `Device.Read.All` | Read all devices |
   | `Directory.Read.All` | Read directory data |

4. Click **Grant admin consent for [Your Tenant]**
5. Verify all permissions show green checkmarks

### Step 3: Create Client Secret

1. Go to **Certificates & secrets** → **Client secrets**
2. Click **New client secret**
3. Configure:
   - **Description**: `Claude Code`
   - **Expires**: 24 months (recommended)
4. Click **Add**
5. **IMMEDIATELY COPY THE SECRET VALUE** (it won't be shown again)

### Step 4: Configure Credentials

```bash
cd skills/azure-ad/config
cp azure_config.template.json azure_config.json
```

Edit `azure_config.json` with your credentials:

```json
{
  "tenants": {
    "default": {
      "name": "Your Organization",
      "tenant_id": "YOUR_DIRECTORY_TENANT_ID",
      "client_id": "YOUR_APPLICATION_CLIENT_ID",
      "client_secret": "YOUR_CLIENT_SECRET_VALUE"
    }
  },
  "defaults": {
    "tenant": "default",
    "timeout": 30,
    "max_retries": 3,
    "page_size": 100
  },
  "aliases": {
    "prod": "default"
  }
}
```

### Step 5: Install Dependencies

```bash
pip install msal requests
```

### Step 6: Test Connection

```bash
cd scripts
python3 auth.py --test
```

Expected output:
```
Testing connection to tenant: default
  Organization: Your Organization Name
  Tenant ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  Primary Domain: yourdomain.com
Connection successful!
```

## Usage

### Basic Commands

```bash
# List users
python3 azure_ad_api.py users list

# Get specific user
python3 azure_ad_api.py users get "user@domain.com"

# Search users
python3 azure_ad_api.py users search "John"

# List groups
python3 azure_ad_api.py groups list

# Get group members
python3 azure_ad_api.py groups members GROUP_ID

# List devices
python3 azure_ad_api.py devices list

# Get organization info
python3 azure_ad_api.py directory organization

# List available licenses
python3 azure_ad_api.py directory licenses
```

### Output Formats

```bash
# Table (default)
python3 azure_ad_api.py users list

# JSON
python3 azure_ad_api.py --format json users list > users.json

# CSV
python3 azure_ad_api.py --format csv users list > users.csv
```

### Filtering with OData

```bash
# Filter by department
python3 azure_ad_api.py users list --filter "department eq 'Engineering'"

# Filter enabled accounts
python3 azure_ad_api.py users list --filter "accountEnabled eq true"

# Filter Windows devices
python3 azure_ad_api.py devices list --filter "operatingSystem eq 'Windows'"

# Filter security groups
python3 azure_ad_api.py groups list --filter "securityEnabled eq true"
```

### Pagination

```bash
# Get specific number of results
python3 azure_ad_api.py users list --top 50

# Get all results (auto-pagination)
python3 azure_ad_api.py users list --all

# Select specific fields
python3 azure_ad_api.py users list --select "id,displayName,mail"
```

### Multi-tenant Support

```bash
# Use specific tenant
python3 azure_ad_api.py -t prod users list

# Use alias
python3 azure_ad_api.py --tenant staging groups list
```

## Command Reference

### Users Domain

| Command | Description |
|---------|-------------|
| `users list` | List all users |
| `users get USER_ID` | Get specific user |
| `users search QUERY` | Search users |
| `users create` | Create new user |
| `users update USER_ID` | Update user |
| `users delete USER_ID` | Delete user |
| `users manager USER_ID` | Get user's manager |
| `users direct-reports USER_ID` | Get direct reports |
| `users member-of USER_ID` | Get group memberships |
| `users owned-devices USER_ID` | Get owned devices |
| `users registered-devices USER_ID` | Get registered devices |
| `users assign-license USER_ID` | Assign licenses |
| `users revoke-license USER_ID` | Remove licenses |

### Groups Domain

| Command | Description |
|---------|-------------|
| `groups list` | List all groups |
| `groups get GROUP_ID` | Get specific group |
| `groups search QUERY` | Search groups |
| `groups create` | Create new group |
| `groups update GROUP_ID` | Update group |
| `groups delete GROUP_ID` | Delete group |
| `groups members GROUP_ID` | List members |
| `groups add-member GROUP_ID MEMBER_ID` | Add member |
| `groups remove-member GROUP_ID MEMBER_ID` | Remove member |
| `groups owners GROUP_ID` | List owners |
| `groups add-owner GROUP_ID OWNER_ID` | Add owner |
| `groups member-of GROUP_ID` | Get parent groups |

### Devices Domain

| Command | Description |
|---------|-------------|
| `devices list` | List all devices |
| `devices get DEVICE_ID` | Get specific device |
| `devices search QUERY` | Search devices |
| `devices update DEVICE_ID` | Update device |
| `devices delete DEVICE_ID` | Delete device |
| `devices registered-owners DEVICE_ID` | Get owners |
| `devices registered-users DEVICE_ID` | Get registered users |
| `devices member-of DEVICE_ID` | Get group memberships |

### Directory Domain

| Command | Description |
|---------|-------------|
| `directory organization` | Get org info |
| `directory domains` | List domains |
| `directory licenses` | List licenses |
| `directory license-details SKU_ID` | Get license details |
| `directory roles` | List directory roles |
| `directory role-members ROLE_ID` | List role members |
| `directory deleted-users` | List deleted users |
| `directory restore-user USER_ID` | Restore user |

## Security Notes

- **Never commit** `azure_config.json` (contains client secret)
- **Never commit** `.azure_tokens.json` (contains access tokens)
- Use **least-privilege permissions** (read-only if possible)
- **Rotate client secrets** before expiration (set calendar reminder)
- Consider using **certificates** instead of secrets for production

## Troubleshooting

### "Insufficient privileges"

- Verify API permissions are granted
- Ensure admin consent was provided
- Check if using Application (not Delegated) permissions

### "Invalid client secret"

- Client secret may have expired
- Secret value was truncated when copying
- Generate a new secret

### "Tenant not found"

- Verify tenant ID is correct (GUID format)
- Check if using correct tenant name in config

### Token issues

- Delete `.azure_tokens.json` to force re-authentication
- Run `python3 auth.py --test` to verify credentials

## API Documentation

- [Microsoft Graph API Overview](https://learn.microsoft.com/en-us/graph/overview)
- [Users API Reference](https://learn.microsoft.com/en-us/graph/api/resources/user)
- [Groups API Reference](https://learn.microsoft.com/en-us/graph/api/resources/group)
- [Devices API Reference](https://learn.microsoft.com/en-us/graph/api/resources/device)
