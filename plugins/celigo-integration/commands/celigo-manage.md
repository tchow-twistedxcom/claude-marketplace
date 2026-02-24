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

### Create Flow
```bash
# Create flow with convenience flags
python3 scripts/celigo_api.py flows create \
  --name "My New Flow" \
  --integration <integration_id> \
  --disabled true

# Create flow from JSON file
python3 scripts/celigo_api.py flows create --file flow_definition.json

# Create flow with inline JSON
python3 scripts/celigo_api.py flows create \
  --data '{"name": "New Flow", "_integrationId": "int123", "disabled": true}'
```

### Update Flow
```bash
# Rename flow
python3 scripts/celigo_api.py flows update <flow_id> --name "Updated Name"

# Enable/disable flow
python3 scripts/celigo_api.py flows update <flow_id> --disabled false
python3 scripts/celigo_api.py flows update <flow_id> --disabled true

# Update with inline JSON (complex changes)
python3 scripts/celigo_api.py flows update <flow_id> \
  --data '{"_runNextFlowIds": ["next_flow_id"]}'

# Update from JSON file
python3 scripts/celigo_api.py flows update <flow_id> --file flow_updates.json
```

### Delete Flow
```bash
python3 scripts/celigo_api.py flows delete <flow_id>
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

## Integration CRUD

```bash
# Create integration
python3 scripts/celigo_api.py integrations create --name "My Integration" --data '{"sandbox": false}'

# Update integration
python3 scripts/celigo_api.py integrations update <id> --name "New Name"

# Delete integration
python3 scripts/celigo_api.py integrations delete <id>

# Register connections to integration
python3 scripts/celigo_api.py integrations register-connections <id> --data '{"_connectionIds": ["conn1"]}'
```

## Clone Operations

```bash
# Clone a flow
python3 scripts/celigo_api.py flows clone <flow_id>

# Clone an export
python3 scripts/celigo_api.py exports clone <export_id>

# Clone an import
python3 scripts/celigo_api.py imports clone <import_id>
```

## PATCH Operations (Partial Updates)

```bash
# Partial update with JSON Patch (RFC 6902)
python3 scripts/celigo_api.py flows patch <flow_id> \
  --data '[{"op": "replace", "path": "/name", "value": "New Name"}]'

python3 scripts/celigo_api.py exports patch <export_id> \
  --data '[{"op": "replace", "path": "/disabled", "value": true}]'

python3 scripts/celigo_api.py connections patch <connection_id> \
  --data '[{"op": "replace", "path": "/name", "value": "Updated"}]'
```

## Replace Connection

```bash
# Replace connection in flow/export/import
python3 scripts/celigo_api.py flows replace-connection <flow_id> \
  --data '{"oldConnectionId": "old_id", "newConnectionId": "new_id"}'
```

## Invoke (Standalone Execution)

```bash
# Invoke an export standalone
python3 scripts/celigo_api.py exports invoke <export_id>

# Invoke an import standalone
python3 scripts/celigo_api.py imports invoke <import_id>
```

## Connection Advanced Operations

```bash
# Update connection
python3 scripts/celigo_api.py connections update <id> --data '{"name": "Updated"}'

# Delete connection
python3 scripts/celigo_api.py connections delete <id>

# Get audit log
python3 scripts/celigo_api.py connections audit <id>

# Get OAuth2 info
python3 scripts/celigo_api.py connections oauth2 <id>

# Virtual export (test without saving)
python3 scripts/celigo_api.py connections virtual-export <id> --data '{"export": {...}}'

# Virtual import
python3 scripts/celigo_api.py connections virtual-import <id> --data '{"import": {...}}'
```

## State Management

```bash
# List all state keys
python3 scripts/celigo_api.py state list

# Get/set state
python3 scripts/celigo_api.py state get "sync_cursor"
python3 scripts/celigo_api.py state set "sync_cursor" --data '{"lastId": "12345"}'
python3 scripts/celigo_api.py state delete "old_key"

# Import-scoped state
python3 scripts/celigo_api.py state list-scoped --import <import_id>
python3 scripts/celigo_api.py state get-scoped --import <import_id> "counter"
python3 scripts/celigo_api.py state set-scoped --import <import_id> "counter" --data '{"count": 100}'
```

## Lookup Cache Data Operations

```bash
# Upsert data (POST /data)
python3 scripts/celigo_api.py caches data-update <cache_id> \
  --data '{"data": [{"key": "SKU-001", "value": {"productId": "123"}}]}'

