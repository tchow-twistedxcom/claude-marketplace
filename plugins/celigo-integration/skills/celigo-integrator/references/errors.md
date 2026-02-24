# Errors API Reference

Errors represent failed records from flow executions. The API supports listing, resolving, retrying, and managing errors.

## Endpoints

### Flow Step Errors (exports and imports use same path pattern)
| Operation | Method | Endpoint |
|-----------|--------|----------|
| List errors | GET | `/flows/{flowId}/{expOrImpId}/errors` |
| List resolved | GET | `/flows/{flowId}/{expOrImpId}/resolved` |
| Get retry data | GET | `/flows/{flowId}/{expOrImpId}/errors/{retryDataKey}` |
| Resolve errors | PUT | `/flows/{flowId}/{expOrImpId}/resolved` |
| Delete resolved | DELETE | `/flows/{flowId}/{expOrImpId}/resolved` |
| Retry errors | POST | `/flows/{flowId}/{expOrImpId}/retry` |
| Update retry data | PUT | `/flows/{flowId}/{expOrImpId}/{retryKey}/data` |
| Assign errors | POST | `/flows/{flowId}/{expOrImpId}/errors/assign` |
| Tag errors | POST | `/flows/{flowId}/{expOrImpId}/errors/tags` |
| View request/response | GET | `/flows/{flowId}/{ppId}/requests/{requestKey}` |

### Integration Errors
| Operation | Method | Endpoint |
|-----------|--------|----------|
| Error summary | GET | `/integrations/{id}/errors` |
| Assign errors | POST | `/integrations/{id}/errors/assign` |

**Note:** The `{expOrImpId}` path segment accepts either an export ID or import ID directly -- do not include `/exports/` or `/imports/` prefix segments.

## Error Object

```json
{
  "_id": "err123",
  "code": "FIELD_VALIDATION_ERROR",
  "message": "Required field 'email' is missing",
  "source": "mapping",
  "occurredAt": "2024-01-15T10:00:00.000Z",
  "retryDataKey": "rdk123",
  "traceKey": "trace123",
  "data": {
    "name": "John Doe",
    "phone": "555-1234"
  },
  "tags": ["validation", "missing-field"],
  "assignedTo": "user@example.com"
}
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `_id` | string | Error unique ID |
| `code` | string | Error code |
| `message` | string | Error description |
| `source` | string | Where error occurred |
| `occurredAt` | string | When error happened |
| `retryDataKey` | string | Key for retry data |
| `traceKey` | string | Trace/log reference |
| `data` | object | Record that failed |
| `tags` | array | Applied tags |
| `assignedTo` | string | Assigned user email |

## Error Sources

| Source | Description |
|--------|-------------|
| `internal` | Platform error |
| `application` | Application-level error |
| `connection` | Authentication/connection error |
| `resource` | Resource access error |
| `transformation` | Data transformation error |
| `mapping` | Field mapping error |
| `lookup` | Lookup operation failed |
| `input_filter` | Input filter rejection |
| `output_filter` | Output filter rejection |
| `pre_map_hook` | Pre-map hook error |
| `post_map_hook` | Post-map hook error |
| `post_submit_hook` | Post-submit hook error |

## Operations

### List Errors

```bash
curl -X GET "https://api.integrator.io/v1/flows/{flowId}/{expOrImpId}/errors" \
  -H "Authorization: Bearer $API_KEY"
```

**Query Parameters:**
```
?occurredAt_gte=2024-01-01T00:00:00.000Z    # After date
?occurredAt_lte=2024-01-31T23:59:59.999Z    # Before date
?source=mapping                              # By source
```

### Get Retry Data

Retrieve the actual record data for an error:

```bash
curl -X GET "https://api.integrator.io/v1/flows/{flowId}/{expOrImpId}/errors/{retryDataKey}" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "555-1234"
}
```

### Resolve Errors

Mark errors as resolved (moves to resolved list):

```bash
curl -X PUT "https://api.integrator.io/v1/flows/{flowId}/{expOrImpId}/resolved" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "errorIds": ["err123", "err456", "err789"]
  }'
