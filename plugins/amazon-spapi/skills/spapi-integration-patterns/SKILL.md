---
name: spapi-integration-patterns
description: "Amazon SP-API integration patterns and best practices. Use for rate limiting strategies, error handling, sandbox testing, multi-marketplace configuration, and API optimization."
license: MIT
version: 1.0.0
---

# Amazon SP-API Integration Patterns

This skill provides cross-cutting patterns and best practices for Amazon Selling Partner API integration.

## When to Use This Skill

Activate this skill when working with:
- Rate limiting and quota management
- Error handling and retry strategies
- Sandbox vs production environments
- Multi-marketplace configuration
- API performance optimization
- Authentication troubleshooting

## Rate Limiting

### Understanding SP-API Quotas

SP-API uses **per-resource quotas** with both rate limits and burst capacity:

| Metric | Description |
|--------|-------------|
| Rate | Requests per second (sustained) |
| Burst | Maximum concurrent requests |

### Rate Limits by API

| API | Rate | Burst | Notes |
|-----|------|-------|-------|
| Vendor Orders | 10/sec | 10 | High limit |
| Vendor Shipments | 10/sec | 10 | High limit |
| Vendor Invoices | 10/sec | 10 | High limit |
| Orders (getOrders) | 0.0167/sec | 20 | 1/minute! |
| Orders (getOrder) | 0.5/sec | 30 | Per order |
| Reports (createReport) | 0.0167/sec | 15 | 1/minute |
| Reports (getReport) | 2/sec | 15 | Status check |
| Catalog Items | 5/sec | 20 | Search/get |
| Listings Items | 5/sec | 10 | CRUD |
| FBA Inventory | 2/sec | 30 | Inventory ops |
| Notifications | 1/sec | 5 | Subscription |

### Built-in Rate Limiting

The CLI automatically handles rate limiting:

```python
from spapi_client import SPAPIClient, RateLimiter

# Automatic rate limiting per API
client = SPAPIClient(auth)
status, data = client.get("/vendor/orders/v1/purchaseOrders", "vendorOrders")

# Manual rate limiter usage
limiter = RateLimiter()
limiter.wait("orders", rate=0.5)  # Wait for slot
```

### Custom Rate Limit Handling

```python
import time
from spapi_client import SPAPIError

def rate_limited_batch(client, items, api_func, rate=1.0):
    """Process items with rate limiting."""
    results = []
    interval = 1.0 / rate

    for item in items:
        start = time.time()

        try:
            result = api_func(item)
            results.append({"success": True, "data": result})
        except SPAPIError as e:
            if e.is_rate_limited():
                # Wait and retry
                time.sleep(5)
                result = api_func(item)
                results.append({"success": True, "data": result})
            else:
                results.append({"success": False, "error": str(e)})

        # Maintain rate
        elapsed = time.time() - start
        if elapsed < interval:
            time.sleep(interval - elapsed)

    return results
```

## Error Handling

### SP-API Error Codes

| Code | HTTP | Meaning | Retry? |
|------|------|---------|--------|
| InvalidInput | 400 | Bad request data | No |
| InvalidParameterValue | 400 | Parameter out of range | No |
| NotFound | 404 | Resource not found | No |
| Unauthorized | 401 | Auth failed | Refresh token |
| Forbidden | 403 | No permission | Check scopes |
| QuotaExceeded | 429 | Rate limited | Yes, backoff |
| InternalFailure | 500 | Server error | Yes |
| ServiceUnavailable | 503 | Temporary outage | Yes |

### Retry Strategy

```python
import time
import random
from spapi_client import SPAPIError

MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 120.0

def retry_with_backoff(func, *args, **kwargs):
    """Execute function with exponential backoff retry."""

    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)

        except SPAPIError as e:
            if not e.is_retryable():
                raise  # Don't retry client errors

            if attempt == MAX_RETRIES - 1:
                raise  # Last attempt

            # Calculate backoff with jitter
            backoff = min(
                INITIAL_BACKOFF * (2 ** attempt) + random.uniform(0, 1),
                MAX_BACKOFF
            )

            print(f"Retry {attempt + 1}/{MAX_RETRIES} after {backoff:.1f}s")
            time.sleep(backoff)

    raise RuntimeError("Max retries exceeded")
```

### Error Classification

```python
from spapi_client import SPAPIError

def handle_spapi_error(e: SPAPIError):
    """Route error to appropriate handler."""

    if e.status_code == 401:
        # Token expired or invalid
        return refresh_and_retry()

    elif e.status_code == 403:
        # Permission denied
        raise PermissionError(f"Missing API scope: {e.message}")

    elif e.status_code == 404:
        # Resource not found
        return None  # or raise custom NotFoundError

    elif e.is_rate_limited():
        # Rate limited - CLI handles automatically
        raise  # Let retry logic handle

    elif e.status_code >= 500:
        # Server error - retry
        raise  # Let retry logic handle

    else:
        # Unknown error
        raise RuntimeError(f"API error: {e}")
```

