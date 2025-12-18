# Assets API Reference

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/assets/search` | List/search assets |
| GET | `/assets/{id}` | Get asset by ID |
| POST | `/assets` | Upload/create asset |
| PATCH | `/assets/{id}` | Update asset metadata |
| DELETE | `/assets/{id}` | Delete asset |
| GET | `/assets/{id}/download` | Get download URL |

**Note:** Plytix uses POST-based search for listing assets. The CLI abstracts this into simple `list` and `search` commands.

## CLI Commands

### List Assets

```bash
python scripts/plytix_api.py assets list [options]

Options:
  --limit, -l     Results per page (default: 50)
  --page, -p      Page number (default: 1)
  --file-type     Filter by file type (e.g., image/jpeg)
  --format, -f    Output format: table, json, compact, summary
```

### Get Asset

```bash
python scripts/plytix_api.py assets get <asset_id>
```

### Upload Asset

```bash
# From URL
python scripts/plytix_api.py assets upload --url "https://example.com/image.jpg"

# With filename override
python scripts/plytix_api.py assets upload --url "https://example.com/image.jpg" --filename "product-hero.jpg"

# With metadata
python scripts/plytix_api.py assets upload --url "https://example.com/image.jpg" --metadata '{"alt_text":"Product image"}'

# From local file (creates asset record, actual upload may require additional steps)
python scripts/plytix_api.py assets upload --file "/path/to/image.jpg"
```

### Update Asset

```bash
python scripts/plytix_api.py assets update <asset_id> --data '<json>'

# Example
python scripts/plytix_api.py assets update abc123 --data '{
  "filename": "new-name.jpg",
  "alt_text": "Updated alt text"
}'
```

### Delete Asset

```bash
python scripts/plytix_api.py assets delete <asset_id>
```

### Search Assets

```bash
python scripts/plytix_api.py assets search [options]

Options:
  --filters      JSON array of filter objects
  --limit, -l    Results per page
  --page, -p     Page number
```

**Filter Examples:**

```bash
# By file type (use 'in' with category names)
--filters '[{"field":"file_type","operator":"in","value":["IMAGES"]}]'

# By filename contains (use 'like' operator)
--filters '[{"field":"filename","operator":"like","value":"hero"}]'

# By extension
--filters '[{"field":"extension","operator":"eq","value":"jpg"}]'

# Created in last 30 days
--filters '[{"field":"created","operator":"last_days","value":30}]'
```

See [filters_api.md](filters_api.md) for complete filter documentation.

### Get Download URL

```bash
python scripts/plytix_api.py assets download-url <asset_id>
```

## Asset Object

```json
{
  "id": "asset-uuid",
  "filename": "product-image.jpg",
  "file_type": "image/jpeg",
  "file_size": 245678,
  "url": "https://cdn.plytix.com/assets/...",
  "thumbnail_url": "https://cdn.plytix.com/thumbnails/...",
  "created": "2024-01-15T10:30:00Z",
  "modified": "2024-01-20T14:45:00Z",
  "metadata": {
    "alt_text": "Product hero image",
    "width": 1920,
    "height": 1080
  }
}
```

## Supported File Types

- **Images**: jpg, jpeg, png, gif, webp, svg, tiff, bmp
- **Documents**: pdf, doc, docx, xls, xlsx, ppt, pptx
- **Videos**: mp4, mov, avi, webm
- **Other**: zip, csv, txt

## Common Patterns

### Export All Assets to JSON

```bash
python scripts/plytix_api.py assets list --limit 1000 --format json > assets.json
```

### Find Large Images

```bash
python scripts/plytix_api.py assets search --filters '[
  {"field":"file_type","operator":"contains","value":"image"},
  {"field":"file_size","operator":"gt","value":5000000}
]'
```

### Download Asset

```bash
# Get download URL
URL=$(python scripts/plytix_api.py assets download-url <asset_id> | grep -oP 'https://[^\s]+')

# Download with curl
curl -o output.jpg "$URL"
```

### Bulk Upload from URLs

```bash
# Create a script to upload multiple assets
for url in "${URLS[@]}"; do
  python scripts/plytix_api.py assets upload --url "$url"
done
```
