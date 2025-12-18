# Imports API Reference

Imports define how data is loaded into destination systems. They act as "page processors" in flows.

## Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List all | GET | `/imports` |
| Get one | GET | `/imports/{id}` |
| Create | POST | `/imports` |
| Update | PUT | `/imports/{id}` |
| Delete | DELETE | `/imports/{id}` |
| Get audit log | GET | `/imports/{id}/audit` |
| Get dependencies | GET | `/imports/{id}/dependencies` |

## Import Object

```json
{
  "_id": "imp123",
  "name": "Customer Import",
  "_connectionId": "conn123",
  "_integrationId": "int123",
  "adaptorType": "NetSuiteImport",
  "sandbox": false,
  "netsuite": {
    "recordType": "customer",
    "operation": "addupdate",
    "internalIdLookup": {
      "expression": "{{email}}"
    }
  },
  "mapping": {
    "fields": [
      {"extract": "name", "generate": "companyname"},
      {"extract": "email", "generate": "email"}
    ]
  },
  "createdAt": "2024-01-01T00:00:00.000Z",
  "lastModified": "2024-01-15T12:00:00.000Z"
}
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `_id` | string | Unique identifier |
| `name` | string | Display name (required) |
| `_connectionId` | string | Connection to use |
| `_integrationId` | string | Parent integration |
| `adaptorType` | string | Import type |
| `sandbox` | boolean | Sandbox mode |
| `mapping` | object | Field mappings |
| `[connector]` | object | Connector-specific config |

## Adaptor Types

| Type | Description |
|------|-------------|
| `RESTImport` | Generic REST API |
| `SalesforceImport` | Salesforce objects |
| `NetSuiteImport` | NetSuite records |
| `MongoDBImport` | MongoDB documents |
| `FTPImport` | File uploads |
| `HTTPImport` | HTTP requests |

## Operations

### List All Imports

```bash
curl -X GET "https://api.integrator.io/v1/imports" \
  -H "Authorization: Bearer $API_KEY"
```

**Query Parameters:**
```
?_integrationId=abc123    # Filter by integration
?_connectionId=conn123    # Filter by connection
?adaptorType=RESTImport   # Filter by type
?limit=100&offset=0       # Pagination
```

### Get Single Import

```bash
curl -X GET "https://api.integrator.io/v1/imports/{import_id}" \
  -H "Authorization: Bearer $API_KEY"
```

### Create REST Import

```bash
curl -X POST "https://api.integrator.io/v1/imports" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer REST Import",
    "_connectionId": "connection_id",
    "_integrationId": "integration_id",
    "adaptorType": "RESTImport",
    "http": {
      "relativeURI": "/api/customers",
      "method": "POST",
      "body": {
        "name": "{{name}}",
        "email": "{{email}}"
      }
    }
  }'
```

### Create Salesforce Import

```bash
curl -X POST "https://api.integrator.io/v1/imports" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Salesforce Contact Import",
    "_connectionId": "sf_connection_id",
    "_integrationId": "integration_id",
    "adaptorType": "SalesforceImport",
    "salesforce": {
      "sObjectType": "Contact",
      "operation": "upsert",
      "externalIdField": "Email"
    },
    "mapping": {
      "fields": [
        {"extract": "firstName", "generate": "FirstName"},
        {"extract": "lastName", "generate": "LastName"},
        {"extract": "email", "generate": "Email"}
      ]
    }
  }'
```

### Create NetSuite Import

```bash
curl -X POST "https://api.integrator.io/v1/imports" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NetSuite Customer Import",
    "_connectionId": "ns_connection_id",
    "_integrationId": "integration_id",
    "adaptorType": "NetSuiteImport",
    "netsuite": {
      "recordType": "customer",
      "operation": "addupdate",
      "internalIdLookup": {
        "expression": "{{externalId}}"
      }
    },
    "mapping": {
      "fields": [
        {"extract": "companyName", "generate": "companyname"},
        {"extract": "email", "generate": "email"},
        {"extract": "phone", "generate": "phone"}
      ]
    }
  }'
```

### Update Import

```bash
curl -X PUT "https://api.integrator.io/v1/imports/{import_id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Import Name",
    "mapping": {
      "fields": [
        {"extract": "name", "generate": "companyname"},
        {"extract": "email", "generate": "email"},
        {"extract": "phone", "generate": "phone"}
      ]
    }
  }'
```

### Delete Import

```bash
curl -X DELETE "https://api.integrator.io/v1/imports/{import_id}" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:** 204 No Content

### Get Dependencies

```bash
curl -X GET "https://api.integrator.io/v1/imports/{import_id}/dependencies" \
  -H "Authorization: Bearer $API_KEY"
```

## Import Operations

| Operation | Description |
|-----------|-------------|
| `add` | Create new records only |
| `update` | Update existing records only |
| `addupdate` | Upsert (create or update) |
| `delete` | Delete records |

## Field Mapping

### Simple Mapping
```json
{
  "mapping": {
    "fields": [
      {"extract": "sourceField", "generate": "destField"}
    ]
  }
}
```

### With Transformation
```json
{
  "mapping": {
    "fields": [
      {
        "extract": "email",
        "generate": "Email",
        "transform": "lowercase"
      }
    ]
  }
}
```

### Static Value
```json
{
  "mapping": {
    "fields": [
      {
        "generate": "Source",
        "hardCodedValue": "API Import"
      }
    ]
  }
}
```

### Handlebars Expression
```json
{
  "mapping": {
    "fields": [
      {
        "generate": "fullName",
        "expression": "{{firstName}} {{lastName}}"
      }
    ]
  }
}
```

### Conditional Mapping
```json
{
  "mapping": {
    "fields": [
      {
        "generate": "status",
        "expression": "{{#if active}}Active{{else}}Inactive{{/if}}"
      }
    ]
  }
}
```

## Lookups

Enrich data with lookups:

```json
{
  "mapping": {
    "lists": [
      {
        "generate": "AccountId",
        "lookup": {
          "_connectionId": "sf_conn",
          "sObjectType": "Account",
          "whereClause": "Name = '{{accountName}}'"
        }
      }
    ]
  }
}
```

## Response Mapping

Map response back to source:

```json
{
  "responseMapping": {
    "fields": [
      {"extract": "id", "generate": "externalId"}
    ],
    "lists": []
  }
}
```

## Hooks

Custom JavaScript processing:

```json
{
  "hooks": {
    "preMap": {"_scriptId": "script1"},
    "postMap": {"_scriptId": "script2"},
    "postSubmit": {"_scriptId": "script3"},
    "postResponseMap": {"_scriptId": "script4"}
  }
}
```

## Input Filters

Filter records before import:

```json
{
  "filter": {
    "type": "expression",
    "expression": {
      "version": "1",
      "rules": [
        ["notEmpty", ["string", ["extract", "email"]]]
      ]
    }
  }
}
```

## Error Handling

### Import in Use
```json
{
  "errors": [{
    "code": "conflict",
    "message": "Import is used by 2 flows"
  }]
}
```

### Mapping Error
```json
{
  "errors": [{
    "code": "validation_error",
    "message": "Invalid mapping field: unknownField"
  }]
}
```

### Destination Error
```json
{
  "errors": [{
    "code": "destination_error",
    "message": "Record not found in destination system"
  }]
}
```

## Best Practices

1. **Use upsert operations** when possible (addupdate)
2. **Set appropriate batch sizes** for performance
3. **Add input filters** to reject invalid records early
4. **Use lookups** for reference data enrichment
5. **Enable response mapping** to capture created IDs
6. **Test with small batches** before full runs
