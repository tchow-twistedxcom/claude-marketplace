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

### Create NetSuite Export (Restlet — TWX Standard)

TWX uses `type: "restlet"` for all NetSuite exports. This is the correct pattern for saved-search exports against standard or custom record types.

**Critical rules for `searchId`:**
- **Always use the numeric internal ID** (e.g., `"264138"`), never the script ID (e.g., `"customsearch_twx_locally_feed_export"`).
- Celigo resolves saved searches by numeric ID internally. When you pick a search from the Celigo UI dropdown, it stores the numeric ID. Using a script ID causes the UI to display the search as a "private saved search" reference and may not resolve the Record Type picker.
- To find the numeric ID: run the saved search in NetSuite and note the `id=` parameter in the URL, or query `SELECT id FROM savedsearch WHERE scriptid = 'customsearch_...'` via SuiteQL.

**Flat export (no row grouping) — e.g., Locally Feed:**
```json
{
  "name": "NS Mirror Record Export - Locally Feed",
  "_connectionId": "5b5f3bc70732ab2b95d98894",
  "adaptorType": "NetSuiteExport",
  "asynchronous": true,
  "pageSize": 1,
  "oneToMany": false,
  "netsuite": {
    "type": "restlet",
    "skipGrouping": true,
    "statsOnly": false,
    "restlet": {
      "recordType": "customrecord_twx_locally_feed_row",
      "searchId": "264138",
      "restletVersion": "suiteapp2.0",
      "markExportedBatchSize": 100
    },
    "distributed": {}
  }
}
```

**Grouped export (EDI style, multiple rows per page) — e.g., Family Center 855:**
```json
{
  "name": "Family Center Farm & Home - Get NetSuite Sales Orders to Acknowledgement",
  "_connectionId": "5b5f3bc70732ab2b95d98894",
  "adaptorType": "NetSuiteExport",
  "asynchronous": true,
  "pageSize": 1,
  "oneToMany": false,
  "netsuite": {
    "type": "restlet",
    "skipGrouping": false,
    "statsOnly": false,
    "restlet": {
      "recordType": "customrecord_twx_edi_history",
      "searchId": "177563",
      "restletVersion": "suiteapp2.0",
      "markExportedBatchSize": 100
    },
    "distributed": {}
  }
}
```

**Field notes:**
| Field | Notes |
|-------|-------|
| `pageSize` | Always `1` for restlet exports. Controls pages passed to imports per batch. |
| `skipGrouping` | `true` = flat records (one row per page, e.g., CSV feed). `false` = group related rows under one key (EDI). |
| `distributed` | Must be `{}` (empty object). **Cannot be set via API PUT — Celigo strips it silently.** Must be set via the Celigo UI. |
| `markExportedBatchSize` | `100` is standard. Controls how many records Celigo marks as exported per RESTlet call. |
| `restletVersion` | Always `"suiteapp2.0"` for TWX. |
| `mockOutput` | **Cannot be cleared via API PUT** — Celigo preserves it as a system field even when omitted from the PUT body. Clear it via the Celigo UI. |

**⚠️ API vs UI limitations for NetSuiteExport restlet exports:**

After creating or updating a NetSuiteExport via the API, two fields require a manual UI step to finalize:
1. **Open the export in the Celigo UI** and save it — this properly writes `distributed: {}` into the netsuite block.
2. **Clear `mockOutput`** via the UI if it was auto-generated or stale.

These fields work correctly when configured through the UI but are silently dropped/preserved by the API. The export will run correctly either way, but the UI will display differently (notably the Record Type picker) until the UI save is done.

**TWX NetSuite Production Connection ID:** `5b5f3bc70732ab2b95d98894`

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
