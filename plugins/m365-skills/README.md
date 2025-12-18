# M365 Skills Plugin

Microsoft 365 and Azure integrations for Claude Code via Microsoft Graph API.

## Available Skills

| Skill | Description | Status |
|-------|-------------|--------|
| `azure-ad` | Azure AD/Entra ID operations (users, groups, devices, directory) | Available |
| `sharepoint` | SharePoint sites, lists, document libraries | Planned |
| `teams` | Microsoft Teams, channels, messages | Planned |
| `exchange` | Exchange Online mailboxes, calendars | Planned |
| `intune` | Intune device management, policies | Planned |

## Quick Start

### 1. Azure AD App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Microsoft Entra ID → App registrations → New registration**
3. Name: `Claude Code M365 Integration`
4. Account type: Single tenant
5. Click **Register**

### 2. Configure API Permissions

Add these **Application permissions** for Microsoft Graph:
- `User.Read.All`
- `Group.Read.All`
- `Device.Read.All`
- `Directory.Read.All`

Then click **Grant admin consent**.

### 3. Create Client Secret

1. Go to **Certificates & secrets → New client secret**
2. Copy the secret value immediately (shown only once)

### 4. Configure Credentials

```bash
cd skills/azure-ad/config
cp azure_config.template.json azure_config.json
# Edit azure_config.json with your credentials
```

### 5. Test Connection

```bash
cd skills/azure-ad/scripts
python3 auth.py --test
```

## Usage

```bash
# List users
python3 azure_ad_api.py users list

# Get specific user
python3 azure_ad_api.py users get "user@domain.com"

# List groups
python3 azure_ad_api.py groups list

# List devices
python3 azure_ad_api.py devices list

# Output formats
python3 azure_ad_api.py --format json users list
python3 azure_ad_api.py --format csv users list > users.csv
```

## Security Notes

- Never commit `azure_config.json` (contains secrets)
- Never commit `.azure_tokens.json` (contains access tokens)
- Use least-privilege permissions (read-only if possible)
- Rotate client secrets before expiration

## Documentation

- [Azure AD Skill Setup](skills/azure-ad/README.md)
- [Users API Reference](skills/azure-ad/references/users_api.md)
- [Groups API Reference](skills/azure-ad/references/groups_api.md)
- [Devices API Reference](skills/azure-ad/references/devices_api.md)
- [Directory API Reference](skills/azure-ad/references/directory_api.md)
