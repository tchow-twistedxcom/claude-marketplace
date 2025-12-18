# Categories API Reference

Plytix supports two category types:
- **Product Categories**: Organize products into hierarchical taxonomies
- **File Categories**: Organize assets/files into hierarchical taxonomies

## Product Category Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/categories/product` | Create product category |
| POST | `/categories/product/{id}` | Get product category by ID |
| PATCH | `/categories/product/{id}` | Update product category |
| DELETE | `/categories/product/{id}` | Delete product category |
| POST | `/categories/product/search` | Search product categories |

## File Category Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/categories/file` | Create file category |
| POST | `/categories/file/{id}` | Get file category by ID |
| PATCH | `/categories/file/{id}` | Update file category |
| DELETE | `/categories/file/{id}` | Delete file category |
| POST | `/categories/file/search` | Search file categories |

**Note:** Plytix doesn't have a dedicated tree endpoint. The CLI builds a tree from the flat category list using `parents_ids` field.

## CLI Commands

### List Categories

```bash
python scripts/plytix_api.py categories list [options]

Options:
  --limit, -l    Results per page (default: 50)
  --page, -p     Page number (default: 1)
  --format, -f   Output format: table, json, compact, summary
```

### Get Category

```bash
python scripts/plytix_api.py categories get <category_id>
```

### Create Category

```bash
python scripts/plytix_api.py categories create --data '<json>'

# Root category
python scripts/plytix_api.py categories create --data '{
  "name": "Electronics"
}'

# Child category (with parent)
python scripts/plytix_api.py categories create --data '{
  "name": "Smartphones",
  "parents_ids": ["parent-category-id"]
}'
```

### Update Category

```bash
python scripts/plytix_api.py categories update <category_id> --data '<json>'

# Example
python scripts/plytix_api.py categories update abc123 --data '{
  "name": "Updated Category Name"
}'
```

### Delete Category

```bash
python scripts/plytix_api.py categories delete <category_id>
```

### Get Category Tree

```bash
# Table format (visual tree built from flat list)
python scripts/plytix_api.py categories tree

# JSON format (full hierarchy)
python scripts/plytix_api.py --format json categories tree
```

**Note:** The tree is built client-side from flat categories using the `parents_ids` field.

### List Products in Category

```bash
python scripts/plytix_api.py categories list-products <category_id> [options]

Options:
  --limit, -l    Results per page (default: 50)
  --page, -p     Page number (default: 1)
```

## Category Object

```json
{
  "id": "6916b72d48fee943a52fc3bf",
  "name": "Electronics",
  "slug": "electronics",
  "path": ["Electronics"],
  "parents_ids": [],
  "n_children": 2,
  "order": 0,
  "modified": "2024-01-20T14:45:00Z"
}
```

### With Children (tree view)

```json
{
  "id": "6916b72d48fee943a52fc3bf",
  "name": "Electronics",
  "parents_ids": [],
  "n_children": 1,
  "children": [
    {
      "id": "child-uuid",
      "name": "Smartphones",
      "parents_ids": ["6916b72d48fee943a52fc3bf"],
      "n_children": 0,
      "children": []
    }
  ]
}
```

## Tree Output Example

```
Category Tree:
----------------------------------------
├── Electronics (150 products)
│   ├── Smartphones (45 products)
│   │   ├── Apple (20 products)
│   │   └── Android (25 products)
│   └── Laptops (55 products)
├── Clothing (200 products)
│   ├── Men's (80 products)
│   └── Women's (120 products)
└── Home & Garden (75 products)
```

## Common Patterns

### Export Category Hierarchy

```bash
python scripts/plytix_api.py categories tree --format json > categories.json
```

### Create Category Hierarchy

```bash
# Create parent
PARENT=$(python scripts/plytix_api.py --format json categories create --data '{"name":"Electronics"}' | jq -r '.id')

# Create children
python scripts/plytix_api.py categories create --data "{\"name\":\"Smartphones\",\"parents_ids\":[\"$PARENT\"]}"
python scripts/plytix_api.py categories create --data "{\"name\":\"Laptops\",\"parents_ids\":[\"$PARENT\"]}"
```

### Move Products Between Categories

```bash
# Remove from old category (via products endpoint)
python scripts/plytix_api.py products update <product_id> --data '{"categories":[]}'

# Add to new category
python scripts/plytix_api.py products add-categories <product_id> --category-ids "new-category-id"
```

### Find Leaf Categories (No Children)

```bash
python scripts/plytix_api.py --format json categories list | jq '.[] | select(.n_children == 0)'
```

---

## File Categories

File categories organize assets/files into hierarchical structures, similar to product categories.

### List File Categories

```bash
python scripts/plytix_api.py file-categories list [options]

Options:
  --limit, -l    Results per page (default: 50)
  --page, -p     Page number (default: 1)
  --format, -f   Output format: table, json, compact, summary
```

### Get File Category

```bash
python scripts/plytix_api.py file-categories get <category_id>
```

### Create File Category

```bash
python scripts/plytix_api.py file-categories create --data '<json>'

# Root file category
python scripts/plytix_api.py file-categories create --data '{
  "name": "Product Images"
}'

# Child file category
python scripts/plytix_api.py file-categories create --data '{
  "name": "Hero Banners",
  "parents_ids": ["parent-file-category-id"]
}'
```

### Update File Category

```bash
python scripts/plytix_api.py file-categories update <category_id> --data '<json>'
```

### Delete File Category

```bash
python scripts/plytix_api.py file-categories delete <category_id>
```

### Search File Categories

```bash
python scripts/plytix_api.py file-categories search --filters '[{"field":"name","operator":"like","value":"product"}]'
```

### File Category Object

```json
{
  "id": "file-category-uuid",
  "name": "Product Images",
  "slug": "product-images",
  "path": ["Product Images"],
  "parents_ids": [],
  "n_children": 3,
  "order": 0,
  "modified": "2024-01-20T14:45:00Z"
}
```

### Common File Category Patterns

```bash
# List all file categories
python scripts/plytix_api.py file-categories list --format json > file-categories.json

# Create hierarchy for asset organization
python scripts/plytix_api.py file-categories create --data '{"name":"Marketing"}'
python scripts/plytix_api.py file-categories create --data '{"name":"Social Media","parents_ids":["marketing-id"]}'
python scripts/plytix_api.py file-categories create --data '{"name":"Print Materials","parents_ids":["marketing-id"]}'
```
