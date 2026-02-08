# Environment Routing

How the NetSuite API Gateway selects which environment to use for API requests.

## Overview

The gateway supports 3 NetSuite environments:
- **production** - Live production account (4138030)
- **sandbox** - Primary sandbox (4138030_SB1)
- **sandbox2** - Secondary sandbox (4138030_SB2)

## Environment Selection Priority

The gateway checks for environment specification in this order (highest to lowest):

| Priority | Method | Parameter | Example |
|----------|--------|-----------|---------|
| 1 (Highest) | Request Body | `netsuiteEnvironment` | `{"netsuiteEnvironment": "sandbox2"}` |
| 2 | Query String | `netsuiteEnvironment` | `?netsuiteEnvironment=sandbox2` |
| 3 (Lowest) | HTTP Header | `X-NetSuite-Environment` | `X-NetSuite-Environment: sandbox2` |

If no environment is specified, the gateway uses the **default environment** configured in the gateway settings (typically `production`).

## Configuration Location

Environment credentials are configured in the gateway's config directory:

```
~/NetSuiteApiGateway/config/
├── oauth.json      # OAuth 1.0a credentials per environment
├── oauth2.json     # OAuth 2.0 credentials per environment
└── apps.json       # App configurations with optional restletId overrides
```

### oauth.json Structure

```json
{
  "environments": {
    "production": {
      "realm": "4138030",
      "accountId": "4138030",
      "tokenEndpoint": "https://4138030.suitetalk.api.netsuite.com/services/rest/auth/oauth2/v1/token",
      "baseUrl": "https://4138030.restlets.api.netsuite.com",
      "credentials": {
        "consumerKey": "${NETSUITE_CONSUMER_KEY}",
        "consumerSecret": "${NETSUITE_CONSUMER_SECRET}",
        "tokenId": "${NETSUITE_TOKEN_ID}",
        "tokenSecret": "${NETSUITE_TOKEN_SECRET}"
      }
    },
    "sandbox2": {
      "realm": "4138030_SB2",
      "accountId": "4138030_SB2",
      "tokenEndpoint": "https://4138030-sb2.suitetalk.api.netsuite.com/services/rest/auth/oauth2/v1/token",
      "baseUrl": "https://4138030-sb2.restlets.api.netsuite.com",
      "credentials": {
        "consumerKey": "${NETSUITE_SB2_CONSUMER_KEY}",
        "consumerSecret": "${NETSUITE_SB2_CONSUMER_SECRET}",
        "tokenId": "${NETSUITE_SB2_TOKEN_ID}",
        "tokenSecret": "${NETSUITE_SB2_TOKEN_SECRET}"
      }
    }
  }
}
```

## Common Issues

### 1. Environment Not Being Read

**Symptom**: Requests always go to production even when specifying another environment.

**Causes**:
- Using wrong parameter name (e.g., `environment` instead of `netsuiteEnvironment`)
- Header name mismatch (must be exactly `X-NetSuite-Environment`)
- Body parameter not being parsed (check Content-Type header)

**Debug**:
```bash
# Test with curl
curl -s "http://localhost:3001/api/homepage?action=getConfig" \
  -H "X-NetSuite-Environment: sandbox2" | jq '.environment'
```

### 2. OAuth Credentials Invalid

**Symptom**: `401 Unauthorized` or OAuth signature errors.

**Causes**:
- Wrong credentials for the target environment
- Environment variables not set
- Token expired or revoked

**Debug**:
```bash
# Run config validation
python3 validate_config.py --verbose
```

### 3. restletId Mismatch

**Symptom**: `Script not found` or wrong data returned.

**Cause**: Each environment may have different script deployment IDs.

**Solution**: Use `restletIdOverrides` in apps.json:
```json
{
  "apps": {
    "homepage": {
      "restletId": "2274",
      "deployId": "1",
      "restletIdOverrides": {
        "sandbox2": "2280"
      }
    }
  }
}
```

## Testing Environments

Use the `test_environments.py` script to verify all environments work:

```bash
# Test all environments
python3 test_environments.py

# Test specific environment
python3 test_environments.py --env sandbox2

# Generate curl commands for manual testing
python3 test_environments.py --curl
```

## Frontend Integration

When calling from a frontend application:

```typescript
// Set environment via header
const response = await fetch('/api/homepage?action=getData', {
  headers: {
    'Content-Type': 'application/json',
    'X-NetSuite-Environment': 'sandbox2'
  }
});

// Or via query parameter
const response = await fetch('/api/homepage?action=getData&netsuiteEnvironment=sandbox2');

// Or via request body (POST only)
const response = await fetch('/api/homepage', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    action: 'getData',
    netsuiteEnvironment: 'sandbox2'
  })
});
```

## Error Messages

When environment routing fails, error responses now include the attempted environment:

```json
{
  "success": false,
  "error": {
    "code": "OAUTH_ERROR",
    "message": "Invalid credentials for environment"
  },
  "environment": "sandbox2"
}
```

This helps identify which environment credentials need to be fixed.
