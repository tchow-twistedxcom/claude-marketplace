---
name: celigo-integrator
description: "Execute Celigo operations via Python CLI. Full REST API coverage: integrations (incl. ILM revisions/snapshots), flows, connections, exports (incl. distributed/RT), imports, scripts, jobs, errors, caches, state, EDI profiles, EDI transactions, EDI audit, trading partner connectors, file definitions, access tokens, parsers/generators, Tools, builder-mode APIs, MCP Servers, async helpers, notifications, OPA management (incl. token rotation), and cross-system EDI reconciliation against NetSuite."
license: MIT
version: 4.1.0
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
| integrations | list, get, create, update, delete, flows, connections, exports, imports, users, template, download-template, dependencies, audit, errors, register-connections |
| flows | list, get, create, update, delete, run, clone, patch, replace-connection, template, dependencies, descendants, jobs-latest, last-export-datetime, audit |
| connections | list, get, create, update, delete, patch, test, debug-log, logs, dependencies, audit, oauth2, ping-virtual, virtual-export, virtual-import |
| exports | list, get, create, update, delete, clone, invoke, patch, replace-connection, audit, dependencies |
| imports | list, get, create, update, delete, clone, invoke, patch, replace-connection, audit, dependencies |
| scripts | list, get, create, update, delete, logs |
| jobs | list, get, cancel |
| errors | list, resolved, retry-data, resolve, retry, assign, tags, delete-resolved, update-retry-data, view-request, integration-summary, integration-assign |
| caches | list, get, delete, data, data-update, data-delete, data-purge |
| tags | list, get, create, update, delete |
| users | list, get, update, delete, disable, invite, invite-multiple, reinvite, sso-update |
| state | list, get, set, delete, list-scoped, get-scoped, set-scoped |
| filedefinitions | list, get, create, update, delete, dependencies |
| recyclebin | list, get, restore, delete |
| audit | list |
| iclients | list, get, create, update, patch, delete, dependencies |
| connectors | list, get, create, update, delete, install-base, publish-update, list-licenses, create-license, get-license, update-license, delete-license |
| processors | parse-xml, parse-csv, generate-csv, generate-structured, parse-structured |
| templates | list, update |
| edi | list, get, create, update, patch, delete, dependencies, update-transactions, update-transaction, download-transaction, query-transactions, fa-details |
| tools | list, get, create, update, delete, invoke, dependencies |
| builder-apis | list, get, create, update, delete, deploy, versions |
| mcp-servers | list, get, create, update, delete, start, stop, status |
| async | submit, poll, result, wait |
| notifications | list, get, create, update, delete |
| opa | list, get, create, update, delete, status, restart |
| trading-partners | list, get, create, update |

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

### Workflow 4: State Management

```bash
# List all state keys
python3 scripts/celigo_api.py state list

# Get/set state values
python3 scripts/celigo_api.py state get "sync_cursor" --format json
python3 scripts/celigo_api.py state set "sync_cursor" --data '{"lastId": "12345"}'

# Import-scoped state
python3 scripts/celigo_api.py state get-scoped --import <import_id> "counter"
python3 scripts/celigo_api.py state set-scoped --import <import_id> "counter" --data '{"count": 100}'
```

### Workflow 5: Clone and PATCH

```bash
# Clone a flow
python3 scripts/celigo_api.py flows clone <flow_id>

# Partial update with JSON Patch (RFC 6902)
python3 scripts/celigo_api.py flows patch <flow_id> \
  --data '[{"op": "replace", "path": "/name", "value": "Updated Name"}]'

# Replace connection in a flow
python3 scripts/celigo_api.py flows replace-connection <flow_id> \
  --data '{"oldConnectionId": "old_id", "newConnectionId": "new_id"}'
```

### Workflow 6: Lookup Cache Data Management

