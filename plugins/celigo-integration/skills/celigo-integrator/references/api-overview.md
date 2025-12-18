# Celigo API Overview

## Base URL

```
https://api.integrator.io/v1
```

For EU region accounts:
```
https://api.eu.integrator.io/v1
```

## Authentication

All API requests require Bearer token authentication:

```http
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
Accept: application/json
```

## Request Format

### GET Requests
```bash
curl -X GET "https://api.integrator.io/v1/{resource}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Accept: application/json"
```

### POST/PUT Requests
```bash
curl -X POST "https://api.integrator.io/v1/{resource}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"field": "value"}'
```

### DELETE Requests
```bash
curl -X DELETE "https://api.integrator.io/v1/{resource}/{id}" \
  -H "Authorization: Bearer $API_KEY"
```

## Response Format

### Success Response
```json
{
  "_id": "abc123",
  "name": "Resource Name",
  "createdAt": "2024-01-01T00:00:00.000Z",
  "lastModified": "2024-01-01T00:00:00.000Z"
}
```

### List Response
```json
[
  {"_id": "abc123", "name": "Resource 1"},
  {"_id": "def456", "name": "Resource 2"}
]
```

### Error Response
```json
{
  "errors": [
    {
      "code": "validation_error",
      "message": "Name is required",
      "field": "name"
    }
  ]
}
```

## Common Query Parameters

### Pagination
```
?limit=100      # Max records per page (default varies)
?offset=0       # Skip N records
```

### Filtering
```
?_integrationId=abc123           # Filter by integration
?_connectionId=def456            # Filter by connection
?status=completed                # Filter by status
?createdAt_gte=2024-01-01        # Created after date
?createdAt_lte=2024-12-31        # Created before date
```

### Sorting
```
?sort=name        # Sort ascending by name
?sort=-createdAt  # Sort descending by date (- prefix)
```

## Resource Hierarchy

```
Account
├── Integrations
│   ├── Flows
│   │   ├── Exports (Page Generators)
│   │   │   └── Errors
│   │   └── Imports (Page Processors)
│   │       └── Errors
│   ├── Connections
│   └── Scripts
├── Lookup Caches
├── File Definitions
├── Templates
└── Users/Shares
```

## HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created |
| 204 | No Content | Delete successful (no body) |
| 400 | Bad Request | Invalid request body |
| 401 | Unauthorized | Invalid/missing API key |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource conflict (duplicate) |
| 422 | Unprocessable | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Server Error | Internal error (retry) |

## Rate Limiting

Celigo enforces rate limits per account. When rate limited:
- Response code: 429
- Retry-After header indicates wait time
- Implement exponential backoff

```python
import time

def api_call_with_backoff(func, max_retries=5):
    for attempt in range(max_retries):
        response = func()
        if response.status_code == 429:
            wait = 2 ** attempt * 60  # 60, 120, 240, 480s
            time.sleep(wait)
            continue
        return response
    raise Exception("Rate limit exceeded after retries")
```

## Common Patterns

### Get All with Pagination
```python
def get_all_resources(resource_type):
    results = []
    offset = 0
    limit = 100

    while True:
        response = api_get(f"/{resource_type}?limit={limit}&offset={offset}")
        data = response.json()

        if not data:
            break

        results.extend(data)
        offset += limit

        if len(data) < limit:
            break

    return results
```

### Safe Delete with Validation
```python
def safe_delete(resource_type, resource_id):
    # Verify exists
    response = api_get(f"/{resource_type}/{resource_id}")
    if response.status_code == 404:
        return "Not found"

    # Delete
    response = api_delete(f"/{resource_type}/{resource_id}")
    return response.status_code == 204
```

## API Versioning

The API is versioned via URL path (`/v1/`). Breaking changes require new version.
Current version: v1

## Idempotency

- GET requests are always safe to retry
- DELETE requests are idempotent (deleting twice is safe)
- POST/PUT may create duplicates - use unique identifiers

## Field Naming

Celigo uses camelCase for field names:
- `_id` - MongoDB ObjectId (24 hex chars)
- `_integrationId` - Reference to integration
- `createdAt` - ISO 8601 timestamp
- `lastModified` - ISO 8601 timestamp