# Delete specific keys
python3 scripts/celigo_api.py caches data-delete <cache_id> --keys key1,key2

# Purge all data
python3 scripts/celigo_api.py caches data-purge <cache_id>

# Delete cache
python3 scripts/celigo_api.py caches delete <cache_id>
```

## User Management (Full)

```bash
# Invite user (POST /invite)
python3 scripts/celigo_api.py users invite --email user@example.com --role manage

# Bulk invite
python3 scripts/celigo_api.py users invite-multiple --data '{"emails": ["a@b.com", "c@d.com"], "accessLevel": "monitor"}'

# Reinvite
python3 scripts/celigo_api.py users reinvite --email user@example.com

# Update permissions
python3 scripts/celigo_api.py users update <share_id> --role administrator

# Disable user
python3 scripts/celigo_api.py users disable <share_id>

# Remove user
python3 scripts/celigo_api.py users delete <share_id>
```

## Script Logs

```bash
# Get execution logs
python3 scripts/celigo_api.py scripts logs <script_id>
```

## File Definitions

```bash
python3 scripts/celigo_api.py filedefinitions list
python3 scripts/celigo_api.py filedefinitions get <id>
python3 scripts/celigo_api.py filedefinitions create --file definition.json
python3 scripts/celigo_api.py filedefinitions update <id> --data '{"name": "Updated"}'
python3 scripts/celigo_api.py filedefinitions delete <id>
```

## Recycle Bin

```bash
# List recycled resources
python3 scripts/celigo_api.py recyclebin list
python3 scripts/celigo_api.py recyclebin list --resource-type flows

# Restore or permanently delete
python3 scripts/celigo_api.py recyclebin restore flows <id>
python3 scripts/celigo_api.py recyclebin delete flows <id>
```

## Account Audit Log

```bash
python3 scripts/celigo_api.py audit list
python3 scripts/celigo_api.py audit list --resource-type flows --since "2024-01-01T00:00:00Z"
```

## iClients (OAuth2 Apps)

```bash
python3 scripts/celigo_api.py iclients list
python3 scripts/celigo_api.py iclients get <id>
python3 scripts/celigo_api.py iclients create --file client.json
python3 scripts/celigo_api.py iclients delete <id>
python3 scripts/celigo_api.py iclients dependencies <id>
```

## Connectors & Licenses

```bash
# Connector CRUD
python3 scripts/celigo_api.py connectors list
python3 scripts/celigo_api.py connectors get <id>
python3 scripts/celigo_api.py connectors install-base <id>
python3 scripts/celigo_api.py connectors publish-update <id> --file update.json

# License management
python3 scripts/celigo_api.py connectors list-licenses <id>
python3 scripts/celigo_api.py connectors create-license <id> --file license.json
python3 scripts/celigo_api.py connectors delete-license <connector_id> <license_id>
```

## Data Processors

```bash
python3 scripts/celigo_api.py processors parse-xml --file xml_config.json
python3 scripts/celigo_api.py processors parse-csv --file csv_config.json
python3 scripts/celigo_api.py processors generate-csv --data '{"data": [...], "options": {...}}'
```

## Templates

```bash
python3 scripts/celigo_api.py templates list
python3 scripts/celigo_api.py templates update <id> --file template.json
```

## EDI/B2B

```bash
# EDI profile management
python3 scripts/celigo_api.py edi list
python3 scripts/celigo_api.py edi get <id>
python3 scripts/celigo_api.py edi create --file profile.json

# Transaction operations
python3 scripts/celigo_api.py edi query-transactions --data '{"filter": {...}}'
python3 scripts/celigo_api.py edi fa-details <transaction_id>
```

## Advanced Error Operations

```bash
# Delete resolved errors
python3 scripts/celigo_api.py errors delete-resolved --flow <flow_id> --import <import_id>

# Update retry data before retrying
python3 scripts/celigo_api.py errors update-retry-data \
  --flow <flow_id> --import <import_id> --key <retry_key> \
  --data '{"email": "fixed@example.com"}'

# View request/response details
python3 scripts/celigo_api.py errors view-request \
  --flow <flow_id> --import <import_id> --key <request_key>
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
