---
name: spapi-setup
description: Set up Amazon SP-API CLI configuration and OAuth authentication for Vendor (1P) operations
---

# Amazon SP-API Setup Guide

This guide helps you configure the Amazon Selling Partner API (SP-API) CLI for Vendor Central operations.

## Prerequisites

1. **Python 3.8+** installed
2. **Amazon Vendor Central account** with API access
3. **SP-API Developer Application** registered in Seller/Vendor Central

## Step 1: Register Your Application

### For Private/Internal Apps (Recommended for Vendors)

1. Go to **Vendor Central** → **Integration** → **API Integration**
2. Or visit: https://vendorcentral.amazon.com/
3. Navigate to **Partner Network** → **Develop Apps**
4. Click **Add new app client**
5. Fill in app details:
   - App name: Your internal name
   - App type: **Private** (for internal use)
   - API Type: **SP-API**
6. Select required **API Permissions**:
   - Vendor Orders (for purchase orders)
   - Vendor Shipments (for ASN/shipping)
   - Vendor Invoices (for invoice submission)
   - Reports (for vendor reports)

### Required Permissions for Vendor Operations

| Permission | Use Case |
|------------|----------|
| Vendor Orders | Purchase order retrieval and acknowledgment |
| Vendor Shipments | ASN submission, label generation |
| Vendor Invoices | Invoice and credit memo submission |
| Reports | Vendor inventory, sales reports |
| Catalog Items | Product catalog access |
| Notifications | Event subscriptions |

## Step 2: Create LWA Credentials

1. After app creation, you'll see **LWA credentials**:
   - **Client ID**: `amzn1.application-oa2-client.xxxx`
   - **Client Secret**: Keep this secure!

2. For **Self-Authorization** (private apps):
   - Click **Authorize** on your app
   - This generates a **Refresh Token** automatically
   - Max 10 self-authorizations per app

3. Save your credentials securely:
   ```
   Client ID: amzn1.application-oa2-client.xxxxx
   Client Secret: your-client-secret
   Refresh Token: Atzr|xxxxx
   ```

## Step 3: Configure the CLI

### Copy the Config Template

```bash
cd plugins/amazon-spapi/config
cp spapi_config.template.json spapi_config.json
```

### Edit spapi_config.json

```json
{
  "default_profile": "production",
  "profiles": {
    "production": {
      "name": "Production - US",
      "region": "NA",
      "marketplace": "US",
      "lwa_client_id": "amzn1.application-oa2-client.xxxxx",
      "lwa_client_secret": "your-actual-client-secret",
      "refresh_token": "Atzr|your-actual-refresh-token",
      "selling_partner_id": "your-vendor-code"
    }
  }
}
```

### Regional Configuration

| Region | Code | Endpoint | Marketplaces |
|--------|------|----------|--------------|
| North America | NA | sellingpartnerapi-na.amazon.com | US, CA, MX, BR |
| Europe | EU | sellingpartnerapi-eu.amazon.com | UK, DE, FR, IT, ES, NL, SE, PL, TR, AE, SA, IN |
| Far East | FE | sellingpartnerapi-fe.amazon.com | JP, AU, SG |

### Multiple Marketplace Setup

For vendors operating in multiple marketplaces:

```json
{
  "default_profile": "us_production",
  "profiles": {
    "us_production": {
      "region": "NA",
      "marketplace": "US",
      "lwa_client_id": "...",
      "lwa_client_secret": "...",
      "refresh_token": "..."
    },
    "uk_production": {
      "region": "EU",
      "marketplace": "UK",
      "lwa_client_id": "...",
      "lwa_client_secret": "...",
      "refresh_token": "..."
    },
    "de_production": {
      "region": "EU",
      "marketplace": "DE",
      "lwa_client_id": "...",
      "lwa_client_secret": "...",
      "refresh_token": "..."
    }
  }
}
```

## Step 4: Test Authentication

### Verify Configuration

```bash
cd plugins/amazon-spapi/scripts

# List available profiles
python3 spapi_auth.py profiles

# Test authentication
python3 spapi_auth.py test

# Test specific profile
python3 spapi_auth.py --profile uk_production test

# Check token info
python3 spapi_auth.py info
```

### Expected Output

```
Testing authentication for profile: production
Success! Token: Atza|xxxxx...xxxxx
Endpoint: https://sellingpartnerapi-na.amazon.com
Marketplace ID: ATVPDKIKX0DER
```

## Step 5: Security Best Practices

### Protect Your Credentials

1. **Never commit** `spapi_config.json` to version control
2. The config directory has `.gitignore` entries for sensitive files
3. Use environment-specific profiles (sandbox for testing)

### Token Caching

- Access tokens are cached in `.spapi_token_cache.json`
- Tokens expire after **1 hour**
- Automatic refresh when expired
- Clear cache if you encounter auth issues:

```bash
python3 spapi_auth.py clear
```

### Restricted Data Tokens (RDT)

For accessing PII (buyer addresses, etc.), the CLI automatically handles RDT:

```python
# Automatic RDT for buyer info
status, data = client.get(
    "/orders/v0/orders/123/buyerInfo",
    use_rdt=True,
    rdt_elements=["buyerInfo"]
)
```

## Troubleshooting

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `401 Unauthorized` | Invalid credentials | Check client_id/secret |
| `403 Forbidden` | Missing permissions | Add required scopes to app |
| `429 Too Many Requests` | Rate limited | CLI handles retry automatically |
| `invalid_grant` | Expired refresh token | Re-authorize the app |

### Re-Authorization Required When

- Refresh token expires (rare, but possible)
- Adding new API permissions
- Annual authorization renewal (for public apps)

### Debug Mode

For detailed request logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Next Steps

Once setup is complete:

1. Use `/amazon-spapi:spapi-manage` for CLI operations
2. Explore vendor skills:
   - `spapi-vendor-orders` - Purchase order management
   - `spapi-vendor-shipments` - ASN and shipping
   - `spapi-vendor-invoices` - Invoice submission
3. Check `spapi-integration-patterns` for best practices

## Resources

- [SP-API Developer Guide](https://developer-docs.amazon.com/sp-api/)
- [API Models (GitHub)](https://github.com/amzn/selling-partner-api-models)
- [Vendor Central Help](https://vendorcentral.amazon.com/help)
- [Rate Limits Reference](https://developer-docs.amazon.com/sp-api/docs/usage-plans-and-rate-limits)
