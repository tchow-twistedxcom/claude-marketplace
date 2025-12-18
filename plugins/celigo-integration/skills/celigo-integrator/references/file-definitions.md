# File Definitions API Reference

File definitions describe the structure and parsing rules for file-based data (CSV, XML, EDI, JSON, fixed-width). Used with FTP/SFTP exports and imports.

## Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List all | GET | `/filedefinitions` |
| Get one | GET | `/filedefinitions/{id}` |
| Create | POST | `/filedefinitions` |
| Update | PUT | `/filedefinitions/{id}` |
| Delete | DELETE | `/filedefinitions/{id}` |

## File Definition Object

```json
{
  "_id": "filedef123",
  "name": "Customer CSV Format",
  "description": "Standard customer data CSV format",
  "format": "csv",
  "csv": {
    "columnDelimiter": ",",
    "rowDelimiter": "\n",
    "hasHeaderRow": true,
    "trimSpaces": true,
    "columns": [
      {"name": "customer_id", "type": "string"},
      {"name": "company_name", "type": "string"},
      {"name": "email", "type": "string"},
      {"name": "created_date", "type": "date", "dateFormat": "YYYY-MM-DD"}
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
| `description` | string | Optional description |
| `format` | string | File format type |
| `[format]` | object | Format-specific config |

## Supported Formats

| Format | Description |
|--------|-------------|
| `csv` | Comma-separated values |
| `xml` | XML documents |
| `json` | JSON files |
| `edi` | EDI transactions |
| `fixedWidth` | Fixed-width text files |

## Operations

### List All File Definitions

```bash
curl -X GET "https://api.integrator.io/v1/filedefinitions" \
  -H "Authorization: Bearer $API_KEY"
```

### Get Single File Definition

```bash
curl -X GET "https://api.integrator.io/v1/filedefinitions/{filedef_id}" \
  -H "Authorization: Bearer $API_KEY"
```

### Create CSV Definition

```bash
curl -X POST "https://api.integrator.io/v1/filedefinitions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Order CSV Format",
    "format": "csv",
    "csv": {
      "columnDelimiter": ",",
      "rowDelimiter": "\n",
      "hasHeaderRow": true,
      "trimSpaces": true,
      "textQualifier": "\"",
      "columns": [
        {"name": "order_id", "type": "string"},
        {"name": "customer_id", "type": "string"},
        {"name": "total", "type": "number"},
        {"name": "order_date", "type": "date", "dateFormat": "MM/DD/YYYY"}
      ]
    }
  }'
```

### Create XML Definition

```bash
curl -X POST "https://api.integrator.io/v1/filedefinitions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Product XML Format",
    "format": "xml",
    "xml": {
      "rootElement": "products",
      "recordElement": "product",
      "fields": [
        {"xpath": "sku", "name": "sku", "type": "string"},
        {"xpath": "name", "name": "productName", "type": "string"},
        {"xpath": "price", "name": "price", "type": "number"},
        {"xpath": "@id", "name": "productId", "type": "string"}
      ]
    }
  }'
```

### Create Fixed-Width Definition

```bash
curl -X POST "https://api.integrator.io/v1/filedefinitions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Legacy System Format",
    "format": "fixedWidth",
    "fixedWidth": {
      "rowDelimiter": "\n",
      "columns": [
        {"name": "customer_id", "start": 0, "length": 10, "type": "string"},
        {"name": "name", "start": 10, "length": 50, "type": "string", "trim": true},
        {"name": "balance", "start": 60, "length": 12, "type": "number", "decimalPlaces": 2}
      ]
    }
  }'
```

### Update File Definition

```bash
curl -X PUT "https://api.integrator.io/v1/filedefinitions/{filedef_id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "csv": {
      "columns": [
        {"name": "id", "type": "string"},
        {"name": "name", "type": "string"},
        {"name": "new_field", "type": "string"}
      ]
    }
  }'
```

### Delete File Definition

```bash
curl -X DELETE "https://api.integrator.io/v1/filedefinitions/{filedef_id}" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:** 204 No Content

## CSV Configuration

