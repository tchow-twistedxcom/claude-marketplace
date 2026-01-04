# Workflow: Image Sync

## Overview

Phase 5 uploads Amazon product images to Plytix as assets and links them to Amazon products.

## Script

```bash
# Preview changes
python scripts/sync_amazon_images.py \
    --mapping data/mca0032_mapping.json \
    --dry-run

# Execute sync
python scripts/sync_amazon_images.py \
    --mapping data/mca0032_mapping.json \
    --execute
```

## Command Line Options

| Flag | Required | Description |
|------|----------|-------------|
| `--mapping` | Yes | Path to mapping JSON file |
| `--dry-run` | No | Preview without uploading |
| `--execute` | No | Actually upload images |
| `--skip-existing` | No | Skip products with existing images |
| `--plytix-account` | No | Plytix account alias |

## Image Storage Strategy

Images are stored on **Amazon products**, NOT canonical products:

```
AMZN-US-B07X8Z63ZL
    │
    ├── thumbnail: {id: "asset_abc123"}
    └── amazon_images (MediaGallery): [asset1, asset2, asset3]
```

**Rationale**:
- Amazon-specific images (lifestyle, A+ content, marketplace-specific)
- Clear separation from canonical product images
- Easy cleanup if Amazon listing is removed
- Different images per marketplace

## Image Deduplication

The same image URL may appear across multiple products. Deduplication prevents redundant uploads:

```python
# Track unique URLs
unique_images = {}  # url -> asset_id

for product in products:
    for image in product.get('amazon_images', []):
        url = image['link']

        if url in unique_images:
            # Reuse existing asset
            asset_id = unique_images[url]
        else:
            # Upload new asset
            result = api.upload_asset_url(url)
            asset_id = result['id']
            unique_images[url] = asset_id

        # Link to product
        api.add_product_assets(product_id, [asset_id], attribute_label='amazon_images')
```

## Handling Duplicate Uploads (409)

Plytix returns 409 Conflict if an asset URL already exists. The wrapper handles this:

```python
def upload_asset_url(self, url: str, return_existing: bool = True) -> Dict:
    """
    Upload asset from URL.

    Args:
        url: Image URL to upload
        return_existing: If True, return existing asset on 409
    """
    try:
        return self.post('/assets', {'url': url})
    except PlytixAPIError as e:
        if e.status_code == 409 and return_existing:
            # Extract existing asset ID from error response
            existing_id = e.details.get('existing_asset_id')
            return {
                'id': existing_id,
                'status': 'existing',
                'url': url
            }
        raise
```

Usage:
```python
result = api.upload_asset_url('https://m.media-amazon.com/images/I/...')
asset_id = result['id']  # Works whether new or existing
```

## Linking Assets to Products

### To Media Gallery Attribute
```python
api.add_product_assets(
    product_id=product_id,
    asset_ids=[asset1, asset2, asset3],
    attribute_label='amazon_images'  # MediaGallery attribute
)
```

### Setting Thumbnail
```python
# String ID is auto-wrapped to {'id': asset_id}
api.update_product(product_id, {
    'thumbnail': asset_id
})

# Explicit format also works
api.update_product(product_id, {
    'thumbnail': {'id': asset_id}
})
```

## Amazon Image Variants

Amazon provides images with variant codes:

| Variant | Purpose |
|---------|---------|
| MAIN | Primary product image |
| PT01-PT08 | Alternate angles |
| SWATCH | Color swatch |
| TOPP | Top view |
| BOTT | Bottom view |

### Processing Logic
```python
for image in amazon_images:
    url = image['link']
    variant = image.get('variant', 'MAIN')

    # Upload or reuse
    asset_id = upload_or_get_asset(url)

    # Link to product
    api.add_product_assets(product_id, [asset_id], attribute_label='amazon_images')

    # Set MAIN as thumbnail
    if variant == 'MAIN':
        api.update_product(product_id, {'thumbnail': asset_id})
```

## Complete Image Sync Workflow

