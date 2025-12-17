# Shopify Workflows

Shopify Admin API workflow automation with 5 specialized skills for content creation, merchant operations, marketing campaigns, developer integrations, and analytics.

## Skills Included

| Skill | Purpose | Required Scopes |
|-------|---------|-----------------|
| **shopify-content-creator** | Blog articles, pages, theme assets | `write_content`, `write_themes` |
| **shopify-merchant-daily** | Products, inventory, orders, customers | `write_products`, `write_inventory`, `write_orders`, `write_customers` |
| **shopify-marketing-ops** | Discounts, price rules, campaigns | `write_discounts`, `write_price_rules`, `write_marketing_events`, `read_analytics` |
| **shopify-developer** | Metafields, webhooks, script tags | `write_metafields`, `write_webhooks`, `write_script_tags` |
| **shopify-analytics** | Reports, analytics queries | `read_analytics`, `read_reports`, `read_orders`, `read_customers` |

## Quick Start

### 1. Create Configuration

```bash
cd plugins/shopify-workflows
cp config/shopify_config.template.json config/shopify_config.json
```

### 2. Get OAuth Credentials

1. Go to [Shopify Partner Dashboard](https://partners.shopify.com/)
2. Select your app → **Settings**
3. Copy **Client ID** and **Client Secret**
4. Configure required scopes under **API access**

### 3. Configure Your Store

Edit `config/shopify_config.json`:

```json
{
  "stores": {
    "my-store": {
      "name": "My Store",
      "shop_domain": "my-store.myshopify.com",
      "api_version": "2024-10"
    }
  },
  "oauth": {
    "client_id": "your-client-id-here",
    "client_secret": "your-client-secret-here"
  },
  "defaults": {
    "store": "my-store"
  }
}
```

### 4. Get Access Token

```bash
# Get token (valid for 24 hours)
python3 scripts/shopify_auth.py --get-token

# Test token works
python3 scripts/shopify_auth.py --test

# View token info
python3 scripts/shopify_auth.py --info
```

### 5. Use in API Requests

```bash
# Get token for use in scripts
TOKEN=$(python3 scripts/shopify_auth.py --token)

# Use with curl
curl -X POST \
  "https://my-store.myshopify.com/admin/api/2024-10/graphql.json" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: $TOKEN" \
  -d '{"query": "{ shop { name } }"}'
```

## Token Management

Tokens expire after **24 hours** (86399 seconds). The auth script handles this automatically:

- Caches tokens in `config/.shopify_tokens.json` (gitignored)
- Checks expiration with 1-hour buffer
- Auto-refreshes when needed via `--token` flag

### Multi-Store Support

Configure multiple stores in your config:

```json
{
  "stores": {
    "production": {
      "name": "Production Store",
      "shop_domain": "my-store.myshopify.com"
    },
    "staging": {
      "name": "Staging Store",
      "shop_domain": "my-store-staging.myshopify.com"
    }
  }
}
```

Then specify which store to use:

```bash
python3 scripts/shopify_auth.py --get-token --store staging
python3 scripts/shopify_auth.py --token --store production
```

## How Skills Work

These skills provide **domain knowledge** for Shopify operations:

1. **Claude** uses the skill to understand Shopify patterns and best practices
2. **Shopify Dev MCP** (if installed) validates GraphQL syntax
3. **You execute** the actual API calls using the auth token

The skills do NOT execute mutations directly—they guide Claude to generate correct GraphQL and help you implement the HTTP layer.

## Files

```
shopify-workflows/
├── README.md                    # This file
├── AUTHENTICATION.md            # Detailed OAuth documentation
├── ECOMMERCE_OPTIMIZATION.md    # E-commerce best practices
├── plugin.json
├── config/
│   ├── shopify_config.template.json  # Config template (copy this)
│   ├── shopify_config.json           # Your config (gitignored)
│   └── .shopify_tokens.json          # Token cache (gitignored)
├── scripts/
│   └── shopify_auth.py          # Token management script
└── skills/
    ├── shopify-content-creator/
    ├── shopify-merchant-daily/
    ├── shopify-marketing-ops/
    ├── shopify-developer/
    └── shopify-analytics/
```

## See Also

- [AUTHENTICATION.md](./AUTHENTICATION.md) - Complete OAuth flow documentation with code examples
- [Shopify Admin API](https://shopify.dev/docs/api/admin-graphql) - Official API docs
- [Access Scopes](https://shopify.dev/docs/api/usage/access-scopes) - Scope reference