```json
{
  "csv": {
    "columnDelimiter": ",",
    "rowDelimiter": "\n",
    "hasHeaderRow": true,
    "trimSpaces": true,
    "textQualifier": "\"",
    "escapeCharacter": "\\",
    "skipRows": 0,
    "columns": [
      {
        "name": "field_name",
        "type": "string|number|date|boolean",
        "dateFormat": "YYYY-MM-DD",
        "required": true,
        "default": "default_value"
      }
    ]
  }
}
```

### CSV Options

| Option | Type | Description |
|--------|------|-------------|
| `columnDelimiter` | string | Field separator (comma, tab, pipe) |
| `rowDelimiter` | string | Line separator |
| `hasHeaderRow` | boolean | First row contains headers |
| `trimSpaces` | boolean | Remove leading/trailing spaces |
| `textQualifier` | string | Quote character for strings |
| `escapeCharacter` | string | Escape character |
| `skipRows` | number | Skip N rows at start |

## XML Configuration

```json
{
  "xml": {
    "rootElement": "root",
    "recordElement": "record",
    "namespaces": {
      "ns": "http://example.com/namespace"
    },
    "fields": [
      {
        "xpath": "path/to/element",
        "name": "fieldName",
        "type": "string",
        "isAttribute": false
      }
    ]
  }
}
```

### XML Options

| Option | Type | Description |
|--------|------|-------------|
| `rootElement` | string | Root XML element |
| `recordElement` | string | Element containing each record |
| `namespaces` | object | Namespace prefix mappings |
| `fields` | array | XPath to field mappings |

## Fixed-Width Configuration

```json
{
  "fixedWidth": {
    "rowDelimiter": "\n",
    "columns": [
      {
        "name": "fieldName",
        "start": 0,
        "length": 10,
        "type": "string",
        "trim": true,
        "padCharacter": " ",
        "alignment": "left"
      }
    ]
  }
}
```

### Fixed-Width Options

| Option | Type | Description |
|--------|------|-------------|
| `start` | number | 0-based start position |
| `length` | number | Field length in characters |
| `trim` | boolean | Remove padding |
| `padCharacter` | string | Padding character |
| `alignment` | string | left, right, center |

## EDI Configuration

```json
{
  "edi": {
    "standard": "X12",
    "version": "004010",
    "transactionSet": "850",
    "elementDelimiter": "*",
    "segmentDelimiter": "~",
    "componentDelimiter": ":"
  }
}
```

## Using in Exports/Imports

### FTP Export with File Definition

```json
{
  "name": "Customer FTP Export",
  "adaptorType": "FTPExport",
  "ftp": {
    "directoryPath": "/outbound",
    "fileNameTemplate": "customers_{{timestamp}}.csv"
  },
  "_fileDefinitionId": "filedef123"
}
```

### FTP Import with File Definition

```json
{
  "name": "Order FTP Import",
  "adaptorType": "FTPImport",
  "ftp": {
    "directoryPath": "/inbound",
    "fileNamePattern": "orders_*.csv"
  },
  "_fileDefinitionId": "filedef456"
}
```

## Data Type Mapping

| Type | Description | Example |
|------|-------------|---------|
| `string` | Text values | "John Doe" |
| `number` | Numeric values | 123.45 |
| `date` | Date values | "2024-01-15" |
| `boolean` | True/false | true |
| `integer` | Whole numbers | 123 |

### Date Formats

| Format | Example |
|--------|---------|
| `YYYY-MM-DD` | 2024-01-15 |
| `MM/DD/YYYY` | 01/15/2024 |
| `DD-MMM-YYYY` | 15-Jan-2024 |
| `YYYYMMDD` | 20240115 |
| `ISO8601` | 2024-01-15T10:00:00Z |

## Error Handling

### Definition Not Found
```json
{
  "errors": [{
    "code": "not_found",
    "message": "File definition not found"
  }]
}
```

### Invalid Format
```json
{
  "errors": [{
    "code": "validation_error",
    "message": "Invalid column configuration"
  }]
}
```

### Definition in Use
```json
{
  "errors": [{
    "code": "conflict",
    "message": "File definition is used by 2 exports"
  }]
}
```

## Best Practices

1. **Match source format exactly** - Test with sample files
2. **Handle edge cases** - Empty values, special characters
3. **Use appropriate types** - Numbers for calculations, strings for IDs
4. **Document date formats** - Be explicit about expected formats
5. **Test with production data** - Validate against real files
6. **Version your definitions** - Track changes over time
