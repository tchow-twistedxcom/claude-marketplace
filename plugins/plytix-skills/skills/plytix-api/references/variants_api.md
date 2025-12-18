# Variants API Reference

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/products/{id}/variants` | List variants for product |
| GET | `/variants/{id}` | Get variant by ID |
| POST | `/products/{id}/variants` | Create variant |
| PATCH | `/variants/{id}` | Update variant |
| DELETE | `/variants/{id}` | Delete variant |
| POST | `/products/{id}/variants/bulk` | Bulk create variants |

**Note:** Variants are always accessed through their parent product. There is no global variants listing endpoint.

## CLI Commands

### List Variants

```bash
# All variants
python scripts/plytix_api.py variants list [options]

# Variants for specific product
python scripts/plytix_api.py variants list --product-id <product_id>

Options:
  --product-id   Filter by parent product
  --limit, -l    Results per page (default: 50)
  --page, -p     Page number (default: 1)
  --format, -f   Output format: table, json, compact, summary
```

### Get Variant

```bash
python scripts/plytix_api.py variants get <variant_id>
```

### Create Variant

```bash
python scripts/plytix_api.py variants create <product_id> --data '<json>'

# Example - size variant
python scripts/plytix_api.py variants create prod123 --data '{
  "sku": "SKU-001-L",
  "label": "Large",
  "attributes": {
    "size": "L",
    "price": 29.99
  }
}'

# Example - color variant
python scripts/plytix_api.py variants create prod123 --data '{
  "sku": "SKU-001-RED",
  "label": "Red",
  "attributes": {
    "color": "Red",
    "color_code": "#FF0000"
  }
}'
```

### Update Variant

```bash
python scripts/plytix_api.py variants update <variant_id> --data '<json>'

# Example
python scripts/plytix_api.py variants update var123 --data '{
  "attributes": {"price": 34.99}
}'
```

### Delete Variant

```bash
python scripts/plytix_api.py variants delete <variant_id>
```

### Bulk Create Variants

```bash
python scripts/plytix_api.py variants bulk-create <product_id> --data '<json array>'

# Example - create size variants
python scripts/plytix_api.py variants bulk-create prod123 --data '[
  {"sku": "SKU-001-S", "label": "Small", "attributes": {"size": "S"}},
  {"sku": "SKU-001-M", "label": "Medium", "attributes": {"size": "M"}},
  {"sku": "SKU-001-L", "label": "Large", "attributes": {"size": "L"}},
  {"sku": "SKU-001-XL", "label": "Extra Large", "attributes": {"size": "XL"}}
]'
```

## Variant Object

```json
{
  "id": "variant-uuid",
  "sku": "SKU-001-L",
  "label": "Large",
  "product_id": "product-uuid",
  "created": "2024-01-15T10:30:00Z",
  "modified": "2024-01-20T14:45:00Z",
  "attributes": {
    "size": "L",
    "price": 29.99,
    "weight": 0.5,
    "stock_quantity": 100
  }
}
```

## Common Patterns

### Create Size/Color Matrix

```bash
# Create all size variants for a product
SIZES='["S", "M", "L", "XL"]'
PRODUCT_ID="prod123"
BASE_SKU="SHIRT-001"

# Generate bulk create data
echo "$SIZES" | jq --arg sku "$BASE_SKU" '
  [.[] | {
    sku: ($sku + "-" + .),
    label: .,
    attributes: {size: .}
  }]
' | xargs -0 -I {} python scripts/plytix_api.py variants bulk-create "$PRODUCT_ID" --data '{}'
```

### Export All Variants

```bash
python scripts/plytix_api.py variants list --limit 1000 --format json > variants.json
```

### Get Variants with Product Info

```bash
# List variants for product
python scripts/plytix_api.py variants list --product-id <product_id> --format json

# Get product details
python scripts/plytix_api.py products get <product_id> --format json
```

### Update Variant Prices in Bulk

```bash
# First, get current variants
VARIANTS=$(python scripts/plytix_api.py variants list --product-id prod123 --format json)

# Update each variant (example script)
echo "$VARIANTS" | jq -c '.[]' | while read variant; do
  ID=$(echo "$variant" | jq -r '.id')
  python scripts/plytix_api.py variants update "$ID" --data '{"attributes":{"price":39.99}}'
done
```

### Delete All Variants for Product

```bash
# Get variant IDs
VARIANT_IDS=$(python scripts/plytix_api.py variants list --product-id prod123 --format json | jq -r '.[].id')

# Delete each
for id in $VARIANT_IDS; do
  python scripts/plytix_api.py variants delete "$id"
done
```

## Variant vs Product

| Aspect | Product | Variant |
|--------|---------|---------|
| Purpose | Parent item | Specific variation |
| SKU | Base SKU | Unique SKU per variant |
| Assets | Product images | Can have own assets |
| Categories | Categorized | Inherits from product |
| Attributes | Core attributes | Differentiating attributes |
