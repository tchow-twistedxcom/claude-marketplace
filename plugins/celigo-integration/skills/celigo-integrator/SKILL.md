---
name: celigo-integrator
description: "Execute Celigo operations via Python CLI. Use when managing integrations, flows, jobs, and errors programmatically."
license: MIT
version: 2.0.0
---

# Celigo Integrator CLI Skill

## Quick Start

Execute Celigo operations via Python CLI script located at:
```
plugins/celigo-integration/scripts/celigo_api.py
```

## Common Patterns

### Daily Health Check
```bash
# Check for failed jobs in last 24 hours
python3 scripts/celigo_api.py jobs list --status failed

# Get error summary for an integration
python3 scripts/celigo_api.py integrations errors <integration_id>

# List currently running jobs
python3 scripts/celigo_api.py jobs list --status running
```

### Monitor Integration Status
```bash
# List all integrations
python3 scripts/celigo_api.py integrations list

# Get flows for an integration
python3 scripts/celigo_api.py integrations flows <integration_id>

# Get latest job status for a flow
python3 scripts/celigo_api.py flows jobs-latest <flow_id>
```

### Run Flow Manually
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

### Troubleshoot Failed Jobs
```bash
# 1. Find failed jobs
python3 scripts/celigo_api.py jobs list --status failed --flow <flow_id>

# 2. Get job details
python3 scripts/celigo_api.py jobs get <job_id>

# 3. List import errors
python3 scripts/celigo_api.py errors list --flow <flow_id> --import <import_id>

# 4. Get retry data for a specific error
python3 scripts/celigo_api.py errors retry-data \
  --flow <flow_id> --import <import_id> --key <retry_data_key>

# 5. Retry failed records
python3 scripts/celigo_api.py errors retry \
  --flow <flow_id> --import <import_id> --keys key1,key2,key3

# 6. Or resolve errors (mark as handled)
python3 scripts/celigo_api.py errors resolve \
  --flow <flow_id> --import <import_id> --ids err1,err2
```

### Connection Management
```bash
# List all connections
python3 scripts/celigo_api.py connections list

# Test a connection
python3 scripts/celigo_api.py connections test <connection_id>

# Get connection dependencies (what uses this connection)
python3 scripts/celigo_api.py connections dependencies <connection_id>

# Get debug log for troubleshooting
python3 scripts/celigo_api.py connections debug-log <connection_id>
```

### Job Monitoring
```bash
# List jobs by status
python3 scripts/celigo_api.py jobs list --status running
python3 scripts/celigo_api.py jobs list --status completed
python3 scripts/celigo_api.py jobs list --status failed

# Filter by integration
python3 scripts/celigo_api.py jobs list --integration <integration_id>

# Filter by date range
python3 scripts/celigo_api.py jobs list \
  --since "2024-01-01T00:00:00.000Z" \
  --until "2024-01-31T23:59:59.999Z"

# Cancel a running job (flow type only)
python3 scripts/celigo_api.py jobs cancel <job_id>
```

### Error Assignment & Tagging
```bash
# Assign errors to user for review
python3 scripts/celigo_api.py errors assign \
  --flow <flow_id> --import <import_id> \
  --ids err1,err2 --email user@example.com

# Tag errors for categorization
python3 scripts/celigo_api.py errors tags \
  --flow <flow_id> --import <import_id> \
  --errors '[{"id":"err1","rdk":"key1"}]' --tag-ids tag1,tag2
```

### Lookup Cache Operations
```bash
# List lookup caches
python3 scripts/celigo_api.py caches list

# Get cache data
python3 scripts/celigo_api.py caches data <cache_id>

# Get specific keys
python3 scripts/celigo_api.py caches data <cache_id> --keys key1,key2

# Get keys with prefix
python3 scripts/celigo_api.py caches data <cache_id> --starts-with "ABC"
```

## CLI Reference

### Global Options
```
--env, -e     Environment (production/sandbox)
--format, -f  Output format (table/json)
```

### Resources & Actions

| Resource | Actions |
|----------|---------|
| integrations | list, get, flows, connections, exports, imports, users, template, dependencies, audit, errors |
| flows | list, get, run, template, dependencies, descendants, jobs-latest, last-export-datetime, audit |
| connections | list, get, test, debug-log, logs, dependencies |
| exports | list, get, audit, dependencies |
| imports | list, get, audit, dependencies |
| jobs | list, get, cancel |
| errors | list, resolved, retry-data, resolve, retry, assign, tags, integration-summary, integration-assign |
| caches | list, get, data |
| tags | list, get, create, update, delete |
| users | list, get |

### Output Formats

```bash
# Human-readable table (default)
python3 scripts/celigo_api.py integrations list

# JSON for scripting
python3 scripts/celigo_api.py integrations list --format json

# Pipe to jq for processing
python3 scripts/celigo_api.py flows get <id> --format json | jq '.name'
```

## Workflow Examples

### Workflow 1: Complete Error Investigation

```bash
# Step 1: Get integration error summary
python3 scripts/celigo_api.py integrations errors <integration_id>

# Step 2: Identify flow with errors (note _flowId from above)
python3 scripts/celigo_api.py flows get <flow_id>

# Step 3: Get flow descendants to find import ID
python3 scripts/celigo_api.py flows descendants <flow_id>

# Step 4: List errors for the import
python3 scripts/celigo_api.py errors list --flow <flow_id> --import <import_id>

# Step 5: Inspect failed record data
python3 scripts/celigo_api.py errors retry-data \
  --flow <flow_id> --import <import_id> --key <retry_data_key>

# Step 6: Fix data and retry (or resolve)
python3 scripts/celigo_api.py errors retry \
  --flow <flow_id> --import <import_id> --keys <keys>
```

### Workflow 2: Flow Execution & Monitoring

```bash
# Step 1: Run the flow
python3 scripts/celigo_api.py flows run <flow_id>
# Output: {"_jobId": "job123", ...}

# Step 2: Monitor job progress
python3 scripts/celigo_api.py jobs get <job_id>

# Step 3: Check for completion
python3 scripts/celigo_api.py flows jobs-latest <flow_id>

# Step 4: If errors, investigate
python3 scripts/celigo_api.py errors list --flow <flow_id> --import <import_id>
```

### Workflow 3: Connection Health Check

```bash
# Step 1: List all connections
python3 scripts/celigo_api.py connections list

# Step 2: Test each connection
python3 scripts/celigo_api.py connections test <connection_id>

# Step 3: If test fails, get debug info
python3 scripts/celigo_api.py connections debug-log <connection_id>

# Step 4: Check what's affected
python3 scripts/celigo_api.py connections dependencies <connection_id>
```

## Configuration

The CLI uses configuration from:
```
plugins/celigo-integration/config/celigo_config.json
```

Setup:
```bash
# Copy template
cp config/celigo_config.template.json config/celigo_config.json

# Edit with your API key
# Add to celigo_config.json:
# "environments": { "production": { "api_key": "YOUR_KEY", ... } }
```

## Reference Documentation

For detailed API documentation, see `references/` directory:
- api-overview.md, authentication.md, integrations.md, flows.md
- connections.md, exports.md, imports.md, jobs.md
- errors.md, lookup-caches.md, tags.md, users.md

## Error Sources

When filtering errors, use these source values:
- `internal` - Platform error
- `application` - Application-level error
- `connection` - Auth/connection error
- `mapping` - Field mapping error
- `lookup` - Lookup operation failed
- `transformation` - Data transformation error
- `pre_map_hook`, `post_map_hook` - Hook errors
