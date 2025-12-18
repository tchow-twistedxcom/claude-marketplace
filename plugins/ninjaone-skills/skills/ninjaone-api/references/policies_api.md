# Policies API Reference

Policy configuration and management.

## Endpoints

### List Policies
```bash
python ninjaone_api.py policies list
```

List all policies in the system.

### Get Policy
```bash
python ninjaone_api.py policies get POLICY_ID
```

Get policy details by ID.

### Policy Conditions
```bash
python ninjaone_api.py policies conditions POLICY_ID
```

Get monitoring conditions defined in a policy.

## Response Fields

### Policy Object
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Policy ID |
| `name` | string | Policy name |
| `description` | string | Policy description |
| `nodeClass` | string | Target device class |
| `parentPolicyId` | integer | Parent policy (inheritance) |
| `updated` | timestamp | Last modification |

### Node Classes
| Class | Description |
|-------|-------------|
| `WINDOWS_WORKSTATION` | Windows desktop policy |
| `WINDOWS_SERVER` | Windows Server policy |
| `MAC` | macOS policy |
| `LINUX_WORKSTATION` | Linux desktop policy |
| `LINUX_SERVER` | Linux server policy |

### Condition Object
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Condition ID |
| `name` | string | Condition name |
| `type` | string | Condition type |
| `enabled` | boolean | Is condition active |
| `severity` | string | Alert severity |
| `parameters` | object | Condition parameters |

## Common Condition Types

| Type | Description | Parameters |
|------|-------------|------------|
| `CPU` | CPU usage threshold | percentage, duration |
| `MEMORY` | RAM usage threshold | percentage, duration |
| `DISK_SPACE` | Disk space threshold | percentage, drive |
| `DISK_USAGE` | Disk I/O threshold | percentage |
| `PROCESS` | Process monitoring | process name, state |
| `SERVICE` | Windows service state | service name, expected state |
| `ANTIVIRUS` | AV status/definitions | max age, enabled |
| `PATCH` | Patch compliance | severity, age |
| `OFFLINE` | Device offline | duration |
| `EVENT_LOG` | Windows event log | event ID, source, level |

## Common Workflows

### Policy Audit
```bash
# List all policies
python ninjaone_api.py policies list --format table

# Get details of specific policy
python ninjaone_api.py policies get 123 --format json

# View monitoring conditions
python ninjaone_api.py policies conditions 123 --format json
```

### Policy Documentation
```bash
# Export all policies
python ninjaone_api.py policies list --format json > policies.json

# Export policy with conditions
python ninjaone_api.py policies get 123 --format json > policy_123.json
python ninjaone_api.py policies conditions 123 --format json > conditions_123.json
```

### Compare Policies
```bash
# Export two policies for comparison
python ninjaone_api.py policies conditions 123 --format json > policy_a.json
python ninjaone_api.py policies conditions 456 --format json > policy_b.json

# Use diff or jq to compare
diff <(jq -S . policy_a.json) <(jq -S . policy_b.json)
```

## Policy Inheritance

Policies can inherit from parent policies:

```
Base Windows Server Policy
├── Production Server Policy
│   ├── Database Server Policy
│   └── Web Server Policy
└── Development Server Policy
```

Child policies inherit conditions from parents and can:
- Override inherited settings
- Add additional conditions
- Disable inherited conditions

## API Notes

- Policy management (create/update/delete) requires NinjaOne admin access
- This skill provides read-only access to policies
- Policy changes should be made through NinjaOne UI
- Condition parameters vary by condition type
- Policy assignments are managed at organization/device level