```python
from plytix_api import PlytixAPI

api = PlytixAPI()

# Load mapping
with open('data/mca0032_mapping.json') as f:
    mapping = json.load(f)

# Track stats
stats = {
    'images_uploaded': 0,
    'images_skipped': 0,
    'links_created': 0,
    'thumbnails_set': 0
}

# Dedupe cache
url_to_asset = {}

# Process each product
all_products = mapping.get('matched', []) + mapping.get('unmatched_amazon', [])

for product in all_products:
    sku = product['suggested_sku']
    images = product.get('amazon_images', [])

    if not images:
        continue

    # Get Plytix product
    result = api.search_products(
        filters=[{'field': 'sku', 'operator': 'eq', 'value': sku}]
    )
    if not result['data']:
        continue

    product_id = result['data'][0]['id']
    main_image_id = None

    for image in images:
        url = image['link']
        variant = image.get('variant', 'MAIN')

        # Upload or reuse asset
        if url in url_to_asset:
            asset_id = url_to_asset[url]
            stats['images_skipped'] += 1
        else:
            result = api.upload_asset_url(url)
            asset_id = result['id']
            url_to_asset[url] = asset_id
            stats['images_uploaded'] += 1

        # Link to product
        api.add_product_assets(product_id, [asset_id], attribute_label='amazon_images')
        stats['links_created'] += 1

        # Track main image
        if variant == 'MAIN':
            main_image_id = asset_id

    # Set thumbnail from MAIN image
    if main_image_id:
        api.update_product(product_id, {'thumbnail': main_image_id})
        stats['thumbnails_set'] += 1

    time.sleep(0.2)  # Rate limiting

print(f"Images uploaded: {stats['images_uploaded']}")
print(f"Images reused: {stats['images_skipped']}")
print(f"Links created: {stats['links_created']}")
print(f"Thumbnails set: {stats['thumbnails_set']}")
```

## Output Structure

```json
{
  "total_products": 16,
  "products_with_images": 16,
  "total_image_refs": 108,
  "unique_images": 12,
  "images_uploaded": 0,
  "images_skipped": 12,
  "links_created": 108,
  "errors": [],
  "main_image_links": 16,
  "parent_links_created": 0,
  "parent_main_image_links": 0,
  "metadata": {
    "source_file": "../data/mca0032_mapping.json",
    "sync_date": "2025-12-23T06:00:47Z",
    "dry_run": false,
    "skip_existing": true
  }
}
```

## Error Handling

### Upload Failures
```python
try:
    result = api.upload_asset_url(url)
except PlytixAPIError as e:
    errors.append({
        'url': url,
        'error': str(e),
        'product_sku': sku
    })
    continue
```

### Invalid Image URLs
- 404 responses logged and skipped
- Malformed URLs caught and logged

### Rate Limiting
```python
except PlytixAPIError as e:
    if e.status_code == 429:
        wait = e.details.get('retry_after', 60)
        time.sleep(int(wait))
        # Retry
```

## Thumbnail Format Note

The Plytix API requires thumbnail to be an object:

```python
# WRONG - string format fails
api.update_product(product_id, {'thumbnail': 'asset123'})
# Error: {'errors': [{'field': 'thumbnail', 'msg': {'_schema': ['Invalid input type.']}}]}

# RIGHT - object format (auto-wrapped by our API)
api.update_product(product_id, {'thumbnail': {'id': 'asset123'}})
```

The `PlytixAPI.update_product()` method now auto-wraps string thumbnails.

## Resume After Failure

The sync is idempotent:
- Existing assets return their ID (409 handling)
- Existing links are ignored by Plytix
- Safe to re-run after partial failure

```bash
# Re-run to continue from where it failed
python scripts/sync_amazon_images.py \
    --mapping data/mca0032_mapping.json \
    --execute
```

## Parent Product Images

VARIATION_PARENT products should also get images:

```python
# Parents often have generic/hero images
for parent in [p for p in products if p.get('item_classification') == 'VARIATION_PARENT']:
    images = parent.get('amazon_images', [])
    if images:
        # Same upload/link logic
        ...
```

## Next Steps

After image sync, the Amazon → Plytix sync is complete.

Future phases:
- Phase 6: Sync changes back to Amazon
- Phase 7: Multi-marketplace support
