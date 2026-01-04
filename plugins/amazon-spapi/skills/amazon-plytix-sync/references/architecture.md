# Architecture: Option B

## Overview

The Amazon-Plytix sync uses **Option B Architecture**: every Amazon ASIN becomes a separate Plytix product. Canonical products remain untouched and serve as the master record.

## Why Option B?

### The Problem with Option A (Enrichment)
Option A would add Amazon data directly to canonical Plytix products. This creates issues:
- Multiple ASINs can map to one canonical (parent + children)
- Amazon data conflicts with canonical data
- Hard to track which data came from Amazon
- Rollback is destructive

### Option B Benefits
- **Clean separation**: Amazon products are clearly identified by SKU prefix
- **Full traceability**: Every ASIN has its own product record
- **Non-destructive**: Canonical products never modified
- **Flexible relationships**: Can link multiple ASINs to one canonical
- **Image isolation**: Amazon images stay on Amazon products

## Data Model

```
┌─────────────────────────────────────────────────────────────────┐
│                     PLYTIX PRODUCT SPACE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Canonical Products              Amazon Products (AMZN-*)        │
│  ─────────────────              ─────────────────────────        │
│                                                                  │
│  ┌─────────────┐                ┌─────────────────────────┐     │
│  │   MCA0032   │ ◄─────────────│ AMZN-US-B09FQ13BDF      │     │
│  │  (parent)   │  Amazon        │ (VARIATION_PARENT)      │     │
│  └─────────────┘  Listings      │ model_number: MCA0032   │     │
│        │                        └─────────────────────────┘     │
│        │                                                         │
│        │                        ┌─────────────────────────┐     │
│        │         ◄─────────────│ AMZN-US-B077QMJFG9      │     │
│        │          Amazon        │ (VARIATION_PARENT)      │     │
│        │          Listings      │ model_number: MDM0049   │◄──┐ │
│        │                        └─────────────────────────┘   │ │
│        │                                    │                  │ │
│        │                                    │ Amazon           │ │
│        │                                    │ Hierarchy        │ │
│        │                                    ▼                  │ │
│  ┌─────────────┐                ┌─────────────────────────┐   │ │
│  │   MDM0049   │ ◄─────────────│ AMZN-US-B07TBFZL3N      │───┘ │
│  │  (parent)   │  Amazon        │ (child variant)         │     │
│  └─────────────┘  Listings      └─────────────────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## SKU Naming Convention

```
AMZN-{marketplace}-{ASIN}
```

| Component | Values | Example |
|-----------|--------|---------|
| Prefix | `AMZN` | Always AMZN |
| Marketplace | `US`, `CA`, `MX` | US for United States |
| ASIN | 10-char Amazon ID | B07X8Z63ZL |

**Full Example**: `AMZN-US-B07X8Z63ZL`

## Relationship Types

### 1. Amazon Hierarchy
**Purpose**: Link parent ASINs to child variant ASINs

```
AMZN-US-B077QMJFG9 (parent)
    │
    ├── AMZN-US-B07TBFZL3N (child - Size 7)
    ├── AMZN-US-B07X8Z63ZL (child - Size 8)
    └── AMZN-US-B07TBG123H (child - Size 9)
```

**Direction**: Parent → Children
**API Call**:
```python
api.add_product_relationships(
    product_id=parent_product_id,
    relationship_id='amazon_hierarchy',
    related_product_ids=[child1, child2, child3]
)
```

### 2. Amazon Listings
**Purpose**: Link canonical Plytix products to Amazon representations

```
MCA0032 (canonical)
    │
    ├── AMZN-US-B09FQ13BDF (parent listing 1)
    ├── AMZN-US-B0C89T5YRQ (parent listing 2)
    └── AMZN-US-B077QMJFG9 (parent listing 3)
