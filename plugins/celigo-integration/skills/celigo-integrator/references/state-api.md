# State API Reference

The State API provides persistent key-value storage for maintaining state between flow executions. Useful for tracking incremental sync positions, counters, and configuration values.

## Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get state | GET | `/state/{key}` |
| Set state | PUT | `/state/{key}` |
| Delete state | DELETE | `/state/{key}` |

## State Object

State values can be any JSON-serializable data:

```json
{
  "key": "customer_sync_position",
  "value": {
    "lastSyncId": "12345",
    "lastSyncDate": "2024-01-15T10:00:00.000Z",
    "recordsProcessed": 1500
  }
}
```

## Operations

### Get State

Retrieve the current value for a key:

```bash
curl -X GET "https://api.integrator.io/v1/state/customer_sync_position" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
{
  "lastSyncId": "12345",
  "lastSyncDate": "2024-01-15T10:00:00.000Z",
  "recordsProcessed": 1500
}
```

**If key doesn't exist:** Returns 404 or empty response

### Set State

Create or update a state value:

```bash
curl -X PUT "https://api.integrator.io/v1/state/customer_sync_position" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "lastSyncId": "12346",
    "lastSyncDate": "2024-01-15T11:00:00.000Z",
    "recordsProcessed": 1550
  }'
```

**Response:**
```json
{
  "success": true
}
```

### Delete State

Remove a state key:

```bash
curl -X DELETE "https://api.integrator.io/v1/state/customer_sync_position" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:** 204 No Content

## Key Naming Conventions

Use descriptive, namespaced keys:

```
# By integration
integration_abc123_last_sync

# By flow
flow_xyz789_cursor

# By resource type
customers_incremental_position
orders_daily_count

# By environment
prod_api_rate_limit_remaining
sandbox_test_counter
```

## Common Use Cases

### Incremental Sync Position

Track the last processed record for delta exports:

```python
# Get current position
current = api_get("/state/orders_last_id").json()
last_id = current.get('lastId', 0)

# Export records after last_id
orders = export_orders_since(last_id)

# Update position
if orders:
    api_put("/state/orders_last_id", {
        "lastId": orders[-1]['id'],
        "syncedAt": datetime.now().isoformat()
    })
```

### Daily Counters

Track records processed per day:

```python
today = datetime.now().strftime('%Y-%m-%d')
key = f"daily_count_{today}"

# Get or initialize counter
try:
    counter = api_get(f"/state/{key}").json()
except:
    counter = {"count": 0, "date": today}

# Increment
counter['count'] += len(processed_records)

# Save
api_put(f"/state/{key}", counter)
```

### Rate Limit Tracking

Monitor API rate limits:

```python
def update_rate_limit(remaining, reset_time):
    api_put("/state/api_rate_limit", {
        "remaining": remaining,
        "resetAt": reset_time,
        "updatedAt": datetime.now().isoformat()
    })

def check_rate_limit():
    state = api_get("/state/api_rate_limit").json()
    if state['remaining'] < 10:
        wait_until(state['resetAt'])
```

### Cursor-Based Pagination

Store pagination cursor for resumable exports:

```python
# Initialize or resume
try:
    state = api_get("/state/shopify_products_cursor").json()
    cursor = state.get('cursor')
except:
    cursor = None

# Fetch page
products, next_cursor = fetch_products(cursor)

# Save cursor for next run
api_put("/state/shopify_products_cursor", {
    "cursor": next_cursor,
    "lastFetchedAt": datetime.now().isoformat(),
    "pageCount": state.get('pageCount', 0) + 1
})
```

### Configuration Storage

Store dynamic configuration:

```python
# Save config
api_put("/state/integration_config", {
    "batchSize": 100,
    "retryAttempts": 3,
    "notifyOnError": True,
    "emailRecipients": ["admin@example.com"]
})

# Read config in flow
config = api_get("/state/integration_config").json()
batch_size = config.get('batchSize', 50)
```

### Error Tracking

Track error patterns:

```python
# Record error occurrence
errors = api_get("/state/error_log").json() or {"errors": []}

errors['errors'].append({
    "timestamp": datetime.now().isoformat(),
    "code": error_code,
    "message": error_message,
    "flowId": flow_id
})

# Keep last 100 errors
errors['errors'] = errors['errors'][-100:]

api_put("/state/error_log", errors)
```

## Using State in Scripts

Access state from within hook scripts:

```javascript
function preSavePage(options) {
  // Get state using built-in state functions
  const lastSync = options.state.get('last_sync_timestamp');

  // Filter to only new records
  const newRecords = options.data.filter(record =>
    new Date(record.modifiedAt) > new Date(lastSync)
  );

  // Update state for next run
  if (newRecords.length > 0) {
    const latestTimestamp = newRecords
      .map(r => r.modifiedAt)
      .sort()
      .pop();
    options.state.set('last_sync_timestamp', latestTimestamp);
  }

  return { data: newRecords, errors: options.errors };
}
```

## Error Handling

### Key Not Found
```json
{
  "errors": [{
    "code": "not_found",
    "message": "State key not found"
  }]
}
```

### Invalid Value
```json
{
  "errors": [{
    "code": "validation_error",
    "message": "Value must be JSON-serializable"
  }]
}
```

### Key Too Long
```json
{
  "errors": [{
    "code": "validation_error",
    "message": "Key exceeds maximum length of 256 characters"
  }]
}
```

## Best Practices

1. **Use namespaced keys** - Prevent collisions with prefixes
2. **Keep values small** - Avoid storing large datasets
3. **Include timestamps** - Track when state was last updated
4. **Handle missing keys** - Initialize defaults gracefully
5. **Clean up old state** - Delete unused keys periodically
6. **Use atomic updates** - Read-modify-write patterns for counters
