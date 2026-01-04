# Rate Limiting Patterns

Patterns for managing API quotas and request throttling in n8n workflows.

## Rate Limit Types

### Request-Based Limits
```yaml
type: request_limit
description: "Maximum requests per time window"
examples:
  - "100 requests per minute"
  - "10,000 requests per day"
  - "5 requests per second"
handling: "Track request count, pause when approaching limit"
```

### Token Bucket
```yaml
type: token_bucket
description: "Tokens consumed per request, refilled over time"
examples:
  - "1000 tokens per hour, each request costs 1-10 tokens"
  - "Complex operations cost more tokens"
handling: "Track token balance, estimate cost before request"
```

### Concurrent Request Limits
```yaml
type: concurrent
description: "Maximum simultaneous requests"
examples:
  - "5 concurrent connections"
  - "10 parallel requests"
handling: "Use queue, limit parallel executions"
```

### Sliding Window
```yaml
type: sliding_window
description: "Rolling time window for limits"
examples:
  - "100 requests in any 60-second window"
handling: "Track request timestamps, check window before each request"
```

## Detection Patterns

### Response Header Parsing
```javascript
// Parse rate limit headers
const headers = $json.headers;

const rateLimitInfo = {
  limit: parseInt(headers['x-ratelimit-limit'] ||
                  headers['x-rate-limit-limit'] || 0),
  remaining: parseInt(headers['x-ratelimit-remaining'] ||
                      headers['x-rate-limit-remaining'] || 0),
  reset: parseInt(headers['x-ratelimit-reset'] ||
                  headers['x-rate-limit-reset'] || 0),
  retryAfter: parseInt(headers['retry-after'] || 0)
};

// Calculate wait time if needed
let waitMs = 0;
if (rateLimitInfo.remaining <= 0 && rateLimitInfo.reset) {
  waitMs = (rateLimitInfo.reset * 1000) - Date.now();
}

return [{
  json: {
    ...item.json,
    rateLimit: rateLimitInfo,
    shouldWait: waitMs > 0,
    waitMs
  }
}];
```

### 429 Response Handling
```javascript
// Handle rate limit exceeded
if ($json.statusCode === 429) {
  const retryAfter = $json.headers['retry-after'];
  const waitMs = retryAfter
    ? parseInt(retryAfter) * 1000
    : 60000; // Default 1 minute

  return [{
    json: {
      action: 'wait_and_retry',
      waitMs,
      originalRequest: $json.request,
      rateLimited: true
    }
  }];
}
```

## Throttling Patterns

### Fixed Delay
```yaml
pattern: fixed_delay
description: "Wait fixed time between requests"
configuration:
  delayMs: 100 # 10 requests per second

implementation:
  - Wait node with fixed interval
  - Simple but may not maximize throughput
```

### Wait Node Configuration
```json
{
  "id": "wait-1",
  "name": "Rate Limit Delay",
  "type": "n8n-nodes-base.wait",
  "typeVersion": 1.1,
  "position": [500, 300],
  "parameters": {
    "amount": 100,
    "unit": "milliseconds"
  }
}
```

### Adaptive Throttling
```javascript
// Adjust delay based on remaining quota
const remaining = $json.rateLimit.remaining;
const limit = $json.rateLimit.limit;
const usagePercent = ((limit - remaining) / limit) * 100;

let delayMs;
if (usagePercent > 90) {
  delayMs = 5000; // Very slow when nearly exhausted
} else if (usagePercent > 75) {
  delayMs = 1000; // Slow down significantly
} else if (usagePercent > 50) {
  delayMs = 500; // Moderate delay
} else {
  delayMs = 100; // Normal speed
}

return [{
  json: {
    ...item.json,
    adaptiveDelay: delayMs,
    quotaUsage: usagePercent
  }
}];
```

