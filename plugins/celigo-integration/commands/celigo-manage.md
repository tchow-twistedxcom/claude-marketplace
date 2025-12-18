---
name: celigo-manage
description: Manage Celigo integrations, flows, and connections via CLI
---

# Celigo Integration Management

Execute Celigo integration platform operations using the Python CLI.

## CLI Location

```bash
# All commands run from the plugin directory
cd plugins/celigo-integration
python3 scripts/celigo_api.py <resource> <action> [options]
```

## Integration Management

### List Integrations
```bash
# List all integrations
python3 scripts/celigo_api.py integrations list

# JSON output for scripting
python3 scripts/celigo_api.py integrations list --format json
```

### Get Integration Details
```bash
# Get specific integration
python3 scripts/celigo_api.py integrations get <integration_id>
```

### Get Integration Resources
```bash
# List flows in integration
python3 scripts/celigo_api.py integrations flows <integration_id>

# List connections in integration
python3 scripts/celigo_api.py integrations connections <integration_id>

# List exports in integration
python3 scripts/celigo_api.py integrations exports <integration_id>

# List imports in integration
python3 scripts/celigo_api.py integrations imports <integration_id>

# Get integration dependencies
python3 scripts/celigo_api.py integrations dependencies <integration_id>

# Get integration audit log
python3 scripts/celigo_api.py integrations audit <integration_id>
```

## Flow Management

### List Flows
```bash
# List all flows
python3 scripts/celigo_api.py flows list

# Get flows for specific integration
python3 scripts/celigo_api.py integrations flows <integration_id>
```

### Get Flow Details
```bash
# Get single flow
python3 scripts/celigo_api.py flows get <flow_id>

# Get flow descendants (exports/imports)
python3 scripts/celigo_api.py flows descendants <flow_id>
```

### Run Flow
```bash
# Trigger full flow run
python3 scripts/celigo_api.py flows run <flow_id>

# Run specific exports only
python3 scripts/celigo_api.py flows run <flow_id> --export-ids exp1,exp2

# Run with date range (delta flows)
python3 scripts/celigo_api.py flows run <flow_id> \
  --start-date "2024-01-01T00:00:00.000Z" \
  --end-date "2024-01-31T23:59:59.999Z"
```

### Flow Status
```bash
# Get latest job for flow
python3 scripts/celigo_api.py flows jobs-latest <flow_id>

# Get last export datetime
python3 scripts/celigo_api.py flows last-export-datetime <flow_id>

# Get flow audit log
python3 scripts/celigo_api.py flows audit <flow_id>
```

## Connection Management

### List Connections
```bash
# List all connections
python3 scripts/celigo_api.py connections list
```

### Connection Operations
```bash
# Get connection details
python3 scripts/celigo_api.py connections get <connection_id>

# Test connection health
python3 scripts/celigo_api.py connections test <connection_id>

# Get connection debug log
python3 scripts/celigo_api.py connections debug-log <connection_id>

# Get connection logs
python3 scripts/celigo_api.py connections logs <connection_id>

# Get what uses this connection
python3 scripts/celigo_api.py connections dependencies <connection_id>
```

## Job Monitoring

### List Jobs
```bash
# List all jobs
python3 scripts/celigo_api.py jobs list

# Filter by status
python3 scripts/celigo_api.py jobs list --status running
python3 scripts/celigo_api.py jobs list --status completed
python3 scripts/celigo_api.py jobs list --status failed

# Filter by integration
python3 scripts/celigo_api.py jobs list --integration <integration_id>

# Filter by flow
python3 scripts/celigo_api.py jobs list --flow <flow_id>

# Filter by date range
python3 scripts/celigo_api.py jobs list \
  --since "2024-01-01T00:00:00.000Z" \
  --until "2024-01-31T23:59:59.999Z"

# Filter by type
python3 scripts/celigo_api.py jobs list --type flow
```

### Job Operations
```bash
# Get job details
python3 scripts/celigo_api.py jobs get <job_id>

# Cancel running job (flow type only)
python3 scripts/celigo_api.py jobs cancel <job_id>
```

## Error Management

### List Errors
```bash
# List import errors
python3 scripts/celigo_api.py errors list --flow <flow_id> --import <import_id>

# List export errors
python3 scripts/celigo_api.py errors list --flow <flow_id> --export <export_id>

# Filter by date
python3 scripts/celigo_api.py errors list --flow <flow_id> --import <import_id> \
  --since "2024-01-01T00:00:00.000Z"

# Filter by source
python3 scripts/celigo_api.py errors list --flow <flow_id> --import <import_id> \
  --source mapping
```

### Error Investigation
```bash
# Get retry data for error
python3 scripts/celigo_api.py errors retry-data \
  --flow <flow_id> --import <import_id> --key <retry_data_key>

# List resolved errors
python3 scripts/celigo_api.py errors resolved --flow <flow_id> --import <import_id>
```

### Error Resolution
```bash
# Retry errors
python3 scripts/celigo_api.py errors retry \
  --flow <flow_id> --import <import_id> --keys key1,key2,key3

# Resolve errors (mark as handled)
python3 scripts/celigo_api.py errors resolve \
  --flow <flow_id> --import <import_id> --ids err1,err2
```

