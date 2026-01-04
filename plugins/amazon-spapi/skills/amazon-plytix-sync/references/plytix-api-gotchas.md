# Plytix API Gotchas

## Overview

Common issues and workarounds when working with the Plytix PIM API.

---

## 1. Search Filters - Custom Attributes NOT Supported

**Problem**: `search_products()` can only filter by built-in fields (sku, label, gtin, status). Custom attributes like `amazon_parent_asin` CANNOT be used as search filters.

**Symptom**:
```python
# This FAILS with "Field 'amazon_parent_asin' doesn't exist"
api.search_products(filters=[
    {'field': 'amazon_parent_asin', 'operator': 'eq', 'value': 'B077QMJFG9'}
])
```

**Solution**: Use `find_products_by_attribute()` which fetches products and filters locally:
```python
# This WORKS (but is slower)
children = api.find_products_by_attribute(
    attribute_name='amazon_parent_asin',
    value='B077QMJFG9',
    sku_pattern='AMZN-'  # Optional: pre-filter by SKU to speed up
)
```

---

## 2. Thumbnail Format

**Problem**: `update_product(thumbnail=...)` requires object format `{'id': asset_id}`, not just the asset ID string.

**Symptom**:
```python
# This FAILS with schema validation error
api.update_product(product_id, {'thumbnail': 'asset123'})
# Error: {'errors': [{'field': 'thumbnail', 'msg': {'_schema': ['Invalid input type.']}}]}
```

**Solution**: The wrapper now auto-wraps string IDs:
```python
# Both work now:
api.update_product(product_id, {'thumbnail': 'asset123'})  # Auto-wrapped
api.update_product(product_id, {'thumbnail': {'id': 'asset123'}})  # Explicit
```

---

## 3. Asset Linking Requires Attribute Label

**Problem**: `add_product_assets()` requires specifying which media gallery attribute to link to.

**Symptom**: Assets linked but not visible in expected location.

**Solution**: Specify the attribute_label:
```python
# Link to default 'assets' attribute
api.add_product_assets(product_id, [asset_id])

# Link to custom 'amazon_images' media gallery
api.add_product_assets(product_id, [asset_id], attribute_label='amazon_images')
```

**Note**: The attribute must exist and be of type `MediaGalleryAttribute`.

---

## 4. Date Attribute Format

**Problem**: DateAttribute values must use `YYYY-MM-DD` format, not ISO timestamps.

**Symptom**:
```python
# This FAILS with validation error
from datetime import datetime
api.update_product(product_id, {
    'attributes': {'amazon_last_synced': datetime.now().isoformat()}
})
```

**Solution**: Use date-only format:
```python
# This WORKS
api.update_product(product_id, {
    'attributes': {'amazon_last_synced': datetime.now().strftime('%Y-%m-%d')}
})
```

---

## 5. Dropdown Attribute Options

**Problem**: Options must be simple strings, not objects.

**Correct**:
```python
api.create_attribute({
    'name': 'Marketplace',
    'label': 'marketplace',
    'type_class': 'DropdownAttribute',
    'options': ['US', 'CA', 'MX']  # Simple strings
})
```

**Wrong**:
```python
# This structure is NOT supported
'options': [
    {'value': 'US', 'label': 'United States'},
    {'value': 'CA', 'label': 'Canada'}
]
```

---

## 6. Asset Upload - Handling Duplicates

**Problem**: `upload_asset_url()` returns 409 Conflict if asset URL already exists.

**Solution**: With `return_existing=True` (default), it extracts and returns the existing asset:
```python
result = api.upload_asset_url('https://example.com/image.jpg')
# If new: {'id': 'new_id', 'filename': '...'}
# If exists: {'id': 'existing_id', 'status': 'existing', 'url': '...'}

asset_id = result['id']  # Works in both cases
```

---

## 7. Relationship Direction

**Problem**: Relationships are directional - `add_product_relationships()` links FROM source TO targets.

**Example**:
```python
# Parent product "has" child products
api.add_product_relationships(
    product_id=parent_id,          # Source
    relationship_id='amazon_hierarchy',
    related_product_ids=[child1, child2]  # Targets
)
```

**For bidirectional visibility**: Link from both directions if needed.

---

## 8. Search vs Get - Attribute Data

**Problem**: `search_products()` returns basic fields only, NOT full attribute values.

**Symptom**: Attributes are empty or None in search results.

**Solution**:
1. Pass `attributes=['attr1', 'attr2']` to search (limited effectiveness)
2. Use `get_product(id)` for complete data:
```python
# Search returns basic info
results = api.search_products(filters=[...])
product_id = results['data'][0]['id']

# Get full details including all attributes
full_product = api.get_product(product_id)
attrs = full_product.get('attributes', {})
```

---

## 9. Rate Limiting

**Problem**: API returns 429 when rate limited.

**Symptom**: `PlytixAPIError` with status_code 429.

**Solution**: Check `Retry-After` header:
```python
try:
    result = api.some_operation()
except PlytixAPIError as e:
    if e.status_code == 429:
        wait_time = e.details.get('retry_after', 60)
        time.sleep(int(wait_time))
        result = api.some_operation()  # Retry
```

---

## 10. Product Creation - SKU Uniqueness

**Problem**: SKU must be unique. Duplicate SKU returns error.

**Solution**: Check before creating:
```python
def create_if_not_exists(sku: str, data: Dict) -> Dict:
    existing = api.search_products(
        filters=[{'field': 'sku', 'operator': 'eq', 'value': sku}],
        limit=1
    )
    if existing.get('data'):
        return {'status': 'exists', 'product': existing['data'][0]}

    return api.create_product({**data, 'sku': sku})
```

---

## Common Patterns

### Batch Processing with Rate Limiting
```python
import time

for item in items:
    try:
        api.update_product(item['id'], item['data'])
    except PlytixAPIError as e:
        if e.status_code == 429:
            time.sleep(60)
            api.update_product(item['id'], item['data'])
        else:
            raise
    time.sleep(0.2)  # Preventive rate limiting
```

### Safe Asset Upload and Link
```python
# Upload (handles duplicates)
result = api.upload_asset_url(image_url)
asset_id = result['id']

# Link to product
api.add_product_assets(product_id, [asset_id], attribute_label='amazon_images')

# Set as thumbnail
api.update_product(product_id, {'thumbnail': asset_id})  # Auto-wrapped
```

### Find Products by Custom Attribute
```python
# Since search doesn't support custom attributes, use helper method
products = api.find_products_by_attribute(
    attribute_name='amazon_parent_asin',
    value='B077QMJFG9',
    operator='eq',
    sku_pattern='AMZN-',  # Optional: speed up with SKU pre-filter
    limit=50
)
```

### Idempotent Updates
```python
def safe_update(product_id: str, updates: Dict):
    """
    Update product idempotently.
    Safe to call multiple times with same data.
    """
    try:
        return api.update_product(product_id, updates)
    except PlytixAPIError as e:
        if e.status_code == 404:
            return {'status': 'not_found'}
        raise
```
