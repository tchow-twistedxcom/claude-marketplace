# Amazon SP-API Gotchas & Common Patterns

This document captures lessons learned and common issues when working with the Amazon Selling Partner API.

---

## 1. Catalog Items `includedData` - `variations` Causes InvalidInput

**Problem**: Including `variations` in the `includedData` parameter for `getCatalogItem` causes an `InvalidInput` error, even though it's listed in the API documentation.

**Symptom**:
```python
# This FAILS with InvalidInput error
catalog_api.get_catalog_item(
    asin='B01EXAMPLE',
    included_data=['attributes', 'identifiers', 'images', 'variations']
)
# Error: InvalidInput - Request has missing or invalid parameters
```

**Solution**: Use `SAFE_CATALOG_INCLUDED_DATA` without `variations`:
```python
# This WORKS
SAFE_CATALOG_INCLUDED_DATA = [
    'attributes',
    'dimensions',
    'identifiers',
    'images',
    'productTypes',
    'relationships',  # Use this instead for parent/child info
    'salesRanks',
    'summaries',
]

catalog_api.get_catalog_item(
    asin='B01EXAMPLE',
    included_data=SAFE_CATALOG_INCLUDED_DATA
)
```

**Key Points**:
- The `relationships` data contains parent/child variation info as an alternative
- Variation theme and parent ASIN can be extracted from `relationships` and `attributes`
- This appears to be an undocumented API limitation

---

## 2. Rate Limiting - Token Bucket Algorithm

**Problem**: SP-API uses a token bucket algorithm. Exceeding limits returns 429 errors.

**Symptom**:
```
HTTP 429 - QuotaExceeded
x-amzn-RateLimit-Limit: 0.5
```

**Solution**: Implement exponential backoff with jitter:
```python
import random
import time

def backoff_retry(attempt):
    base_delay = min(120, 2 ** attempt)  # Max 120 seconds
    jitter = random.uniform(0, base_delay * 0.1)
    return base_delay + jitter

# Or use the built-in RateLimiter from batch_processor.py
from sync.extractors.batch_processor import RateLimiter
rate_limiter = RateLimiter(rate=5, burst=5)  # 5 RPS
rate_limiter.acquire()  # Blocks if needed
```

**Common Rate Limits**:
| API | Rate (req/sec) | Burst |
|-----|----------------|-------|
| Catalog.searchItems | 5 | 5 |
| Catalog.getCatalogItem | 5 | 5 |
| Orders.getOrders | 0.0167 | 20 |
| Reports.createReport | 0.0167 | 15 |

---

## 3. Authentication - Token Expiration

**Problem**: Access tokens expire after 1 hour. Requests fail with 401 Unauthorized.

**Symptom**:
```
HTTP 401 - Unauthorized
"message": "Access token is invalid or expired"
```

**Solution**: The `SPAPIAuth` class handles automatic token refresh:
```python
from spapi_auth import SPAPIAuth

auth = SPAPIAuth(profile="production")
# Tokens are cached and auto-refreshed 5 minutes before expiry
headers = auth.get_headers(account)
```

**Key Points**:
- Token cache is stored in `~/.sp-api/tokens.json`
- Refresh occurs automatically when token is within 5 minutes of expiry
- If refresh fails, clear cache: `auth.clear_cache()`

---

## 4. Marketplace IDs Required

**Problem**: Most SP-API endpoints require `marketplaceIds` parameter.

**Symptom**:
```
InvalidInput - marketplaceIds is required
```

**Solution**: Always include marketplace ID:
```python
# US Marketplace
MARKETPLACE_US = 'ATVPDKIKX0DER'

catalog_api.search_catalog_items(
    keywords='laptop',
    marketplaceIds=[MARKETPLACE_US]
)
```

**Common Marketplace IDs**:
| Country | Marketplace ID |
|---------|---------------|
| USA | ATVPDKIKX0DER |
| Canada | A2EUQ1WTGCTBG2 |
| Mexico | A1AM78C64UM0Y8 |
| UK | A1F83G8C2ARO7P |
| Germany | A1PA6795UKMFR9 |

---

## 5. Empty Responses vs Errors

