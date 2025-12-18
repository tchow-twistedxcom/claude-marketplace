# Plytix API Skill

Comprehensive CLI for Plytix PIM (Product Information Management) system.

## Prerequisites

- Python 3.8+
- Plytix account with API access
- API Key and API Password from [accounts.plytix.com](https://accounts.plytix.com)

## Installation

1. **Copy the config template**:
   ```bash
   cd skills/plytix-api
   cp config/plytix_config.template.json config/plytix_config.json
   ```

2. **Edit the config file** with your credentials:
   ```json
   {
     "accounts": {
       "production": {
         "name": "Production",
         "api_url": "https://pim.plytix.com/api/v1",
         "auth_url": "https://auth.plytix.com/auth/api/get-token",
         "api_key": "your-api-key-here",
         "api_password": "your-api-password-here"
       }
     }
   }
   ```

3. **Test the connection**:
   ```bash
   python scripts/auth.py --test
   ```

## Getting API Credentials

1. Log in to [accounts.plytix.com](https://accounts.plytix.com)
2. Navigate to **Settings** → **API**
3. Create a new API key if needed
4. Copy the **API Key** and **API Password**
5. Store securely in your config file

## Quick Start

```bash
# List products
python scripts/plytix_api.py products list

# Get specific product
python scripts/plytix_api.py products get <product_id>

# Search products by SKU
python scripts/plytix_api.py products search --filters '[{"field":"sku","operator":"contains","value":"ABC"}]'

# View as JSON
python scripts/plytix_api.py products list --format json

# Use staging account
python scripts/plytix_api.py products list --account staging
```

## Multi-Environment Setup

For production and staging environments:

```json
{
  "accounts": {
    "production": {
      "name": "Production",
      "api_url": "https://pim.plytix.com/api/v1",
      "auth_url": "https://auth.plytix.com/auth/api/get-token",
      "api_key": "PROD_API_KEY",
      "api_password": "PROD_API_PASSWORD"
    },
    "staging": {
      "name": "Staging",
      "api_url": "https://pim.plytix.com/api/v1",
      "auth_url": "https://auth.plytix.com/auth/api/get-token",
      "api_key": "STAGING_API_KEY",
      "api_password": "STAGING_API_PASSWORD"
    }
  },
  "defaults": {
    "account": "production"
  },
  "aliases": {
    "prod": "production",
    "stg": "staging"
  }
}
```

## Security

**Important**: Never commit your actual credentials!

Files that should NOT be committed:
- `config/plytix_config.json` - Contains your API credentials
- `config/.token_cache.json` - Contains cached access tokens

These are already in `.gitignore`.

## Troubleshooting

### Authentication Failed
- Verify your API key and password are correct
- Check if your API access is enabled in Plytix settings
- Try clearing the token cache: `python scripts/auth.py --clear-cache`

### Rate Limited (429)
- The CLI handles rate limiting automatically
- If persistent, reduce request frequency
- Check your Plytix plan's API limits

### Network Errors
- Verify internet connectivity
- Check if Plytix API is accessible
- Verify firewall/proxy settings

## Support

- **Plytix API Docs**: https://apidocs.plytix.com
- **Plytix Help Center**: https://help.plytix.com/en/api
- **Plytix Support**: support@plytix.com
