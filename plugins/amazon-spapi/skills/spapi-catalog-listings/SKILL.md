---
name: spapi-catalog-listings
description: "Manage Amazon product catalog and listings. Use when searching catalog items, creating/updating listings, managing product types, or working with A+ content."
license: MIT
version: 1.0.0
---

# Amazon SP-API Catalog & Listings

This skill provides guidance for managing Amazon catalog items and product listings through the Selling Partner API.

## When to Use This Skill

Activate this skill when working with:
- Catalog item search and retrieval
- Listing creation and updates
- Product type definitions
- A+ Content management
- ASIN/SKU operations

## Core APIs

- **Catalog Items API** - Search and retrieve product information
- **Listings Items API** - CRUD operations for listings
- **Product Type Definitions API** - Product attribute schemas
- **A+ Content API** - Enhanced product content

## Quick Reference

```python
from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient

auth = SPAPIAuth()
client = SPAPIClient(auth)

# Search catalog
status, data = client.get(
    "/catalog/2022-04-01/items",
    "catalogItems",
    params={
        "keywords": "laptop",
        "marketplaceIds": auth.get_marketplace_id(),
        "includedData": "summaries,images,productTypes"
    }
)

# Get item details
status, data = client.get(
    f"/catalog/2022-04-01/items/{asin}",
    "catalogItems",
    params={"marketplaceIds": auth.get_marketplace_id()}
)

# Get listing
status, data = client.get(
    f"/listings/2021-08-01/items/{seller_id}/{sku}",
    "listingsItems",
    params={"marketplaceIds": auth.get_marketplace_id()}
)

# Create/update listing
status, data = client.put(
    f"/listings/2021-08-01/items/{seller_id}/{sku}",
    "listingsItems",
    params={"marketplaceIds": auth.get_marketplace_id()},
    data=listing_data
)
```

## Rate Limits

| Operation | Rate |
|-----------|------|
| Catalog search | 5/sec |
| Catalog get | 5/sec |
| Listings get | 5/sec |
| Listings put | 5/sec |
| Product types | 5/sec |

## Related Skills

- `spapi-vendor-orders` - Order product references
- `spapi-reports-feeds` - Bulk catalog updates via feeds
- `spapi-integration-patterns` - Error handling
