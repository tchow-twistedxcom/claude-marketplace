# Attribute Mapping

## Overview

This document defines the attribute schema and write rules for Amazon products in Plytix.

## Complete Attribute List

### Product Family Assignment

Products are assigned to the **"8 - Amazon"** product family (not an attribute):

```python
product_data = {
    'product_family': '694a3a2d665d9e1363da7922',  # "8 - Amazon"
    ...
}
```

**Note**: `product_family` is a top-level product field, not an attribute. It determines which attributes are available for the product.

### Amazon Identifiers

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| amazon_asin | TextAttribute | Yes | 10-character Amazon ASIN |
| amazon_parent_asin | TextAttribute | No | Parent ASIN for variant products |
| amazon_sku | TextAttribute | No | Seller's Amazon SKU |
| amazon_upc | TextAttribute | No | UPC code from Amazon |
| amazon_ean | TextAttribute | No | EAN code from Amazon |
| amazon_gtin | TextAttribute | No | GTIN code from Amazon |

### Amazon Metadata

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| amazon_title | TextAttribute | Yes | Product title from Amazon |
| amazon_size | TextAttribute | No | Size variant value |
| amazon_color | TextAttribute | No | Color variant value |
| amazon_brand | TextAttribute | No | Brand name |
| amazon_model_number | TextAttribute | No | Model/style number |
| amazon_variation_theme | TextAttribute | No | Variation type (SizeColor, etc.) |

### Classification & Status

| Attribute | Type | Options | Description |
|-----------|------|---------|-------------|
| amazon_item_classification | DropdownAttribute | BASE_PRODUCT, VARIATION_PARENT, VARIATION_CHILD | Product type |
| amazon_listing_status | DropdownAttribute | ACTIVE, INACTIVE, SUPPRESSED | Listing status |
| amazon_marketplace | DropdownAttribute | US, CA, MX | Marketplace |

### Option B Specific

| Attribute | Type | Description |
|-----------|------|-------------|
| amazon_canonical_sku | TextAttribute | Linked canonical Plytix SKU |
| amazon_is_primary | BooleanAttribute | Primary listing flag |

### Sync Tracking

| Attribute | Type | Format | Description |
|-----------|------|--------|-------------|
| amazon_last_synced | DateAttribute | YYYY-MM-DD | Last sync date |
| amazon_sync_status | DropdownAttribute | SYNCED, PENDING, ERROR | Sync state |

## Write Rules

### ALWAYS_WRITE
These attributes are updated on every sync:

```python
ALWAYS_WRITE = [
    'amazon_title',
    'amazon_listing_status',
    'amazon_last_synced',
    'amazon_sync_status',
]
```

### FILL_EMPTY
Only written if the attribute is empty/null:

```python
FILL_EMPTY = [
    'amazon_asin',        # Never changes
    'amazon_parent_asin', # Set once
    'amazon_sku',         # Seller's SKU
    'amazon_upc',
    'amazon_ean',
    'amazon_gtin',
    'amazon_size',
    'amazon_color',
    'amazon_brand',
    'amazon_model_number',
    'amazon_variation_theme',
    'amazon_item_classification',
    'amazon_marketplace',
    'amazon_canonical_sku',
]
```

### NEVER_WRITE
Never modified by sync scripts (manual only):

```python
NEVER_WRITE = [
    'amazon_is_primary',  # Manual designation
]
```

## Write Rule Implementation

```python
def apply_write_rules(existing: Dict, new_data: Dict) -> Dict:
    """
    Apply write rules to determine which attributes to update.

    Args:
        existing: Current product attributes
        new_data: New attribute values from Amazon

    Returns:
        Filtered dict of attributes to update
    """
    updates = {}

    for attr, value in new_data.items():
        if attr in NEVER_WRITE:
            continue

        if attr in ALWAYS_WRITE:
            updates[attr] = value

        elif attr in FILL_EMPTY:
            existing_value = existing.get(attr)
            if not existing_value:  # Empty, None, or missing
                updates[attr] = value

    return updates
```

## Date Format Requirements

Plytix DateAttribute requires `YYYY-MM-DD` format:

```python
# CORRECT
'amazon_last_synced': '2025-12-23'

# WRONG - ISO timestamp fails
'amazon_last_synced': '2025-12-23T06:00:00Z'

# WRONG - datetime object fails
'amazon_last_synced': datetime.now()
```

### Date Formatting Pattern
```python
from datetime import datetime, timezone

# Always use strftime for dates
sync_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
```

## Dropdown Attribute Options

Dropdown options must be simple strings, not objects:

```python
# CORRECT
api.create_attribute({
    'name': 'Amazon Marketplace',
    'label': 'amazon_marketplace',
    'type_class': 'DropdownAttribute',
    'options': ['US', 'CA', 'MX']  # Simple strings
})

# WRONG - Object format not supported
'options': [
    {'value': 'US', 'label': 'United States'},
    {'value': 'CA', 'label': 'Canada'}
]
```

## Creating Missing Attributes

Before first sync, ensure all attributes exist:

```python
REQUIRED_ATTRIBUTES = [
    {
        'name': 'Amazon ASIN',
        'label': 'amazon_asin',
        'type_class': 'TextAttribute'
    },
    {
        'name': 'Amazon Parent ASIN',
        'label': 'amazon_parent_asin',
        'type_class': 'TextAttribute'
    },
    {
        'name': 'Amazon Marketplace',
        'label': 'amazon_marketplace',
        'type_class': 'DropdownAttribute',
        'options': ['US', 'CA', 'MX']
    },
    {
        'name': 'Amazon Last Synced',
        'label': 'amazon_last_synced',
        'type_class': 'DateAttribute'
    },
    # ... etc
]

def ensure_attributes_exist(api: PlytixAPI):
    """Create missing amazon_* attributes."""
    existing = {a['label']: a for a in api.get_attributes()}

    for attr_def in REQUIRED_ATTRIBUTES:
        if attr_def['label'] not in existing:
            api.create_attribute(attr_def)
            print(f"Created attribute: {attr_def['label']}")
```

## Conflict Detection

When re-syncing, detect conflicts between Amazon and existing data:

```python
def detect_conflicts(existing: Dict, amazon_data: Dict) -> List[Dict]:
    """
    Detect conflicting attribute values.

    Returns list of conflicts for review.
    """
    conflicts = []

    for attr in FILL_EMPTY:
        existing_value = existing.get(attr)
        amazon_value = amazon_data.get(attr)

        if existing_value and amazon_value and existing_value != amazon_value:
            conflicts.append({
                'attribute': attr,
                'existing': existing_value,
                'amazon': amazon_value
            })

    return conflicts
```

### Conflict Resolution Strategy

1. **Log conflicts** for manual review
2. **Prefer existing** for FILL_EMPTY attributes
3. **Override with Amazon** only for ALWAYS_WRITE
4. **Flag for review** in sync report

## Attribute Groups

Organize amazon_* attributes in Plytix UI:

```python
api.create_attribute_group({
    'name': 'Amazon Integration',
    'attributes': [
        'amazon_asin',
        'amazon_parent_asin',
        'amazon_sku',
        'amazon_title',
        'amazon_marketplace',
        'amazon_last_synced'
    ]
})
```

## Null Value Handling

Remove None values before API calls:

```python
def clean_attributes(data: Dict) -> Dict:
    """Remove None values from attributes dict."""
    return {
        'attributes': {
            k: v for k, v in data.get('attributes', {}).items()
            if v is not None
        }
    }
```

## Example Attribute Update

```python
# Get existing product
product = api.get_product(product_id)
existing_attrs = product.get('attributes', {})

# Prepare new data from Amazon
amazon_attrs = {
    'amazon_asin': 'B07X8Z63ZL',
    'amazon_title': 'Updated Title from Amazon',
    'amazon_listing_status': 'ACTIVE',
    'amazon_last_synced': datetime.now().strftime('%Y-%m-%d'),
}

# Apply write rules
updates = apply_write_rules(existing_attrs, amazon_attrs)

# Update product
if updates:
    api.update_product(product_id, {'attributes': updates})
```
