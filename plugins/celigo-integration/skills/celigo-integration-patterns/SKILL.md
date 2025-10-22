---
name: celigo-integration-patterns
description: "Best practices and patterns for building Celigo integrations. Use when designing data integrations, ETL workflows, or connecting business applications via Celigo."
license: MIT
---

# Celigo Integration Patterns

## When to Use

This skill activates when:
- Designing Celigo integrations
- Building ETL/data sync workflows
- Connecting SaaS applications
- Troubleshooting integration issues
- Optimizing integration performance

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