## Sandbox Testing

### Static vs Dynamic Sandbox

| Feature | Static | Dynamic |
|---------|--------|---------|
| Response Type | Canned | Realistic |
| Data Persistence | No | Limited |
| Use Case | Unit tests | Integration tests |
| Rate Limits | 5/sec, 15 burst | Same |

### Sandbox Configuration

```json
{
  "profiles": {
    "sandbox": {
      "name": "Sandbox - US",
      "region": "NA",
      "marketplace": "US",
      "lwa_client_id": "YOUR_CLIENT_ID",
      "lwa_client_secret": "YOUR_CLIENT_SECRET",
      "refresh_token": "YOUR_SANDBOX_REFRESH_TOKEN",
      "is_sandbox": true
    }
  }
}
```

### Testing Patterns

```python
# Use sandbox for testing
auth = SPAPIAuth()
client = SPAPIClient(auth, profile="sandbox")

# Test vendor operations
def test_vendor_order_flow():
    from spapi_vendor import VendorOrdersAPI

    api = VendorOrdersAPI(client)

    # Sandbox returns static test data
    status, data = api.get_purchase_orders(
        created_after="2024-01-01T00:00:00Z"
    )

    assert status == 200
    assert "payload" in data

    orders = data.get("payload", {}).get("orders", [])
    assert len(orders) > 0

# Test error handling
def test_error_handling():
    from spapi_client import SPAPIError

    try:
        # Invalid PO number should return 404
        status, data = api.get_purchase_order("INVALID_PO")
    except SPAPIError as e:
        assert e.status_code == 404
```

### Sandbox Limitations

1. **No real data** - Returns mock/static responses
2. **Limited operations** - Not all endpoints supported
3. **RDT from production** - Must get RDT tokens from prod
4. **No performance testing** - Not for load testing

## Multi-Marketplace Configuration

### Regional Setup

```json
{
  "default_profile": "us_production",
  "profiles": {
    "us_production": {
      "region": "NA",
      "marketplace": "US",
      "lwa_client_id": "amzn1.application-oa2-client.xxx",
      "lwa_client_secret": "secret",
      "refresh_token": "Atzr|xxx"
    },
    "ca_production": {
      "region": "NA",
      "marketplace": "CA",
      "lwa_client_id": "amzn1.application-oa2-client.xxx",
      "lwa_client_secret": "secret",
      "refresh_token": "Atzr|xxx"
    },
    "uk_production": {
      "region": "EU",
      "marketplace": "UK",
      "lwa_client_id": "amzn1.application-oa2-client.xxx",
      "lwa_client_secret": "secret",
      "refresh_token": "Atzr|xxx"
    },
    "de_production": {
      "region": "EU",
      "marketplace": "DE",
      "lwa_client_id": "amzn1.application-oa2-client.xxx",
      "lwa_client_secret": "secret",
      "refresh_token": "Atzr|xxx"
    },
    "jp_production": {
      "region": "FE",
      "marketplace": "JP",
      "lwa_client_id": "amzn1.application-oa2-client.xxx",
      "lwa_client_secret": "secret",
      "refresh_token": "Atzr|xxx"
    }
  }
}
```

### Cross-Region Operations

```python
# Process orders from multiple marketplaces
from concurrent.futures import ThreadPoolExecutor
from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient
from spapi_vendor import VendorOrdersAPI

def get_orders_for_marketplace(profile):
    auth = SPAPIAuth()
    client = SPAPIClient(auth, profile=profile)
    api = VendorOrdersAPI(client)

    status, data = api.get_purchase_orders(
        created_after="2024-01-01T00:00:00Z"
    )

    return {
        "profile": profile,
        "orders": data.get("payload", {}).get("orders", [])
    }

# Parallel fetch from multiple marketplaces
profiles = ["us_production", "uk_production", "de_production"]

with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(get_orders_for_marketplace, profiles))

# Consolidate results
all_orders = []
for result in results:
    for order in result["orders"]:
        order["marketplace"] = result["profile"]
        all_orders.append(order)
```

### Marketplace IDs Reference

```python
# North America
NA_MARKETPLACES = {
    "US": "ATVPDKIKX0DER",
    "CA": "A2EUQ1WTGCTBG2",
    "MX": "A1AM78C64UM0Y8",
    "BR": "A2Q3Y263D00KWC"
}

# Europe
EU_MARKETPLACES = {
    "UK": "A1F83G8C2ARO7P",
    "DE": "A1PA6795UKMFR9",
    "FR": "A13V1IB3VIYZZH",
    "IT": "APJ6JRA9NG5V4",
    "ES": "A1RKKUPIHCS9HS",
    "NL": "A1805IZSGTT6HS",
    "SE": "A2NODRKZP88ZB9",
    "PL": "A1C3SOZRARQ6R3",
    "TR": "A33AVAJ2PDY3EV",
    "IN": "A21TJRUUN4KGV"
}

# Far East
FE_MARKETPLACES = {
    "JP": "A1VC38T7YXB528",
    "AU": "A39IBJ37TRP1C6",
    "SG": "A19VAU5U5O7RUS"
}
```