### Error Assignment & Tagging
```bash
# Assign errors to user
python3 scripts/celigo_api.py errors assign \
  --flow <flow_id> --import <import_id> \
  --ids err1,err2 --email user@example.com

# Tag errors
python3 scripts/celigo_api.py errors tags \
  --flow <flow_id> --import <import_id> \
  --errors '[{"id":"err1","rdk":"key1"}]' --tag-ids tag1,tag2
```

### Integration Error Summary
```bash
# Get error summary for integration
python3 scripts/celigo_api.py integrations errors <integration_id>

# Assign integration errors
python3 scripts/celigo_api.py errors integration-assign \
  --integration <integration_id> --ids err1,err2 --email user@example.com
```

## Lookup Cache Operations

```bash
# List all caches
python3 scripts/celigo_api.py caches list

# Get cache metadata
python3 scripts/celigo_api.py caches get <cache_id>

# Get cache data
python3 scripts/celigo_api.py caches data <cache_id>

# Get specific keys
python3 scripts/celigo_api.py caches data <cache_id> --keys key1,key2

# Get keys with prefix
python3 scripts/celigo_api.py caches data <cache_id> --starts-with "ABC"

# Paginate cache data
python3 scripts/celigo_api.py caches data <cache_id> --page-size 100
```

## Tag Management

```bash
# List tags
python3 scripts/celigo_api.py tags list

# Get tag
python3 scripts/celigo_api.py tags get <tag_id>

# Create tag
python3 scripts/celigo_api.py tags create "my-tag-name"

# Update tag
python3 scripts/celigo_api.py tags update <tag_id> --name "new-name"

# Delete tag
python3 scripts/celigo_api.py tags delete <tag_id>
```

## User Management

```bash
# List users
python3 scripts/celigo_api.py users list

# Get user details
python3 scripts/celigo_api.py users get <user_id>
```

## Common Workflows

### Daily Health Check
```bash
# 1. Check for failed jobs in last 24 hours
python3 scripts/celigo_api.py jobs list --status failed

# 2. Get error summary for integration
python3 scripts/celigo_api.py integrations errors <integration_id>

# 3. List currently running jobs
python3 scripts/celigo_api.py jobs list --status running

# 4. Test critical connections
python3 scripts/celigo_api.py connections test <connection_id>
```

### Troubleshoot Failed Jobs
```bash
# 1. Find failed jobs
python3 scripts/celigo_api.py jobs list --status failed --flow <flow_id>

# 2. Get job details
python3 scripts/celigo_api.py jobs get <job_id>

# 3. Get flow descendants to find import ID
python3 scripts/celigo_api.py flows descendants <flow_id>

# 4. List import errors
python3 scripts/celigo_api.py errors list --flow <flow_id> --import <import_id>

# 5. Get retry data for failed record
python3 scripts/celigo_api.py errors retry-data \
  --flow <flow_id> --import <import_id> --key <retry_data_key>

# 6. Fix data and retry
python3 scripts/celigo_api.py errors retry \
  --flow <flow_id> --import <import_id> --keys <keys>

# 7. Or resolve errors
python3 scripts/celigo_api.py errors resolve \
  --flow <flow_id> --import <import_id> --ids <error_ids>
```

### Connection Health Check
```bash
# 1. List all connections
python3 scripts/celigo_api.py connections list

# 2. Test connection
python3 scripts/celigo_api.py connections test <connection_id>

# 3. If failed, get debug log
python3 scripts/celigo_api.py connections debug-log <connection_id>

# 4. Check what's affected
python3 scripts/celigo_api.py connections dependencies <connection_id>
```

### Flow Execution & Monitoring
```bash
# 1. Run flow
python3 scripts/celigo_api.py flows run <flow_id>
# Output: {"_jobId": "job123", ...}

# 2. Monitor job progress
python3 scripts/celigo_api.py jobs get <job_id>

# 3. Check for completion
python3 scripts/celigo_api.py flows jobs-latest <flow_id>

# 4. If errors, investigate
python3 scripts/celigo_api.py errors list --flow <flow_id> --import <import_id>
```

## Error Codes Reference

| Code | Description | Solution |
|------|-------------|----------|
| 401 | Authentication failed | Check API token |
| 403 | Permission denied | Verify token scope |
| 404 | Resource not found | Check integration/flow ID |
| 429 | Rate limit exceeded | Reduce API calls |
| 500 | Server error | Retry after delay |

## Error Sources

When filtering errors, use these source values:
- `internal` - Platform error
- `application` - Application-level error
- `connection` - Auth/connection error
- `mapping` - Field mapping error
- `lookup` - Lookup operation failed
- `transformation` - Data transformation error
- `pre_map_hook`, `post_map_hook` - Hook errors

## Security Notes

- Always use config file for tokens (never hardcode)
- Add `config/celigo_config.json` to `.gitignore`
- Rotate API tokens regularly
- Use role-based access in Celigo
- Monitor API usage for anomalies
