---
name: ninjaone-api
description: |
  NinjaOne RMM API integration for device monitoring, management, ticketing, and reporting.

  Activates when user mentions:
  - NinjaOne, NinjaRMM, Ninja RMM, Ninja One
  - RMM (Remote Monitoring and Management) with device/endpoint context
  - MSP device management, endpoint monitoring
  - IT management with devices, patches, alerts, tickets
  - Device inventory, software inventory, patch management
  - Windows services monitoring, disk monitoring
  - Endpoint alerts, device alerts
  - IT ticketing with device context
---

# NinjaOne API Skill

Execute NinjaOne RMM operations via Python CLI for device monitoring, management, ticketing, and reporting.

## Quick Reference

```bash
# Device Operations
python ninjaone_api.py devices list [--org-id ID] [--filter FILTER]
python ninjaone_api.py devices get DEVICE_ID
python ninjaone_api.py devices detailed DEVICE_ID
python ninjaone_api.py devices search --filter "class = WINDOWS_WORKSTATION"
python ninjaone_api.py devices software DEVICE_ID
python ninjaone_api.py devices patches DEVICE_ID
python ninjaone_api.py devices services DEVICE_ID

# Organization Operations
python ninjaone_api.py organizations list
python ninjaone_api.py organizations get ORG_ID
python ninjaone_api.py organizations devices ORG_ID

# Alert Operations
python ninjaone_api.py alerts list [--severity SEVERITY]
python ninjaone_api.py alerts reset ALERT_ID

# Ticket Operations
python ninjaone_api.py tickets list [--status STATUS]
python ninjaone_api.py tickets create --org-id ORG_ID --subject "Subject" --description "Description"
python ninjaone_api.py tickets update TICKET_ID --status STATUS

# Management Actions
python ninjaone_api.py management reboot DEVICE_ID [--reason "Reason"]
python ninjaone_api.py management run-script DEVICE_ID --script-id SCRIPT_ID
python ninjaone_api.py management scan-patches DEVICE_ID
python ninjaone_api.py management apply-patches DEVICE_ID

# Query/Reports
python ninjaone_api.py queries antivirus-status [--filter FILTER]
python ninjaone_api.py queries software [--filter FILTER]
python ninjaone_api.py queries os-patches [--status STATUS]
python ninjaone_api.py queries device-health
```

## Authentication

Uses OAuth 2.0 Client Credentials flow. Configure in `config/ninjaone_config.json`:

```json
{
  "instance": {
    "api_url": "https://app.ninjarmm.com",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "scopes": ["monitoring", "management", "control"]
  }
}
```

## Device Filter Syntax

NinjaOne uses a filter parameter (`df`) for device queries:

```bash
# Filter by device class
--filter "class = WINDOWS_WORKSTATION"
--filter "class = WINDOWS_SERVER"
--filter "class = MAC"

# Filter by organization
--filter "org = 123"

# Filter by status
--filter "status = OFFLINE"

# Combine filters
--filter "class = WINDOWS_SERVER AND org = 123"
```

## API Domains

| Domain | Description | Key Operations |
|--------|-------------|----------------|
| Devices | Device inventory & monitoring | list, get, search, software, patches, services |
| Organizations | Client/tenant management | list, get, locations, end-users |
| Queries | Reports & analytics | 20+ report types (AV, patches, software, health) |
| Management | Remote actions | reboot, scripts, patches, services |
| Alerts | Alert management | list, get, reset, delete |
| Tickets | Ticketing system | CRUD, comments, status management |
| Policies | Policy configuration | list, get |
| Webhooks | Event notifications | configure, disable |

## Output Formats

```bash
--format table    # Default: formatted table output
--format json     # Raw JSON for automation
--format compact  # One-line per item
--format summary  # Count only
```

## Common Workflows

### Device Health Check
```bash
# List all offline devices
python ninjaone_api.py devices list --filter "status = OFFLINE"

# Check specific device health
python ninjaone_api.py devices detailed DEVICE_ID
python ninjaone_api.py devices alerts DEVICE_ID
```

### Patch Management
```bash
# Check patch status across fleet
python ninjaone_api.py queries os-patches --status PENDING

# Apply patches to device
python ninjaone_api.py management scan-patches DEVICE_ID
python ninjaone_api.py management apply-patches DEVICE_ID
```

### Incident Response
```bash
# Get active alerts
python ninjaone_api.py alerts list --severity CRITICAL

# Create ticket for alert
python ninjaone_api.py tickets create --org-id 123 --subject "Critical Alert" --description "..."

# Reset alert after resolution
python ninjaone_api.py alerts reset ALERT_ID
```

## References

- [NinjaOne API Documentation](https://app.ninjarmm.com/apidocs/)
- [OpenAPI Specification](https://app.ninjarmm.com/apidocs/NinjaRMM-API-v2.json)
- See `references/` directory for domain-specific documentation
