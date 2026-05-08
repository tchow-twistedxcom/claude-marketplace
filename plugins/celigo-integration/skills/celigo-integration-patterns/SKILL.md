---
name: celigo-integration-patterns
description: "Best practices and patterns for building Celigo integrations. Use when designing data integrations, ETL workflows, connecting business applications, managing EDI partners, setting up MCP servers/Tools/OPAs, or running the EDI cross-system audit."
license: MIT
version: 4.0.0
---

# Celigo Integration Patterns

## When to Use

This skill activates when:
- Designing Celigo integrations
- Building ETL/data sync workflows
- Connecting SaaS applications
- Troubleshooting integration issues
- Optimizing integration performance
- Managing EDI profiles, trading partner connectors, or file definitions
- Setting up Tools, builder-mode APIs, or MCP Servers
- Managing OPAs (On-Premise Agents)
- Running or interpreting EDI cross-system audit results

## CLI Architecture (v4.0.0)

The Celigo integration plugin provides two complementary layers:

**Core layer** (`scripts/celigo_api.py`) — pure Python REST wrapper for the full Celigo API. No external dependencies beyond `requests`. Covers ~170 operations across 27 resource types. This is the canonical tool for all Celigo operations.

**CLI bridge** (`scripts/celigo_cli_wrapper.py`) — thin subprocess wrapper for `@celigo/celigo-cli` (official npm). Only used when the official CLI provides a capability not yet in the Python layer. Requires Node 22+ and `npm install -g @celigo/celigo-cli`.

**EDI audit** (`scripts/edi_audit.py`) — standalone cross-system reconciliation script. Calls both Celigo API and the NetSuite gateway to surface mismatches between Celigo flow results and NS EDI History records.

For all day-to-day operations, use `celigo_api.py` directly.

## Integration Architecture Patterns

### 1. Bi-Directional Sync Pattern

**Use Case**: Keep two systems in sync (e.g., Salesforce ↔ NetSuite)

**Pattern:**
```
System A ←→ Celigo ←→ System B

Components:
├── Connection A (source/destination)
├── Connection B (source/destination)
├── Export Flow (A → B)
├── Import Flow (B → A)
├── Conflict Resolution Logic
└── Error Handling
```

**Best Practices:**
- Use unique identifiers for record matching
- Implement conflict resolution (last-write-wins or manual review)
- Add timestamp tracking for change detection
- Enable error notifications
- Schedule flows to avoid simultaneous runs

### 2. Hub-and-Spoke Pattern

**Use Case**: Central system distributing data to multiple endpoints

**Pattern:**
```
        System A
           ↑
    Celigo (Hub)
      ↙  ↓  ↘
  Sys B  C   D

Components:
├── Central Source Connection
├── Multiple Destination Connections
├── Data Transformation Flow
├── Distribution Flows (one per spoke)
└── Aggregation Error Handling
```

**Best Practices:**
- Centralize data transformation logic
- Use lookup tables for mapping
- Batch data for efficiency
- Implement retry logic per spoke
- Monitor each spoke independently

### 3. Chain/Pipeline Pattern

**Use Case**: Sequential data processing through multiple steps

**Pattern:**
```
Source → Transform 1 → Transform 2 → Destination

Components:
├── Initial Export Flow
├── Transformation Flows (chained)
├── Final Import Flow
└── Checkpoint/Resume Logic
```

**Best Practices:**
- Use intermediate storage (Celigo lookup caches)
- Implement idempotent transformations
- Add checkpoints for long pipelines
- Enable partial failure recovery
- Log transformation steps

## Data Transformation Patterns

### Field Mapping Pattern

```javascript
// Simple field mapping
{
  "source_field": "customer.email",
  "destination_field": "contact.email_address",
  "transform": "lowercase"
}

// Conditional mapping
{
  "source_field": "order.status",
  "destination_field": "sales_order.state",
  "mapping": {
    "pending": "draft",
    "confirmed": "approved",
    "shipped": "fulfilled"
  }
}

// Computed field
{
  "destination_field": "full_name",
  "formula": "{{first_name}} {{last_name}}"
}
```

### Lookup Pattern