### Leaky Bucket Implementation
```javascript
// Leaky bucket rate limiter
const bucketSize = 10; // Max burst
const leakRate = 2; // Requests per second

let bucket = $json.bucketLevel || 0;
const lastLeak = $json.lastLeakTime || Date.now();
const now = Date.now();

// Leak tokens based on time passed
const leaked = Math.floor((now - lastLeak) / 1000) * leakRate;
bucket = Math.max(0, bucket - leaked);

// Check if we can add to bucket
if (bucket < bucketSize) {
  bucket++;
  return [{
    json: {
      ...item.json,
      canProceed: true,
      bucketLevel: bucket,
      lastLeakTime: now
    }
  }];
} else {
  // Calculate wait time
  const waitMs = Math.ceil((1 / leakRate) * 1000);
  return [{
    json: {
      canProceed: false,
      waitMs,
      bucketLevel: bucket,
      lastLeakTime: now
    }
  }];
}
```

## Queue Management

### Request Queue Pattern
```yaml
pattern: request_queue
description: "Queue requests and process at controlled rate"
components:
  - Incoming request handler
  - Queue storage (database, Redis)
  - Queue processor (scheduled workflow)
  - Rate-limited API caller
```

### Queue Entry Schema
```javascript
// Queue entry structure
const queueEntry = {
  id: `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
  createdAt: new Date().toISOString(),
  priority: $json.priority || 'normal', // low, normal, high
  request: {
    method: $json.method,
    url: $json.url,
    headers: $json.headers,
    body: $json.body
  },
  status: 'pending', // pending, processing, completed, failed
  retries: 0,
  maxRetries: 3,
  callbackUrl: $json.callbackUrl
};

return [{ json: queueEntry }];
```

### Queue Processor
```javascript
// Process queue respecting rate limits
const rateLimitPerMinute = 60;
const batchSize = Math.min(10, rateLimitPerMinute);
const delayBetweenBatches = (60 / (rateLimitPerMinute / batchSize)) * 1000;

// Fetch batch of pending requests
const pending = $node["Get Pending"].json.items;
const batch = pending.slice(0, batchSize);

return batch.map(item => ({
  json: {
    ...item,
    status: 'processing',
    processingStarted: new Date().toISOString()
  }
}));

// After processing batch, wait before next batch
```

## Quota Tracking

### Per-API Quota Tracker
```javascript
// Track quota usage per API
const apiQuotas = $json.quotas || {
  'api.example.com': {
    daily: { limit: 10000, used: 0, reset: null },
    perMinute: { limit: 100, used: 0, reset: null }
  }
};

const api = extractDomain($json.url);
const now = Date.now();

// Reset counters if window passed
if (apiQuotas[api].daily.reset && now > apiQuotas[api].daily.reset) {
  apiQuotas[api].daily.used = 0;
  apiQuotas[api].daily.reset = getEndOfDay();
}

if (apiQuotas[api].perMinute.reset && now > apiQuotas[api].perMinute.reset) {
  apiQuotas[api].perMinute.used = 0;
  apiQuotas[api].perMinute.reset = now + 60000;
}

// Check if within limits
const canProceed =
  apiQuotas[api].daily.used < apiQuotas[api].daily.limit &&
  apiQuotas[api].perMinute.used < apiQuotas[api].perMinute.limit;

if (canProceed) {
  apiQuotas[api].daily.used++;
  apiQuotas[api].perMinute.used++;
}

return [{
  json: {
    canProceed,
    quotas: apiQuotas,
    waitUntil: canProceed ? null : apiQuotas[api].perMinute.reset
  }
}];
```

### Quota Monitoring Report
```javascript
// Generate quota usage report
const quotas = $json.quotaData;

