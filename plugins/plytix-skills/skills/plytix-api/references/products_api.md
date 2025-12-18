# Products API Reference

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/products/search` | List/search products |
| GET | `/products/{id}` | Get product by ID |
| POST | `/products` | Create product |
| PATCH | `/products/{id}` | Update product |
| DELETE | `/products/{id}` | Delete product |
| POST | `/products/bulk` | Bulk update |
| POST | `/products/{id}/assets` | Add assets |
| DELETE | `/products/{id}/assets` | Remove assets |
| POST | `/products/{id}/categories` | Add to categories |
| DELETE | `/products/{id}/categories` | Remove from categories |

**Note:** Plytix uses POST-based search for listing products. The CLI abstracts this into simple `list` and `search` commands.

## CLI Commands

### List Products

```bash
python scripts/plytix_api.py products list [options]

Options:
  --limit, -l    Results per page (default: 50)
  --page, -p     Page number (default: 1)
  --sort-by      Sort field
  --sort-order   asc or desc (default: asc)
  --format, -f   Output format: table, json, compact, summary
```

### Get Product

```bash
python scripts/plytix_api.py products get <product_id>
```

### Create Product

```bash
python scripts/plytix_api.py products create --data '<json>'

# Example
python scripts/plytix_api.py products create --data '{
  "sku": "SKU-001",
  "label": "Product Name",
  "attributes": {
    "description": "Product description",
    "price": 99.99
  }
}'
```

### Update Product

```bash
python scripts/plytix_api.py products update <product_id> --data '<json>'

# Example
python scripts/plytix_api.py products update abc123 --data '{
  "label": "Updated Name",
  "attributes": {"price": 89.99}
}'
```

### Delete Product

```bash
python scripts/plytix_api.py products delete <product_id>
```

### Search Products

```bash
python scripts/plytix_api.py products search [options]

Options:
  --filters      JSON array of filter objects
  --attributes   Comma-separated attribute names to return
  --limit, -l    Results per page
  --page, -p     Page number

# Filter operators: like, !like, eq, !eq, in, !in, gt, gte, lt, lte, last_days
# IMPORTANT: Use 'like' for text search, NOT 'contains'
```

**Filter Examples:**

```bash
# By SKU contains (use 'like' operator)
--filters '[{"field":"sku","operator":"like","value":"ABC"}]'

# By status
--filters '[{"field":"status","operator":"eq","value":"active"}]'

# By modified date
--filters '[{"field":"modified","operator":"gte","value":"2024-01-01"}]'

# Modified in last 7 days
--filters '[{"field":"modified","operator":"last_days","value":7}]'

# Multiple filters (AND)
--filters '[
  {"field":"sku","operator":"like","value":"ABC"},
  {"field":"status","operator":"eq","value":"active"}
]'
```

See [filters_api.md](filters_api.md) for complete filter documentation.

### Bulk Update

```bash
python scripts/plytix_api.py products bulk-update --data '<json array>'

# Example - update multiple products
python scripts/plytix_api.py products bulk-update --data '[
  {"id": "prod1", "attributes": {"status": "active"}},
  {"id": "prod2", "attributes": {"status": "active"}}
]'
```

### Add Assets to Product

```bash
python scripts/plytix_api.py products add-assets <product_id> --asset-ids "id1,id2,id3"
```

### Add Product to Categories

```bash
python scripts/plytix_api.py products add-categories <product_id> --category-ids "cat1,cat2"
```

## Product Object

```json
{
  "id": "product-uuid",
  "sku": "SKU-001",
  "label": "Product Name",
  "status": "active",
  "created": "2024-01-15T10:30:00Z",
  "modified": "2024-01-20T14:45:00Z",
  "attributes": {
    "description": "Product description",
    "price": 99.99,
    "weight": 1.5,
    "custom_field": "value"
  },
  "categories": ["cat-id-1", "cat-id-2"],
  "assets": ["asset-id-1", "asset-id-2"],
  "variants": ["variant-id-1"]
}
```

## Common Patterns

### Export Products to JSON

```bash
python scripts/plytix_api.py products list --limit 1000 --format json > products.json
```

### Find Products Without Images

```bash
python scripts/plytix_api.py products search --filters '[{"field":"assets","operator":"eq","value":[]}]'
```

### Update Product Status in Bulk

```bash
# First, search for products
python scripts/plytix_api.py products search --filters '[{"field":"status","operator":"eq","value":"draft"}]' --format json

# Then bulk update
python scripts/plytix_api.py products bulk-update --data '[
  {"id": "prod1", "status": "active"},
  {"id": "prod2", "status": "active"}
]'
```
