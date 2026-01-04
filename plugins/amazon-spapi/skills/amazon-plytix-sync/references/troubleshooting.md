# Troubleshooting Guide

## Overview

Common errors and their resolutions for Amazon → Plytix sync operations.

---

## Export Phase Errors

### No Products Found

**Symptom**:
```
Found 0 products matching brand "Twisted X"
```

**Causes & Solutions**:

1. **Brand name mismatch**
   - Check exact brand spelling in Seller Central
   - Try partial match: `--brand "Twisted"` instead of `--brand "Twisted X"`

2. **Marketplace mismatch**
   - Verify `--marketplace US` is correct
   - Check if products are listed in different marketplace

3. **API permissions**
   - Verify SP-API credentials have catalog access
   - Check `Seller Central > Settings > User Permissions`

### 403 Forbidden

**Symptom**:
```
PlytixAPIError: 403 Forbidden - Access denied
```

**Causes & Solutions**:

1. **Invalid credentials**
   - Verify SP-API refresh token is valid
   - Check LWA client credentials

2. **Missing marketplace authorization**
   - Enable marketplace in Seller Central
   - Wait for authorization propagation (up to 24h)

### Parent ASINs Missing

**Symptom**:
```
Product B07X8Z63ZL references parent B077QMJFG9 not in export
```

**Solution**:
```bash
# Re-run export with parent fetching
python scripts/export_amazon_catalog.py \
    --brand "Twisted X" \
    --include-parents \
    --output data/export.json
```

---

## Mapping Phase Errors

### Low Match Rate

**Symptom**:
```
Match rate: 45% (expected 90%+)
```

**Causes & Solutions**:

1. **Missing identifiers in Plytix**
   - Verify Plytix products have GTIN/UPC populated
   - Check for leading zero differences

2. **Identifier normalization**
   - Amazon: `0888869826918`
   - Plytix: `888869826918`
   - Mapping script normalizes, but verify data quality

3. **Different product structure**
   - Amazon may have more variants than Plytix
   - Parent ASINs won't match (use model_number instead)

### No model_number for Parents

**Symptom**:
```
VARIATION_PARENT B09FQ13BDF has no model_number - cannot link to canonical
```

**Causes & Solutions**:

1. **Missing in Amazon data**
   - Some parent ASINs don't have model_number attribute
   - Manually determine canonical via product research

2. **Data quality issue**
   - Export with `--include-parents` to get full metadata
   - Check Amazon listing for model/style number

---

## Sync Phase Errors

### Schema Validation Error

**Symptom**:
```json
{"errors": [{"field": "attributes.amazon_last_synced", "msg": "Invalid date format"}]}
```

**Solution**: Use YYYY-MM-DD format for dates:
```python
# WRONG
datetime.now().isoformat()

# RIGHT
datetime.now().strftime('%Y-%m-%d')
```

### Thumbnail Invalid Type

**Symptom**:
```json
{"errors": [{"field": "thumbnail", "msg": {"_schema": ["Invalid input type."]}}]}
```

**Solution**: Use object format (auto-wrapped in current API):
```python
# API now auto-wraps, but explicit format is:
{'thumbnail': {'id': 'asset_id'}}
```

### Attribute Doesn't Exist

**Symptom**:
```
PlytixAPIError: Attribute 'amazon_marketplace' does not exist
```

**Solution**: Create missing attributes first:
```python
api.create_attribute({
    'name': 'Amazon Marketplace',
    'label': 'amazon_marketplace',
    'type_class': 'DropdownAttribute',
    'options': ['US', 'CA', 'MX']
})
```

### Rate Limit (429)

**Symptom**:
```
PlytixAPIError: 429 Too Many Requests
```

**Solution**: Add delays and retry logic:
```python
try:
    api.update_product(...)
except PlytixAPIError as e:
    if e.status_code == 429:
        time.sleep(60)
        api.update_product(...)  # Retry
```

---

## Relationship Phase Errors

### Relationship Not Found

**Symptom**:
```
Relationship 'Amazon Hierarchy' not found
```

**Solution**: Create in Plytix UI first:
1. Go to Settings > Relationships
2. Create "Amazon Hierarchy" relationship
3. Create "Amazon Listings" relationship

### Cannot Filter by Custom Attribute

**Symptom**:
```
PlytixAPIError: Field 'amazon_parent_asin' doesn't exist
```

**Solution**: Use `find_products_by_attribute()`:
```python
# DON'T use search filter
api.search_products(filters=[{'field': 'amazon_parent_asin', ...}])

# DO use helper method
api.find_products_by_attribute(
    attribute_name='amazon_parent_asin',
    value='B077QMJFG9',
    sku_pattern='AMZN-'
)
```

### Product Not Found for Linking

**Symptom**:
```
Cannot find product AMZN-US-B077QMJFG9 for relationship
```

**Causes & Solutions**:

1. **Product not synced**
   - Re-run sync_amazon_products.py
   - Check if SKU is in mapping file