```

**Note:** The method is `PUT` and the path ends with `/resolved` (not `/errors/resolve`).

### Retry Errors

Reprocess failed records:

```bash
curl -X POST "https://api.integrator.io/v1/flows/{flowId}/{expOrImpId}/retry" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "retryDataKeys": ["rdk123", "rdk456"]
  }'
```

**Note:** Use `retryDataKey` values from error objects, not error IDs.

### Assign Errors

Assign errors to a user for review:

```bash
curl -X POST "https://api.integrator.io/v1/flows/{flowId}/{expOrImpId}/errors/assign" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "errorIds": ["err123", "err456"],
    "email": "user@example.com"
  }'
```

### Tag Errors

Apply tags to errors:

```bash
curl -X POST "https://api.integrator.io/v1/flows/{flowId}/{expOrImpId}/errors/tags" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "errors": [
      {"id": "err123", "rdk": "rdk123"},
      {"id": "err456", "rdk": "rdk456"}
    ],
    "tagIds": ["tag1", "tag2"]
  }'
```

**Note:** This REPLACES all existing tags on the errors.

### List Resolved Errors

```bash
curl -X GET "https://api.integrator.io/v1/flows/{flowId}/{expOrImpId}/resolved" \
  -H "Authorization: Bearer $API_KEY"
```

### Delete Resolved Errors

```bash
curl -X DELETE "https://api.integrator.io/v1/flows/{flowId}/{expOrImpId}/resolved" \
  -H "Authorization: Bearer $API_KEY"
```

### Get Integration Error Summary

Get error counts by flow:

```bash
curl -X GET "https://api.integrator.io/v1/integrations/{integrationId}/errors" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
[
  {"_flowId": "flow1", "numError": 5},
  {"_flowId": "flow2", "numError": 12}
]
```

## Error Handling Workflow

### 1. Monitor Errors

```python
def check_for_errors(integration_id):
    # Get error summary
    summary = api_get(f"/integrations/{integration_id}/errors").json()

    for flow_errors in summary:
        if flow_errors['numError'] > 0:
            print(f"Flow {flow_errors['_flowId']}: {flow_errors['numError']} errors")

    return summary
```

### 2. Investigate Errors

```python
def investigate_errors(flow_id, import_id):
    errors = api_get(f"/flows/{flow_id}/{import_id}/errors").json()

    for error in errors.get('errors', []):
        print(f"Error: {error['message']}")
        print(f"Source: {error['source']}")

        # Get failed record data
        if error.get('retryDataKey'):
            data = api_get(
                f"/flows/{flow_id}/{import_id}/errors/{error['retryDataKey']}"
            ).json()
            print(f"Data: {data}")
```

### 3. Fix and Retry

```python
def retry_all_errors(flow_id, import_id):
    errors = api_get(f"/flows/{flow_id}/{import_id}/errors").json()

    retry_keys = [
        e['retryDataKey']
        for e in errors.get('errors', [])
        if e.get('retryDataKey')
    ]

    if retry_keys:
        api_post(
            f"/flows/{flow_id}/{import_id}/retry",
            {"retryDataKeys": retry_keys}
        )
```

### 4. Resolve Remaining

```python
def resolve_errors(flow_id, import_id, error_ids):
    api_put(
        f"/flows/{flow_id}/{import_id}/resolved",
        {"errorIds": error_ids}
    )
```

## Common Error Patterns

### Missing Required Field
```json
{
  "code": "FIELD_VALIDATION_ERROR",
  "message": "Required field 'email' is missing",
  "source": "mapping"
}
```

### Lookup Failed
```json
{
  "code": "LOOKUP_NOT_FOUND",
  "message": "No matching record found for lookup",
  "source": "lookup"
}
```

### Connection Timeout
```json
{
  "code": "CONNECTION_TIMEOUT",
  "message": "Request timed out after 30 seconds",
  "source": "connection"
}
```

### Duplicate Record
```json
{
  "code": "DUPLICATE_RECORD",
  "message": "Record with this ID already exists",
  "source": "application"
}
```

## Best Practices

1. **Monitor regularly** - Check error counts daily
2. **Categorize errors** - Use tags for organization
3. **Assign ownership** - Route errors to appropriate team members
4. **Fix root causes** - Update mappings/filters before retry
5. **Bulk operations** - Retry/resolve errors in batches
6. **Document patterns** - Track recurring error types
