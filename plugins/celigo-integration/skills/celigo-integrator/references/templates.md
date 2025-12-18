# Templates API Reference

Templates are pre-built integration packages that can be shared and installed. They bundle integrations, flows, exports, imports, and configurations for reuse.

## Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List available | GET | `/templates` |
| Get one | GET | `/templates/{id}` |
| Download integration | GET | `/integrations/{id}/template` |
| Download flow | GET | `/flows/{id}/template` |
| Install template | POST | `/templates/install` |
| Publish template | POST | `/templates` |

## Template Object

```json
{
  "_id": "template123",
  "name": "Shopify to NetSuite",
  "description": "Sync orders, customers, and inventory between Shopify and NetSuite",
  "version": "2.1.0",
  "category": "eCommerce",
  "publisher": "Celigo",
  "tags": ["shopify", "netsuite", "orders", "inventory"],
  "applications": ["Shopify", "NetSuite"],
  "installCount": 1500,
  "rating": 4.5,
  "createdAt": "2024-01-01T00:00:00.000Z",
  "lastModified": "2024-01-15T12:00:00.000Z"
}
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `_id` | string | Unique identifier |
| `name` | string | Template name |
| `description` | string | Description |
| `version` | string | Version number |
| `category` | string | Category classification |
| `publisher` | string | Publisher name |
| `tags` | array | Searchable tags |
| `applications` | array | Connected applications |
| `installCount` | number | Installation count |
| `rating` | number | User rating (1-5) |

## Operations

### List Available Templates

```bash
curl -X GET "https://api.integrator.io/v1/templates" \
  -H "Authorization: Bearer $API_KEY"
```

**Query Parameters:**
```
?category=eCommerce           # Filter by category
?application=Shopify          # Filter by application
?search=inventory             # Search in name/description
?publisher=Celigo             # Filter by publisher
```

### Get Template Details

```bash
curl -X GET "https://api.integrator.io/v1/templates/{template_id}" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
{
  "_id": "template123",
  "name": "Shopify to NetSuite",
  "description": "Complete bidirectional sync...",
  "version": "2.1.0",
  "contents": {
    "integrations": 1,
    "flows": 5,
    "exports": 10,
    "imports": 8,
    "connections": 2,
    "scripts": 3
  },
  "requirements": {
    "connections": [
      {"type": "Shopify", "description": "Shopify store connection"},
      {"type": "NetSuite", "description": "NetSuite account connection"}
    ],
    "settings": [
      {"key": "subsidiary", "description": "NetSuite subsidiary ID"},
      {"key": "priceLevel", "description": "Default price level"}
    ]
  },
  "documentation": "https://docs.celigo.com/templates/shopify-netsuite"
}
```

### Download Integration as Template

Get a signed URL to download an integration as a ZIP template:

```bash
curl -X GET "https://api.integrator.io/v1/integrations/{integration_id}/template" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
{
  "signedURL": "https://s3.amazonaws.com/...",
  "key": "templates/int123_2024-01-15.zip",
  "expiresAt": "2024-01-15T11:00:00.000Z"
}
```

### Download Flow as Template

```bash
curl -X GET "https://api.integrator.io/v1/flows/{flow_id}/template" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
{
  "signedURL": "https://s3.amazonaws.com/...",
  "key": "templates/flow456_2024-01-15.zip"
}
```

### Install Template

Install a template into your account:

```bash
curl -X POST "https://api.integrator.io/v1/templates/install" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "_templateId": "template123",
    "name": "My Shopify Integration",
    "settings": {
      "subsidiary": "1",
      "priceLevel": "Base Price"
    },
    "connections": {
      "shopify": "conn_shopify_123",
      "netsuite": "conn_netsuite_456"
    }
  }'
```

**Response:**
```json
{
  "_integrationId": "new_int_789",
  "installStatus": "completed",
  "createdResources": {
    "flows": ["flow1", "flow2", "flow3"],
    "exports": ["exp1", "exp2"],
    "imports": ["imp1", "imp2"]
  }
}
```

### Publish Template

Publish an integration as a template:

```bash
curl -X POST "https://api.integrator.io/v1/templates" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "_integrationId": "int123",
    "name": "My Custom Integration Template",
    "description": "Custom sync between systems",
    "version": "1.0.0",
    "category": "Custom",
    "tags": ["custom", "sync"],
    "visibility": "private"
  }'