```

**Direction**: Canonical → Amazon Products
**API Call**:
```python
api.add_product_relationships(
    product_id=canonical_product_id,
    relationship_id='amazon_listings',
    related_product_ids=[amzn_product_1, amzn_product_2]
)
```

## VARIATION_PARENT Handling

Amazon VARIATION_PARENT ASINs require special handling:

### The Challenge
- Parent ASINs may not appear in brand searches
- Parent ASINs have no GTIN/UPC for matching
- One parent can have variants from different canonical products

### The Solution: model_number Field
Amazon's `model_number` attribute typically contains the original product style number:

```json
{
  "asin": "B09FQ13BDF",
  "item_classification": "VARIATION_PARENT",
  "model_number": "MCA0032"
}
```

### Linking Logic
1. Export includes `model_number` from Amazon attributes
2. Find canonical product by matching SKU to `model_number`
3. Link via Amazon Listings relationship

```python
# Find canonical by model_number
model_number = amazon_export['model_number']  # "MCA0032"
canonical = api.search_products(
    filters=[{'field': 'sku', 'operator': 'eq', 'value': model_number}]
)

# Link VARIATION_PARENT to canonical
api.add_product_relationships(
    product_id=canonical['id'],
    relationship_id='amazon_listings',
    related_product_ids=[variation_parent_product_id]
)
```

## Image Storage Strategy

Images are stored on Amazon products, NOT canonical products:

```
AMZN-US-B07X8Z63ZL
    │
    ├── thumbnail: {id: "asset_main_image"}
    └── amazon_images: [asset1, asset2, asset3, ...]
```

**Rationale**:
- Amazon-specific images (lifestyle, A+ content)
- Different images per marketplace
- Clear ownership and cleanup

## Product Attribute Schema

Amazon products store these attributes:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| amazon_asin | TextAttribute | Yes | 10-char ASIN |
| amazon_parent_asin | TextAttribute | No | Parent for variants |
| amazon_sku | TextAttribute | No | Seller's Amazon SKU |
| amazon_upc | TextAttribute | No | UPC from Amazon |
| amazon_ean | TextAttribute | No | EAN from Amazon |
| amazon_title | TextAttribute | Yes | Product title |
| amazon_size | TextAttribute | No | Size variant value |
| amazon_color | TextAttribute | No | Color variant value |
| amazon_variation_theme | TextAttribute | No | e.g., "SizeColor" |
| amazon_listing_status | DropdownAttribute | No | ACTIVE, INACTIVE |
| amazon_marketplace | DropdownAttribute | Yes | US, CA, MX |
| amazon_canonical_sku | TextAttribute | No | Linked canonical SKU |
| amazon_is_primary | BooleanAttribute | No | Primary listing flag |
| amazon_last_synced | DateAttribute | Yes | Sync date (YYYY-MM-DD) |

## Phase Sequence

```
Phase 1: Export
    └─▶ Fetch all ASINs from SP-API
    └─▶ Include parent metadata via fetch_missing_parents()
    └─▶ Output: {brand}_export.json

Phase 2: Mapping
    └─▶ Match ASINs to canonical SKUs
    └─▶ Logic: GTIN → EAN → UPC → SKU prefix
    └─▶ Output: {style}_mapping.json

Phase 3: Sync Products
    └─▶ Create AMZN-* products in Plytix
    └─▶ Set all amazon_* attributes
    └─▶ Output: {style}_mapping.sync_products.json

Phase 4: Relationships
    └─▶ Link children to parents (Amazon Hierarchy)
    └─▶ Link parents to canonical (Amazon Listings)
    └─▶ Use model_number for VARIATION_PARENT matching

Phase 5: Images
    └─▶ Upload images as Plytix assets
    └─▶ Deduplicate by URL
    └─▶ Link to Amazon products
    └─▶ Set thumbnails
```

## Future Phases (Planned)

### Phase 6: Sync Back to Amazon
- Update Amazon listings from Plytix data
- Detect conflicts and flag for review
- Automated attribute sync via SP-API

### Phase 7: Multi-Marketplace
- Support CA, MX marketplaces
- Cross-marketplace ASIN linking
- Currency/locale handling
