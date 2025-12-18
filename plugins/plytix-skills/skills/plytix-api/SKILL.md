---
name: plytix-api
description: |
  Plytix PIM API operations. Use when user mentions: plytix, PIM, product information management,
  product catalog management, digital asset management (DAM) with products, SKU/GTIN/EAN/UPC management,
  product variants, product categories, product attributes, or needs to manage product data at scale.
  Provides full CRUD for Products, Assets, Categories, Variants, and Attributes.
version: 1.0.0
author: tchow
triggers:
  - plytix
  - pim
  - product information management
  - product catalog
  - digital asset management
  - sku management
  - product variants
  - product attributes
---

# Plytix PIM API Skill

Full REST API coverage for Plytix Product Information Management system.

## Quick Reference

| Domain | Operations |
|--------|------------|
| Products | list, get, create, update, delete, search, bulk-update, add-assets, add-categories |
| Assets | list, get, upload, update, delete, search, download-url |
| Categories | list, get, create, update, delete, tree, list-products |
| Variants | list, get, create, update, delete, bulk-create |
| Attributes | list, get, create, update, delete |

## Setup

1. **Get API credentials** from [accounts.plytix.com](https://accounts.plytix.com)
2. **Copy config template**:
   ```bash
   cp config/plytix_config.template.json config/plytix_config.json
   ```
3. **Edit config** with your credentials:
   ```json
   {
     "accounts": {
       "production": {
         "api_key": "YOUR_API_KEY",
         "api_password": "YOUR_API_PASSWORD"
       }
     }
   }
   ```
4. **Test connection**:
   ```bash
   python scripts/auth.py --test
   ```

## Usage Examples

### Products

```bash
# List products
python scripts/plytix_api.py products list --limit 50

# Get product details
python scripts/plytix_api.py products get <product_id>

# Search products
python scripts/plytix_api.py products search --filters '[{"field":"sku","operator":"contains","value":"ABC"}]'

# Create product
python scripts/plytix_api.py products create --data '{"sku":"SKU-001","label":"New Product"}'

# Update product
python scripts/plytix_api.py products update <product_id> --data '{"label":"Updated Name"}'

# Add assets to product
python scripts/plytix_api.py products add-assets <product_id> --asset-ids "asset1,asset2"
```

### Assets

```bash
# List assets
python scripts/plytix_api.py assets list --limit 100

# Upload asset from URL
python scripts/plytix_api.py assets upload --url "https://example.com/image.jpg"

# Get download URL
python scripts/plytix_api.py assets download-url <asset_id>

# Search assets
python scripts/plytix_api.py assets search --filters '[{"field":"file_type","operator":"eq","value":"image/jpeg"}]'
```

### Categories

```bash
# Get category tree
python scripts/plytix_api.py categories tree

# List products in category
python scripts/plytix_api.py categories list-products <category_id>

# Create category
python scripts/plytix_api.py categories create --data '{"label":"New Category","parent_id":"parent123"}'
```

### Variants

```bash
# List variants for product
python scripts/plytix_api.py variants list --product-id <product_id>

# Create variant
python scripts/plytix_api.py variants create <product_id> --data '{"sku":"VAR-001","label":"Size Large"}'

# Bulk create variants
python scripts/plytix_api.py variants bulk-create <product_id> --data '[{"sku":"VAR-S"},{"sku":"VAR-M"},{"sku":"VAR-L"}]'
```

### Attributes

```bash
# List attributes
python scripts/plytix_api.py attributes list

# Create attribute
python scripts/plytix_api.py attributes create --data '{"label":"Color","type_class":"select","options":["Red","Blue","Green"]}'
```

**Note:** Attribute groups are not available via API. Use the Plytix UI to manage groups.

## Multi-Account Support

Use the `--account` flag to switch between environments:

```bash
# Production (default)
python scripts/plytix_api.py products list

# Staging
python scripts/plytix_api.py products list --account staging

# Using alias
python scripts/plytix_api.py products list -a stg
```

## Output Formats

```bash
# Table (default)
python scripts/plytix_api.py products list

# JSON
python scripts/plytix_api.py products list --format json

# Compact
python scripts/plytix_api.py products list --format compact

# Summary
python scripts/plytix_api.py products list --format summary
```

## Authentication Flow

1. API Key + Password sent to auth endpoint
2. Access token returned and cached
3. Token auto-refreshes before expiry
4. Tokens persist across sessions

## File Structure

```
skills/plytix-api/
├── SKILL.md                    # This file
├── README.md                   # Setup guide
├── config/
│   ├── plytix_config.template.json  # Template (safe to commit)
│   ├── plytix_config.json           # Your config (DO NOT commit)
│   └── .token_cache.json            # Token cache (auto-generated)
├── scripts/
│   ├── auth.py                      # Authentication module
│   ├── plytix_api.py                # Main CLI
│   └── formatters.py                # Output formatting
└── references/
    ├── products_api.md
    ├── assets_api.md
    ├── categories_api.md
    ├── variants_api.md
    └── attributes_api.md
```

## API Reference

- **Base URL**: `https://pim.plytix.com/api/v1`
- **Auth URL**: `https://auth.plytix.com/auth/api/get-token`
- **Docs**: [apidocs.plytix.com](https://apidocs.plytix.com)
- **Help**: [help.plytix.com/en/api](https://help.plytix.com/en/api)

## Rate Limits

Plytix API returns 429 status with `Retry-After` header when rate limited.
The CLI handles this automatically with exponential backoff.

## Security Notes

- **NEVER commit** `plytix_config.json` or `.token_cache.json`
- Store credentials securely
- Use environment-specific accounts for prod/staging
- Rotate API credentials periodically
