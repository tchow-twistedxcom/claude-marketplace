# Plytix Skills Plugin

Plytix PIM (Product Information Management) operations via REST API.

## Features

- **Products**: Full CRUD, search, bulk updates, asset/category linking
- **Assets**: Upload, manage, search digital assets
- **Categories**: Hierarchical category management with tree view
- **Variants**: Product variant management with bulk operations
- **Attributes**: Schema management, attribute groups

## Skills

### plytix-api

Full API coverage for Plytix PIM system.

```bash
# Products
python scripts/plytix_api.py products list
python scripts/plytix_api.py products search --filters '[...]'

# Assets
python scripts/plytix_api.py assets list
python scripts/plytix_api.py assets upload --url "https://..."

# Categories
python scripts/plytix_api.py categories tree

# Variants
python scripts/plytix_api.py variants list --product-id <id>

# Attributes
python scripts/plytix_api.py attributes list
```

## Setup

1. Get API credentials from [accounts.plytix.com](https://accounts.plytix.com)
2. Copy `config/plytix_config.template.json` to `config/plytix_config.json`
3. Add your API key and password
4. Test: `python scripts/auth.py --test`

See `skills/plytix-api/README.md` for detailed setup instructions.

## Multi-Account Support

Supports multiple environments (production, staging) with account aliases.

```bash
# Default (production)
python scripts/plytix_api.py products list

# Staging
python scripts/plytix_api.py products list --account staging
python scripts/plytix_api.py products list -a stg
```

## Security

- Config template is safe to commit
- Actual config with credentials is NOT committed
- Token cache is NOT committed
- See `.gitignore` for excluded files