```bash
# Upsert cache data
python3 scripts/celigo_api.py caches data-update <cache_id> \
  --data '{"data": [{"key": "SKU-001", "value": {"productId": "123"}}]}'

# Delete specific keys
python3 scripts/celigo_api.py caches data-delete <cache_id> --keys SKU-001,SKU-002

# Purge all data
python3 scripts/celigo_api.py caches data-purge <cache_id>
```

### Workflow 7: User Management

```bash
# Invite a user
python3 scripts/celigo_api.py users invite --email user@example.com --role manage

# Disable a user
python3 scripts/celigo_api.py users disable <share_id>

# Reinvite
python3 scripts/celigo_api.py users reinvite --email user@example.com
```

### Workflow 8: EDI Cross-System Audit

```bash
# Audit last 24 hours (all partners, both directions)
python3 scripts/edi_audit.py --since 24h

# Audit specific date range, inbound only
python3 scripts/edi_audit.py \
  --since "2024-01-01T00:00:00Z" \
  --until "2024-01-31T23:59:59Z" \
  --direction inbound

# Filter to one partner, exit non-zero if mismatches found (useful in CI)
python3 scripts/edi_audit.py --since 24h --partner "ACME" --exit-nonzero-on-mismatch

# JSON output only (no summary table)
python3 scripts/edi_audit.py --since 7d --json-only | jq '.summary'
```

**Or use the slash command:**
```bash
/celigo-edi-audit
```

### Workflow 9: OPA (On-Premise Agent) Management

```bash
# List all OPAs
python3 scripts/celigo_api.py opa list

# Check if an OPA is connected
python3 scripts/celigo_api.py opa status <opa_id>

# Restart a disconnected OPA
python3 scripts/celigo_api.py opa restart <opa_id>
```

### Workflow 10: Tools & MCP Servers

```bash
# List custom Tools
python3 scripts/celigo_api.py tools list

# Invoke a tool
python3 scripts/celigo_api.py tools invoke <tool_id> --data '{"param": "value"}'

# List MCP server configs
python3 scripts/celigo_api.py mcp-servers list

# Start/stop an MCP server
python3 scripts/celigo_api.py mcp-servers start <mcp_id>
python3 scripts/celigo_api.py mcp-servers status <mcp_id>

# Submit async helper job and wait for result
python3 scripts/celigo_api.py async submit <helper_id> --data '{"input": "..."}'
python3 scripts/celigo_api.py async wait <token_id>   # polls until done
```

### Workflow 11: Trading Partner & EDI Profile Setup

```bash
# Create EDI profile (X12)
python3 scripts/celigo_api.py edi create --data '{
  "name": "ACME X12 Prod",
  "fileType": "x12",
  "isa06": "ACMECORP",
  "isa08": "PARTNERCODE",
  "gs02": "ACMECORP"
}'

# Create file definition (850)
python3 scripts/celigo_api.py filedefinitions create \
  --data '{"name": "850 Purchase Order", "format": "x12", "documentType": "850", "globalId": "004010850"}'

# Create trading partner connector
python3 scripts/celigo_api.py trading-partners create --data '{
  "name": "ACME B2B Connector",
  "supportedBy": [
    {"type": "ediProfile", "_id": "<profile_id>"},
    {"type": "connection",  "_id": "<connection_id>"},
    {"type": "export",      "_id": "<export_id>"},
    {"type": "import",      "_id": "<import_id>"}
  ]
}'

# Check EDI profile dependencies before deleting
python3 scripts/celigo_api.py edi dependencies <profile_id>
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
- state-api.md, file-definitions.md, templates.md

For new resource families (v4.0.0), see `docs/new-resources/`:
- tools.md, apis.md, mcp-servers.md, async-helpers.md
- notifications.md, opa.md, edi-profiles.md
- trading-partner-connectors.md, file-definitions-edi.md

## Error Sources

When filtering errors, use these source values:
- `internal` - Platform error
- `application` - Application-level error
- `connection` - Auth/connection error
- `mapping` - Field mapping error
- `lookup` - Lookup operation failed
- `transformation` - Data transformation error
- `pre_map_hook`, `post_map_hook` - Hook errors
