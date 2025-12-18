# Product Families API Reference

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/product_families` | Create product family |
| GET | `/product_families/{id}` | Get product family by ID |
| PATCH | `/product_families/{id}` | Update product family |
| DELETE | `/product_families/{id}` | Delete product family |
| POST | `/product_families/search` | Search product families |
| POST | `/product_families/{id}/attributes/link` | Link attributes to family |
| POST | `/product_families/{id}/attributes/unlink` | Unlink attributes from family |
| GET | `/product_families/{id}/attributes` | Get linked attributes |
| GET | `/product_families/{id}/all_attributes` | Get all available attributes |

**Note:** Product families group products that share common attributes. They define which attributes are available for products in that family.

## CLI Commands

### List Product Families

```bash
python scripts/plytix_api.py families list [options]

Options:
  --limit, -l    Results per page (default: 50)
  --page, -p     Page number (default: 1)
  --format, -f   Output format: table, json, compact, summary
```

### Get Product Family

```bash
python scripts/plytix_api.py families get <family_id>
```

### Create Product Family

```bash
python scripts/plytix_api.py families create --data '<json>'

# Example
python scripts/plytix_api.py families create --data '{
  "name": "Footwear",
  "label": "Footwear Products"
}'
```

### Update Product Family

```bash
python scripts/plytix_api.py families update <family_id> --data '<json>'

# Example
python scripts/plytix_api.py families update abc123 --data '{
  "label": "All Footwear"
}'
```

### Delete Product Family

```bash
python scripts/plytix_api.py families delete <family_id>
```

### Search Product Families

```bash
python scripts/plytix_api.py families search [options]

Options:
  --filters      JSON array of filter objects
  --limit, -l    Results per page
  --page, -p     Page number
```

**Filter Examples:**

```bash
# By name contains
--filters '[{"field":"name","operator":"like","value":"foot"}]'

# Created in last 30 days
--filters '[{"field":"created","operator":"last_days","value":30}]'
```

### Link Attributes to Family

```bash
python scripts/plytix_api.py families link-attributes <family_id> --attribute-ids "attr1,attr2,attr3"

# Example - Link size and color attributes
python scripts/plytix_api.py families link-attributes foot-123 --attribute-ids "size,color,material"
```

### Unlink Attributes from Family

```bash
python scripts/plytix_api.py families unlink-attributes <family_id> --attribute-ids "attr1,attr2"
```

### Get Family Attributes

```bash
# Get attributes linked to this family
python scripts/plytix_api.py families get-attributes <family_id>

# Get all available attributes (linked + unlinked)
python scripts/plytix_api.py families get-all-attributes <family_id>
```

## Product Family Object

```json
{
  "id": "family-uuid",
  "name": "Footwear",
  "label": "Footwear Products",
  "attributes": ["size", "color", "material", "width"],
  "product_count": 1250,
  "created": "2024-01-15T10:30:00Z",
  "modified": "2024-01-20T14:45:00Z"
}
```

## Common Patterns

### Export All Families

```bash
python scripts/plytix_api.py families list --limit 1000 --format json > families.json
```

### Set Up New Product Family with Attributes

```bash
# 1. Create the family
python scripts/plytix_api.py families create --data '{
  "name": "Electronics",
  "label": "Electronic Products"
}'

# 2. Link required attributes
python scripts/plytix_api.py families link-attributes <new_family_id> \
  --attribute-ids "voltage,wattage,warranty_months,certifications"
```

### Audit Family Attribute Coverage

```bash
# Get all families and their attributes
for family_id in $(python scripts/plytix_api.py families list --format json | jq -r '.[].id'); do
  echo "Family: $family_id"
  python scripts/plytix_api.py families get-attributes "$family_id"
done
```

### Assign Product to Family

```bash
# Update product's family assignment
python scripts/plytix_api.py products update <product_id> --data '{
  "product_family": "<family_id>"
}'
```

## Relationship with Products

Products belong to exactly one product family. The family determines:
- Which attributes are available for the product
- Default attribute values
- Attribute validation rules

To change a product's family:
```bash
python scripts/plytix_api.py products update <product_id> --data '{
  "product_family": "<new_family_id>"
}'
```

**Warning:** Changing a product's family may cause attribute data loss if the new family doesn't include the same attributes.
