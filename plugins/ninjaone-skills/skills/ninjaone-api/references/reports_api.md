# Reports API Reference

Pre-built reports for common IT management scenarios.

## Endpoints

### Hardware Report
```bash
python ninjaone_api.py reports hardware [OPTIONS]
```

Generate a hardware utilization report analyzing storage and memory across devices.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--org-id` | int | - | Filter by organization ID |
| `--org-name` | string | - | Filter by organization name |
| `--filter`, `--df` | string | - | Device filter expression |
| `--storage-warning` | int | 80 | Storage warning threshold (%) |
| `--storage-critical` | int | 90 | Storage critical threshold (%) |
| `--memory-warning` | int | 16 | Memory warning threshold (GB) |
| `--memory-critical` | int | 8 | Memory critical threshold (GB) |

**Examples:**
```bash
# Hardware report for specific organization
python ninjaone_api.py reports hardware --org-name "Twisted X"

# Hardware report with custom thresholds
python ninjaone_api.py reports hardware --org-id 2 --storage-critical 95 --memory-critical 4

# JSON output for further processing
python ninjaone_api.py -f json reports hardware --org-name "Acme Corp" > hardware_report.json

# Filter to only Windows servers
python ninjaone_api.py reports hardware --filter "class = WINDOWS_SERVER"
```

## Report Output

### Summary Section
| Field | Description |
|-------|-------------|
| `organization` | Organization name or ID |
| `total_devices` | Total devices analyzed |
| `storage_critical_count` | Devices with critical storage issues |
| `storage_warning_count` | Devices with storage warnings |
| `memory_critical_count` | Devices with critical memory issues |
| `memory_warning_count` | Devices with memory warnings |
| `thresholds` | Applied threshold values |

### Storage Issues
Lists devices with storage utilization above thresholds:
| Field | Description |
|-------|-------------|
| `device_id` | NinjaOne device ID |
| `device_name` | Device hostname |
| `drive` | Drive letter or mount point |
| `capacity_gb` | Total capacity in GB |
| `free_gb` | Free space in GB |
| `used_pct` | Utilization percentage |

### Memory Issues
Lists devices with RAM below thresholds:
| Field | Description |
|-------|-------------|
| `device_id` | NinjaOne device ID |
| `device_name` | Device hostname |
| `ram_gb` | Total RAM in GB |
| `manufacturer` | System manufacturer |
| `model` | System model |

## Common Workflows

### Monthly Hardware Assessment
```bash
# Generate hardware report
python ninjaone_api.py reports hardware --org-name "My Company" -f json > monthly_hw_report.json

# View critical issues only
python ninjaone_api.py reports hardware --org-name "My Company" | jq '.storage_issues.critical, .memory_issues.critical'
```

### Replacement Planning
```bash
# Find devices needing upgrades (low memory + high storage)
python ninjaone_api.py reports hardware --memory-critical 8 --storage-critical 85 -f json
```

### Multi-Organization Audit
```bash
# Run reports for multiple orgs
for org in "Org A" "Org B" "Org C"; do
  python ninjaone_api.py reports hardware --org-name "$org" -f json > "hw_report_${org// /_}.json"
done
```

## Threshold Guidelines

### Storage Thresholds
| Level | Default | Recommendation |
|-------|---------|----------------|
| Warning | 80% | Review within 30 days |
| Critical | 90% | Immediate attention needed |

### Memory Thresholds
| Level | Default | Recommendation |
|-------|---------|----------------|
| Warning | <16 GB | Consider upgrade for power users |
| Critical | <8 GB | Upgrade required for modern workloads |

## API Notes

- Report aggregates data from `queries/volumes` and `queries/computer-systems` endpoints
- Organization name lookup is case-insensitive and supports partial matching
- Results are sorted by severity (most critical first)
- Use `-f json` for programmatic consumption
