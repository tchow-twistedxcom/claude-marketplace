# Data Sync Patterns

Patterns for synchronizing data between systems using n8n.

## Sync Strategy Types

### Full Sync
```yaml
pattern: full_sync
description: "Replace all data with fresh copy"
when_to_use:
  - Initial data load
  - Small datasets (<1000 records)
  - Infrequent sync (daily/weekly)
  - No reliable change tracking

workflow:
  1. Schedule Trigger (daily)
  2. Fetch all source data
  3. Clear/archive destination
  4. Insert all records
  5. Log completion
```

### Incremental Sync
```yaml
pattern: incremental_sync
description: "Only sync changed records"
when_to_use:
  - Large datasets
  - Frequent sync needs
  - Source has timestamps
  - Performance critical

workflow:
  1. Schedule Trigger
  2. Get last sync timestamp
  3. Fetch records modified since
  4. Upsert to destination
  5. Update sync timestamp
```

### Delta Sync
```yaml
pattern: delta_sync
description: "Track and sync only differences"
when_to_use:
  - Source provides change events
  - Real-time sync requirements
  - Webhook-based sources

workflow:
  1. Webhook receives change event
  2. Parse change type (create/update/delete)
  3. Apply change to destination
  4. Acknowledge event
```

### Bidirectional Sync
```yaml
pattern: bidirectional_sync
description: "Changes flow both directions"
when_to_use:
  - Two-way data ownership
  - Collaborative systems
  - Master-master setup

challenges:
  - Conflict detection
  - Resolution strategy
  - Infinite loop prevention
```

## Change Detection

### Timestamp-Based
```javascript
// Get records modified since last sync
const lastSync = $node["Get Last Sync"].json.timestamp;
const now = new Date().toISOString();

// Query: WHERE updated_at > lastSync
return [{
  json: {
    query: `modified_after=${lastSync}`,
    syncStart: now
  }
}];
```

### Hash-Based
```javascript
// Compare content hashes
const crypto = require('crypto');

return items.map(item => {
  const hash = crypto
    .createHash('md5')
    .update(JSON.stringify(item.json))
    .digest('hex');

  return {
    json: {
      ...item.json,
      contentHash: hash
    }
  };
});

// Later: compare with stored hashes
```

### Version-Based
```javascript
// Track record versions
const sourceVersion = $json.version;
const storedVersion = $node["Get Stored"].json.version || 0;

if (sourceVersion > storedVersion) {
  return [{ json: { ...item.json, needsSync: true } }];
}

return []; // Skip unchanged
```

### Sequence-Based
```javascript
// For systems with sequence numbers
const lastProcessedSeq = $node["Get Cursor"].json.sequence || 0;

// Fetch: WHERE sequence > lastProcessedSeq ORDER BY sequence LIMIT 100
// After processing: store new highest sequence
```

## Pagination Patterns

### Offset Pagination
```javascript
// Loop with offset
const pageSize = 100;
let offset = 0;
let hasMore = true;

// In Loop node:
const url = `${baseUrl}?limit=${pageSize}&offset=${offset}`;
// After fetch: offset += pageSize; hasMore = results.length === pageSize;
```

### Cursor Pagination
```javascript
// Use cursor from previous response
const cursor = $node["Previous Page"].json.nextCursor || null;

return [{
  json: {
    url: cursor
      ? `${baseUrl}?cursor=${cursor}`
      : `${baseUrl}?limit=100`,
    hasMore: !!$json.nextCursor
  }
}];
```

### Page Token Pagination
```javascript
// Token-based (Google APIs style)
const pageToken = $json.nextPageToken;

if (!pageToken) {
  // End of data
  return [];
}

return [{
  json: {
    params: { pageToken }
  }
}];
```

## Batch Processing

### Split In Batches Node
```json
{
  "id": "batch-1",
  "name": "Split In Batches",
  "type": "n8n-nodes-base.splitInBatches",
  "typeVersion": 3,
  "position": [400, 300],
  "parameters": {
    "batchSize": 50,
    "options": {}
  }
}
```

### Manual Batching
```javascript
// Create batches manually
const batchSize = 50;
const items = $input.all();
const batches = [];

for (let i = 0; i < items.length; i += batchSize) {
  batches.push({
    json: {
      batch: items.slice(i, i + batchSize).map(item => item.json),
      batchIndex: Math.floor(i / batchSize),
      totalBatches: Math.ceil(items.length / batchSize)
    }
  });
}

return batches;
```

## Conflict Resolution

### Last Write Wins
```javascript
// Simple: most recent update wins
const sourceUpdated = new Date($json.source.updated_at);
const destUpdated = new Date($json.destination.updated_at);

if (sourceUpdated > destUpdated) {
  return [{ json: { action: 'update', data: $json.source } }];
}

return [{ json: { action: 'skip', reason: 'destination newer' } }];
```

