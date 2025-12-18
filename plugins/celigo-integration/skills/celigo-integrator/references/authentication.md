# Celigo Authentication Reference

## API Key Authentication

Celigo uses Bearer token authentication. API keys are tied to user accounts.

### Request Header
```http
Authorization: Bearer YOUR_API_KEY
```

### Full Request Example
```bash
curl -X GET "https://api.integrator.io/v1/integrations" \
  -H "Authorization: Bearer abc123xyz789" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json"
```

## Getting an API Key

1. Log in to [integrator.io](https://integrator.io)
2. Click profile icon → **My Account**
3. Navigate to **API Tokens**
4. Click **Generate New Token**
5. Name your token descriptively
6. **Copy immediately** (won't be shown again)

## API Key Permissions

API keys inherit the user's permissions:

| Role | Capabilities |
|------|-------------|
| Viewer | GET operations only |
| Editor | GET, POST, PUT |
| Admin | All operations including DELETE |

## Environment-Specific Keys

Best practice: Separate keys per environment.

```json
{
  "production": {
    "api_key": "prod_key_here"
  },
  "sandbox": {
    "api_key": "sandbox_key_here"
  }
}
```

## Token Security

### Do's
- Store keys securely (env vars, secrets manager)
- Use separate keys per application
- Rotate keys periodically (90 days)
- Revoke unused keys immediately

### Don'ts
- Never commit keys to version control
- Don't share keys between environments
- Don't embed keys in client-side code
- Never log API keys

## Testing Authentication

```bash
# Quick test
curl -X GET "https://api.integrator.io/v1/integrations?limit=1" \
  -H "Authorization: Bearer $API_KEY"
```

### Success Response (200)
```json
[{"_id": "abc123", "name": "Test Integration"}]
```

### Invalid Key Response (401)
```json
{
  "errors": [{
    "code": "unauthorized",
    "message": "Invalid or missing API key"
  }]
}
```

## Common Authentication Errors

### 401 Unauthorized
**Causes:**
- Missing Authorization header
- Invalid/expired API key
- Malformed Bearer token

**Solutions:**
```bash
# Check header format
-H "Authorization: Bearer $API_KEY"  # Correct
-H "Authorization: $API_KEY"          # Wrong
-H "Bearer $API_KEY"                  # Wrong
```

### 403 Forbidden
**Causes:**
- Valid key but insufficient permissions
- Resource belongs to different account

**Solutions:**
- Check user role in integrator.io
- Verify resource ownership
- Request elevated permissions

## Rate Limiting

API keys are rate-limited per account:
- Response: 429 Too Many Requests
- `Retry-After` header indicates wait time

```python
import time

def handle_rate_limit(response):
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        time.sleep(retry_after)
        return True
    return False
```

## Multi-Region Support

Different base URLs per region:

| Region | Base URL |
|--------|----------|
| US (default) | `https://api.integrator.io/v1` |
| EU | `https://api.eu.integrator.io/v1` |

API keys work only in their home region.

## Helper Script Usage

```bash
# Test API key
python3 scripts/celigo_auth.py --test

# Get key for scripting
API_KEY=$(python3 scripts/celigo_auth.py --key)

# Show config info
python3 scripts/celigo_auth.py --info

# Generate curl command
python3 scripts/celigo_auth.py --curl /integrations
```

## Programmatic Authentication

### Python
```python
import requests

API_KEY = "your_api_key"
BASE_URL = "https://api.integrator.io/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

response = requests.get(f"{BASE_URL}/integrations", headers=headers)
```

### JavaScript/Node.js
```javascript
const API_KEY = process.env.CELIGO_API_KEY;
const BASE_URL = 'https://api.integrator.io/v1';

const response = await fetch(`${BASE_URL}/integrations`, {
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json'
  }
});
```

### cURL with Environment Variable
```bash
export CELIGO_API_KEY="your_api_key"

curl -X GET "https://api.integrator.io/v1/integrations" \
  -H "Authorization: Bearer $CELIGO_API_KEY" \
  -H "Content-Type: application/json"
```
