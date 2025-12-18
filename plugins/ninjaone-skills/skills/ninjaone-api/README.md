# NinjaOne API Skill

Full REST API coverage for NinjaOne RMM (Remote Monitoring & Management) with OAuth 2.0 authentication.

## Features

- **70+ API Operations** across 9 domains
- **OAuth 2.0 Client Credentials** with automatic token refresh
- **Secure Credential Storage** (config template checked in, secrets NOT checked in)
- **Multiple Output Formats** (table, JSON, compact, summary)
- **Device Filtering** with NinjaOne's filter syntax

## Prerequisites

- Python 3.8+
- NinjaOne account with API access
- API application created in NinjaOne admin portal

## Setup

### 1. Create API Application in NinjaOne

1. Log in to [NinjaOne](https://app.ninjarmm.com)
2. Navigate to **Administration → Apps → API**
3. Click **Add** to create a new API application
4. Configure the application:
   - **Name**: `Claude Code Integration` (or your preferred name)
   - **Application Platform**: API Services (Machine-to-Machine)
   - **Grant Type**: Client Credentials
   - **Scopes**: Select the scopes you need:
     - `monitoring` - Read device and alert data
     - `management` - Execute management actions
     - `control` - Remote control capabilities
5. Click **Save**
6. Copy the **Client ID** and **Client Secret** (shown only once!)

### 2. Configure Credentials

```bash
# Navigate to skill directory
cd plugins/ninjaone-skills/skills/ninjaone-api

# Copy template to create config
cp config/ninjaone_config.template.json config/ninjaone_config.json

# Edit with your credentials
# NEVER commit ninjaone_config.json to version control!
```

Edit `config/ninjaone_config.json`:

```json
{
  "instance": {
    "name": "NinjaOne",
    "api_url": "https://app.ninjarmm.com",
    "client_id": "YOUR_CLIENT_ID_HERE",
    "client_secret": "YOUR_CLIENT_SECRET_HERE",
    "scopes": ["monitoring", "management", "control"]
  },
  "defaults": {
    "timeout": 30,
    "max_retries": 3,
    "page_size": 100
  }
}
```

### 3. Test Connection

```bash
# Test authentication
python scripts/auth.py --test

# Expected output:
# Testing authentication for: NinjaOne
# API URL: https://app.ninjarmm.com
# Authentication successful!
# Token expires in: 3600s
# Scopes: monitoring management control
```

## Usage

### Device Operations

```bash
# List all devices
python scripts/ninjaone_api.py devices list

# List devices with filter
python scripts/ninjaone_api.py devices list --filter "class = WINDOWS_SERVER"

# Get device details
python scripts/ninjaone_api.py devices get 12345
python scripts/ninjaone_api.py devices detailed 12345

# Device inventory
python scripts/ninjaone_api.py devices software 12345
python scripts/ninjaone_api.py devices patches 12345
python scripts/ninjaone_api.py devices services 12345
python scripts/ninjaone_api.py devices network 12345
```

### Organization Operations

```bash
# List organizations (clients)
python scripts/ninjaone_api.py organizations list

# Get organization details
python scripts/ninjaone_api.py organizations get 456

# Get organization's devices
python scripts/ninjaone_api.py organizations devices 456
```

### Alert Operations

```bash
# List all alerts
python scripts/ninjaone_api.py alerts list

# List critical alerts only
python scripts/ninjaone_api.py alerts list --severity CRITICAL

# Reset an alert
python scripts/ninjaone_api.py alerts reset abc123
```

### Ticket Operations

```bash
# List tickets
python scripts/ninjaone_api.py tickets list

# Create a ticket
python scripts/ninjaone_api.py tickets create \
  --org-id 456 \
  --subject "Server Maintenance Required" \
  --description "Scheduled maintenance for server updates"

# Update ticket status
python scripts/ninjaone_api.py tickets update 789 --status CLOSED
```

### Management Actions

```bash
# Reboot a device
python scripts/ninjaone_api.py management reboot 12345 --reason "Patch installation"

# Run a script
python scripts/ninjaone_api.py management run-script 12345 --script-id 999

# Patch management
python scripts/ninjaone_api.py management scan-patches 12345
python scripts/ninjaone_api.py management apply-patches 12345

# Service control
python scripts/ninjaone_api.py management control-service 12345 \
  --service-id "wuauserv" --action START
```

### Query/Reports

```bash
# Antivirus status
python scripts/ninjaone_api.py queries antivirus-status

# Software inventory
python scripts/ninjaone_api.py queries software

# Patch reports
python scripts/ninjaone_api.py queries os-patches --status PENDING
python scripts/ninjaone_api.py queries software-patches

# Device health
python scripts/ninjaone_api.py queries device-health
```

## Device Filter Syntax

NinjaOne uses a special filter syntax for device queries:

| Filter | Example | Description |
|--------|---------|-------------|
| Class | `class = WINDOWS_SERVER` | Device type |
| Organization | `org = 123` | Organization ID |
| Status | `status = OFFLINE` | Online/offline status |
| Policy | `policy = 456` | Policy assignment |

### Device Classes

- `WINDOWS_WORKSTATION`
- `WINDOWS_SERVER`
- `MAC`
- `MAC_SERVER`
- `LINUX_WORKSTATION`
- `LINUX_SERVER`
- `VMWARE_VM_HOST`
- `CLOUD_MONITOR_TARGET`

### Combining Filters

```bash
# Multiple conditions with AND
--filter "class = WINDOWS_SERVER AND org = 123"

# Filter examples
--filter "class = WINDOWS_WORKSTATION AND status = OFFLINE"
--filter "org = 123 AND policy = 456"
```

## Output Formats

```bash
# Table format (default)
python scripts/ninjaone_api.py devices list --format table

# JSON format (for automation)
python scripts/ninjaone_api.py devices list --format json

# Compact format (one line per item)
python scripts/ninjaone_api.py devices list --format compact

# Summary format (count only)
python scripts/ninjaone_api.py devices list --format summary
```

## API Domains Reference

| Domain | Endpoints | Description |
|--------|-----------|-------------|
| Devices | 20+ | Device inventory, hardware, software, patches |
| Organizations | 10+ | Client/tenant management |
| Queries | 23+ | Reports and analytics |
| Management | 15+ | Remote actions and control |
| Alerts | 5+ | Alert monitoring and management |
| Tickets | 12+ | Ticketing system |
| Policies | 5+ | Policy configuration |
| Webhooks | 3+ | Event notifications |

See the `references/` directory for detailed API documentation per domain.

## Security Notes

- **NEVER commit** `ninjaone_config.json` to version control
- Store credentials securely - they provide full API access
- Use minimal scopes for your use case
- Token cache (`.ninjaone_tokens.json`) is gitignored
- Rotate credentials periodically

## Troubleshooting

### Authentication Failed

```
Error: Token acquisition failed (401): invalid_client
```

**Solution**: Verify `client_id` and `client_secret` in your config file. Regenerate credentials in NinjaOne if needed.

### Scope Error

```
Error: Token acquisition failed: insufficient_scope
```

**Solution**: Add required scopes to your API application in NinjaOne admin portal.

### Network Error

```
Error: Network error during authentication
```

**Solution**: Check network connectivity and firewall rules. Ensure `https://app.ninjarmm.com` is accessible.

### Clear Token Cache

```bash
python scripts/auth.py --clear-cache
```

## References

- [NinjaOne API Documentation](https://app.ninjarmm.com/apidocs/)
- [NinjaOne API v2 OpenAPI Spec](https://app.ninjarmm.com/apidocs/NinjaRMM-API-v2.json)
- [NinjaOne Support](https://www.ninjaone.com/support/)
