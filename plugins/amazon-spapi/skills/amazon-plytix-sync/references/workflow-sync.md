# Workflow: Sync Products to Plytix

## Overview

Phase 3 creates Plytix products from the ASIN mapping, populating amazon_* attributes.

## Script

```bash
# Preview changes
python scripts/sync_amazon_products.py \
    --mapping data/mca0032_mapping.json \
    --dry-run

# Execute sync
python scripts/sync_amazon_products.py \
    --mapping data/mca0032_mapping.json \
    --execute
```

## Command Line Options

| Flag | Required | Description |
|------|----------|-------------|
| `--mapping` | Yes | Path to mapping JSON file |
| `--dry-run` | No | Preview without making changes |
| `--execute` | No | Actually perform the sync |
| `--plytix-account` | No | Plytix account alias |

**Note**: Either `--dry-run` or `--execute` must be specified for safety.

## Product Creation Logic

### SKU Assignment
```python
sku = mapping['suggested_sku']  # AMZN-US-B07X8Z63ZL
```

### Label Generation
```python
label = mapping.get('amazon_title') or f"Amazon {asin}"
```

### Attribute Population
```python
product_data = {
    'sku': sku,
    'label': label,
    # Assign to "8 - Amazon" product family
    'product_family': '694a3a2d665d9e1363da7922',
    'attributes': {
        # Amazon identifiers
        'amazon_asin': asin,
        'amazon_parent_asin': mapping.get('amazon_parent_asin'),
        'amazon_sku': mapping.get('amazon_sku'),
        'amazon_upc': mapping.get('amazon_upc'),
        'amazon_ean': mapping.get('amazon_ean'),

        # Amazon metadata
        'amazon_title': mapping.get('amazon_title'),
        'amazon_size': mapping.get('amazon_size'),
        'amazon_color': mapping.get('amazon_color'),
        'amazon_variation_theme': mapping.get('amazon_variation_theme'),
        'amazon_listing_status': mapping.get('amazon_listing_status'),

        # Option B specific
        'amazon_marketplace': mapping.get('marketplace', 'US'),
        'amazon_canonical_sku': mapping.get('canonical_plytix_sku'),
        'amazon_is_primary': False,

        # Sync tracking (YYYY-MM-DD format required)
        'amazon_last_synced': datetime.now().strftime('%Y-%m-%d'),
    }
}
```

## Handling Matched vs Unmatched

The sync processes BOTH matched and unmatched Amazon items:

### Matched Items
- Have `canonical_plytix_sku` and `canonical_plytix_id`
- Can be linked via Amazon Listings in relationship phase
- Full attribute data available

### Unmatched Items (including VARIATION_PARENT)
- Created without canonical link
- Still have `suggested_sku` for creation
- May have `model_number` for later linking

```python
# Combine for sync
all_mappings = mapping_data.get('matched', []) + mapping_data.get('unmatched_amazon', [])
```

## Duplicate Detection

Before creating, check if SKU exists:

```python
def check_product_exists(self, sku: str) -> Optional[Dict]:
    result = self.api.search_products(
        filters=[{'field': 'sku', 'operator': 'eq', 'value': sku}],
        limit=1
    )
    return result['data'][0] if result.get('data') else None
```

If exists:
- Status: `exists`
- Skip creation
- Product ID returned for relationship phase

## Output Structure

```json
{
  "total": 20,
  "created": 3,
  "exists": 17,
  "linked": 0,
  "errors": [],
  "metadata": {
    "source_file": "../data/mca0032_mapping.json",
    "sync_date": "2025-12-23T05:59:15Z",
    "dry_run": false
  }
}
```

### Result States

| Status | Meaning |
|--------|---------|
| `created` | New product created successfully |
| `exists` | Product with SKU already exists |
| `preview` | Dry run - would create |
| `error` | Creation failed (see errors[]) |

## Rate Limiting

Plytix has API rate limits. The script includes:

```python
for mapping in mappings:
    result = self.create_amazon_product(mapping, dry_run)
    time.sleep(0.2)  # Preventive rate limiting
```

## Console Output

```
Loading mapping from ../data/mca0032_mapping.json
Found 16 matched + 4 unmatched = 20 Amazon products to sync
Marketplace: US
Found 'Amazon Listings' relationship: rel_abc123

[DRY RUN] Syncing Amazon products...
============================================================
  AMZN-US-B07X8Z63ZL (canonical: MCA0032-105W-BOMB)... EXISTS
  AMZN-US-B07TBFZL3N (canonical: MCA0032-100W-BOMB)... EXISTS
  AMZN-US-B09FQ13BDF (canonical: N/A)... CREATED
  AMZN-US-B0C89T5YRQ (canonical: N/A)... CREATED
  AMZN-US-B077QMJFG9 (canonical: N/A)... CREATED

============================================================
SYNC SUMMARY
============================================================
Total mappings:      20
Products created:    3
Products existing:   17
Canonical links:     0
============================================================

Results saved to ../data/mca0032_mapping.sync_products.json
```

## Error Handling

### Common Errors

**Schema Validation Error**
```json
{"errors": [{"field": "attributes.amazon_last_synced", "msg": "Invalid date format"}]}
```
- Solution: Use YYYY-MM-DD format for dates

**Rate Limit (429)**
```python
except PlytixAPIError as e:
    if e.status_code == 429:
        time.sleep(60)
        # Retry
```

**Duplicate SKU**
- Script detects via `check_product_exists()`
- Returns `status: exists`

## Example Usage

### Full Sync with Dry Run
```bash
# Preview first
python scripts/sync_amazon_products.py \
    --mapping data/mca0032_mapping.json \
    --dry-run

# If looks good, execute
python scripts/sync_amazon_products.py \
    --mapping data/mca0032_mapping.json \
    --execute
```

### Resume After Partial Sync
The script handles existing products gracefully:
```bash
# Safe to re-run - existing products return 'exists'
python scripts/sync_amazon_products.py \
    --mapping data/mca0032_mapping.json \
    --execute
```

## Resulting Products

After sync, Plytix contains:

```
AMZN-US-B07X8Z63ZL
├── product_family: "8 - Amazon"
├── amazon_asin: B07X8Z63ZL
├── amazon_parent_asin: B077QMJFG9
├── amazon_title: "Twisted X Men's Lite..."
├── amazon_size: "10.5 Wide"
├── amazon_marketplace: US
├── amazon_canonical_sku: MCA0032-105W-BOMB
└── amazon_last_synced: 2025-12-23
```

## Next Phase

After product sync, proceed to [Relationships Workflow](workflow-relationships.md) to link products.