return Object.entries(quotas).map(([api, limits]) => ({
  json: {
    api,
    dailyUsage: {
      used: limits.daily.used,
      limit: limits.daily.limit,
      percent: ((limits.daily.used / limits.daily.limit) * 100).toFixed(1),
      remaining: limits.daily.limit - limits.daily.used
    },
    perMinuteUsage: {
      used: limits.perMinute.used,
      limit: limits.perMinute.limit,
      percent: ((limits.perMinute.used / limits.perMinute.limit) * 100).toFixed(1)
    },
    alerts: [
      limits.daily.used > limits.daily.limit * 0.8 ? 'Daily quota >80%' : null,
      limits.perMinute.used > limits.perMinute.limit * 0.9 ? 'Per-minute near limit' : null
    ].filter(Boolean)
  }
}));
```

## Backoff Strategies

### Linear Backoff
```javascript
const attempt = $json.retryAttempt || 1;
const baseDelay = 1000;
const delay = baseDelay * attempt;

return [{
  json: {
    ...item.json,
    delay,
    strategy: 'linear'
  }
}];
```

### Exponential Backoff
```javascript
const attempt = $json.retryAttempt || 1;
const baseDelay = 1000;
const maxDelay = 60000;
const delay = Math.min(baseDelay * Math.pow(2, attempt - 1), maxDelay);

return [{
  json: {
    ...item.json,
    delay,
    strategy: 'exponential'
  }
}];
```

### Exponential with Jitter
```javascript
// Prevents thundering herd problem
const attempt = $json.retryAttempt || 1;
const baseDelay = 1000;
const maxDelay = 60000;

// Full jitter
const cap = Math.min(baseDelay * Math.pow(2, attempt - 1), maxDelay);
const delay = Math.random() * cap;

// Decorrelated jitter (alternative)
// const delay = Math.min(maxDelay, Math.random() * (baseDelay * 3) + baseDelay);

return [{
  json: {
    ...item.json,
    delay: Math.round(delay),
    strategy: 'exponential_jitter'
  }
}];
```

## Multi-API Orchestration

### Priority-Based Processing
```javascript
// Process requests by priority, respecting rate limits
const requests = $input.all();

const prioritized = requests.sort((a, b) => {
  const priorityOrder = { high: 0, normal: 1, low: 2 };
  return priorityOrder[a.json.priority] - priorityOrder[b.json.priority];
});

// Group by API to respect per-API limits
const byApi = {};
for (const req of prioritized) {
  const api = extractDomain(req.json.url);
  if (!byApi[api]) byApi[api] = [];
  byApi[api].push(req);
}

return Object.entries(byApi).map(([api, reqs]) => ({
  json: {
    api,
    requests: reqs.map(r => r.json),
    count: reqs.length
  }
}));
```

### API Budget Allocation
```yaml
pattern: budget_allocation
description: "Distribute rate limit across workflows"

example:
  total_limit: 1000 # per minute
  allocation:
    critical_sync: 400 # 40%
    normal_operations: 300 # 30%
    background_tasks: 200 # 20%
    reserve: 100 # 10% buffer

implementation:
  - Track usage per workflow category
  - Enforce per-category limits
  - Allow borrowing from reserve
  - Alert when approaching limits
```

## Common API Rate Limits

```yaml
reference:
  shopify:
    bucket_size: 40
    leak_rate: 2 # per second
    type: "leaky_bucket"

  github:
    authenticated: 5000 # per hour
    unauthenticated: 60 # per hour
    type: "token_bucket"

  stripe:
    read: 100 # per second
    write: 100 # per second
    type: "request_based"

  google_apis:
    varies_by_api: true
    typical: "100 per 100 seconds"
    type: "sliding_window"

  slack:
    web_api: 50 # per minute
    events_api: "no hard limit"
    type: "tiered"
```

## Best Practices

```yaml
design:
  - Always check rate limit headers
  - Implement backoff before hitting limits
  - Use queues for high-volume operations
  - Track quota usage persistently

implementation:
  - Parse vendor-specific header formats
  - Add jitter to prevent synchronized retries
  - Implement circuit breakers
  - Log rate limit events for analysis

monitoring:
  - Track quota usage trends
  - Alert before limits are reached
  - Monitor for 429 response spikes
  - Review API usage periodically

optimization:
  - Batch requests where possible
  - Cache frequently accessed data
  - Use webhooks instead of polling
  - Prioritize critical operations
```