### Source Priority
```yaml
strategy: source_priority
description: "Source system always wins"
implementation:
  - Always overwrite destination
  - Log conflicts for review
  - No merge logic needed
```

### Merge Strategy
```javascript
// Merge non-conflicting fields
const source = $json.source;
const dest = $json.destination;

const merged = {
  id: source.id,
  // Source wins for these
  name: source.name,
  email: source.email,
  // Destination wins for these
  customField: dest.customField,
  notes: dest.notes,
  // Merge arrays
  tags: [...new Set([...source.tags, ...dest.tags])],
  // Take latest for timestamp
  updated_at: source.updated_at > dest.updated_at
    ? source.updated_at
    : dest.updated_at
};

return [{ json: merged }];
```

### Manual Resolution Queue
```javascript
// Flag conflicts for human review
if (hasConflict(source, dest)) {
  return [{
    json: {
      action: 'queue_for_review',
      conflict: {
        recordId: source.id,
        source: source,
        destination: dest,
        detectedAt: new Date().toISOString()
      }
    }
  }];
}
```

## State Management

### Sync Cursor Storage
```yaml
approaches:
  workflow_variable:
    description: "Store in n8n workflow variables"
    limitation: "Lost if workflow recreated"

  database:
    description: "Store in dedicated sync state table"
    fields: [sync_name, last_cursor, last_run, status]

  file_based:
    description: "Store in local/remote file"
    format: JSON with cursor and metadata

  api_based:
    description: "Store via external API"
    use_case: "Distributed sync management"
```

### Sync State Schema
```javascript
// State object structure
const syncState = {
  syncId: 'orders-to-erp',
  lastSuccessfulRun: '2024-01-15T10:30:00Z',
  lastCursor: 'cursor_abc123',
  lastProcessedId: 12345,
  recordsProcessed: 1000,
  errors: [],
  status: 'completed'
};
```

## Upsert Patterns

### Database Upsert
```yaml
postgres:
  query: |
    INSERT INTO records (id, name, email, updated_at)
    VALUES ($1, $2, $3, NOW())
    ON CONFLICT (id)
    DO UPDATE SET
      name = EXCLUDED.name,
      email = EXCLUDED.email,
      updated_at = NOW()

mysql:
  query: |
    INSERT INTO records (id, name, email)
    VALUES (?, ?, ?)
    ON DUPLICATE KEY UPDATE
      name = VALUES(name),
      email = VALUES(email)
```

### API Upsert Logic
```javascript
// Check existence, then create or update
const id = $json.id;
const checkResult = $node["Check Exists"].json;

if (checkResult.exists) {
  return [{
    json: {
      action: 'update',
      method: 'PUT',
      url: `/api/records/${id}`,
      data: $json
    }
  }];
} else {
  return [{
    json: {
      action: 'create',
      method: 'POST',
      url: '/api/records',
      data: $json
    }
  }];
}
```

## Sync Monitoring

### Progress Tracking
```javascript
// Calculate and log progress
const processed = $json.processedCount;
const total = $json.totalCount;
const percent = ((processed / total) * 100).toFixed(1);

console.log(`Sync progress: ${processed}/${total} (${percent}%)`);

return [{
  json: {
    ...item.json,
    progress: {
      processed,
      total,
      percent: parseFloat(percent),
      estimatedRemaining: total - processed
    }
  }
}];
```

### Sync Summary
```javascript
// Generate sync report
return [{
  json: {
    syncId: $json.syncId,
    completedAt: new Date().toISOString(),
    duration: Date.now() - $json.startTime,
    stats: {
      total: $json.totalRecords,
      created: $json.createdCount,
      updated: $json.updatedCount,
      skipped: $json.skippedCount,
      errors: $json.errorCount
    },
    errors: $json.errors.slice(0, 10) // First 10 errors
  }
}];
```

## Anti-Patterns

```yaml
avoid:
  no_pagination:
    problem: "Loading all records at once"
    solution: "Always paginate large datasets"

  missing_state:
    problem: "No sync cursor tracking"
    solution: "Store and update sync state"

  no_idempotency:
    problem: "Duplicate records on re-run"
    solution: "Use upsert or check-before-insert"

  sync_deletes:
    problem: "Immediate hard deletes"
    solution: "Soft delete with grace period"

  no_monitoring:
    problem: "Silent sync failures"
    solution: "Log, alert, and report on sync status"
```

## Best Practices

```yaml
design:
  - Start with incremental sync if possible
  - Always implement pagination
  - Track sync state persistently
  - Handle duplicates gracefully

reliability:
  - Implement retry logic for failures
  - Use transactions where possible
  - Validate data before sync
  - Log all changes for audit

performance:
  - Batch API calls (50-100 records)
  - Use parallel processing carefully
  - Optimize database queries
  - Schedule during low-traffic periods

monitoring:
  - Track sync duration and record counts
  - Alert on sync failures
  - Monitor for sync delays
  - Review conflict resolution logs
```
