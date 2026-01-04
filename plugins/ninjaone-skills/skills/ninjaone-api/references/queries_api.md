# Queries API Reference

Reports and analytics across the device fleet.

## Common Parameters

All query commands support these filtering options:

| Parameter | Description |
|-----------|-------------|
| `--filter`, `--df` | Device filter expression (e.g., `"class = WINDOWS_SERVER"`) |
| `--org-id` | Filter by organization ID (convenience flag) |
| `--org-name` | Filter by organization name (auto-resolves to ID) |

**Examples:**
```bash
# Filter by organization ID
python ninjaone_api.py queries volumes --org-id 2

# Filter by organization name (case-insensitive, partial match)
python ninjaone_api.py queries computer-systems --org-name "Twisted X"

# Combine with device class filter
python ninjaone_api.py queries software --org-id 2 --filter "class = WINDOWS_SERVER"
```

## Endpoints

### Antivirus Status
```bash
python ninjaone_api.py queries antivirus-status [--filter FILTER] [--org-id ID] [--org-name NAME]
```

Get antivirus status across all devices.

### Antivirus Threats
```bash
python ninjaone_api.py queries antivirus-threats [--filter FILTER]
```

Get detected antivirus threats.

### Computer Systems
```bash
python ninjaone_api.py queries computer-systems [--filter FILTER]
```

System inventory report (hardware specs).

### Disk Drives
```bash
python ninjaone_api.py queries disk-drives [--filter FILTER]
```

Physical disk drive inventory.

### Software Inventory
```bash
python ninjaone_api.py queries software [--filter FILTER] [--name NAME]
```

**Parameters:**
- `--name`: Filter by software name (partial match)

### OS Patches
```bash
python ninjaone_api.py queries os-patches [--filter FILTER] [--status STATUS]
```

**Parameters:**
- `--status`: APPROVED, PENDING, REJECTED, INSTALLED

### Software Patches
```bash
python ninjaone_api.py queries software-patches [--filter FILTER] [--status STATUS]
```

Third-party software patch status.

### Windows Services
```bash
python ninjaone_api.py queries windows-services [--filter FILTER] [--name NAME] [--state STATE]
```

**Parameters:**
- `--name`: Filter by service name
- `--state`: RUNNING, STOPPED, PAUSED

### RAID Controllers
```bash
python ninjaone_api.py queries raid-controllers [--filter FILTER]
```

RAID controller inventory.

### RAID Drives
```bash
python ninjaone_api.py queries raid-drives [--filter FILTER]
```

RAID drive status and health.

### Processors
```bash
python ninjaone_api.py queries processors [--filter FILTER]
```

CPU inventory across fleet.

### Memory Modules
```bash
python ninjaone_api.py queries memory [--filter FILTER]
```

RAM module inventory.

### Network Interfaces
```bash
python ninjaone_api.py queries network-interfaces [--filter FILTER]
```

Network adapter inventory.

### Volumes
```bash
python ninjaone_api.py queries volumes [--filter FILTER]
```

Disk volume information.

### Device Health
```bash
python ninjaone_api.py queries device-health [--filter FILTER]
```

Overall device health status.

### Custom Fields
```bash
python ninjaone_api.py queries custom-fields [--filter FILTER]
```

Custom field values across devices.

### Backup Usage
```bash
python ninjaone_api.py queries backup-usage [--filter FILTER]
```

Backup storage usage report.

### Operating Systems
```bash
python ninjaone_api.py queries operating-systems [--filter FILTER]
```

OS distribution report.

### Logged-In Users
```bash
python ninjaone_api.py queries logged-in-users [--filter FILTER]
```

Currently logged-in users.

### Last Logged-In User
```bash
python ninjaone_api.py queries last-logged-in-user [--filter FILTER]
```

Last user to log in per device.

## Query Filter Syntax

Same filter syntax as device queries:

```bash
# By device class
--filter "class = WINDOWS_SERVER"

# By organization
--filter "org = 123"

# Combined
--filter "class = WINDOWS_WORKSTATION AND org = 123"
```

## Response Formats

### Antivirus Status
| Field | Type | Description |
|-------|------|-------------|
| `deviceId` | integer | Device ID |
| `deviceName` | string | Device name |
| `productName` | string | AV product |
| `productState` | string | AV state |
| `definitionDate` | timestamp | Definitions date |

### Patch Status
| Field | Type | Description |
|-------|------|-------------|
| `deviceId` | integer | Device ID |
| `kb` | string | KB number |
| `title` | string | Patch title |
| `severity` | string | Severity level |
| `status` | string | Installation status |

### Software Inventory
| Field | Type | Description |
|-------|------|-------------|
| `deviceId` | integer | Device ID |
| `name` | string | Software name |
| `version` | string | Version |
| `publisher` | string | Publisher |
| `installDate` | timestamp | Install date |

## Common Workflows

### Security Audit
```bash
# Check AV status
python ninjaone_api.py queries antivirus-status --format table

# Check for threats
python ninjaone_api.py queries antivirus-threats

# Check pending patches
python ninjaone_api.py queries os-patches --status PENDING
```

### Inventory Report
```bash
# Hardware inventory
python ninjaone_api.py queries computer-systems --format json > hardware.json

# Software inventory
python ninjaone_api.py queries software --format json > software.json

# Export specific software
python ninjaone_api.py queries software --name "Microsoft Office"
```

### Patch Compliance
```bash
# Get all pending OS patches
python ninjaone_api.py queries os-patches --status PENDING

# Get pending third-party patches
python ninjaone_api.py queries software-patches --status PENDING

# Check specific org compliance
python ninjaone_api.py queries os-patches --filter "org = 123" --status PENDING
```

## API Notes

- Query results are paginated
- Large result sets may require multiple API calls
- Filter syntax follows NinjaOne's device filter format
- Some queries require specific NinjaOne modules enabled