**Problem**: SP-API often returns empty data instead of errors for invalid/missing ASINs.

**Symptom**:
```python
result = catalog_api.get_catalog_item(asin='INVALID123')
# Returns: {'asin': 'INVALID123', 'summaries': [], 'identifiers': [], ...}
# No error raised!
```

**Solution**: Always check for actual data presence:
```python
result = catalog_api.get_catalog_item(asin=asin)
summaries = result.get('summaries', [])
if not summaries:
    logger.warning(f"No data returned for ASIN {asin}")
    return None
```

---

## 6. Catalog Search vs Get - Different Response Formats

**Problem**: `searchCatalogItems` and `getCatalogItem` return different structures.

**Search Response**:
```json
{
  "items": [
    {"asin": "B01...", "summaries": [...]}
  ],
  "pagination": {"nextToken": "..."}
}
```

**Get Response**:
```json
{
  "asin": "B01...",
  "summaries": [...],
  "identifiers": [...]
}
```

**Solution**: Handle both formats appropriately:
```python
# For search (paginated list)
result = catalog_api.search_catalog_items(keywords='...')
for item in result.get('items', []):
    asin = item['asin']

# For single item get
result = catalog_api.get_catalog_item(asin='B01...')
asin = result['asin']
```

---

## 7. Image URLs - Temporary or Missing

**Problem**: Amazon image URLs may be temporary or unavailable for some products.

**Symptom**:
- Image URL returns 403 Forbidden after some time
- No images returned for certain ASINs

**Solution**:
1. Download/upload images quickly after fetching
2. Handle missing images gracefully:
```python
images = data.get('images', [])
if not images:
    logger.debug(f"No images for ASIN {asin}")
    return []

# Prefer MAIN variant
for img_group in images:
    for image in img_group.get('images', []):
        if image.get('variant') in ('MAIN', 'LARGE'):
            yield image.get('link')
```

---

## Common Patterns

### Safe Catalog Item Fetch
```python
from spapi_catalog import CatalogItemsAPI
from sync.extractors.catalog_extractor import SAFE_CATALOG_INCLUDED_DATA

def fetch_catalog_item(api: CatalogItemsAPI, asin: str) -> Optional[Dict]:
    """Safely fetch catalog item with all available data."""
    try:
        data = api.get_catalog_item(
            asin=asin,
            included_data=SAFE_CATALOG_INCLUDED_DATA
        )
        # Verify we got actual data
        if not data.get('summaries'):
            logger.warning(f"No summary data for {asin}")
            return None
        return data
    except Exception as e:
        logger.error(f"Failed to fetch {asin}: {e}")
        return None
```

---

## 8. Catalog Search Requires Keywords OR Identifiers

**Problem**: `searchCatalogItems` requires either `keywords` or `identifiers` parameter - `brand_names` alone is NOT sufficient.

**Symptom**:
```python
# This FAILS with InvalidInput error
catalog_api.search_catalog_items(
    brand_names=['Twisted X']
)
# Error: InvalidInput: Missing required 'identifiers' or 'keywords'.
```

**Solution**: Include keywords when searching by brand:
```python
# This WORKS - use brand name as keywords too
catalog_api.search_catalog_items(
    keywords=['Twisted X'],
    brand_names=['Twisted X'],
    included_data=['identifiers', 'summaries']
)
```

**Key Points**:
- The `keywords` parameter accepts the brand name as a search term
- Combining `keywords` + `brand_names` filters to products matching both
- For precise brand filtering, always include both parameters

---

## Common Patterns

### Batch Processing with Rate Limiting
```python
from sync.extractors.batch_processor import BatchProcessor, RateLimiter

processor = BatchProcessor(
    batch_size=50,
    delay_between_batches=1.0,
    max_retries=3
)
rate_limiter = RateLimiter(rate=5, burst=5)

def process_batch(asins: List[str]) -> List[Dict]:
    results = []
    for asin in asins:
        rate_limiter.acquire()
        result = fetch_catalog_item(api, asin)
        if result:
            results.append(result)
    return results

all_results = processor.process_batches(
    items=asins,
    processor=process_batch
)
```
