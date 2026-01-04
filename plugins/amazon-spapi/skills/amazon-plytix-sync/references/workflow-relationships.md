# Workflow: Relationships

## Overview

Phase 4 establishes relationships between products:
1. **Amazon Hierarchy**: Parent ASIN → Child ASINs
2. **Amazon Listings**: Canonical Plytix → Amazon Products

## Two Relationship Types

### Amazon Hierarchy
Links VARIATION_PARENT ASINs to their child variant ASINs.

**Direction**: Parent → Children (within Amazon product space)

```
AMZN-US-B077QMJFG9 (VARIATION_PARENT)
    │
    └── Amazon Hierarchy ──┬── AMZN-US-B07TBFZL3N (Size 7)
                           ├── AMZN-US-B07X8Z63ZL (Size 10.5)
                           └── AMZN-US-B07TBG123H (Size 12)
```

### Amazon Listings
Links canonical Plytix products to their Amazon representations.

**Direction**: Canonical → Amazon Products

```
MCA0032 (Canonical)
    │
    └── Amazon Listings ──┬── AMZN-US-B09FQ13BDF (Parent 1)
                          ├── AMZN-US-B0C89T5YRQ (Parent 2)
                          └── AMZN-US-B077QMJFG9 (Parent 3)
```

## Creating Relationships in Plytix

### Prerequisite: Relationship Must Exist

First verify the relationship exists in Plytix:

```python
from plytix_api import PlytixAPI

api = PlytixAPI()

# Find Amazon Hierarchy relationship
hierarchy_rel = api.get_relationship_by_name("Amazon Hierarchy")
print(f"Hierarchy ID: {hierarchy_rel['id']}")

# Find Amazon Listings relationship
listings_rel = api.get_relationship_by_name("Amazon Listings")
print(f"Listings ID: {listings_rel['id']}")
```

### Linking Amazon Hierarchy

```python
# Get parent and child product IDs
parent_product = api.search_products(
    filters=[{'field': 'sku', 'operator': 'eq', 'value': 'AMZN-US-B077QMJFG9'}]
)
parent_id = parent_product['data'][0]['id']

child_products = api.search_products(
    filters=[{'field': 'amazon_parent_asin', 'operator': 'eq', 'value': 'B077QMJFG9'}]
)
# Note: This filter won't work! See "Finding Children" below

# Link parent to children
api.add_product_relationships(
    product_id=parent_id,
    relationship_id=hierarchy_rel['id'],
    related_product_ids=[child1_id, child2_id, child3_id]
)
```

## Finding Children by Parent ASIN

### The Challenge
Plytix search API **cannot filter by custom attributes** like `amazon_parent_asin`.

### The Solution: find_products_by_attribute()

```python
# Use the helper method that fetches and filters locally
children = api.find_products_by_attribute(
    attribute_name='amazon_parent_asin',
    value='B077QMJFG9',
    operator='eq',
    sku_pattern='AMZN-',  # Pre-filter by SKU for speed
    limit=100
)

child_ids = [c['id'] for c in children]
```

### How find_products_by_attribute Works
1. Fetches products matching SKU pattern (if provided)
2. For each product, calls `get_product()` for full attributes
3. Filters locally by attribute value
4. Returns matching products

```python
def find_products_by_attribute(
    self,
    attribute_name: str,
    value: str,
    operator: str = 'eq',
    sku_pattern: str = None,
    limit: int = 100
) -> List[Dict]:
    """
    Find products by custom attribute value.

    Workaround for Plytix API limitation that doesn't support
    filtering by custom attributes in search.
    """
    # Search by SKU pattern first (uses API filter)
    if sku_pattern:
        results = self.search_products(
            filters=[{'field': 'sku', 'operator': 'contains', 'value': sku_pattern}],
            limit=limit
        )
    else:
        results = self.search_products(limit=limit)

    # Filter locally by attribute
    matching = []
    for product in results.get('data', []):
        full_product = self.get_product(product['id'])
        attrs = full_product.get('attributes', {})

        if operator == 'eq' and attrs.get(attribute_name) == value:
            matching.append(full_product)
        elif operator == 'contains' and value in str(attrs.get(attribute_name, '')):
            matching.append(full_product)

    return matching
```

## Linking VARIATION_PARENT to Canonical

### The Challenge
VARIATION_PARENT ASINs often don't have identifiers (GTIN/UPC) for matching.

### The Solution: model_number Field

Amazon's `model_number` attribute typically contains the original style number:

```json
{
  "asin": "B09FQ13BDF",
  "item_classification": "VARIATION_PARENT",
  "model_number": "MCA0032"
}
```

### Linking Logic

