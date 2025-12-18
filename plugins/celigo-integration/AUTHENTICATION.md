# Celigo Authentication Guide

## Overview

Celigo integrator.io uses **API Key authentication** (Bearer tokens). Each API key is tied to your user account and inherits your permissions.

## Quick Start

### 1. Get Your API Key

1. Log in to [integrator.io](https://integrator.io)
2. Click your profile icon (top-right) → **My Account**
3. Go to **API Tokens** section
4. Click **Generate New Token**
5. Give it a descriptive name (e.g., "Claude Automation")
6. Copy the token immediately (it won't be shown again!)

### 2. Configure the Plugin

```bash
cd plugins/celigo-integration
cp config/celigo_config.template.json config/celigo_config.json
```

Edit `config/celigo_config.json`:

```json
{
  "environments": {
    "production": {
      "name": "Production",
      "api_url": "https://api.integrator.io/v1",
      "api_key": "YOUR_API_KEY_HERE"
    }
  },
  "defaults": {
    "environment": "production"
  }
}
```

### 3. Test Your Configuration

```bash
python3 scripts/celigo_auth.py --test
```

Expected output:
```
Testing API key for: Production
API URL: https://api.integrator.io/v1

API Key: VALID
Status: 200
Found 5 integration(s)
```

## API Request Format

All Celigo API requests require:

```http
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
Accept: application/json
```

### Example: List Integrations

```bash
# Get your API key
API_KEY=$(python3 scripts/celigo_auth.py --key)

# Make request
curl -X GET "https://api.integrator.io/v1/integrations" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json"
```

### Example: Get Specific Integration

```bash
curl -X GET "https://api.integrator.io/v1/integrations/{integration_id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json"
```

## Multi-Environment Setup

For production and sandbox environments:

```json
{
  "environments": {
    "production": {
      "name": "Production",
      "api_url": "https://api.integrator.io/v1",
      "api_key": "prod_api_key_here"
    },
    "sandbox": {
      "name": "Sandbox",
      "api_url": "https://api.integrator.io/v1",
      "api_key": "sandbox_api_key_here"
    }
  },
  "defaults": {
    "environment": "production"
  }
}
```

Switch environments:

```bash
# Test sandbox
python3 scripts/celigo_auth.py --test --env sandbox

# Get sandbox API key
python3 scripts/celigo_auth.py --key --env sandbox
```

## Auth Helper Commands

```bash
# Test API key validity
python3 scripts/celigo_auth.py --test

# Print API key for scripting
python3 scripts/celigo_auth.py --key

# Show configuration info
python3 scripts/celigo_auth.py --info

# Generate curl command
python3 scripts/celigo_auth.py --curl /integrations
```

## API Permissions

Your API key inherits your user permissions:

| Permission | Allows |
|------------|--------|
| **Viewer** | GET operations only |
| **Editor** | GET, POST, PUT operations |
| **Admin** | All operations including DELETE |

Ensure your user has appropriate permissions for intended operations.

## Security Best Practices

1. **Never commit API keys** - The config file is gitignored
2. **Use separate keys** per environment (prod/sandbox)
3. **Rotate keys** periodically (recommend 90 days)
4. **Revoke unused keys** from integrator.io
5. **Use minimum permissions** required for your use case

## Troubleshooting

### Invalid API Key (401)

```
API Key: INVALID
Status: 401
Error: Unauthorized
```

**Solutions:**
- Verify key is copied correctly (no extra spaces)
- Check key hasn't been revoked in integrator.io
- Generate a new key if needed

### Forbidden (403)

```
Status: 403
Error: Forbidden
```

**Solutions:**
- Your user lacks permissions for this operation
- Request elevated permissions from your admin

### Rate Limited (429)

```
Status: 429
Error: Too Many Requests
```

**Solutions:**
- Implement exponential backoff
- Reduce request frequency
- Contact Celigo support for rate limit increase

## API Base URLs

| Environment | Base URL |
|-------------|----------|
| Production | `https://api.integrator.io/v1` |
| EU Region | `https://api.eu.integrator.io/v1` |

Note: Use the appropriate base URL for your account region.
