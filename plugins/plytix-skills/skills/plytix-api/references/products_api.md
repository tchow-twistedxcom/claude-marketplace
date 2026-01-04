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

### ⚠️ CRITICAL: Top-Level Fields vs Attributes

Products have **two types of fields**:

1. **Top-Level Fields** - Built-in system fields set directly on the product
2. **Attributes** - Custom/configurable fields set inside the `attributes` object

**This distinction is crucial when updating products:**

```python
# CORRECT - product_family is a top-level field
api.update_product(product_id, {
    'product_family': '694a3a2d665d9e1363da7922'  # Direct on product
})

# WRONG - product_family is NOT an attribute
api.update_product(product_id, {
    'attributes': {'family': '8 - Amazon'}  # Will fail: "label does not exist"
})
```

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Product UUID (read-only) |
| `sku` | string | Unique product identifier |
| `label` | string | Product display name |
| `status` | string | Product status |
| `product_family` | string | **Family ID** (not name!) - determines available attributes |
| `thumbnail` | object | `{"id": "asset_id"}` or string (auto-wrapped) |
| `gtin` | string | Global Trade Item Number |
| `created` | datetime | Creation timestamp (read-only) |
| `modified` | datetime | Last modified timestamp (read-only) |
| `categories` | array | Category IDs |
| `assets` | array | Asset IDs |
| `variants` | array | Variant IDs |

### Attributes Object

Custom fields go inside `attributes`. Their availability depends on the product's `product_family`:

```json
"attributes": {
  "description": "Product description",
  "price": 99.99,
  "amazon_asin": "B07X8Z63ZL",
  "custom_field": "value"
}
```

### Full Product Object Example

```json
{
  "id": "product-uuid",
  "sku": "SKU-001",
  "label": "Product Name",
  "status": "active",
  "product_family": "694a3a2d665d9e1363da7922",
  "gtin": "1234567890123",
  "thumbnail": {"id": "asset-uuid"},
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
