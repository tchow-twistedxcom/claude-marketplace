# Scripts API Reference

Scripts contain custom JavaScript code used for data transformation, filtering, and business logic in flows.

## Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List all | GET | `/scripts` |
| Get one | GET | `/scripts/{id}` |
| Create | POST | `/scripts` |
| Update | PUT | `/scripts/{id}` |
| Delete | DELETE | `/scripts/{id}` |

## Script Object

```json
{
  "_id": "script123",
  "name": "Transform Customer Data",
  "description": "Normalize customer records before import",
  "function": "preSavePage",
  "code": "function preSavePage(options) {\n  return {\n    data: options.data.map(record => ({\n      ...record,\n      email: record.email.toLowerCase()\n    })),\n    errors: options.errors\n  };\n}",
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
| `function` | string | Hook type |
| `code` | string | JavaScript code |
| `createdAt` | string | Creation timestamp |
| `lastModified` | string | Last update timestamp |

## Hook Types

| Hook | Used In | Purpose |
|------|---------|---------|
| `preSavePage` | Export | Transform exported data |
| `preMap` | Import | Transform before mapping |
| `postMap` | Import | Transform after mapping |
| `postSubmit` | Import | Process after submission |
| `postResponseMap` | Import | Handle response data |
| `postAggregate` | Import | Process aggregated data |

## Operations

### List All Scripts

```bash
curl -X GET "https://api.integrator.io/v1/scripts" \
  -H "Authorization: Bearer $API_KEY"
```

### Get Single Script

```bash
curl -X GET "https://api.integrator.io/v1/scripts/{script_id}" \
  -H "Authorization: Bearer $API_KEY"
```

### Create Script

```bash
curl -X POST "https://api.integrator.io/v1/scripts" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Normalize Email",
    "description": "Convert email to lowercase",
    "function": "preMap",
    "code": "function preMap(options) {\n  return {\n    data: options.data.map(r => ({...r, email: r.email?.toLowerCase()}))\n  };\n}"
  }'
```

### Update Script

```bash
curl -X PUT "https://api.integrator.io/v1/scripts/{script_id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Script Name",
    "code": "function preMap(options) {\n  // Updated logic\n  return options;\n}"
  }'
```

### Delete Script

```bash
curl -X DELETE "https://api.integrator.io/v1/scripts/{script_id}" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:** 204 No Content

**Warning:** Cannot delete scripts used in flows.

## Script Function Signatures

### preSavePage (Export)

```javascript
function preSavePage(options) {
  // options.data - Array of exported records
  // options.errors - Array of existing errors
  // options.settings - Integration settings
  // options._exportId - Export ID
  // options._flowId - Flow ID

  return {
    data: options.data,      // Modified records
    errors: options.errors,  // Errors to report
    abort: false             // Stop processing if true
  };
}
```

### preMap (Import)

```javascript
function preMap(options) {
  // options.data - Array of records before mapping
  // options.settings - Integration settings

  return {
    data: options.data       // Modified records
  };
}
```

### postMap (Import)

```javascript
function postMap(options) {
  // options.data - Array of mapped records
  // options.postMapData - Original pre-map data

  return {
    data: options.data
  };
}
```

### postSubmit (Import)

```javascript
function postSubmit(options) {
  // options.data - Submitted records
  // options.responseData - Response from destination
  // options.errors - Submission errors

  return {
    data: options.data,
    errors: options.errors
  };
}
```

## Common Patterns

### Data Transformation

```javascript
function preMap(options) {
  return {
    data: options.data.map(record => ({
      ...record,
      fullName: `${record.firstName} ${record.lastName}`,
      email: record.email?.toLowerCase(),
      phone: record.phone?.replace(/\D/g, '')
    }))
  };
}
```

### Conditional Filtering

```javascript
function preSavePage(options) {
  return {
    data: options.data.filter(record =>
      record.status === 'active' &&
      record.email?.includes('@')
    ),
    errors: options.errors
  };
}
```

### Error Handling

```javascript
function preMap(options) {
  const validData = [];
  const errors = [];

  options.data.forEach((record, index) => {
    if (!record.email) {
      errors.push({
        code: 'MISSING_EMAIL',
        message: `Record ${index}: Missing email address`,
        source: 'preMap'
      });
    } else {
      validData.push(record);
    }
  });

  return { data: validData, errors };
}
```

### External API Call

```javascript
function preMap(options) {
  const enrichedData = options.data.map(record => {
    // Use options.request for HTTP calls
    const response = options.request('GET',
      `https://api.example.com/enrich?email=${record.email}`
    );
    return { ...record, ...response };
  });

  return { data: enrichedData };
}
```

### Date Formatting

```javascript
function preMap(options) {
  return {
    data: options.data.map(record => ({
      ...record,
      createdDate: new Date(record.createdAt).toISOString().split('T')[0],
      timestamp: Date.now()
    }))
  };
}
```

## Using Scripts in Flows

### Attach to Export

```json
{
  "hooks": {
    "preSavePage": {
      "_scriptId": "script123"
    }
  }
}
```

### Attach to Import

```json
{
  "hooks": {
    "preMap": {"_scriptId": "script1"},
    "postMap": {"_scriptId": "script2"},
    "postSubmit": {"_scriptId": "script3"}
  }
}
```

## Error Handling

### Script Not Found
```json
{
  "errors": [{
    "code": "not_found",
    "message": "Script not found"
  }]
}
```

### Script in Use
```json
{
  "errors": [{
    "code": "conflict",
    "message": "Script is used by 3 flows"
  }]
}
```

### Syntax Error
```json
{
  "errors": [{
    "code": "syntax_error",
    "message": "Unexpected token at line 5"
  }]
}
```

## Best Practices

1. **Keep scripts focused** - Single responsibility per script
2. **Handle errors gracefully** - Return meaningful error objects
3. **Use descriptive names** - Clear naming for discoverability
4. **Test thoroughly** - Validate with sample data before production
5. **Document logic** - Add comments for complex transformations
6. **Avoid side effects** - Scripts should be deterministic
