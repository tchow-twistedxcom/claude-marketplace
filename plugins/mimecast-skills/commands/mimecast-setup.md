---
name: mimecast-setup
description: Set up Mimecast CLI configuration and API authentication
---

# Mimecast CLI Setup

Configure the Mimecast Python CLI for email security platform access.

## Prerequisites

- **Python 3.8+** installed
- **tabulate** library (`pip install tabulate`) - for table output
- **Mimecast account** with API access
- **Mimecast API credentials** (from Mimecast Admin Console)

## Quick Setup

### 1. Get Your Mimecast API Credentials

Mimecast uses HMAC-SHA1 signature authentication. You need 4 credentials:

1. Log in to your Mimecast Admin Console
2. Navigate to **Administration → Services → API and Platform Integrations**
3. Click **Your Application Integrations**
4. Create or select an application
5. Generate the following credentials:
   - **Application ID** (app_id)
   - **Application Key** (app_key)
   - **Access Key** (access_key)
   - **Secret Key** (secret_key)

### 2. Create Configuration File

Create the config file at `plugins/mimecast-skills/config/mimecast_config.json`:

```bash
# Navigate to config directory
cd plugins/mimecast-skills/config

# Copy template
cp mimecast_config.template.json mimecast_config.json

# Edit with your credentials
```

Configuration file format:

```json
{
  "default_profile": "production",
  "profiles": {
    "production": {
      "name": "Production",
      "region": "us",
      "base_url": "https://us-api.mimecast.com",
      "app_id": "YOUR_APP_ID",
      "app_key": "YOUR_APP_KEY",
      "access_key": "YOUR_ACCESS_KEY",
      "secret_key": "YOUR_SECRET_KEY"
    }
  }
}
```

### 3. Select Your Region

Choose the correct regional endpoint based on your Mimecast instance:

| Region | Base URL |
|--------|----------|
| US | `https://us-api.mimecast.com` |
| EU | `https://eu-api.mimecast.com` |
| DE | `https://de-api.mimecast.com` |
| AU | `https://au-api.mimecast.com` |
| ZA | `https://za-api.mimecast.com` |
| CA | `https://ca-api.mimecast.com` |
| UK | `https://uk-api.mimecast.com` |
| Sandbox | `https://sandbox-api.mimecast.com` |

### 4. Install Dependencies

```bash
pip install tabulate
```

### 5. Verify Installation

```bash
# Test authentication
cd plugins/mimecast-skills
python3 scripts/mimecast_auth.py --test

# Test the CLI
python3 scripts/mimecast_api.py account info

# Should display your account details
```

## CLI Usage

### Basic Commands

```bash
# Get account information
python3 scripts/mimecast_api.py account info

# List internal users
python3 scripts/mimecast_api.py users list

# Search messages
python3 scripts/mimecast_api.py messages search --from "sender@example.com"

# List held messages
python3 scripts/mimecast_api.py messages held

# Get TTP URL logs
python3 scripts/mimecast_api.py ttp urls --start 2024-01-01
```

### Output Formats

```bash
# Human-readable table (default)
python3 scripts/mimecast_api.py users list

# JSON for scripting
python3 scripts/mimecast_api.py users list --output json

# Pipe to jq for processing
python3 scripts/mimecast_api.py groups list --output json | jq '.[].name'
```

### Profile Selection

```bash
# Use production (default)
python3 scripts/mimecast_api.py users list

# Use sandbox
python3 scripts/mimecast_api.py users list --profile sandbox
```

## Available Operations (28 Total)

| Resource | Operations |
|----------|------------|
| account | info |
| messages | search, held, release, info |
| ttp | urls, attachments, impersonation |
| archive | search |
| users | list, create, update, delete |
| groups | list, create, add-member, remove-member |
| policies | list, block-sender, permit-sender, definitions |
| reports | audit, siem, stats, threat-intel |

## Security Best Practices

1. **Never Commit Config**: The `config/.gitignore` excludes `mimecast_config.json`
2. **Use Template**: Keep `mimecast_config.template.json` without real keys
3. **Rotate Keys Regularly**: Generate new access/secret keys periodically
4. **Limit Permissions**: Use role-based API permissions in Mimecast
5. **Monitor API Usage**: Track API calls in Mimecast Admin Console

## Troubleshooting

### Authentication Failed
```
Error: [401] Authentication Error: Signature mismatch
```

**Solution:**
- Verify all 4 credentials in `config/mimecast_config.json`
- Ensure secret_key is base64 encoded (as provided by Mimecast)
- Check system clock is accurate (HMAC signature is time-sensitive)
- Regenerate keys in Mimecast Admin Console

### Wrong Region
```
Error: Connection refused / timeout
```

**Solution:**
- Verify `base_url` matches your Mimecast region
- Check regional endpoint in Mimecast Admin Console
- Update `region` field in config

### Config File Not Found
```
Error: Config file not found
```

**Solution:**
```bash
# Create config from template
cp config/mimecast_config.template.json config/mimecast_config.json

# Edit with your credentials
```

### Permission Denied
```
Error: [403] Access denied
```

**Solution:**
- Verify API application has required permissions
- Check with Mimecast admin for API role permissions
- Some endpoints require specific subscriptions

### Missing Dependencies
```
ModuleNotFoundError: No module named 'tabulate'
```

**Solution:**
```bash
pip install tabulate
```

## Usage Examples

**User:** "Set up Mimecast integration"
**Action:** Guide through config file creation and credential setup

**User:** "List Mimecast users"
**Action:** Execute `python3 scripts/mimecast_api.py users list`

**User:** "Check for phishing URLs"
**Action:** Execute `python3 scripts/mimecast_api.py ttp urls --start 2024-01-01`