**Use Case**: Enrich data with reference information

```javascript
// Lookup customer by email
{
  "lookup": {
    "connection": "salesforce",
    "object": "Contact",
    "key_field": "Email",
    "key_value": "{{customer.email}}",
    "return_fields": ["Id", "AccountId", "Phone"]
  }
}
```

**Best Practices:**
- Cache frequent lookups
- Handle missing lookups gracefully
- Use batch lookups when possible
- Set lookup timeouts
- Monitor lookup performance

### Aggregation Pattern

**Use Case**: Combine multiple records into summary

```javascript
// Sum order totals by customer
{
  "group_by": "customer_id",
  "aggregations": [
    {
      "field": "order_total",
      "function": "sum",
      "alias": "total_orders"
    },
    {
      "field": "order_id",
      "function": "count",
      "alias": "order_count"
    }
  ]
}
```

## Error Handling Patterns

### Retry with Backoff

```javascript
{
  "error_handling": {
    "strategy": "retry",
    "max_attempts": 3,
    "backoff": "exponential",
    "backoff_base": 60  // seconds
  }
}
```

**Backoff Schedule:**
- Attempt 1: Immediate
- Attempt 2: Wait 60s
- Attempt 3: Wait 120s
- Attempt 4: Fail and log

### Dead Letter Queue Pattern

```javascript
{
  "error_handling": {
    "strategy": "dlq",
    "dlq_flow": "error_processing_flow",
    "notifications": ["admin@company.com"]
  }
}
```

**Process:**
1. Record fails processing
2. Send to dead letter queue
3. Notify administrators
4. Manual review and retry
5. Log for reporting

### Circuit Breaker Pattern

```javascript
{
  "error_handling": {
    "strategy": "circuit_breaker",
    "failure_threshold": 10,
    "timeout": 300,  // seconds
    "half_open_requests": 3
  }
}
```

**States:**
- **Closed**: Normal operation
- **Open**: Stop processing after threshold
- **Half-Open**: Test with limited requests

## Performance Optimization

### Batch Processing

```javascript
{
  "batch_config": {
    "size": 100,  // records per batch
    "parallel": true,
    "max_parallel": 5
  }
}
```

**Guidelines:**
- **Small batches (10-50)**: Real-time, low latency
- **Medium batches (50-200)**: Balanced throughput
- **Large batches (200-1000)**: High volume, scheduled

### Delta Sync Pattern

Only sync changed records:

```javascript
{
  "delta_config": {
    "field": "modified_date",
    "since": "{{last_run_timestamp}}",
    "full_sync_schedule": "weekly"
  }
}
```

**Best Practices:**
- Track last sync timestamp
- Use indexed timestamp fields
- Schedule periodic full syncs
- Handle timezone differences
- Account for clock skew

### Pagination Strategy

```javascript
{
  "pagination": {
    "type": "offset",
    "page_size": 500,
    "max_pages": 100
  }
}

// Alternative: cursor-based
{
  "pagination": {
    "type": "cursor",
    "cursor_field": "id",
    "page_size": 500
  }
}
```

## Monitoring & Alerting Patterns

### Health Check Flow

```javascript
{
  "schedule": "*/15 * * * *",  // Every 15 minutes
  "checks": [
    "test_connections",
    "check_job_failures",
    "validate_data_quality"
  ],
  "alert_on_failure": true
}
```

### Metrics Tracking

Key metrics to monitor:
- **Success Rate**: % of successful job runs
- **Throughput**: Records processed per hour
- **Latency**: Time from source update to destination
- **Error Rate**: Errors per 1000 records
- **Data Quality**: Validation failures

### Alert Thresholds

```javascript
{
  "alerts": {
    "failure_rate": {
      "threshold": 5,  // %
      "window": 3600,  // seconds
      "recipients": ["ops@company.com"]
    },
    "latency": {
      "threshold": 300,  // seconds
      "recipients": ["admin@company.com"]
    }
  }
}
```

## Security Patterns

### Token Management

```javascript
{
  "authentication": {
    "type": "oauth2",
    "token_refresh": "automatic",
    "token_storage": "encrypted",
    "rotation_schedule": "90d"
  }
}
```

