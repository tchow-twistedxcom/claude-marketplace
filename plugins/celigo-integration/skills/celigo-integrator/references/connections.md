# Connections API Reference

Connections represent authenticated endpoints to external systems (APIs, databases, file systems).

## Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List all | GET | `/connections` |
| Get one | GET | `/connections/{id}` |
| Create | POST | `/connections` |
| Update | PUT | `/connections/{id}` |
| Delete | DELETE | `/connections/{id}` |
| Test/Ping | POST | `/connections/{id}/ping` |
| Get debug log | GET | `/connections/{id}/debuglog` |
| Get usage logs | GET | `/connections/{id}/logs` |
| Get dependencies | GET | `/connections/{id}/dependencies` |

## Connection Object

```json
{
  "_id": "conn123",
  "name": "Salesforce Production",
  "type": "salesforce",
  "_integrationId": "int123",
  "sandbox": false,
  "offline": false,
  "http": {
    "baseURI": "https://login.salesforce.com",
    "auth": {
      "type": "oauth"
    }
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
| `type` | string | Connector type (salesforce, netsuite, rest, etc.) |
| `_integrationId` | string | Parent integration ID |
| `sandbox` | boolean | Sandbox/test mode |
| `offline` | boolean | Connection disabled |
| `http` | object | HTTP configuration |
| `http.baseURI` | string | Base URL for requests |
| `http.auth` | object | Authentication configuration |

## Connection Types

### REST API
```json
{
  "name": "Generic REST API",
  "type": "http",
  "http": {
    "baseURI": "https://api.example.com",
    "auth": {
      "type": "basic",
      "basic": {
        "username": "user",
        "password": "pass"
      }
    }
  }
}
```

### OAuth 2.0
```json
{
  "name": "OAuth Service",
  "type": "http",
  "http": {
    "baseURI": "https://api.service.com",
    "auth": {
      "type": "oauth",
      "oauth": {
        "clientId": "your_client_id",
        "clientSecret": "your_client_secret",
        "tokenURI": "https://api.service.com/oauth/token",
        "scope": "read write"
      }
    }
  }
}
```

### API Key
```json
{
  "name": "API Key Service",
  "type": "http",
  "http": {
    "baseURI": "https://api.service.com",
    "headers": [
      {"name": "X-API-Key", "value": "your_api_key"}
    ]
  }
}
```

## Operations

### List All Connections

```bash
curl -X GET "https://api.integrator.io/v1/connections" \
  -H "Authorization: Bearer $API_KEY"
```

**Query Parameters:**
```
?_integrationId=abc123    # Filter by integration
?type=salesforce          # Filter by type
```

### Get Single Connection

```bash
curl -X GET "https://api.integrator.io/v1/connections/{connection_id}" \
  -H "Authorization: Bearer $API_KEY"
```

### Create Connection

```bash
curl -X POST "https://api.integrator.io/v1/connections" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New REST Connection",
    "type": "http",
    "_integrationId": "integration_id_here",
    "http": {
      "baseURI": "https://api.example.com",
      "auth": {
        "type": "basic",
        "basic": {
          "username": "user",
          "password": "password"
        }
      }
    }
  }'
```

### Update Connection

```bash
curl -X PUT "https://api.integrator.io/v1/connections/{connection_id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Connection Name",
    "http": {
      "baseURI": "https://new-api.example.com"
    }
  }'
```

### Delete Connection

```bash
curl -X DELETE "https://api.integrator.io/v1/connections/{connection_id}" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:** 204 No Content

**Warning:** Cannot delete connections in use by flows.

### Test Connection (Ping)

```bash
curl -X POST "https://api.integrator.io/v1/connections/{connection_id}/ping" \
  -H "Authorization: Bearer $API_KEY"
```

**Success Response:**
```json
{
  "success": true,
  "message": "Connection successful"
}
```

**Failure Response:**
```json
{
  "success": false,
  "message": "Authentication failed",
  "details": "Invalid credentials"
}
```

### Get Debug Log

```bash
curl -X GET "https://api.integrator.io/v1/connections/{connection_id}/debuglog" \
  -H "Authorization: Bearer $API_KEY"
```

Returns detailed request/response logs for debugging.

### Get Dependencies

```bash
curl -X GET "https://api.integrator.io/v1/connections/{connection_id}/dependencies" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
{
  "integrations": [{"_id": "int1", "name": "My Integration"}],
  "flows": [{"_id": "flow1", "name": "Customer Sync"}],
  "exports": [{"_id": "exp1", "name": "Customer Export"}],
  "imports": [{"_id": "imp1", "name": "Customer Import"}]
}
```

## Common Connection Configurations

### Salesforce
```json
{
  "name": "Salesforce Production",
  "type": "salesforce",
  "_integrationId": "int123",
  "salesforce": {
    "environment": "production",
    "oauth": {
      "clientId": "your_client_id",
      "clientSecret": "your_client_secret"
    }
  }
}
```

### NetSuite (Token-Based)
```json
{
  "name": "NetSuite Production",
  "type": "netsuite",
  "_integrationId": "int123",
  "netsuite": {
    "accountId": "1234567",
    "tokenAuth": {
      "consumerKey": "consumer_key",
      "consumerSecret": "consumer_secret",
      "tokenId": "token_id",
      "tokenSecret": "token_secret"
    }
  }
}
```

### FTP/SFTP
```json
{
  "name": "SFTP Server",
  "type": "ftp",
  "ftp": {
    "host": "sftp.example.com",
    "port": 22,
    "protocol": "sftp",
    "username": "user",
    "password": "password",
    "path": "/uploads"
  }
}
```

### MongoDB
```json
{
  "name": "MongoDB Atlas",
  "type": "mongodb",
  "mongodb": {
    "connectionString": "mongodb+srv://user:pass@cluster.mongodb.net/database"
  }
}
```

## Error Handling

### Connection in Use
```json
{
  "errors": [{
    "code": "conflict",
    "message": "Cannot delete connection - in use by 3 flows"
  }]
}
```

### Invalid Credentials
```json
{
  "errors": [{
    "code": "authentication_failed",
    "message": "Unable to authenticate with provided credentials"
  }]
}
```

### Network Error
```json
{
  "errors": [{
    "code": "connection_failed",
    "message": "Unable to reach host: Connection timed out"
  }]
}
```

## Best Practices

1. **Test after creation**: Always ping new connections
2. **Use descriptive names**: Include environment (prod/sandbox)
3. **Rotate credentials**: Update passwords/keys regularly
4. **Monitor usage**: Check logs for failures
5. **Clean up**: Remove unused connections
