# Attributes API Reference

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/attributes/product/search` | List/search attributes |
| GET | `/attributes/{id}` | Get attribute by ID |
| POST | `/attributes` | Create attribute |
| PATCH | `/attributes/{id}` | Update attribute |
| DELETE | `/attributes/{id}` | Delete attribute |

**Note:** Plytix uses POST-based search for listing attributes. Attribute groups are NOT available via API - use the Plytix UI to manage groups.

## CLI Commands

### List Attributes

```bash
python scripts/plytix_api.py attributes list [options]

Options:
  --limit, -l    Results per page (default: 50)
  --page, -p     Page number (default: 1)
  --format, -f   Output format: table, json, compact, summary
```

### Get Attribute

```bash
python scripts/plytix_api.py attributes get <attribute_id>
```

### Create Attribute

```bash
python scripts/plytix_api.py attributes create --data '<json>'

# Text attribute
python scripts/plytix_api.py attributes create --data '{
  "label": "Product Description",
  "type_class": "text",
  "mandatory": false
}'

# Select attribute with options
python scripts/plytix_api.py attributes create --data '{
  "label": "Color",
  "type_class": "select",
  "options": ["Red", "Blue", "Green", "Black", "White"],
  "mandatory": true
}'

# Number attribute
python scripts/plytix_api.py attributes create --data '{
  "label": "Weight (kg)",
  "type_class": "number",
  "mandatory": false
}'

# Multi-select attribute
python scripts/plytix_api.py attributes create --data '{
  "label": "Features",
  "type_class": "multiselect",
  "options": ["Waterproof", "Breathable", "UV Protection", "Quick Dry"]
}'
```

### Update Attribute

```bash
python scripts/plytix_api.py attributes update <attribute_id> --data '<json>'

# Add options to select attribute
python scripts/plytix_api.py attributes update attr123 --data '{
  "options": ["Red", "Blue", "Green", "Black", "White", "Yellow"]
}'

# Make attribute mandatory
python scripts/plytix_api.py attributes update attr123 --data '{
  "mandatory": true
}'
```

### Delete Attribute

```bash
python scripts/plytix_api.py attributes delete <attribute_id>
```

## Attribute Object

```json
{
  "id": "attribute-uuid",
  "label": "Color",
  "type_class": "select",
  "mandatory": true,
  "group": "group-uuid",
  "description": "Product color selection",
  "options": ["Red", "Blue", "Green", "Black", "White"],
  "created": "2024-01-15T10:30:00Z",
  "modified": "2024-01-20T14:45:00Z"
}
```

## Attribute Types

| Type | Description | Example |
|------|-------------|---------|
| `text` | Single line text | Name, SKU |
| `textarea` | Multi-line text | Description |
| `number` | Numeric value | Price, Weight |
| `select` | Single choice dropdown | Color, Size |
| `multiselect` | Multiple choice | Features, Tags |
| `boolean` | True/False | Active, Featured |
| `date` | Date value | Release Date |
| `datetime` | Date and time | Last Updated |
| `url` | URL/Link | Product Page |
| `media` | Asset reference | Main Image |

## Common Patterns

### Export Attribute Schema

```bash
python scripts/plytix_api.py attributes list --limit 500 --format json > attribute_schema.json
```

### Create Standard Ecommerce Attributes

```bash
# Basic product attributes
python scripts/plytix_api.py attributes create --data '{"label":"SKU","type_class":"text","mandatory":true}'
python scripts/plytix_api.py attributes create --data '{"label":"Name","type_class":"text","mandatory":true}'
python scripts/plytix_api.py attributes create --data '{"label":"Description","type_class":"textarea"}'
python scripts/plytix_api.py attributes create --data '{"label":"Price","type_class":"number","mandatory":true}'
python scripts/plytix_api.py attributes create --data '{"label":"Compare At Price","type_class":"number"}'
python scripts/plytix_api.py attributes create --data '{"label":"Weight","type_class":"number"}'
python scripts/plytix_api.py attributes create --data '{"label":"Active","type_class":"boolean"}'
```

### Add Options to Existing Select

```bash
# Get current options
CURRENT=$(python scripts/plytix_api.py attributes get attr123 --format json | jq -r '.options')

# Add new option
NEW_OPTIONS=$(echo "$CURRENT" | jq '. + ["New Option"]')

# Update attribute
python scripts/plytix_api.py attributes update attr123 --data "{\"options\":$NEW_OPTIONS}"
```

### Find Mandatory Attributes

```bash
python scripts/plytix_api.py attributes list --format json | jq '.[] | select(.mandatory == true)'
```