### Data Encryption

```javascript
{
  "security": {
    "encrypt_in_transit": true,
    "encrypt_at_rest": true,
    "pii_fields": ["email", "phone", "ssn"],
    "masking": "partial"  // Show last 4 digits only
  }
}
```

### Audit Logging

```javascript
{
  "audit": {
    "log_level": "full",
    "retention": "365d",
    "fields": [
      "user",
      "action",
      "timestamp",
      "source_system",
      "destination_system",
      "records_affected"
    ]
  }
}
```

## Common Integration Scenarios

### Salesforce ↔ NetSuite Sync

**Components:**
- Salesforce Connection (OAuth)
- NetSuite Connection (Token-based)
- Customer Export (SF → NS)
- Customer Import (NS → SF)
- Order Export (SF → NS)
- Lookup: Customer matching by email
- Error handling: Duplicate detection

### E-commerce → ERP Integration

**Components:**
- Shopify Connection (API key)
- SAP Connection (OData)
- Order Export (Shopify → SAP)
- Inventory Import (SAP → Shopify)
- Product Sync (SAP → Shopify)
- Real-time webhook triggers
- Stock level monitoring

### CRM → Marketing Automation

**Components:**
- HubSpot Connection
- Marketo Connection
- Lead Export (HS → Marketo)
- Campaign Response Import (Marketo → HS)
- Contact enrichment via lookup
- Duplicate prevention logic
- Score synchronization

## Testing Strategies

### Test Environments

1. **Development**: Initial build and testing
2. **Staging**: Pre-production validation
3. **Production**: Live operations

### Test Cases

**Connection Testing:**
- [ ] Authentication succeeds
- [ ] API permissions verified
- [ ] Rate limits respected
- [ ] Timeout handling works

**Data Testing:**
- [ ] Sample data processes correctly
- [ ] Edge cases handled (nulls, duplicates)
- [ ] Large datasets perform well
- [ ] Data validation rules work

**Error Testing:**
- [ ] Connection failures handled
- [ ] Bad data rejected appropriately
- [ ] Retry logic functions
- [ ] Notifications sent on errors

## Page Processor Pipeline Patterns

### Pipeline Field Persistence Rules

Understanding which data persists through the Page Processor (PP) pipeline is critical for multi-PP flows.

**Three persistence layers:**

```
┌─────────────────────────────────────────────────┐
│ Layer 1: Export-stage fields (preSavePage)       │
│   ✅ PERSISTS through ALL PPs                    │
│   Set once, available everywhere downstream      │
├─────────────────────────────────────────────────┤
│ Layer 2: postResponseMap / responseMapping       │
│   ✅ PERSISTS — ADDS fields to pipeline record   │
│   Each PP can enrich the record for downstream   │
├─────────────────────────────────────────────────┤
│ Layer 3: preMap hook output                      │
│   ❌ DOES NOT PERSIST — consumed by current PP   │
│   Only the current import sees this data         │
└─────────────────────────────────────────────────┘
```

**Key rules:**
- **Export preSavePage output** → foundational record, persists through all PPs
- **postResponseMap additions** → persist on pipeline record for downstream PPs
- **responseMapping additions** → persist on pipeline record for downstream PPs
- **preMap output** → consumed ONLY by the current PP's import, NOT on pipeline
- **Module-level vars** → persist across records in same job, but NOT shared between preMap and postResponseMap (separate scopes)
- **Returning `{}` from preMap** → skips record for current import only; record continues through subsequent PPs

### Cross-PP Data Flow Pattern

**Use Case**: Data computed at one PP needs to be available at a later PP

**❌ Wrong approach** — setting data in a PP's preMap:
```javascript
// PP3 preMap — this data is consumed by PP3's import only
function preMap(options) {
  var triggerRec = {};
  triggerRec.computedData = JSON.stringify(myData);  // ❌ NOT on pipeline
  return [{ data: triggerRec }];
}
// PP4 preMap — computedData is NOT available here
```

**✅ Correct approach** — setting data at the export stage:
```javascript
// Export preSavePage — persists through ALL PPs
function preSavePage(options) {
  records.push({
    isTrigger: true,
    computedData: JSON.stringify(myData)  // ✅ Available at PP0–PP4
  });
  return { data: records, errors: options.errors, abort: false };
}
```

