# Management API Reference

Remote management actions and device control.

## Endpoints

### Reboot Device
```bash
python ninjaone_api.py management reboot DEVICE_ID [--reason REASON] [--mode MODE]
```

**Parameters:**
- `--reason`: Reason for reboot (logged)
- `--mode`: NORMAL, FORCED (default: NORMAL)

**Example:**
```bash
python ninjaone_api.py management reboot 12345 --reason "Monthly maintenance"
```

### Run Script
```bash
python ninjaone_api.py management run-script DEVICE_ID --script-id SCRIPT_ID [--parameters PARAMS]
```

**Parameters:**
- `--script-id`: ID of script from NinjaOne library
- `--parameters`: JSON string of script parameters

**Example:**
```bash
python ninjaone_api.py management run-script 12345 --script-id 999 --parameters '{"param1": "value"}'
```

### Scan Patches
```bash
python ninjaone_api.py management scan-patches DEVICE_ID
```

Trigger a patch scan on the device.

### Apply Patches
```bash
python ninjaone_api.py management apply-patches DEVICE_ID [--reboot] [--patch-ids IDS]
```

**Parameters:**
- `--reboot`: Reboot after patching if required
- `--patch-ids`: Comma-separated list of specific patch IDs

**Example:**
```bash
# Apply all approved patches
python ninjaone_api.py management apply-patches 12345 --reboot

# Apply specific patches
python ninjaone_api.py management apply-patches 12345 --patch-ids "KB123,KB456"
```

### Control Service
```bash
python ninjaone_api.py management control-service DEVICE_ID --service-id SERVICE --action ACTION
```

**Parameters:**
- `--service-id`: Windows service name
- `--action`: START, STOP, RESTART

**Example:**
```bash
python ninjaone_api.py management control-service 12345 --service-id "Spooler" --action RESTART
```

### Maintenance Mode
```bash
python ninjaone_api.py management maintenance DEVICE_ID --enable [--duration MINUTES]
python ninjaone_api.py management maintenance DEVICE_ID --disable
```

**Parameters:**
- `--enable`: Enable maintenance mode
- `--disable`: Disable maintenance mode
- `--duration`: Duration in minutes (default: 60)

### Approve Device
```bash
python ninjaone_api.py management approve DEVICE_ID
python ninjaone_api.py management reject DEVICE_ID
```

Approve or reject pending device registration.

### Update Device
```bash
python ninjaone_api.py management update DEVICE_ID [--display-name NAME] [--description DESC]
```

Update device metadata.

### Control Windows Update
```bash
python ninjaone_api.py management windows-update DEVICE_ID --action ACTION
```

**Parameters:**
- `--action`: SCAN, DOWNLOAD, INSTALL

### Syslog Configure
```bash
python ninjaone_api.py management syslog DEVICE_ID --enable --server SERVER --port PORT
python ninjaone_api.py management syslog DEVICE_ID --disable
```

Configure syslog forwarding.

## Action Responses

### Reboot Response
| Field | Type | Description |
|-------|------|-------------|
| `jobId` | string | Job tracking ID |
| `status` | string | PENDING, RUNNING, COMPLETED |
| `deviceId` | integer | Target device |

### Script Response
| Field | Type | Description |
|-------|------|-------------|
| `jobId` | string | Job tracking ID |
| `scriptId` | integer | Script executed |
| `status` | string | Execution status |
| `output` | string | Script output |
| `exitCode` | integer | Exit code |

### Patch Response
| Field | Type | Description |
|-------|------|-------------|
| `jobId` | string | Job tracking ID |
| `patchCount` | integer | Patches to apply |
| `status` | string | Job status |

## Common Workflows

### Emergency Patch
```bash
# Scan for available patches
python ninjaone_api.py management scan-patches 12345

# Wait for scan to complete, then check status
python ninjaone_api.py devices patches 12345 --status PENDING

# Apply patches with reboot
python ninjaone_api.py management apply-patches 12345 --reboot
```

### Service Troubleshooting
```bash
# Check service status
python ninjaone_api.py devices services 12345 --name "Spooler"

# Restart the service
python ninjaone_api.py management control-service 12345 --service-id "Spooler" --action RESTART

# Verify service is running
python ninjaone_api.py devices services 12345 --name "Spooler" --state RUNNING
```

### Scheduled Maintenance
```bash
# Enable maintenance mode
python ninjaone_api.py management maintenance 12345 --enable --duration 120

# Perform maintenance tasks
python ninjaone_api.py management apply-patches 12345 --reboot

# Disable maintenance mode (or wait for timeout)
python ninjaone_api.py management maintenance 12345 --disable
```

### Script Deployment
```bash
# List available scripts (via queries)
python ninjaone_api.py scripts list

# Run script on device
python ninjaone_api.py management run-script 12345 --script-id 999

# Check job status
python ninjaone_api.py jobs get JOB_ID
```

## Safety Considerations

- **Reboot**: Always provide a reason; consider maintenance windows
- **Patches**: Test patches in staging before production rollout
- **Scripts**: Validate scripts in NinjaOne before deployment
- **Services**: Critical services may affect system stability
- **Maintenance Mode**: Suppresses alerts during maintenance

## API Notes

- Management actions are asynchronous; use job ID to track status
- Some actions require specific NinjaOne permissions
- Actions are logged in device activity history
- Forced reboots may cause data loss; use with caution
