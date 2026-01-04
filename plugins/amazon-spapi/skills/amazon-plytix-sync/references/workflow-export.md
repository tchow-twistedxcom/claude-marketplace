# Workflow: Export Amazon Catalog

## Overview

Phase 1 extracts Amazon catalog data via SP-API and prepares it for mapping to Plytix products.

## Script

```bash
python scripts/export_amazon_catalog.py \
    --brand "Twisted X" \
    --marketplace US \
    --include-parents \
    --output data/twistedx_export.json
```

## Command Line Options

| Flag | Required | Description |
|------|----------|-------------|
| `--brand` | Yes | Brand name to search (e.g., "Twisted X") |
| `--marketplace` | No | Marketplace code (default: US) |
| `--include-parents` | No | Fetch missing parent ASIN metadata |
| `--no-parents` | No | Skip parent fetching |
| `--output` | No | Output file path |
| `--limit` | No | Max products to fetch |

## Data Included

The export captures comprehensive Amazon catalog data:

### Product Summaries
```json
{
  "asin": "B07X8Z63ZL",
  "marketplaceId": "ATVPDKIKX0DER",
  "itemName": "Twisted X Men's Lite Cowboy...",
  "brand": "Twisted X"
}
```

### Identifiers
```json
{
  "identifiers": [
    {"identifierType": "GTIN", "identifier": "0888869826918"},
    {"identifierType": "UPC", "identifier": "888869826918"},
    {"identifierType": "EAN", "identifier": "0888869826918"}
  ]
}
```

### Relationships
```json
{
  "relationships": [
    {
      "type": "VARIATION",
      "parentAsins": ["B077QMJFG9"],
      "childAsins": []
    }
  ]
}
```

### Attributes
```json
{
  "attributes": {
    "item_name": "Twisted X Men's Lite...",
    "model_number": "MCA0032",
    "size": "10.5 Wide",
    "color": "Bomber/Bomber",
    "item_classification": "VARIATION_CHILD"
  }
}
```

### Images
```json
{
  "images": [
    {
      "variant": "MAIN",
      "link": "https://m.media-amazon.com/images/I/..."
    },
    {
      "variant": "PT01",
      "link": "https://m.media-amazon.com/images/I/..."
    }
  ]
}
```

## Fetching Missing Parents

Parent ASINs (VARIATION_PARENT) often don't appear in brand searches. The `--include-parents` flag triggers `fetch_missing_parents()`:

### How It Works
1. Scan all exported products for `parentAsins` references
2. Identify parent ASINs not in the export
3. Fetch each missing parent via `getCatalogItem` API
4. Merge parent data into export

### Why Parents Are Missing
Amazon's `searchCatalogItems` returns products matching brand filters. Parent ASINs may:
- Not have the brand attribute set
- Be generic containers for multiple brands
- Be created for customer browsing, not as actual products

### Parent Data Captured
```json
{
  "asin": "B077QMJFG9",
  "item_classification": "VARIATION_PARENT",
  "model_number": "MDM0049",
  "summaries": [...],
  "relationships": {
    "childAsins": ["B07TBFZL3N", "B07X8Z63ZL"]
  }
}
```

## Output Structure

```json
{
  "metadata": {
    "brand": "Twisted X",
    "marketplace": "US",
    "export_date": "2025-12-23T05:30:00Z",
    "total_products": 156,
    "parents_fetched": 12
  },
  "products": [
    {
      "asin": "B07X8Z63ZL",
      "marketplaceId": "ATVPDKIKX0DER",
      "summaries": [...],
      "identifiers": [...],
      "relationships": [...],
      "attributes": {...},
      "images": [...]
    }
  ]
}
```

## SP-API Configuration

The script requires SP-API credentials in environment or config:

```bash
# Environment variables
SP_API_REFRESH_TOKEN=...
SP_API_LWA_APP_ID=...
SP_API_LWA_CLIENT_SECRET=...
SP_API_AWS_ACCESS_KEY=...
SP_API_AWS_SECRET_KEY=...
SP_API_ROLE_ARN=...
```

## Rate Limiting

SP-API has rate limits per endpoint:

| Endpoint | Rate | Burst |
|----------|------|-------|
| searchCatalogItems | 2/sec | 2 |
| getCatalogItem | 2/sec | 2 |

The script handles rate limiting with automatic backoff.

## Error Handling

### Common Errors

**403 Forbidden**
- Check SP-API credentials
- Verify marketplace access in Seller Central

**429 Too Many Requests**
- Script handles automatically with backoff
- Reduce `--limit` if persistent

**No products found**
- Verify brand name spelling
- Check marketplace code
- Try partial brand name

## Example Usage

### Full Brand Export
```bash
python scripts/export_amazon_catalog.py \
    --brand "Twisted X" \
    --include-parents \
    --output data/twistedx_full_export.json
```

### Limited Test Export
```bash
python scripts/export_amazon_catalog.py \
    --brand "Twisted X" \
    --limit 50 \
    --output data/twistedx_test_export.json
```

### Specific Style Search
```bash
# Filter in mapping phase, not export
# Export all, then filter during mapping
python scripts/generate_asin_mapping.py \
    --export data/twistedx_export.json \
    --style MCA0032
```

## Next Phase

After export, proceed to [Mapping Workflow](workflow-mapping.md) to match ASINs to Plytix SKUs.