2. **SKU mismatch**
   - Verify exact SKU format: `AMZN-US-B077QMJFG9`
   - Check for typos or case sensitivity

---

## Image Phase Errors

### 409 Conflict on Upload

**Symptom**:
```
PlytixAPIError: 409 Conflict - Asset already exists
```

**Solution**: Already handled by API wrapper:
```python
result = api.upload_asset_url(url)  # Returns existing asset on 409
asset_id = result['id']  # Works in both cases
```

### Asset Not Visible on Product

**Symptom**: Asset uploaded but not showing on product.

**Causes & Solutions**:

1. **Wrong attribute label**
   ```python
   # Specify correct media gallery attribute
   api.add_product_assets(product_id, [asset_id], attribute_label='amazon_images')
   ```

2. **Attribute doesn't exist**
   - Create `amazon_images` as MediaGalleryAttribute in Plytix

### Image URL 404

**Symptom**:
```
Failed to upload: https://m.media-amazon.com/... - 404 Not Found
```

**Causes & Solutions**:

1. **Image no longer exists on Amazon**
   - Skip and log for manual review
   - Re-export to get current image URLs

2. **Temporary CDN issue**
   - Retry after delay
   - Check URL manually in browser

---

## General Debugging

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# API wrapper will log requests/responses
```

### Check API Response Details

```python
try:
    api.update_product(product_id, data)
except PlytixAPIError as e:
    print(f"Status: {e.status_code}")
    print(f"Message: {e.message}")
    print(f"Details: {e.details}")
```

### Verify Product State

```python
# Get full product data
product = api.get_product(product_id)
print(json.dumps(product, indent=2))

# Check specific attribute
attrs = product.get('attributes', {})
print(f"amazon_asin: {attrs.get('amazon_asin')}")
```

### Test API Connectivity

```python
from plytix_api import PlytixAPI

api = PlytixAPI()

# Simple test call
result = api.search_products(limit=1)
print(f"API connected, found {result.get('pagination', {}).get('total', 0)} products")
```

---

## Recovery Procedures

### Resume Interrupted Sync

The unified sync CLI supports checkpoint-based resume:

```bash
# List available runs
python amazon_plytix_sync.py --list-runs

# Resume from last checkpoint
python amazon_plytix_sync.py --resume 20251226_130220

# Check run status
python amazon_plytix_sync.py --show-run 20251226_130220
```

The checkpoint system tracks:
- Current phase (extract, transform, match, load_products, load_images, etc.)
- Processed/pending/failed ASINs
- Rate-limited items for retry

### Retry Rate-Limited Canonical Links

When canonical linking fails due to Plytix rate limits (common with large syncs):

**Symptom**:
```
Canonical linking complete: 2739 linked, 0 skipped, 172 errors
Saved 172 canonical failures to canonical_failures.json
```

**Solution**: Use the dedicated retry script:

```bash
# Preview failures to retry
python retry_canonical_failures.py --run-id 20251226_130220 --dry-run

# Execute retry (waits for rate limits automatically)
python retry_canonical_failures.py --run-id 20251226_130220
```

**Output**:
```
Loaded 172 canonical failures to retry
Looking up relationship: amazon_listings
Found relationship ID: 694a205716b247294c744755
[1/172] Retrying 610860233c932200cc945d74 with 1 Amazon products...
  ✓ Linked successfully
[2/172] Retrying 6529b5f270ea796207364e92 with 1 Amazon products...
  ✓ Linked successfully
...
==================================================
RETRY COMPLETE
==================================================
  Succeeded: 172
  Failed:    0
```

If any still fail, remaining failures are saved to `canonical_failures_remaining.json`.

### Rerun Specific Phases

To rerun a phase without starting from scratch:

```bash
# Rerun only canonical linking
python amazon_plytix_sync.py --resume 20251226_130220 --rerun-phases canonical

# Rerun images and hierarchy
python amazon_plytix_sync.py --resume 20251226_130220 --rerun-phases images,hierarchy

# Available phases: images, hierarchy, canonical, attributes
```

### Partial Sync Recovery (Legacy)

Legacy scripts are also idempotent - safe to re-run:

```bash
# Resume product sync (existing products return 'exists')
python scripts/sync_amazon_products.py --mapping data/mapping.json --execute

# Resume image sync (existing assets return from 409)
python scripts/sync_amazon_images.py --mapping data/mapping.json --execute
```

### Data Cleanup

If sync created incorrect products:

```python
# Find products to delete
products = api.find_products_by_attribute(
    attribute_name='amazon_marketplace',
    value='US',
    sku_pattern='AMZN-WRONG-'
)

# Delete (with confirmation)
for p in products:
    print(f"Would delete: {p['sku']}")
    # api.delete_product(p['id'])
```

### Rollback Relationships

```python
# Remove all relationships of a type
api.remove_all_product_relationships(
    product_id=product_id,
    relationship_id='amazon_hierarchy'
)
```
