# Plytix API Gotchas & Common Patterns

This document captures lessons learned and common issues when working with the Plytix PIM API.

> **See also**: [rate_limits_api.md](rate_limits_api.md) for comprehensive rate limiting documentation.

---

## API Limits Summary ⚠️ CRITICAL

These are official limits from the Plytix API documentation:

| Limit | Value | Description |
|-------|-------|-------------|
| **Rate Limit (short)** | Plan-based | Requests per 10 seconds |
| **Rate Limit (long)** | Plan-based | Requests per hour |
| **Search columns** | **50 max** | Attributes + properties in search request |
| **Search attributes** | **20 max** | Custom attributes returned per search |
| **Page size** | **100 max** | Items per page (default: 25) |
| **Token lifetime** | **15 minutes** | Must refresh after expiry |
| **Order + large results** | **10,000 products** | Returns 428 if ordering with >10K results |

### Search Prefix Requirements

When using `search_products()`, you MUST prefix certain fields:

```python
# User attributes MUST be prefixed with "attributes."
api.search_products(
    filters=[{'field': 'attributes.my_custom_field', 'operator': 'eq', 'value': 'test'}],
    attributes=['sku', 'label', 'attributes.my_custom_field', 'attributes.another_field']
)

# Relationship columns MUST be prefixed with "relationships."
api.search_products(
    attributes=['sku', 'relationships.related_products']
)
```

### 50 Column Limit (Search Requests)

