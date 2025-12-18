# Exports API Reference

Exports define how data is extracted from source systems. They act as "page generators" in flows.

## Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List all | GET | `/exports` |
| Get one | GET | `/exports/{id}` |
| Create | POST | `/exports` |
| Update | PUT | `/exports/{id}` |
| Delete | DELETE | `/exports/{id}` |
| Get audit log | GET | `/exports/{id}/audit` |
| Get dependencies | GET | `/exports/{id}/dependencies` |

## Export Object

```json
{
  "_id": "exp123",
  "name": "Customer Export",
  "_connectionId": "conn123",
  "_integrationId": "int123",
  "adaptorType": "SalesforceExport",
  "sandbox": false,
  "salesforce": {
    "type": "soql",
    "soql": {
      "query": "SELECT Id, Name, Email FROM Contact WHERE LastModifiedDate > {{lastExportDateTime}}"
    }
  },
  "pageSize": 100,
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
| `adaptorType` | string | Export type (connector-specific) |
| `sandbox` | boolean | Sandbox mode |
| `pageSize` | number | Records per page/batch |
| `[connector]` | object | Connector-specific config |

## Adaptor Types

| Type | Description |
|------|-------------|
| `RESTExport` | Generic REST API |
| `SalesforceExport` | Salesforce SOQL |
| `NetSuiteExport` | NetSuite SuiteQL/Saved Search |
| `MongoDBExport` | MongoDB queries |
| `FTPExport` | File-based export |
| `HTTPExport` | HTTP requests |

## Operations

### List All Exports

```bash
curl -X GET "https://api.integrator.io/v1/exports" \
  -H "Authorization: Bearer $API_KEY"
```

**Query Parameters:**
```
?_integrationId=abc123    # Filter by integration
?_connectionId=conn123    # Filter by connection
?adaptorType=RESTExport   # Filter by type
?limit=100&offset=0       # Pagination
```

### Get Single Export

```bash
curl -X GET "https://api.integrator.io/v1/exports/{export_id}" \
  -H "Authorization: Bearer $API_KEY"
```

### Create REST Export

```bash
curl -X POST "https://api.integrator.io/v1/exports" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer REST Export",
    "_connectionId": "connection_id",
    "_integrationId": "integration_id",
    "adaptorType": "RESTExport",
    "http": {
      "relativeURI": "/api/customers",
      "method": "GET",
      "paging": {
        "method": "page",
        "page": {
          "pageArgument": "page",
          "maxPagePath": "totalPages"
        }
      }
    },
    "pageSize": 100
  }'
```

### Create Salesforce Export

```bash
curl -X POST "https://api.integrator.io/v1/exports" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Salesforce Contact Export",
    "_connectionId": "sf_connection_id",
    "_integrationId": "integration_id",
    "adaptorType": "SalesforceExport",
    "salesforce": {
      "type": "soql",
      "soql": {
        "query": "SELECT Id, FirstName, LastName, Email FROM Contact WHERE LastModifiedDate > {{lastExportDateTime}}"
      }
    },
    "pageSize": 200
  }'
```

### Create NetSuite Export

```bash
curl -X POST "https://api.integrator.io/v1/exports" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NetSuite Customer Export",
    "_connectionId": "ns_connection_id",
    "_integrationId": "integration_id",
    "adaptorType": "NetSuiteExport",
    "netsuite": {
      "type": "search",
      "searches": [{
        "recordType": "customer",
        "searchId": "customsearch_customers"
      }]
    },
    "pageSize": 100
  }'
```

### Update Export

```bash
curl -X PUT "https://api.integrator.io/v1/exports/{export_id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Export Name",
    "pageSize": 200
  }'
```

### Delete Export

```bash
curl -X DELETE "https://api.integrator.io/v1/exports/{export_id}" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:** 204 No Content

**Warning:** Cannot delete exports used in flows.

### Get Dependencies

```bash
curl -X GET "https://api.integrator.io/v1/exports/{export_id}/dependencies" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
{
  "integrations": [{"_id": "int1", "name": "My Integration"}],
  "flows": [{"_id": "flow1", "name": "Customer Sync"}]
}
```

## Delta Export Configuration

For incremental exports using timestamps:

```json
{
  "name": "Delta Export",
  "adaptorType": "RESTExport",
  "http": {
    "relativeURI": "/api/customers?modified_after={{lastExportDateTime}}"
  },
  "delta": {
    "dateField": "lastModifiedDate",
    "dateFormat": "ISO8601"
  }
}
```

### Handlebars Variables

| Variable | Description |
|----------|-------------|
| `{{lastExportDateTime}}` | Last successful export timestamp |
| `{{currentExportDateTime}}` | Current execution timestamp |
| `{{settings.field}}` | Custom settings value |

## Pagination Configurations

### Offset-based
```json
{
  "paging": {
    "method": "page",
    "page": {
      "pageArgument": "page",
      "maxPagePath": "totalPages"
    }
  }
}
```

### Cursor-based
```json
{
  "paging": {
    "method": "cursor",
    "cursor": {
      "cursorPath": "next_cursor",
      "cursorArgument": "cursor"
    }
  }
}
```

### Link Header
```json
{
  "paging": {
    "method": "linkheader"
  }
}
```

## Output Filters

Filter exported records:

```json
{
  "filter": {
    "type": "expression",
    "expression": {
      "version": "1",
      "rules": [
        ["equals", ["string", ["extract", "status"]], "active"]
      ]
    }
  }
}
```

## Hooks

Custom JavaScript processing:

```json
{
  "hooks": {
    "preSavePage": {
      "_scriptId": "script123"
    },
    "postSubmit": {
      "_scriptId": "script456"
    }
  }
}
```

## Error Handling

### Export in Use
```json
{
  "errors": [{
    "code": "conflict",
    "message": "Export is used by 2 flows"
  }]
}
```

### Invalid Query
```json
{
  "errors": [{
    "code": "validation_error",
    "message": "Invalid SOQL query syntax"
  }]
}
```

### Connection Error
```json
{
  "errors": [{
    "code": "connection_error",
    "message": "Unable to connect to source system"
  }]
}
```