**✅ Also correct** — adding data via postResponseMap:
```javascript
// PP0 postResponseMap — adds field that persists to PP1, PP2, etc.
function captureResponse(options) {
  var data = options.data || options.postResponseMapData || [];
  var result = [];
  for (var i = 0; i < data.length; i++) {
    var newRec = {};
    // Copy existing fields + add new ones
    var source = data[i].data || data[i];
    for (var k in source) newRec[k] = source[k];
    newRec.enrichedField = JSON.stringify(options.responseData[i].data);  // ✅ Persists
    result.push(data[i].data !== undefined ? { data: newRec } : newRec);
  }
  return result;
}
```

### Dynamic Button Generation Pattern

**Use Case**: Generate interactive Slack buttons for any flow with errors, without static configuration

**Pattern:**
1. **Export preSavePage** sets `flowMap` (flowId → flowName) on trigger record
2. **PP3 preMap** (AI Agent) consumes `liveErrors` but pipeline retains `flowMap`
3. **PP4 preMap** (Slack) reads `flowMap` from pipeline, matches flow names in AI text
4. **Button value**: `flowId|actionType` — handler discovers `expOrImpIds` dynamically

```javascript
// block_kit_builder.js — dynamic button generation
var flowMap = {};
if (rec.flowMap) {
  try { flowMap = JSON.parse(rec.flowMap); } catch (e) {}
}
// Sort by name length descending to avoid substring conflicts
var entries = Object.keys(flowMap).map(function(fid) {
  return { flowId: fid, flowName: flowMap[fid] };
}).sort(function(a, b) { return b.flowName.length - a.flowName.length; });

// Match flow names in AI text → generate buttons
for (var fe = 0; fe < entries.length; fe++) {
  if (paragraph.indexOf(entries[fe].flowName) !== -1) {
    buttons.push({
      type: 'button',
      value: entries[fe].flowId + '|resolve',  // Handler looks up expOrImpIds
      style: 'primary'
    });
  }
}
```

### AI Agent Import Specifics

- **postResponseMap**: `options.data` is `null` for AI Agent imports. Use `options.postResponseMapData` instead.
- **Response mapping**: AI Agent returns `_text` field. Map via `responseMapping.fields: [{extract: "_text", generate: "aiSummary"}]`.
- **preMap return `{}`**: Skips record for AI processing, but record continues through pipeline to subsequent PPs.

**See also**: [Pipeline Field Persistence Solution Doc](../../docs/solutions/integration-issues/pipeline-field-persistence-premap-vs-export-CeligoIntegration-20260224.md)

## New Resource Families (v4.0.0)

### Tools

Custom Celigo Tools are reusable callable units (HTTP, script, or connector-based).

```bash
python3 scripts/celigo_api.py tools list
python3 scripts/celigo_api.py tools get <id>
python3 scripts/celigo_api.py tools invoke <id> --data '{"input": "value"}'
python3 scripts/celigo_api.py tools dependencies <id>
```

See `docs/new-resources/tools.md` for payload shape.

### Builder-Mode APIs

Builder APIs expose integrations as API endpoints via Celigo's API builder.

```bash
python3 scripts/celigo_api.py apis list
python3 scripts/celigo_api.py apis deploy <id>
python3 scripts/celigo_api.py apis versions <id>
```

See `docs/new-resources/apis.md`.

### MCP Servers