```

**Visibility Options:**
- `private` - Only visible to your account
- `organization` - Visible to your organization
- `public` - Available in marketplace (requires approval)

## Template Structure

When downloaded, templates contain:

```
template.zip
├── manifest.json           # Template metadata
├── integration.json        # Integration configuration
├── flows/
│   ├── flow1.json
│   └── flow2.json
├── exports/
│   ├── export1.json
│   └── export2.json
├── imports/
│   ├── import1.json
│   └── import2.json
├── scripts/
│   └── script1.json
└── README.md               # Installation instructions
```

### Manifest Structure

```json
{
  "name": "Template Name",
  "version": "1.0.0",
  "celigo": {
    "minVersion": "2024.1"
  },
  "components": {
    "integrations": ["integration.json"],
    "flows": ["flows/flow1.json", "flows/flow2.json"],
    "exports": ["exports/export1.json"],
    "imports": ["imports/import1.json"],
    "scripts": ["scripts/script1.json"]
  },
  "connectionMappings": {
    "source_connection": {
      "type": "Shopify",
      "description": "Your Shopify store"
    },
    "destination_connection": {
      "type": "NetSuite",
      "description": "Your NetSuite account"
    }
  },
  "settings": [
    {
      "key": "subsidiary",
      "label": "NetSuite Subsidiary",
      "type": "string",
      "required": true
    }
  ]
}
```

## Installation Steps

Templates can define installation steps for guided setup:

```json
{
  "installSteps": [
    {
      "name": "Connect Shopify",
      "description": "Authorize connection to your Shopify store",
      "type": "connection",
      "connectionType": "Shopify"
    },
    {
      "name": "Connect NetSuite",
      "description": "Authorize connection to your NetSuite account",
      "type": "connection",
      "connectionType": "NetSuite"
    },
    {
      "name": "Configure Settings",
      "description": "Set your integration preferences",
      "type": "settings",
      "settings": ["subsidiary", "priceLevel", "warehouse"]
    },
    {
      "name": "Enable Flows",
      "description": "Choose which flows to enable",
      "type": "flowSelection"
    }
  ]
}
```

## Common Operations

### Clone Integration

```python
# Download as template
template_url = api_get(f"/integrations/{integration_id}/template").json()

# Download ZIP
import requests
zip_content = requests.get(template_url['signedURL']).content

# Save or install
with open('integration_backup.zip', 'wb') as f:
    f.write(zip_content)
```

### Migrate Between Environments

```python
# Export from source
source_template = api_get(f"/integrations/{source_id}/template").json()

# Install to target (different account/environment)
target_api_post("/templates/install", {
    "templateUrl": source_template['signedURL'],
    "name": "Migrated Integration",
    "connections": connection_mapping
})
```

### Version Control

```python
import datetime

# Create versioned backup
version = datetime.now().strftime('%Y%m%d_%H%M%S')
template = api_get(f"/integrations/{integration_id}/template").json()

# Save with version
save_to_storage(f"backups/{integration_id}/{version}.zip", template['signedURL'])
```

## Error Handling

### Template Not Found
```json
{
  "errors": [{
    "code": "not_found",
    "message": "Template not found"
  }]
}
```

### Missing Required Connection
```json
{
  "errors": [{
    "code": "validation_error",
    "message": "Required connection 'shopify' not provided"
  }]
}
```

### Incompatible Version
```json
{
  "errors": [{
    "code": "incompatible",
    "message": "Template requires Celigo version 2024.2 or higher"
  }]
}
```

## Best Practices

1. **Version your templates** - Use semantic versioning
2. **Document requirements** - List all required connections and settings
3. **Test installations** - Verify template works in clean environment
4. **Include README** - Provide setup and usage instructions
5. **Use meaningful names** - Clear naming for exported resources
6. **Backup before changes** - Download template before major updates
