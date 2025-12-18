# Relationships API Reference

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/relationships` | Create relationship |
| GET | `/relationships/{id}` | Get relationship by ID |
| PATCH | `/relationships/{id}` | Update relationship |
| DELETE | `/relationships/{id}` | Delete relationship |
| POST | `/relationships/search` | Search relationships |

**Note:** Relationships define connections between products (e.g., accessories, cross-sells, up-sells, related items).

## CLI Commands

### List Relationships

```bash
python scripts/plytix_api.py relationships list [options]

Options:
  --limit, -l    Results per page (default: 50)
  --page, -p     Page number (default: 1)
  --format, -f   Output format: table, json, compact, summary
```

### Get Relationship

```bash
python scripts/plytix_api.py relationships get <relationship_id>
```

### Create Relationship

```bash
python scripts/plytix_api.py relationships create --data '<json>'

# Example
python scripts/plytix_api.py relationships create --data '{
  "name": "Accessories",
  "label": "Works with",
  "bidirectional": false
}'
```

### Update Relationship

```bash
python scripts/plytix_api.py relationships update <relationship_id> --data '<json>'

# Example
python scripts/plytix_api.py relationships update abc123 --data '{
  "label": "Compatible with"
}'
```

### Delete Relationship

```bash
python scripts/plytix_api.py relationships delete <relationship_id>
```

### Search Relationships

```bash
python scripts/plytix_api.py relationships search [options]

Options:
  --filters      JSON array of filter objects
  --limit, -l    Results per page
  --page, -p     Page number
```

**Filter Examples:**

```bash
# By name contains
--filters '[{"field":"name","operator":"like","value":"access"}]'

# By bidirectional flag
--filters '[{"field":"bidirectional","operator":"eq","value":true}]'
```

See [filters_api.md](filters_api.md) for complete filter documentation.

## Relationship Object

```json
{
  "id": "relationship-uuid",
  "name": "Accessories",
  "label": "Works with",
  "bidirectional": false,
  "created": "2024-01-15T10:30:00Z",
  "modified": "2024-01-20T14:45:00Z"
}
```

## Relationship Types

Common relationship patterns:
- **Accessories**: Products that complement main product
- **Cross-sells**: Alternative products customers might like
- **Up-sells**: Premium alternatives to current product
- **Related**: General product associations
- **Replacements**: Products that can substitute for another

## Using Relationships with Products

### Link Products via Relationship

```bash
# Add related products to a product
python scripts/plytix_api.py products add-relationships <product_id> \
  --relationship-id "rel-123" \
  --related-product-ids "prod-a,prod-b,prod-c"
```

### Get Product Relationships

```bash
# View all relationships for a product
python scripts/plytix_api.py products get <product_id> --include relationships
```

## Common Patterns

### Export All Relationships

```bash
python scripts/plytix_api.py relationships list --limit 1000 --format json > relationships.json
```

### Find Bidirectional Relationships

```bash
python scripts/plytix_api.py relationships search --filters '[
  {"field":"bidirectional","operator":"eq","value":true}
]'
```

### Create Cross-Sell Relationship

```bash
python scripts/plytix_api.py relationships create --data '{
  "name": "cross-sell",
  "label": "Customers also bought",
  "bidirectional": true
}'
```
