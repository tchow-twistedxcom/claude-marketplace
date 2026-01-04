---
name: amazon-plytix-sync
description: "Sync Amazon ASINs to Plytix catalog. Use when importing Amazon catalog data, creating ASIN products, linking relationships, syncing images, or working with Amazon Hierarchy and Amazon Listings relationships."
---

# Amazon → Plytix Sync Workflow

Complete workflow for syncing Amazon catalog data into Plytix PIM using the **Option B Architecture**: separate Plytix products for each Amazon ASIN.

## When to Use This Skill

- Syncing Amazon catalog data to Plytix
- Creating Plytix products from Amazon ASINs
- Establishing Amazon Hierarchy relationships (parent ASIN → child ASINs)
- Establishing Amazon Listings relationships (canonical → Amazon products)
- Syncing product images from Amazon to Plytix
- Linking VARIATION_PARENT ASINs to Plytix canonical parents
- Working with SP-API catalog exports

## Core Architecture: Option B

**Key Principle**: ALL Amazon ASINs become separate Plytix products. Canonical products remain untouched.

```
Canonical Plytix Product (MCA0032)
    │
    └── [Amazon Listings] ──┬── AMZN-US-B09FQ13BDF (VARIATION_PARENT)
                            ├── AMZN-US-B0C89T5YRQ (VARIATION_PARENT)
                            └── AMZN-US-B077QMJFG9 (VARIATION_PARENT)
                                    │
                                    └── [Amazon Hierarchy] ──┬── AMZN-US-B07TBFZL3N
                                                             └── AMZN-US-B07X8Z63ZL
```

## Quick Reference

| Concept | Value |
|---------|-------|
| SKU Format | `AMZN-{marketplace}-{ASIN}` → `AMZN-US-B07X8Z63ZL` |
| Product Family | `8 - Amazon` (ID: `694a3a2d665d9e1363da7922`) |
| Parent→Child Relationship | Amazon Hierarchy |
| Canonical→Amazon Relationship | Amazon Listings |
| Images Stored On | Amazon products (not canonical) |
| Parent Linking Key | `model_number` field matches canonical SKU |

## Workflow Overview

```
Phase 1: Export          Phase 2: Mapping         Phase 3: Sync
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Amazon SP-API   │────▶│ ASIN ↔ Plytix   │────▶│ Create Products │
│ Catalog Export  │     │ SKU Mapping     │     │ in Plytix       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                                               │
        ▼                                               ▼
Phase 4: Relationships                          Phase 5: Images
┌─────────────────┐                            ┌─────────────────┐
│ Link Hierarchy  │                            │ Upload & Link   │
│ Link Listings   │                            │ Product Images  │
└─────────────────┘                            └─────────────────┘
```

### Phase Scripts

| Phase | Script | Purpose |
|-------|--------|---------|
| 1. Export | `export_amazon_catalog.py` | Export ASINs from SP-API with metadata |
| 2. Mapping | `generate_asin_mapping.py` | Match ASINs to canonical Plytix SKUs |
| 3. Sync | `sync_amazon_products.py` | Create AMZN-* products in Plytix |
| 4. Relationships | API calls | Link via Amazon Hierarchy & Amazon Listings |
| 5. Images | `sync_amazon_images.py` | Upload and link product images |

## Two Relationship Types

### Amazon Hierarchy (Parent → Children)
Links VARIATION_PARENT ASINs to their child variant ASINs within the Amazon product space.

```python
# Parent has children
api.add_product_relationships(
    product_id=parent_amzn_product_id,  # AMZN-US-B077QMJFG9
    relationship_id='amazon_hierarchy',
    related_product_ids=[child1_id, child2_id]  # AMZN-US-B07TBFZL3N, etc.
)
```

### Amazon Listings (Canonical → Amazon Products)
Links canonical Plytix products to their Amazon listing representations.

```python
# Canonical links to Amazon products
api.add_product_relationships(
    product_id=canonical_product_id,  # MCA0032
    relationship_id='amazon_listings',
    related_product_ids=[amzn_product_id]  # AMZN-US-B09FQ13BDF
)
```

## VARIATION_PARENT Linking Strategy

Parent ASINs often don't match canonical SKUs directly. Use the `model_number` field:

```python
# Amazon export shows:
# B09FQ13BDF: model_number = "MCA0032"
# B0C89T5YRQ: model_number = "MCA0032"

# Find canonical by model_number
canonical = api.search_products(
    filters=[{'field': 'sku', 'operator': 'eq', 'value': model_number}]
)

# Link via Amazon Listings
api.add_product_relationships(
    product_id=canonical['id'],
    relationship_id='amazon_listings',
    related_product_ids=[variation_parent_product_id]
)
```

## Data Flow Example

Starting with style MCA0032:

1. **Export**: Fetch all ASINs with brand "Twisted X" containing MCA0032 variants
2. **Mapping**: Match by GTIN/EAN/UPC → canonical Plytix SKUs
3. **Sync**: Create 20 AMZN-US-* products with amazon_* attributes
4. **Relationships**:
   - Link 3 VARIATION_PARENTs to MCA0032 via Amazon Listings
   - Link child ASINs to their parents via Amazon Hierarchy
5. **Images**: Upload 12 unique images, link 108 references across products

## Unified Sync CLI

The primary sync tool is `amazon_plytix_sync.py` - a production-grade orchestrator with checkpoint/resume support.

### Basic Usage

```bash
# Sync by brand (most common)
python amazon_plytix_sync.py --brand "Twisted X"

# Sync specific ASINs
python amazon_plytix_sync.py --asins B07X8Z63ZL,B08Y8Z63ZL

# Sync from file
python amazon_plytix_sync.py --asin-file asins.txt

# Dry run (preview only)
python amazon_plytix_sync.py --brand "Twisted X" --dry-run
```

### Resume & Retry

```bash
# Resume interrupted sync
python amazon_plytix_sync.py --resume 20251226_130220

# Rerun specific phases
python amazon_plytix_sync.py --resume 20251226_130220 --rerun-phases canonical

# Retry only failed canonical links
python retry_canonical_failures.py --run-id 20251226_130220

# List previous runs
python amazon_plytix_sync.py --list-runs
```

### CLI Reference

| Flag | Description |
|------|-------------|
| `--brand NAME` | Sync all products for a brand |
| `--asins LIST` | Comma-separated ASINs to sync |
| `--asin-file PATH` | File with ASINs (one per line) |
| `--resume RUN_ID` | Resume a previous sync run |
| `--dry-run` | Preview without making changes |
| `--rerun-phases LIST` | Force rerun: images,hierarchy,canonical,attributes |
| `--skip-extract` | Use cached raw_catalog.json |
| `--list-runs` | Show previous sync runs |
| `--show-run RUN_ID` | Show details of a run |
| `--verify` | Verify Plytix setup |
| `--log-file PATH` | Log to file |
| `--log-level LEVEL` | DEBUG, INFO, WARNING, ERROR |

### Checkpoint System

Each sync creates checkpoint files in `data/sync_runs/{run_id}/`:

| File | Purpose |
|------|---------|
| `checkpoint.json` | Current phase and state |
| `raw_catalog.json` | Extracted Amazon products |
| `matches.json` | ASIN → Canonical matching results |
| `asin_mapping.json` | ASIN → Plytix product ID map |
| `canonical_failures.json` | Failed canonical links for retry |
| `sync_results.json` | Final sync statistics |

### Retry Failures

When canonical linking fails due to rate limits, use the retry script:

```bash
# Preview what will be retried
python retry_canonical_failures.py --run-id 20251226_130220 --dry-run

# Execute retry
python retry_canonical_failures.py --run-id 20251226_130220
```

The script reads `canonical_failures.json` and retries only the failed links.

## Scripts Location

```
plugins/amazon-spapi/scripts/
├── amazon_plytix_sync.py         # Unified sync CLI (primary)
├── retry_canonical_failures.py   # Retry failed canonical links
├── sync_config.yaml              # Sync configuration
├── sync/                         # Sync engine modules
│   ├── orchestrator.py           # Phase orchestration
│   ├── models.py                 # Data models
│   ├── extractors/               # SP-API extraction
│   ├── loaders/                  # Plytix loaders
│   └── state/                    # Checkpoint management
└── data/sync_runs/               # Sync run data
```

## Required Plytix Attributes

All Amazon products use these custom attributes:

| Attribute | Type | Purpose |
|-----------|------|---------|
| amazon_asin | Text | Amazon ASIN identifier |
| amazon_parent_asin | Text | Parent ASIN for variants |
| amazon_sku | Text | Amazon seller SKU |
| amazon_title | Text | Amazon product title |
| amazon_marketplace | Dropdown | US, CA, MX |
| amazon_canonical_sku | Text | Link to canonical Plytix SKU |
| amazon_last_synced | Date | Sync timestamp (YYYY-MM-DD) |

## Bundled References

- **[Architecture](references/architecture.md)** - Option B data model and rationale
- **[Export Workflow](references/workflow-export.md)** - SP-API catalog export process
- **[Mapping Workflow](references/workflow-mapping.md)** - ASIN to SKU matching logic
- **[Sync Workflow](references/workflow-sync.md)** - Product creation in Plytix
- **[Relationships](references/workflow-relationships.md)** - Hierarchy and listing links
- **[Image Sync](references/workflow-images.md)** - Asset upload and linking
- **[Attribute Mapping](references/attribute-mapping.md)** - Attribute conventions and rules
- **[Plytix API Gotchas](references/plytix-api-gotchas.md)** - Common issues and workarounds
- **[Troubleshooting](references/troubleshooting.md)** - Error resolution guide
