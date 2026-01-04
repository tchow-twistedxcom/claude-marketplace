# Workflow: Generate ASIN Mapping

## Overview

Phase 2 matches Amazon ASINs to canonical Plytix products using identifier matching logic.

## Script

```bash
python scripts/generate_asin_mapping.py \
    --export data/twistedx_export.json \
    --style MCA0032 \
    --output data/mca0032_mapping.json
```

## Command Line Options

| Flag | Required | Description |
|------|----------|-------------|
| `--export` | Yes | Path to Amazon export JSON |
| `--style` | No | Filter to specific style/SKU prefix |
| `--plytix-account` | No | Plytix account alias |
| `--output` | No | Output file path |

## Matching Logic

The script matches ASINs to Plytix products using this priority order:

### 1. GTIN Match (Highest Priority)
```python
# Amazon GTIN → Plytix GTIN
if amazon_gtin == plytix_gtin:
    match()
```

### 2. EAN Match
```python
# Amazon EAN → Plytix EAN (with zero normalization)
if normalize(amazon_ean) == normalize(plytix_ean):
    match()
```

### 3. UPC Match
```python
# Amazon UPC → Plytix UPC (with zero normalization)
if normalize(amazon_upc) == normalize(plytix_upc):
    match()
```

### 4. SKU Prefix Match (Fallback)
```python
# Amazon model_number matches Plytix SKU pattern
if plytix_sku.startswith(amazon_model_number):
    match()
```

## Identifier Normalization

UPC/EAN codes require normalization due to leading zero inconsistencies:

```python
def normalize_identifier(value: str) -> str:
    """Strip leading zeros for comparison."""
    return value.lstrip('0') if value else ''

# Examples:
# "0888869826918" → "888869826918"
# "888869826918"  → "888869826918"
# Both match!
```

### Why Normalization Matters
- Amazon often includes leading zeros: `0888869826918`
- Plytix may store without: `888869826918`
- Direct comparison would fail without normalization

## Output Structure

```json
{
  "metadata": {
    "source_export": "data/twistedx_export.json",
    "style_filter": "MCA0032",
    "mapping_date": "2025-12-23T05:45:00Z",
    "marketplace": "US"
  },
  "matched": [
    {
      "amazon_asin": "B07X8Z63ZL",
      "amazon_title": "Twisted X Men's Lite Cowboy...",
      "amazon_sku": "MCA0032-10.5-BOMBER",
      "amazon_upc": "888869826918",
      "amazon_ean": "0888869826918",
      "amazon_parent_asin": "B077QMJFG9",
      "amazon_size": "10.5 Wide",
      "amazon_color": "Bomber/Bomber",
      "amazon_variation_theme": "SizeColor",
      "amazon_listing_status": "ACTIVE",
      "amazon_images": [...],
      "canonical_plytix_sku": "MCA0032-105W-BOMB",
      "canonical_plytix_id": "prod_abc123",
      "match_type": "gtin",
      "suggested_sku": "AMZN-US-B07X8Z63ZL",
      "marketplace": "US"
    }
  ],
  "unmatched_amazon": [
    {
      "amazon_asin": "B09FQ13BDF",
      "amazon_title": "Twisted X Parent Product",
      "item_classification": "VARIATION_PARENT",
      "model_number": "MCA0032",
      "suggested_sku": "AMZN-US-B09FQ13BDF",
      "reason": "No identifier match (VARIATION_PARENT)"
    }
  ],
  "unmatched_plytix": [
    {
      "sku": "MCA0032-12W-NAVY",
      "reason": "No matching Amazon ASIN found"
    }
  ],
  "statistics": {
    "total_amazon": 20,
    "total_plytix": 18,
    "matched": 16,
    "unmatched_amazon": 4,
    "unmatched_plytix": 2,
    "match_rate": "80%"
  }
}
```

## Result Categories

### matched[]
Products with successful ASIN ↔ SKU match:
- Full Amazon metadata included
- `canonical_plytix_sku` and `canonical_plytix_id` for linking
- `match_type`: gtin, ean, upc, or sku_prefix
- `suggested_sku`: Generated AMZN-* SKU

### unmatched_amazon[]
Amazon ASINs without Plytix matches:
- Often VARIATION_PARENT items (no identifiers)
- New Amazon products not yet in Plytix
- Still get `suggested_sku` for creation

### unmatched_plytix[]
Plytix products without Amazon matches:
- Not listed on Amazon
- Different identifiers in systems
- Discontinued on Amazon

## Handling VARIATION_PARENT

Parent ASINs typically appear in `unmatched_amazon` because:
- No GTIN/UPC/EAN (they're container products)
- Can't match by identifiers

**Key Field**: `model_number` contains the canonical style:
```json
{
  "amazon_asin": "B09FQ13BDF",
  "item_classification": "VARIATION_PARENT",
  "model_number": "MCA0032"
}
```

Use `model_number` in relationship phase to link to canonical.

## suggested_sku Generation

Every Amazon item gets a suggested SKU:

```python
def generate_suggested_sku(asin: str, marketplace: str = 'US') -> str:
    return f"AMZN-{marketplace}-{asin}"

# B07X8Z63ZL → AMZN-US-B07X8Z63ZL
```

This SKU is used when creating the Plytix product.

## Style Filtering

The `--style` flag filters the export to specific products:

```python
# Filter by SKU prefix or model_number
if style_filter:
    products = [p for p in products
                if p.get('model_number', '').startswith(style_filter)
                or any(sku.startswith(style_filter) for sku in p.get('skus', []))]
```

## Example Usage

### Full Brand Mapping
```bash
python scripts/generate_asin_mapping.py \
    --export data/twistedx_export.json \
    --output data/twistedx_mapping.json
```

### Single Style Mapping
```bash
python scripts/generate_asin_mapping.py \
    --export data/twistedx_export.json \
    --style MCA0032 \
    --output data/mca0032_mapping.json
```

### Preview Mapping (Dry Run)
```bash
python scripts/generate_asin_mapping.py \
    --export data/twistedx_export.json \
    --style MCA0032 \
    --dry-run
```

## Common Issues

### Low Match Rate
- Check identifier format differences
- Verify Plytix has GTIN/UPC populated
- Try SKU prefix matching as fallback

### Missing Parent Data
- Re-run export with `--include-parents`
- Parent model_number required for linking

### Duplicate Matches
- Same identifier on multiple products
- Review and resolve in Plytix first

## Next Phase

After mapping, proceed to [Sync Workflow](workflow-sync.md) to create products in Plytix.
