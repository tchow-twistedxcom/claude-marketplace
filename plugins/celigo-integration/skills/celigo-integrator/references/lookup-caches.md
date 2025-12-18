# Lookup Caches API Reference

Lookup caches store key-value reference data for use in integrations. Common uses include product catalogs, customer mappings, and configuration values.

## Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List all | GET | `/lookupcaches` |
| Get metadata | GET | `/lookupcaches/{id}` |
| Create | POST | `/lookupcaches` |
| Update | PUT | `/lookupcaches/{id}` |
| Delete | DELETE | `/lookupcaches/{id}` |
| Get data | GET | `/lookupcaches/{id}/data` |
| Update data | PUT | `/lookupcaches/{id}/data` |
| Delete data | DELETE | `/lookupcaches/{id}/data` |

## Lookup Cache Object

```json
{
  "_id": "cache123",
  "name": "Product SKU Mapping",
  "description": "Maps external SKUs to internal product IDs",
  "size": 1500,
  "createdAt": "2024-01-01T00:00:00.000Z",
  "lastModified": "2024-01-15T12:00:00.000Z"
}
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `_id` | string | Unique identifier |
| `name` | string | Display name (required) |
| `description` | string | Optional description |
| `size` | number | Number of entries |
| `createdAt` | string | Creation timestamp |
| `lastModified` | string | Last update timestamp |

## Cache Data Format

Data is stored as key-value pairs:

```json
{
  "data": [
    {"key": "SKU-001", "value": {"productId": "123", "name": "Widget A"}},
    {"key": "SKU-002", "value": {"productId": "456", "name": "Widget B"}},
    {"key": "SKU-003", "value": {"productId": "789", "name": "Widget C"}}
  ]
}
```

## Operations

### List All Caches

```bash
curl -X GET "https://api.integrator.io/v1/lookupcaches" \
  -H "Authorization: Bearer $API_KEY"
```

### Get Cache Metadata

```bash
curl -X GET "https://api.integrator.io/v1/lookupcaches/{cache_id}" \
  -H "Authorization: Bearer $API_KEY"
```

### Create Cache

```bash
curl -X POST "https://api.integrator.io/v1/lookupcaches" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer ID Mapping",
    "description": "Maps external customer IDs to internal IDs"
  }'
```

### Update Cache Metadata

```bash
curl -X PUT "https://api.integrator.io/v1/lookupcaches/{cache_id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "description": "Updated description"
  }'
```

### Delete Cache

```bash
curl -X DELETE "https://api.integrator.io/v1/lookupcaches/{cache_id}" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:** 204 No Content

### Get Cache Data

```bash
curl -X GET "https://api.integrator.io/v1/lookupcaches/{cache_id}/data" \
  -H "Authorization: Bearer $API_KEY"
```

**Query Parameters:**

```
# Get specific keys
?keys=SKU-001,SKU-002,SKU-003

# Filter by prefix
?starts_with=SKU-

# Pagination
?page_size=100
?start_after_key=SKU-099
```

**Response:**
```json
{
  "data": [
    {"key": "SKU-001", "value": {"productId": "123"}},
    {"key": "SKU-002", "value": {"productId": "456"}}
  ],
  "nextPageURL": "/lookupcaches/cache123/data?start_after_key=SKU-002",
  "success": true
}
```

### Update Cache Data

Add or update entries:

```bash
curl -X PUT "https://api.integrator.io/v1/lookupcaches/{cache_id}/data" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"key": "SKU-001", "value": {"productId": "123", "name": "Widget A"}},
      {"key": "SKU-002", "value": {"productId": "456", "name": "Widget B"}}
    ]
  }'
```

### Delete Cache Data

Delete specific keys:

```bash
curl -X DELETE "https://api.integrator.io/v1/lookupcaches/{cache_id}/data" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "keys": ["SKU-001", "SKU-002"]
  }'
```

Delete all data:

```bash
curl -X DELETE "https://api.integrator.io/v1/lookupcaches/{cache_id}/data" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "deleteAll": true
  }'
```

## Pagination

Data retrieval returns max 1000 entries per request.

### Manual Pagination

```python
def get_all_cache_data(cache_id):
    all_data = []
    start_after_key = None

    while True:
        params = "page_size=100"
        if start_after_key:
            params += f"&start_after_key={start_after_key}"

        response = api_get(f"/lookupcaches/{cache_id}/data?{params}")
        result = response.json()

        data = result.get('data', [])
        all_data.extend(data)

        if not result.get('nextPageURL') or not data:
            break

        start_after_key = data[-1]['key']

    return all_data
```

## Common Use Cases

### Product Mapping

```python
# Create product mapping cache
cache = api_post("/lookupcaches", {
    "name": "Product SKU to ID",
    "description": "Maps external SKUs to internal product IDs"
}).json()

# Add mappings
api_put(f"/lookupcaches/{cache['_id']}/data", {
    "data": [
        {"key": "EXT-SKU-001", "value": {"internalId": "PROD-123"}},
        {"key": "EXT-SKU-002", "value": {"internalId": "PROD-456"}}
    ]
})
```

### Customer Cross-Reference

```python
# Store customer IDs from multiple systems
api_put(f"/lookupcaches/{cache_id}/data", {
    "data": [
        {
            "key": "CUST-001",
            "value": {
                "salesforceId": "003xxx",
                "netsuiteId": "123",
                "hubspotId": "456"
            }
        }
    ]
})
```

### Configuration Values

```python
# Store environment-specific config
api_put(f"/lookupcaches/{cache_id}/data", {
    "data": [
        {"key": "api_endpoint", "value": {"url": "https://api.example.com"}},
        {"key": "batch_size", "value": {"size": 100}},
        {"key": "retry_count", "value": {"count": 3}}
    ]
})
```

### Bulk Data Load

```python
def bulk_load_cache(cache_id, data_dict):
    """Load large dataset in batches."""
    batch_size = 500
    items = [{"key": k, "value": v} for k, v in data_dict.items()]

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        api_put(f"/lookupcaches/{cache_id}/data", {"data": batch})
        print(f"Loaded {min(i + batch_size, len(items))} of {len(items)}")
```

## Using in Flows

### Lookup in Import Mapping

```json
{
  "mapping": {
    "lists": [
      {
        "generate": "internalProductId",
        "lookupName": "Product SKU to ID",
        "lookupKey": "{{externalSku}}"
      }
    ]
  }
}
```

### Lookup in Export Filter

```json
{
  "filter": {
    "type": "expression",
    "expression": {
      "rules": [
        ["exists", ["lookup", "Product SKU to ID", ["extract", "sku"]]]
      ]
    }
  }
}
```

## Error Handling

### Cache Not Found
```json
{
  "errors": [{
    "code": "not_found",
    "message": "Lookup cache not found"
  }]
}
```

### Key Not Found
```json
{
  "errors": [{
    "code": "key_not_found",
    "message": "Key 'SKU-999' not found in cache"
  }]
}
```

### Invalid Data Format
```json
{
  "errors": [{
    "code": "validation_error",
    "message": "Data must be array of key-value objects"
  }]
}
```

## Best Practices

1. **Use meaningful keys** - Include prefixes for organization
2. **Keep values lightweight** - Store only needed fields
3. **Batch updates** - Load data in chunks of 500-1000
4. **Refresh regularly** - Set up sync flows for dynamic data
5. **Monitor size** - Large caches impact performance
6. **Use prefix queries** - Filter with `starts_with` for efficiency
