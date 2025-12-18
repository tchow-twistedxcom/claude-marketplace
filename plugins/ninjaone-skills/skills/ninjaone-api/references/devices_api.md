# Devices API Reference

Device inventory, monitoring, and hardware/software information.

## Endpoints

### List Devices
```bash
python ninjaone_api.py devices list [--org-id ID] [--filter FILTER] [--page-size N]
```

**Parameters:**
- `--org-id`: Filter by organization ID
- `--filter`: Device filter expression (see filter syntax below)
- `--page-size`: Results per page (default: 100)

**Example:**
```bash
python ninjaone_api.py devices list --filter "class = WINDOWS_SERVER"
```

### Get Device
```bash
python ninjaone_api.py devices get DEVICE_ID
```

Returns basic device information.

### Get Detailed Device
```bash
python ninjaone_api.py devices detailed DEVICE_ID
```

Returns comprehensive device information including hardware specs.

### Search Devices
```bash
python ninjaone_api.py devices search --filter FILTER
```

Search with advanced filter criteria.

### Device Activities
```bash
python ninjaone_api.py devices activities DEVICE_ID [--older-than TIMESTAMP] [--newer-than TIMESTAMP]
```

Get device activity history.

### Device Alerts
```bash
python ninjaone_api.py devices alerts DEVICE_ID
```

Get alerts for a specific device.

### Software Inventory
```bash
python ninjaone_api.py devices software DEVICE_ID
```

List installed software on device.

### Patch Status
```bash
python ninjaone_api.py devices patches DEVICE_ID [--status STATUS] [--type TYPE]
```

**Parameters:**
- `--status`: APPROVED, PENDING, REJECTED
- `--type`: os, software

### Disk Drives
```bash
python ninjaone_api.py devices disk-drives DEVICE_ID
```

Get physical disk drive information.

### Volumes
```bash
python ninjaone_api.py devices volumes DEVICE_ID
```

Get volume/partition information.

### Processors
```bash
python ninjaone_api.py devices processors DEVICE_ID
```

Get CPU information.

### Network Interfaces
```bash
python ninjaone_api.py devices network DEVICE_ID
```

Get network adapter information.

### Windows Services
```bash
python ninjaone_api.py devices services DEVICE_ID [--state STATE]
```

**Parameters:**
- `--state`: RUNNING, STOPPED, PAUSED

### Custom Fields
```bash
# Get custom fields
python ninjaone_api.py devices custom-fields DEVICE_ID

# Update custom fields
python ninjaone_api.py devices custom-fields DEVICE_ID --set '{"fieldName": "value"}'
```

## Device Filter Syntax

### Device Classes
| Value | Description |
|-------|-------------|
| `WINDOWS_WORKSTATION` | Windows desktop/laptop |
| `WINDOWS_SERVER` | Windows Server |
| `MAC` | macOS workstation |
| `MAC_SERVER` | macOS Server |
| `LINUX_WORKSTATION` | Linux desktop |
| `LINUX_SERVER` | Linux server |
| `VMWARE_VM_HOST` | VMware ESXi host |
| `CLOUD_MONITOR_TARGET` | Cloud-monitored target |

### Filter Operators
| Operator | Description |
|----------|-------------|
| `=` | Equals |
| `!=` | Not equals |
| `AND` | Logical AND |
| `OR` | Logical OR |

### Filter Examples
```bash
# By device class
--filter "class = WINDOWS_SERVER"

# By organization
--filter "org = 123"

# By status
--filter "status = OFFLINE"

# Combined
--filter "class = WINDOWS_SERVER AND org = 123"
--filter "class = WINDOWS_WORKSTATION AND status = OFFLINE"
```

## Response Fields

### Device Object
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Device ID |
| `systemName` | string | Computer name |
| `dnsName` | string | DNS hostname |
| `organizationId` | integer | Organization ID |
| `nodeClass` | string | Device class |
| `offline` | boolean | Offline status |
| `lastContact` | timestamp | Last check-in time |
| `os` | object | Operating system info |
| `system` | object | System hardware info |

### Detailed Device Fields
| Field | Type | Description |
|-------|------|-------------|
| `processor` | object | CPU details |
| `memory` | object | RAM information |
| `volumes` | array | Disk volumes |
| `networkInterfaces` | array | Network adapters |
| `installedSoftware` | array | Software list |

## API Notes

- Device list is paginated (default 100 per page)
- Filter parameter uses NinjaOne's `df` query format
- Timestamps are Unix epoch (seconds)
- Custom fields require proper field definitions in NinjaOne