```python
# From mapping data
model_number = mapping.get('model_number')  # "MCA0032"

# Find canonical product by model_number (which matches SKU)
canonical = api.search_products(
    filters=[{'field': 'sku', 'operator': 'eq', 'value': model_number}]
)

if canonical['data']:
    canonical_id = canonical['data'][0]['id']

    # Find the VARIATION_PARENT product
    parent = api.search_products(
        filters=[{'field': 'sku', 'operator': 'eq', 'value': f'AMZN-US-{asin}'}]
    )
    parent_id = parent['data'][0]['id']

    # Link via Amazon Listings
    api.add_product_relationships(
        product_id=canonical_id,
        relationship_id=listings_rel['id'],
        related_product_ids=[parent_id]
    )
```

## Complete Relationship Workflow

### Step 1: Link Amazon Hierarchy (Parent → Children)

```python
# For each VARIATION_PARENT in the mapping
for parent_mapping in [m for m in mappings if m.get('item_classification') == 'VARIATION_PARENT']:
    parent_asin = parent_mapping['amazon_asin']
    parent_sku = f"AMZN-US-{parent_asin}"

    # Get parent product
    parent = api.search_products(
        filters=[{'field': 'sku', 'operator': 'eq', 'value': parent_sku}]
    )
    if not parent['data']:
        continue
    parent_id = parent['data'][0]['id']

    # Find children by amazon_parent_asin attribute
    children = api.find_products_by_attribute(
        attribute_name='amazon_parent_asin',
        value=parent_asin,
        sku_pattern='AMZN-'
    )
    child_ids = [c['id'] for c in children]

    if child_ids:
        api.add_product_relationships(
            product_id=parent_id,
            relationship_id=hierarchy_rel['id'],
            related_product_ids=child_ids
        )
        print(f"Linked {parent_sku} → {len(child_ids)} children")
```

### Step 2: Link Amazon Listings (Canonical → Parents)

```python
# Group VARIATION_PARENTs by model_number
from collections import defaultdict
parents_by_model = defaultdict(list)

for mapping in mappings:
    if mapping.get('item_classification') == 'VARIATION_PARENT':
        model_num = mapping.get('model_number')
        if model_num:
            parents_by_model[model_num].append(mapping)

# Link each canonical to its Amazon parents
for model_number, parent_mappings in parents_by_model.items():
    # Find canonical
    canonical = api.search_products(
        filters=[{'field': 'sku', 'operator': 'eq', 'value': model_number}]
    )
    if not canonical['data']:
        continue
    canonical_id = canonical['data'][0]['id']

    # Get parent product IDs
    parent_ids = []
    for pm in parent_mappings:
        parent_sku = f"AMZN-US-{pm['amazon_asin']}"
        parent = api.search_products(
            filters=[{'field': 'sku', 'operator': 'eq', 'value': parent_sku}]
        )
        if parent['data']:
            parent_ids.append(parent['data'][0]['id'])

    if parent_ids:
        api.add_product_relationships(
            product_id=canonical_id,
            relationship_id=listings_rel['id'],
            related_product_ids=parent_ids
        )
        print(f"Linked {model_number} → {len(parent_ids)} Amazon parents")
```

## Relationship Direction

Relationships in Plytix are directional:

| Relationship | Direction | API Call Pattern |
|--------------|-----------|------------------|
| Amazon Hierarchy | Parent → Children | `add_product_relationships(parent_id, ..., [child_ids])` |
| Amazon Listings | Canonical → Amazon | `add_product_relationships(canonical_id, ..., [amazon_ids])` |

### Viewing Relationships

From the **source product**, relationships show as "related products":
- MCA0032 shows B09FQ13BDF, B0C89T5YRQ, B077QMJFG9 as Amazon Listings
- AMZN-US-B077QMJFG9 shows B07TBFZL3N, B07X8Z63ZL as Amazon Hierarchy

### Bidirectional Linking (Optional)

For two-way visibility, link from both directions:

```python
# Canonical → Amazon (standard)
api.add_product_relationships(canonical_id, listings_rel, [amazon_id])

# Amazon → Canonical (optional, for reverse navigation)
# Requires a separate relationship type or inverse relationship
```

## Error Handling

### Relationship Not Found
```python
rel = api.get_relationship_by_name("Amazon Hierarchy")
if not rel:
    print("ERROR: Create 'Amazon Hierarchy' relationship in Plytix first")
    sys.exit(1)
```

### Product Not Found
```python
result = api.search_products(filters=[...])
if not result.get('data'):
    print(f"WARNING: Product not found, skipping relationship")
    continue
```

### Duplicate Relationships
Plytix silently ignores duplicate relationship links - safe to re-run.

## Next Phase

After relationships, proceed to [Image Sync Workflow](workflow-images.md) to upload and link product images.
