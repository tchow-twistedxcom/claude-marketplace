# Plytix API Rate Limits Reference

Official rate limiting documentation and best practices for the Plytix PIM API.

## Rate Limit Structure

Plytix enforces **two-tier rate limiting**:

| Limit Type | Window | Description |
|------------|--------|-------------|
| **Short-term** | 10 seconds | Burst protection - limits rapid requests |
| **Long-term** | 1 hour | Sustained usage limit |

**Key Points**:
- Every single request counts as a "hit"
- Both limits must be satisfied for a request to succeed
- Limits vary by account plan (check [Plytix Pricing](https://www.plytix.com/pricing))
- Contact your account manager for specific limit values

## HTTP Status Codes

| Code | Name | Description |
|------|------|-------------|
| 429 | TOO MANY REQUESTS | API rate limit exceeded - must wait before retrying |

### 429 Response Format

```json
{
  "error": {
    "msg": "Rate limit exceeded",
    "retry_after": 1800
  }
}
```

The `retry_after` field indicates seconds to wait before retrying.

## Authentication Limits

| Limit | Value | Description |
|-------|-------|-------------|
| Token Lifetime | **15 minutes** | Tokens expire after 15 minutes |
| Token Refresh | On 401 | Must request new token when expired |

```python
# Token refresh pattern
try:
    result = api.some_operation()
except PlytixAPIError as e:
    if e.status_code == 401:
        api.refresh_token()  # Get new token
        result = api.some_operation()  # Retry
```

## Search & Pagination Limits

| Limit | Default | Max | Description |
|-------|---------|-----|-------------|
| `page` | 1 | - | First page returned by default |
| `page_size` | 25 | 100 | Items per page |
| `attributes` | - | **20** | Maximum attributes per search result |

### Attributes Limit (Important!)

> **There's a limit of 20 attributes that can be retrieved per search.**
> If you need more than 20 attributes, you must make additional `get_product(id)` calls.

```python
# If you need more than 20 attributes:
results = api.search_products(
    filters=[...],
    attributes=['attr1', 'attr2', ..., 'attr20']  # Max 20
)

# Then get full details for products that need more attributes
for product in results['data']:
    full_product = api.get_product(product['id'])  # All attributes
```

## Rate Limit Handling

### Basic Retry Pattern

```python
import time
from plytix_api import PlytixAPI, PlytixAPIError

api = PlytixAPI()

def with_rate_limit_retry(operation, max_retries=3):
    """Execute operation with rate limit retry."""
    for attempt in range(max_retries):
        try:
            return operation()
        except PlytixAPIError as e:
            if e.status_code == 429:
                # Extract retry_after from error
                retry_after = e.details.get('retry_after', 60)

                # Cap wait time for reasonable retry
                wait_time = min(int(retry_after), 300)  # Max 5 min wait

                print(f"Rate limited. Waiting {wait_time}s (attempt {attempt + 1})")
                time.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")

# Usage
result = with_rate_limit_retry(lambda: api.search_products(filters=[...]))
```

### Batch Processing with Pacing

```python
import time

def batch_process_with_pacing(items, operation, delay=0.2):
    """
    Process items with delay between requests.

    Args:
        items: List of items to process
        operation: Function(item) -> result
        delay: Seconds between requests (default 0.2 = 5 req/sec)
    """
    results = []

    for i, item in enumerate(items):
        try:
            result = operation(item)
            results.append({'item': item, 'result': result, 'status': 'success'})
        except PlytixAPIError as e:
            if e.status_code == 429:
                # Rate limited - wait and retry
                retry_after = e.details.get('retry_after', 60)
                print(f"Rate limited at item {i}. Waiting {retry_after}s...")
                time.sleep(int(retry_after))

                # Retry this item
                result = operation(item)
                results.append({'item': item, 'result': result, 'status': 'success'})
            else:
                results.append({'item': item, 'error': str(e), 'status': 'failed'})

        # Preventive delay between requests
        time.sleep(delay)

    return results

# Usage
products = [...]  # List of products to update
results = batch_process_with_pacing(
    products,
    lambda p: api.update_product(p['id'], p['data']),
    delay=0.3  # ~3 requests per second
)
```

### RateLimiter Class Pattern

For high-volume operations, use a token bucket rate limiter:

```python
import time
import threading

class RateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(self, rate: float = 3.0, burst: int = 5):
        """
        Args:
            rate: Requests per second (default 3.0)
            burst: Maximum burst size (default 5)
        """
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self, timeout: float = 30.0) -> bool:
        """Wait for a token to become available."""
        deadline = time.monotonic() + timeout

        while True:
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
                self.last_update = now

                if self.tokens >= 1:
                    self.tokens -= 1
                    return True

            if time.monotonic() >= deadline:
                return False

            time.sleep(0.1)

# Usage
limiter = RateLimiter(rate=3.0, burst=5)

for product in products:
    limiter.acquire()  # Wait for rate limit slot
    api.update_product(product['id'], product['data'])
```

## Recommended Rate Limits

Based on typical Plytix plan limits and best practices:

| Operation Type | Recommended Rate | Delay |
|----------------|------------------|-------|
| Search operations | 3-5 req/sec | 0.2-0.3s |
| Single CRUD | 3-5 req/sec | 0.2-0.3s |
| Bulk updates | 2-3 req/sec | 0.3-0.5s |
| Asset uploads | 1-2 req/sec | 0.5-1.0s |
| Heavy operations | 1 req/sec | 1.0s |

## Best Practices

### 1. Use Bulk Operations When Available

```python
# BAD: Individual calls (N API calls)
for product_id in product_ids:
    api.get_product(product_id)

# GOOD: Search with filters (1-2 API calls)
api.search_products(
    filters=[{'field': 'id', 'operator': 'in', 'value': product_ids}],
    limit=100
)
```

### 2. Pre-build Indexes for Deduplication

```python
# Instead of checking each product individually:
# BAD: N API calls
for product in products:
    existing = api.get_product_assets(product['id'])  # API call each time

# GOOD: Build index upfront (paginated search)
products_with_assets = set()
page = 1
while True:
    result = api.search_products(
        filters=[{'field': 'assets', 'operator': 'len_gte', 'value': 1}],
        page=page, limit=100
    )
    for p in result['data']:
        products_with_assets.add(p['id'])
    if not result['pagination'].get('has_next'):
        break
    page += 1

# Then use the index (no API calls)
for product in products:
    if product['id'] in products_with_assets:
        continue  # Already has assets
```

### 3. Implement Exponential Backoff

```python
import random

def exponential_backoff_retry(operation, max_retries=5, base_delay=1.0):
    """Retry with exponential backoff and jitter."""
    for attempt in range(max_retries):
        try:
            return operation()
        except PlytixAPIError as e:
            if e.status_code == 429:
                # Use retry_after if provided, otherwise calculate
                retry_after = e.details.get('retry_after')
                if retry_after:
                    delay = int(retry_after)
                else:
                    # Exponential backoff with jitter
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)

                print(f"Rate limited. Retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                raise
    raise Exception("Max retries exceeded")
```

### 4. Monitor and Log Rate Limit Events

```python
import logging

logger = logging.getLogger(__name__)

class RateLimitTracker:
    """Track rate limit events for monitoring."""

    def __init__(self):
        self.events = []

    def record(self, retry_after: int, endpoint: str):
        self.events.append({
            'timestamp': time.time(),
            'retry_after': retry_after,
            'endpoint': endpoint
        })
        logger.warning(
            f"Rate limited on {endpoint}: retry_after={retry_after}s "
            f"(total events: {len(self.events)})"
        )

    def get_summary(self):
        if not self.events:
            return "No rate limit events"

        total = len(self.events)
        max_wait = max(e['retry_after'] for e in self.events)
        return f"{total} rate limit events, max wait: {max_wait}s"
```

## Common Pitfalls

### 1. Per-Item API Calls in Loops

```python
# WRONG: This will rate limit quickly
for asin in asins:  # 1000 items
    product = api.search_products(filters=[{'field': 'sku', 'operator': 'eq', 'value': asin}])
    assets = api.get_product_assets(product['id'])  # 2000 API calls!
```

### 2. Not Using Pagination Limits

```python
# WRONG: Fetching 1 item per page
for page in range(1, 1000):
    result = api.search_products(page=page, limit=1)  # 1000 API calls

# RIGHT: Fetch max items per page
for page in range(1, 10):
    result = api.search_products(page=page, limit=100)  # 10 API calls
```

### 3. Ignoring retry_after

```python
# WRONG: Fixed delay
except PlytixAPIError as e:
    if e.status_code == 429:
        time.sleep(60)  # May be too short or too long

# RIGHT: Use retry_after from response
except PlytixAPIError as e:
    if e.status_code == 429:
        wait = e.details.get('retry_after', 60)
        time.sleep(int(wait))
```

## Summary

| Concept | Value/Recommendation |
|---------|---------------------|
| Rate limit tiers | 10-second + 1-hour windows |
| HTTP code for rate limit | 429 TOO MANY REQUESTS |
| Token lifetime | 15 minutes |
| Max attributes per search | 20 |
| Default page size | 25 (max 100) |
| Recommended delay | 0.2-0.5s between requests |
| Always use | `retry_after` from 429 responses |
