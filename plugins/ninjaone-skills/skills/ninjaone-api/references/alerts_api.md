# Alerts API Reference

Alert monitoring and management.

## Endpoints

### List Alerts
```bash
python ninjaone_api.py alerts list [--severity SEVERITY] [--source SOURCE] [--device-filter FILTER]
```

**Parameters:**
- `--severity`: Filter by severity (CRITICAL, MAJOR, MODERATE, MINOR)
- `--source`: Filter by alert source/type
- `--device-filter`: Device filter expression

**Example:**
```bash
python ninjaone_api.py alerts list --severity CRITICAL
python ninjaone_api.py alerts list --device-filter "org = 123"
```

### Get Alert
```bash
python ninjaone_api.py alerts get ALERT_UID
```

Get alert details by UID.

### Reset Alert
```bash
python ninjaone_api.py alerts reset ALERT_UID
```

Reset/acknowledge an alert.

### Delete Alert
```bash
python ninjaone_api.py alerts delete ALERT_UID
```

Delete an alert (removes from history).

## Response Fields

### Alert Object
| Field | Type | Description |
|-------|------|-------------|
| `uid` | string | Alert unique ID |
| `deviceId` | integer | Device ID |
| `message` | string | Alert message |
| `severity` | string | Severity level |
| `sourceType` | string | Alert source |
| `sourceName` | string | Source name |
| `createTime` | timestamp | Alert creation time |
| `data` | object | Alert-specific data |

### Severity Levels
| Level | Description |
|-------|-------------|
| `CRITICAL` | Immediate attention required |
| `MAJOR` | High priority issue |
| `MODERATE` | Medium priority |
| `MINOR` | Low priority/informational |

### Common Source Types
| Source | Description |
|--------|-------------|
| `CONDITION` | Monitoring condition triggered |
| `PATCH` | Patch-related alert |
| `ANTIVIRUS` | AV threat detected |
| `DISK` | Disk space/health |
| `BACKUP` | Backup failure |
| `OFFLINE` | Device offline |

## Common Workflows

### Alert Triage
```bash
# Get all critical alerts
python ninjaone_api.py alerts list --severity CRITICAL --format table

# Get alert details
python ninjaone_api.py alerts get abc123-def456

# Create ticket if needed
python ninjaone_api.py tickets create \
  --org-id 123 \
  --subject "Critical Alert: [Alert Message]" \
  --description "Alert details from device..."

# Reset after addressing
python ninjaone_api.py alerts reset abc123-def456
```

### Alert Dashboard
```bash
# Count alerts by severity
python ninjaone_api.py alerts list --severity CRITICAL --format summary
python ninjaone_api.py alerts list --severity MAJOR --format summary

# Export all alerts for reporting
python ninjaone_api.py alerts list --format json > alerts.json
```

### Organization Alert Review
```bash
# Get alerts for specific org
python ninjaone_api.py alerts list --device-filter "org = 123"

# Get alerts for servers only
python ninjaone_api.py alerts list --device-filter "class = WINDOWS_SERVER"
```

### Alert Automation
```bash
#!/bin/bash
# Auto-create tickets for critical alerts

alerts=$(python ninjaone_api.py alerts list --severity CRITICAL --format json)

echo "$alerts" | jq -c '.[]' | while read alert; do
    uid=$(echo "$alert" | jq -r '.uid')
    device_id=$(echo "$alert" | jq -r '.deviceId')
    message=$(echo "$alert" | jq -r '.message')
    org_id=$(echo "$alert" | jq -r '.organizationId')

    # Create ticket
    python ninjaone_api.py tickets create \
        --org-id "$org_id" \
        --subject "Critical Alert: $message" \
        --description "Auto-generated from alert $uid" \
        --device-id "$device_id" \
        --priority "Critical"

    # Note: Don't reset alert until ticket is resolved
done
```

## Alert Lifecycle

1. **Triggered**: Monitoring condition triggers alert
2. **Active**: Alert visible in dashboard
3. **Reset**: Alert acknowledged/reset by user
4. **Cleared**: Condition no longer met (auto-clear)
5. **Deleted**: Removed from history

## API Notes

- Alert UIDs are unique identifiers (not sequential IDs)
- Resetting an alert marks it as acknowledged
- Deleted alerts are removed from history permanently
- Some alerts auto-clear when the condition resolves
- Alert history retention depends on NinjaOne settings
