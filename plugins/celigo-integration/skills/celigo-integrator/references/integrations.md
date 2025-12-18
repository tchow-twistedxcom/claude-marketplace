# Integrations API Reference

Integrations are top-level containers for organizing flows, exports, imports, and connections.

## Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List all | GET | `/integrations` |
| Get one | GET | `/integrations/{id}` |
| Create | POST | `/integrations` |
| Update | PUT | `/integrations/{id}` |
| Delete | DELETE | `/integrations/{id}` |
| Get flows | GET | `/integrations/{id}/flows` |
| Get exports | GET | `/integrations/{id}/exports` |
| Get imports | GET | `/integrations/{id}/imports` |
| Get connections | GET | `/integrations/{id}/connections` |
| Get audit log | GET | `/integrations/{id}/audit` |
| Get errors | GET | `/integrations/{id}/errors` |
| Get users | GET | `/integrations/{id}/ashares` |
| Download template | GET | `/integrations/{id}/template` |

## Integration Object

```json
{
  "_id": "abc123def456",
  "name": "Salesforce to NetSuite Sync",
  "description": "Bi-directional customer sync",
  "sandbox": false,
  "installSteps": [],
  "uninstallSteps": [],
  "flowGroupings": [],
  "createdAt": "2024-01-01T00:00:00.000Z",
  "lastModified": "2024-01-15T12:00:00.000Z"
}
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `_id` | string | Unique identifier (24 hex chars) |
| `name` | string | Display name (required) |
| `description` | string | Optional description |
| `sandbox` | boolean | true = sandbox/test mode |
| `installSteps` | array | Installation wizard steps |
| `uninstallSteps` | array | Uninstallation steps |
| `flowGroupings` | array | Logical flow groups |
| `createdAt` | string | ISO 8601 creation timestamp |
| `lastModified` | string | ISO 8601 last update timestamp |

## Operations

### List All Integrations

```bash
curl -X GET "https://api.integrator.io/v1/integrations" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
[
  {
    "_id": "abc123",
    "name": "Salesforce Sync",
    "sandbox": false,
    "lastModified": "2024-01-15T12:00:00.000Z"
  },
  {
    "_id": "def456",
    "name": "NetSuite Integration",
    "sandbox": true,
    "lastModified": "2024-01-10T08:00:00.000Z"
  }
]
```

### Get Single Integration

```bash
curl -X GET "https://api.integrator.io/v1/integrations/{integration_id}" \
  -H "Authorization: Bearer $API_KEY"
```

### Create Integration

```bash
curl -X POST "https://api.integrator.io/v1/integrations" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Integration",
    "description": "Created via API",
    "sandbox": false
  }'
```

**Response (201 Created):**
```json
{
  "_id": "new_integration_id",
  "name": "New Integration",
  "description": "Created via API",
  "sandbox": false,
  "createdAt": "2024-01-20T10:00:00.000Z",
  "lastModified": "2024-01-20T10:00:00.000Z"
}
```

### Update Integration

```bash
curl -X PUT "https://api.integrator.io/v1/integrations/{integration_id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "description": "Updated description"
  }'
```

### Delete Integration

```bash
curl -X DELETE "https://api.integrator.io/v1/integrations/{integration_id}" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:** 204 No Content

**Warning:** Deleting an integration also deletes all contained flows, exports, and imports.

### Get Integration Flows

```bash
curl -X GET "https://api.integrator.io/v1/integrations/{integration_id}/flows" \
  -H "Authorization: Bearer $API_KEY"
```

### Get Audit Log

```bash
curl -X GET "https://api.integrator.io/v1/integrations/{integration_id}/audit" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
[
  {
    "timestamp": "2024-01-15T12:00:00.000Z",
    "user": "user@example.com",
    "action": "update",
    "resourceType": "integration",
    "changes": {
      "name": {
        "old": "Old Name",
        "new": "New Name"
      }
    }
  }
]
```

### Get Error Summary

```bash
curl -X GET "https://api.integrator.io/v1/integrations/{integration_id}/errors" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
[
  {
    "_flowId": "flow123",
    "numError": 5
  },
  {
    "_flowId": "flow456",
    "numError": 2
  }
]
```

## Query Parameters

### Filtering
```
?sandbox=true           # Only sandbox integrations
?sandbox=false          # Only production integrations
```

### Pagination
```
?limit=50               # Max results per page
?offset=0               # Skip N results
```

## Common Use Cases

### Clone Integration Structure

```python
# Get existing integration
existing = api_get(f"/integrations/{source_id}")

# Create new integration with same structure
new_integration = api_post("/integrations", {
    "name": f"Copy of {existing['name']}",
    "description": existing.get('description', ''),
    "sandbox": True  # Start in sandbox
})

print(f"Created: {new_integration['_id']}")
```

### List All Production Integrations

```bash
curl -X GET "https://api.integrator.io/v1/integrations?sandbox=false" \
  -H "Authorization: Bearer $API_KEY"
```

### Get Integration with All Related Resources

```python
integration_id = "abc123"

# Get integration details
integration = api_get(f"/integrations/{integration_id}")

# Get related resources
flows = api_get(f"/integrations/{integration_id}/flows")
exports = api_get(f"/integrations/{integration_id}/exports")
imports = api_get(f"/integrations/{integration_id}/imports")
connections = api_get(f"/integrations/{integration_id}/connections")

print(f"Integration: {integration['name']}")
print(f"  Flows: {len(flows)}")
print(f"  Exports: {len(exports)}")
print(f"  Imports: {len(imports)}")
print(f"  Connections: {len(connections)}")
```

## Error Handling

### 404 Not Found
Integration doesn't exist or you don't have access:
```json
{
  "errors": [{
    "code": "not_found",
    "message": "Integration not found"
  }]
}
```

### 400 Bad Request
Invalid request body:
```json
{
  "errors": [{
    "code": "validation_error",
    "message": "Name is required",
    "field": "name"
  }]
}
```

### 409 Conflict
Duplicate name:
```json
{
  "errors": [{
    "code": "conflict",
    "message": "Integration with this name already exists"
  }]
}
```