Search requests are limited to **50 attributes** (ID and SKU are always returned and don't count).

```python
# This will return 422 error - too many attributes
api.search_products(attributes=['attr1', 'attr2', ..., 'attr51'])  # 51 attributes = FAILS

# If you need more, get IDs first then iterate
results = api.search_products(filters=[...], attributes=['sku'])  # Just IDs
for product in results['data']:
    full = api.get_product(product['id'])  # All attributes
```

### 20 Attribute Limit (Search Results)

Search results can return a maximum of **20 custom attributes** per product.

```python
# If you need more than 20 attributes, use get_product()
product = api.get_product(product_id)  # Returns all attributes
```

### 428 Error - Large Result Sets with Ordering

If you order results and the filter matches more than **10,000 products**, you get a 428 error.

```python
# This may return 428 if > 10,000 products match
api.search_products(
    filters=[{'field': 'status', 'operator': 'eq', 'value': 'draft'}],
    pagination={'order': '-modified', 'page': 1, 'page_size': 100}
)

# Solution: Remove ordering or add more restrictive filters
api.search_products(
    filters=[
        {'field': 'status', 'operator': 'eq', 'value': 'draft'},
        {'field': 'modified', 'operator': 'gt', 'value': '2024-01-01'}  # Reduce result set
    ],
    pagination={'page': 1, 'page_size': 100}  # No order
)
```

---

## 0. Product Family Assignment ⚠️ CRITICAL

**Problem**: Product family must be assigned using the dedicated endpoint, NOT via `create_product()` or `update_product()`. Both POST and PATCH endpoints silently ignore `product_family` in the payload!

**Symptom**:
```python
# This FAILS on CREATE - family is silently ignored!
api.create_product({
    'sku': 'TEST-001',
    'label': 'Test Product',
    'product_family': '694a3a2d665d9e1363da7922'  # Ignored!
})
# Product is created but product_family_id will be None

# This also FAILS on UPDATE - family is silently ignored
api.update_product(product_id, {
    'product_family': '694a3a2d665d9e1363da7922'
})

# This also FAILS - family is NOT an attribute
api.update_product(product_id, {
    'attributes': {'family': '8 - Amazon'}
})
```

**Solution**: Use `assign_product_family()` with the **family ID** (not the name):
```python
# First, find the family ID
families = api.list_product_families()
# Find "8 - Amazon" → ID: '694a3a2d665d9e1363da7922'

# Create product first (without product_family)
result = api.create_product({'sku': 'TEST-001', 'label': 'Test'})
product_id = result['data'][0]['id']

# Then assign family with the dedicated method
api.assign_product_family(product_id, '694a3a2d665d9e1363da7922')
```

**Key Points**:
- Use `assign_product_family()` ALWAYS - both POST and PATCH ignore the `product_family` field
- Use the family's **ID**, not its **name** (e.g., `'694a3a2d665d9e1363da7922'` not `'8 - Amazon'`)
- The API response field is `product_family_id` (not `product_family`)
- The family determines which attributes are available for the product

---

## 1. Use `like` NOT `contains` for Text Search

**Problem**: There is no `contains` operator. Use `like` for substring matching.

**Symptom**:
```python
# This FAILS - "contains" is not a valid operator
api.search_products(filters=[
    {'field': 'sku', 'operator': 'contains', 'value': 'AMZN'}
])
# Error: Invalid operator 'contains'. Valid operators: exists, !exists, text_search, like, !like, in, !in, eq, !eq, gt, gte, lt, lte...
```

**Solution**: Use `like` for substring matching (case-insensitive):
```python
# This WORKS - finds all products where SKU contains "AMZN"
api.search_products(filters=[
    {'field': 'sku', 'operator': 'like', 'value': 'AMZN'}
])
```

**Key Points**:
- `like` is case-insensitive substring match
- No wildcards needed - `like` with `AMZN` matches `AMZN-US-B07X8Z63ZL`
- See [filters_api.md](filters_api.md) for complete operator list

---

## 2. Search Filters - Custom Attributes NOT Supported

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

## 3. Thumbnail Format

**Problem**: `update_product(thumbnail=...)` requires object format `{'id': asset_id}`, not just the asset ID string.

**Symptom**:
```python
# This FAILS with schema validation error
api.update_product(product_id, {'thumbnail': 'asset123'})
```

**Solution**: The wrapper now auto-wraps string IDs:
```python
# Both work now:
api.update_product(product_id, {'thumbnail': 'asset123'})  # Auto-wrapped
api.update_product(product_id, {'thumbnail': {'id': 'asset123'}})  # Explicit
```

---

## 4. Asset Linking Requires Attribute Label

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

## 5. Date Attribute Format

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

## 6. Dropdown Attribute Options

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

## 7. Asset Upload - Response Format & Duplicates

**Problem 1**: The raw API returns `{'data': [{'id': '...', ...}]}` format, but the wrapper unwraps this to return the asset dict directly.

**Problem 2**: `upload_asset_url()` returns 409 Conflict if asset URL already exists.

**Solution**: The wrapper handles both cases - returns unwrapped asset dict with `id` accessible:
```python
result = api.upload_asset_url('https://example.com/image.jpg')
# If new: {'id': 'new_id', 'filename': '...', 'url': '...', ...}
# If exists: {'id': 'existing_id', 'status': 'existing', 'url': '...'}

asset_id = result['id']  # Works in both cases
```

**Note**: The wrapper unwraps `{'data': [...]}` responses automatically as of the 2025-12 update.

---

## 8. Relationship Direction

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

## 9. Search vs Get - Attribute Data & Product Family

**Problem**: `search_products()` returns basic fields only, NOT full attribute values. Additionally, `search_products()` does NOT return `product_family_id` even though the family is assigned!

**Symptom**:
- Attributes are empty or None in search results
- `product_family_id` shows as None in search results even though family is correctly assigned

**Solution**:
1. Pass `attributes=['attr1', 'attr2']` to search (limited effectiveness)
2. Use `get_product(id)` for complete data including `product_family_id`:
```python
# Search returns basic info - product_family_id will be None!
results = api.search_products(filters=[...])
product_id = results['data'][0]['id']
family_from_search = results['data'][0].get('product_family_id')  # Always None!

# Get full details including product_family_id and all attributes
full_product = api.get_product(product_id)
family_id = full_product.get('product_family_id')  # Correct value here!
attrs = full_product.get('attributes', {})
```

**Key Point**: To verify product family assignment, you MUST use `get_product()`, NOT `search_products()`.

---

## 10. Rate Limiting

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

---

## 11. Attribute Groups API - Unstable

**Problem**: The `/attributes/product/groups` endpoint returns 500 Internal Server Error. This appears to be a Plytix API issue, not a client issue.

**Symptom**:
```python
# This returns 500 Internal Server Error
api.list_attribute_groups()
api.search_attribute_groups()
```

**Workaround**: Attribute groups can be viewed in the Plytix UI. The API methods are implemented but may not work until Plytix fixes the backend.

**Note**: Individual attribute operations (`list_attributes()`, `get_attribute()`, etc.) work correctly.

---

## 12. Filter Endpoint Naming Inconsistency

**Problem**: The Plytix API has inconsistent singular/plural naming for filter endpoints.

**Correct Endpoints**:
- `/filters/asset` - Works (singular)
- `/filters/product` - Works (singular)
- `/filters/relationships` - Works (plural)

**Incorrect Patterns**:
```python
# These do NOT work
api.get('/filters/products')  # 404 - should be /filters/product
api.get('/filters/relationship')  # 404 - should be /filters/relationships
```

**Note**: The CLI wrapper handles this correctly. Just use `filters products`, `filters assets`, `filters relationships`.
