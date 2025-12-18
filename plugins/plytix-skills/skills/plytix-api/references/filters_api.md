# Filters API Reference

## Filter Structure

Plytix uses a **nested array structure** for filters:

```
filters: [ [AND_group_1], [AND_group_2], ... ]
```

- **Outer array**: OR conditions (any group matches)
- **Inner array**: AND conditions (all filters in group must match)

### Single Filter
```json
{
  "filters": [[{"field": "sku", "operator": "like", "value": "25-"}]]
}
```

### Multiple AND Conditions
```json
{
  "filters": [[
    {"field": "sku", "operator": "like", "value": "25-"},
    {"field": "status", "operator": "eq", "value": "active"}
  ]]
}
```

### OR Conditions
```json
{
  "filters": [
    [{"field": "sku", "operator": "like", "value": "25-"}],
    [{"field": "sku", "operator": "like", "value": "24-"}]
  ]
}
```

## Standard Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `like` | Contains text (case-insensitive) | `{"field": "sku", "operator": "like", "value": "ABC"}` |
| `!like` | Does not contain text | `{"field": "sku", "operator": "!like", "value": "TEST"}` |
| `eq` | Equals exactly | `{"field": "status", "operator": "eq", "value": "active"}` |
| `!eq` | Not equal to | `{"field": "status", "operator": "!eq", "value": "draft"}` |
| `in` | In list of values | `{"field": "category", "operator": "in", "value": ["cat1", "cat2"]}` |
| `!in` | Not in list | `{"field": "category", "operator": "!in", "value": ["archived"]}` |
| `gt` | Greater than | `{"field": "price", "operator": "gt", "value": 100}` |
| `gte` | Greater than or equal | `{"field": "stock", "operator": "gte", "value": 10}` |
| `lt` | Less than | `{"field": "price", "operator": "lt", "value": 50}` |
| `lte` | Less than or equal | `{"field": "weight", "operator": "lte", "value": 5.0}` |
| `last_days` | Within last N days | `{"field": "modified", "operator": "last_days", "value": 7}` |
| `exists` | Field has a value (not empty) | `{"field": "description", "operator": "exists"}` |
| `!exists` | Field is empty/null | `{"field": "thumbnail", "operator": "!exists"}` |
| `text_search` | Multi-field text search | `{"operator": "text_search", "value": "boot leather"}` |

## Special Operators

### Existence Operators (`exists`, `!exists`)

Unary operators that check if a field has or lacks a value. No `value` field needed.

```bash
# Find products with descriptions
--filters '[{"field":"description","operator":"exists"}]'

# Find products missing images
--filters '[{"field":"thumbnail","operator":"!exists"}]'
```

### Text Search Operator (`text_search`)

Searches across multiple text fields simultaneously. No `field` specified - searches all searchable fields.

```bash
# Search for "leather boot" across all text fields
--filters '[{"operator":"text_search","value":"leather boot"}]'

# Combine with other filters
--filters '[
  {"operator":"text_search","value":"western"},
  {"field":"status","operator":"eq","value":"active"}
]'
```

## Filter Types by Field

### Text Fields (sku, label, name, filename, etc.)
- `like` - Contains substring
- `!like` - Does not contain
- `eq` - Exact match
- `!eq` - Not exact match

### Boolean Fields (assigned, public, active, etc.)
- `eq` - Equals true/false
- `!eq` - Not equals

### Multi-Select Fields (file_type, category, etc.)
- `in` - Value is in list
- `!in` - Value is not in list

### Date Fields (created, modified, etc.)
- `eq` - On exact date
- `gt` - After date
- `gte` - On or after date
- `lt` - Before date
- `lte` - On or before date
- `last_days` - Within last N days

### Numeric Fields (price, stock, weight, etc.)
- `eq`, `!eq` - Equals/Not equals
- `gt`, `gte` - Greater than
- `lt`, `lte` - Less than

## CLI Examples

### Products Search

```bash
# SKU contains "25-" (Fall 2025 products)
python scripts/plytix_api.py products search --filters '[{"field":"sku","operator":"like","value":"25-"}]'

# Active products only
python scripts/plytix_api.py products search --filters '[{"field":"status","operator":"eq","value":"active"}]'

# Modified in last 7 days
python scripts/plytix_api.py products search --filters '[{"field":"modified","operator":"last_days","value":7}]'

# Multiple conditions (AND)
python scripts/plytix_api.py products search --filters '[
  {"field":"sku","operator":"like","value":"25-"},
  {"field":"status","operator":"eq","value":"active"}
]'
```

### Assets Search

```bash
# Images only
python scripts/plytix_api.py assets search --filters '[{"field":"file_type","operator":"in","value":["IMAGES"]}]'

# Filename contains "hero"
python scripts/plytix_api.py assets search --filters '[{"field":"filename","operator":"like","value":"hero"}]'

# Created in last 30 days
python scripts/plytix_api.py assets search --filters '[{"field":"created","operator":"last_days","value":30}]'
```

## Available Filter Fields

### Products
Use `GET /filters/products` to retrieve available fields (may return 404, use standard fields).

Standard fields:
- `sku` - Product SKU
- `label` - Product label/name
- `status` - Product status
- `created` - Creation date
- `modified` - Last modified date
- Custom attributes by their attribute ID

### Assets
Use `GET /filters/asset` to retrieve available fields.

Standard fields:
- `id` - Asset ID
- `filename` - File name
- `extension` - File extension
- `file_type` - File category (IMAGES, VIDEOS, etc.)
- `assigned` - Assigned to product
- `public` - Public visibility
- `created` - Creation date
- `modified` - Last modified date

## Important Notes

1. **Use `like` not `contains`**: The Plytix API uses `like` for text search
2. **Nested arrays required**: Always wrap filters in `[[]]` for proper structure
3. **Case-insensitive**: Text operators are case-insensitive
4. **Negation prefix**: Use `!` prefix for negation (`!like`, `!eq`, `!in`)
5. **Date format**: Use ISO 8601 format for dates (`2024-01-15`)