## Performance Optimization

### Batch Operations

```python
# Batch multiple items in single request (where supported)
def batch_acknowledge_orders(client, acknowledgements):
    """Submit multiple acknowledgements in one request."""
    from spapi_vendor import VendorOrdersAPI

    api = VendorOrdersAPI(client)

    # API accepts batch
    return api.submit_acknowledgement(acknowledgements)
```

### Pagination Efficiency

```python
from spapi_client import paginate

# Efficient pagination with max page size
all_orders = paginate(
    client,
    "/vendor/orders/v1/purchaseOrders",
    "vendorOrders",
    params={
        "createdAfter": "2024-01-01T00:00:00Z",
        "limit": 100  # Max page size
    },
    max_pages=50  # Safety limit
)
```

### Caching

```python
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

CACHE_DIR = Path("~/.spapi_cache").expanduser()
CACHE_TTL = timedelta(hours=1)

def cache_key(endpoint, params):
    """Generate cache key from request."""
    key_data = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
    return hashlib.md5(key_data.encode()).hexdigest()

def get_cached(key):
    """Get cached response if valid."""
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        data = json.loads(cache_file.read_text())
        cached_at = datetime.fromisoformat(data["cached_at"])
        if datetime.now() - cached_at < CACHE_TTL:
            return data["response"]
    return None

def set_cached(key, response):
    """Cache response."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / f"{key}.json"
    cache_file.write_text(json.dumps({
        "cached_at": datetime.now().isoformat(),
        "response": response
    }))

# Usage
def cached_get(client, endpoint, api_name, params=None):
    key = cache_key(endpoint, params or {})
    cached = get_cached(key)
    if cached:
        return 200, cached

    status, data = client.get(endpoint, api_name, params=params)
    if status == 200:
        set_cached(key, data)
    return status, data
```

## Authentication Troubleshooting

### Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Expired token | 401 Unauthorized | Refresh automatically |
| Invalid credentials | 401 Unauthorized | Check config |
| Wrong region | 403 Forbidden | Match region to marketplace |
| Missing scope | 403 Forbidden | Add API permission |
| Invalid refresh token | invalid_grant | Re-authorize app |

### Debug Authentication

```python
from spapi_auth import SPAPIAuth

auth = SPAPIAuth()

# List available profiles
print("Profiles:", auth.list_profiles())

# Check token status
info = auth.get_token_info("production")
print(f"Token status: {info['status']}")
print(f"Expires in: {info['expires_in_seconds']}s")

# Test token refresh
try:
    token = auth.get_access_token("production")
    print(f"Token acquired: {token[:20]}...")
except Exception as e:
    print(f"Auth failed: {e}")

# Clear and retry
auth.clear_token_cache("production")
token = auth.get_access_token("production")
```

### Token Lifecycle

```
1. Initial: Refresh token from OAuth authorization
2. Request: Exchange refresh token for access token (LWA)
3. Cache: Store access token (~1 hour validity)
4. Use: Include access token in x-amz-access-token header
5. Refresh: Auto-refresh when expired
6. Rotate: Re-authorize annually (public apps)
```

## Monitoring and Logging

### Request Logging

```python
import logging

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Client includes request stats
client = SPAPIClient(auth)
# ... make requests ...

stats = client.get_stats()
print(f"Total requests: {stats['requests']}")
print(f"Retries: {stats['retries']}")
print(f"Rate limits hit: {stats['rate_limits_hit']}")
print(f"Errors: {stats['errors']}")
```

### Health Check

```python
def health_check(auth, profiles=None):
    """Check SP-API connectivity for all profiles."""
    profiles = profiles or auth.list_profiles()
    results = {}

    for profile in profiles:
        try:
            token = auth.get_access_token(profile)
            endpoint = auth.get_endpoint(profile)
            results[profile] = {
                "status": "healthy",
                "endpoint": endpoint,
                "token_preview": f"{token[:10]}..."
            }
        except Exception as e:
            results[profile] = {
                "status": "error",
                "error": str(e)
            }

    return results

# Run health check
auth = SPAPIAuth()
status = health_check(auth)
for profile, info in status.items():
    print(f"{profile}: {info['status']}")
```

## Related Skills

- `spapi-vendor-orders` - Order management
- `spapi-vendor-shipments` - Shipment operations
- `spapi-vendor-invoices` - Invoice submission
- `spapi-reports-feeds` - Reports and feeds