Celigo-hosted MCP server configurations (not to be confused with Claude Code's MCP).

```bash
python3 scripts/celigo_api.py mcp-servers list
python3 scripts/celigo_api.py mcp-servers start <id>
python3 scripts/celigo_api.py mcp-servers stop <id>
python3 scripts/celigo_api.py mcp-servers status <id>
```

See `docs/new-resources/mcp-servers.md`.

### Async Helpers

Three-phase async pattern: submit → poll → result. Use for long-running operations.

```bash
python3 scripts/celigo_api.py async submit <helper_id> --data '{"key": "value"}'
python3 scripts/celigo_api.py async poll <token_id>
python3 scripts/celigo_api.py async result <token_id>
python3 scripts/celigo_api.py async wait <token_id>   # blocks until done
```

See `docs/new-resources/async-helpers.md`.

### Notifications

Email/Slack notifications for integration events.

```bash
python3 scripts/celigo_api.py notifications list
python3 scripts/celigo_api.py notifications create --data '<json>'
```

See `docs/new-resources/notifications.md`.

### OPA (On-Premise Agents)

OPAs bridge Celigo cloud to private/on-premise data sources.

```bash
python3 scripts/celigo_api.py opa list
python3 scripts/celigo_api.py opa status <id>   # connected / disconnected / unknown
python3 scripts/celigo_api.py opa restart <id>  # triggers reconnect
```

See `docs/new-resources/opa.md`.

### EDI Profiles

X12 and EDIFACT interchange envelope configs (ISA/GS for X12, UNB/UNG for EDIFACT).

**Critical constraint**: `fileType` is immutable after creation. The CLI enforces this client-side.

```bash
python3 scripts/celigo_api.py edi create --data '{"name": "...", "fileType": "x12", ...}'
python3 scripts/celigo_api.py edi update <id> --data '{"isa06": "NEW_ID"}'  # fileType omitted
python3 scripts/celigo_api.py edi dependencies <id>   # check before deleting
```

See `docs/new-resources/edi-profiles.md`.

### Trading Partner Connectors

B2B onboarding templates bundling connection, export, import, and EDI profile.

```bash
python3 scripts/celigo_api.py trading-partners list
python3 scripts/celigo_api.py trading-partners create --data '<json>'
python3 scripts/celigo_api.py trading-partners update <id> --data '<partial-json>'
```

Note: Trading Partner Connectors do not support delete via API.

See `docs/new-resources/trading-partner-connectors.md`.

### File Definitions (EDI Formats)

X12 and EDIFACT file definitions require `documentType` and `globalId` in addition to `format`.

```bash
python3 scripts/celigo_api.py filedefinitions create \
  --data '{"name": "850 PO", "format": "x12", "documentType": "850", "globalId": "004010850"}'
python3 scripts/celigo_api.py filedefinitions create --schema-version 2 --data '<json>'
python3 scripts/celigo_api.py filedefinitions dependencies <id>
```

See `docs/new-resources/file-definitions-edi.md`.

### EDI Cross-System Audit

Reconciles Celigo flow results against NetSuite EDI History records.

**What it checks:**
- Inbound: Every Celigo success has a corresponding NS EDI record (status=2). 850s additionally verify an SO was created (`custrecord_twx_edi_history_transaction IS NOT NULL`).
- Outbound: Every NS EDI record has a corresponding Celigo success. Also flags NS errors (status=6).

**Three result buckets:**
1. `celigo_success_ns_missing` — Celigo reports success but no NS record found
2. `ns_sent_celigo_missing` — NS has the record but Celigo job is missing/failed
3. `ns_status_error` — NS record exists but status = error (6)

```bash
# Standard 24-hour audit
python3 scripts/edi_audit.py --since 24h

# Weekly audit for specific partner
python3 scripts/edi_audit.py --since 7d --partner "ACME" --direction inbound

# CI mode — exit 1 if any mismatches
python3 scripts/edi_audit.py --since 24h --exit-nonzero-on-mismatch
```

## Troubleshooting Guide

### Common Issues

**Integration Not Running**
1. Check connection health
2. Verify API credentials
3. Review flow schedule
4. Check error logs
5. Test with manual trigger

**Data Not Syncing**
1. Verify field mappings
2. Check data transformations
3. Review filter conditions
4. Validate lookup configurations
5. Check destination permissions

**Performance Degradation**
1. Review batch sizes
2. Check API rate limits
3. Analyze transformation complexity
4. Monitor connection latency
5. Optimize lookup queries

### Debug Workflow

1. **Identify**: Check job logs and error messages
2. **Isolate**: Test individual components
3. **Analyze**: Review data samples and mappings
4. **Fix**: Apply correction (mapping, connection, logic)
5. **Verify**: Rerun with test data
6. **Monitor**: Watch for recurring issues
