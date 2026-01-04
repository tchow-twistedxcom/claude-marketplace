# Performance Optimization Patterns

Patterns for improving n8n workflow execution speed and resource efficiency.

## Performance Metrics

### Key Measurements
```yaml
metrics:
  execution_time:
    description: "Total workflow duration"
    target: "Depends on use case"
    measurement: "End time - start time"

  throughput:
    description: "Items processed per time unit"
    target: "Maximize within constraints"
    measurement: "Items / execution time"

  memory_usage:
    description: "Peak memory consumption"
    target: "Below system limits"
    measurement: "Monitor during execution"

  api_efficiency:
    description: "Useful data per API call"
    target: "Minimize calls, maximize payload"
    measurement: "Items / API calls"
```

## Parallel Processing

### When to Parallelize
```yaml
good_candidates:
  - Independent item processing
  - Multiple API calls to different endpoints
  - File operations on different files
  - Data transformations without dependencies

avoid_parallel:
  - Sequential dependencies
  - Shared resource modifications
  - Rate-limited APIs
  - Order-sensitive operations
```

### Parallel HTTP Requests
```json
{
  "id": "http-1",
  "name": "HTTP Request",
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4.2,
  "parameters": {
    "method": "GET",
    "url": "={{ $json.url }}",
    "options": {
      "batching": {
        "batch": {
          "batchSize": 10,
          "batchInterval": 100
        }
      }
    }
  }
}
```

### Split and Merge Pattern
```yaml
workflow:
  1. Trigger with items
  2. Split In Batches (10 items)
  3. Process batch (parallel operations)
  4. Merge results
  5. Continue with combined data

nodes:
  - Split In Batches (batchSize: 10)
  - Process (executes in parallel per batch)
  - Merge (wait for all batches)
```

### Parallel Branch Execution
```javascript
// Fan out to parallel branches
// n8n executes branches concurrently when multiple connections
// from same output
```

```yaml
connections:
  "Trigger":
    main:
      - # All these execute in parallel
        - node: "API Call 1"
        - node: "API Call 2"
        - node: "API Call 3"
```

## Batch Optimization

### Optimal Batch Sizes
```yaml
guidelines:
  api_calls:
    recommended: 50-100
    reasoning: "Balance between parallelism and rate limits"

  database_operations:
    recommended: 100-500
    reasoning: "Reduce query overhead"

  file_operations:
    recommended: 10-50
    reasoning: "Memory constraints"

  email_sending:
    recommended: 10-25
    reasoning: "SMTP server limits"
```

### Batch Insert Pattern
```javascript
// Instead of: 100 individual INSERTs
// Use: 1 bulk INSERT with 100 records

const records = items.map(item => ({
  id: item.json.id,
  name: item.json.name,
  email: item.json.email
}));

// Single bulk operation
return [{
  json: {
    query: `INSERT INTO users (id, name, email) VALUES ${
      records.map(() => '(?, ?, ?)').join(', ')
    }`,
    params: records.flatMap(r => [r.id, r.name, r.email])
  }
}];
```

### Batch API Requests
```javascript
// Combine multiple items into single API call
const items = $input.all();
const batchPayload = {
  records: items.map(item => item.json)
};

// Single API call instead of many
return [{
  json: {
    method: 'POST',
    url: 'https://api.example.com/batch',
    body: batchPayload
  }
}];
```

## Memory Management

### Streaming Large Data
```yaml
pattern: streaming
description: "Process data in chunks to avoid memory issues"

approach:
  - Fetch data in pages
  - Process each page
  - Discard processed data
  - Continue to next page

benefits:
  - Constant memory usage
  - Handles unlimited data size
  - More reliable for large datasets
```

### Field Selection
```javascript
// Only keep needed fields
return items.map(item => ({
  json: {
    // Only essential fields, not entire payload
    id: item.json.id,
    name: item.json.name,
    status: item.json.status
    // Exclude: large blobs, unused metadata, nested objects
  }
}));
```

### Early Filtering
```javascript
// Filter before expensive operations
const relevant = items.filter(item =>
  item.json.status === 'active' &&
  item.json.amount > 0
);

// Only process relevant items
return relevant;
```

### Memory-Efficient Transformations
```javascript
// Bad: creates many intermediate arrays
const step1 = items.map(i => transform1(i));
const step2 = step1.map(i => transform2(i));
const step3 = step2.filter(i => validate(i));
const result = step3.map(i => finalize(i));

// Good: single pass
return items.reduce((acc, item) => {
  const t1 = transform1(item);
  const t2 = transform2(t1);
  if (validate(t2)) {
    acc.push({ json: finalize(t2) });
  }
  return acc;
}, []);
```

## API Efficiency

### Request Consolidation
```yaml
before:
  calls: 100 # One per record
  latency: 100 * 200ms = 20s

after:
  calls: 2 # Batch of 50 each
  latency: 2 * 300ms = 0.6s
```

### Pagination Optimization
```javascript
// Maximize page size to reduce calls
const pageSize = 100; // Use API maximum
const totalPages = Math.ceil(totalRecords / pageSize);

// Fewer calls = faster execution
return [{
  json: {
    url: `${baseUrl}?limit=${pageSize}&offset=${offset}`
  }
}];
```

### Conditional Fetching
```javascript
// Use ETags or If-Modified-Since
const lastEtag = $json.storedEtag;

return [{
  json: {
    url: $json.url,
    headers: {
      'If-None-Match': lastEtag
    }
  }
}];

// Handle 304 Not Modified - skip processing
```

### GraphQL Field Selection
```javascript
// Only request needed fields
const query = `
  query {
    users(first: 100) {
      id
      name
      email
      # Don't request: avatar, preferences, history
    }
  }
`;

// Smaller response = faster transfer = less memory
```

## Caching Patterns

### Response Caching
```javascript
// Cache frequently accessed data
const cacheKey = `lookup_${$json.id}`;
const cached = await getFromCache(cacheKey);

if (cached && !isCacheExpired(cached)) {
  return [{ json: cached.data }];
}

// Fetch fresh data
const fresh = await fetchFromAPI($json.id);

// Store in cache
await setInCache(cacheKey, fresh, { ttl: 3600 });

return [{ json: fresh }];
```

### Lookup Table Pattern
```javascript
// Fetch all reference data once at start
const allCategories = $node["Get All Categories"].json;
const categoryMap = new Map(
  allCategories.map(c => [c.id, c.name])
);

// Use map for O(1) lookups instead of O(n) searches
return items.map(item => ({
  json: {
    ...item.json,
    categoryName: categoryMap.get(item.json.categoryId) || 'Unknown'
  }
}));
```

### Preloading Pattern
```yaml
workflow:
  1. Start - fetch all reference data in parallel
     - Categories
     - Statuses
     - Users
  2. Merge reference data
  3. Process main items using cached references
  4. No additional lookups needed during processing
```

## Database Optimization

### Query Optimization
```yaml
guidelines:
  - Select only needed columns
  - Use appropriate indexes
  - Limit result sets
  - Use EXPLAIN to analyze queries
  - Batch operations where possible
```

### Index-Aware Queries
```javascript
// Query using indexed columns
const query = `
  SELECT id, name, status
  FROM orders
  WHERE customer_id = $1   -- indexed
    AND created_at > $2    -- indexed
  ORDER BY created_at DESC
  LIMIT 100
`;

// Avoid non-indexed filters in WHERE clause
```

### Connection Pooling
```yaml
recommendation:
  - Reuse database connections
  - Configure appropriate pool size
  - Close connections properly
  - Monitor connection usage
```

## Workflow Structure

### Minimize Node Count
```yaml
before:
  nodes: 15
  - Get Data
  - Filter 1
  - Transform 1
  - Filter 2
  - Transform 2
  - ... (more single-purpose nodes)

after:
  nodes: 5
  - Get Data
  - Process (Code node combining transforms)
  - Validate
  - Output
```

### Code Node Consolidation
```javascript
// Combine multiple operations in single Code node
return items.map(item => {
  const data = item.json;

  // Filter
  if (data.status !== 'active') return null;

  // Transform
  const transformed = {
    id: data.id,
    fullName: `${data.firstName} ${data.lastName}`,
    email: data.email.toLowerCase(),
    total: data.price * data.quantity
  };

  // Validate
  if (!transformed.email.includes('@')) return null;

  return { json: transformed };
}).filter(Boolean);
```

### Early Termination
```javascript
// Stop processing when condition met
const targetFound = items.find(item => item.json.id === targetId);

if (targetFound) {
  // Found what we need, skip remaining processing
  return [{ json: targetFound.json }];
}

// Continue only if not found
```

## Monitoring and Profiling

### Execution Timing
```javascript
// Track timing in Code nodes
const startTime = Date.now();

// ... processing ...

const duration = Date.now() - startTime;
console.log(`Processing took ${duration}ms`);

return items.map(item => ({
  json: {
    ...item.json,
    _processingTime: duration
  }
}));
```

### Performance Logging
```javascript
// Log performance metrics
const metrics = {
  executionId: $execution.id,
  workflow: $workflow.name,
  itemCount: items.length,
  startTime: $json.startTime,
  endTime: new Date().toISOString(),
  duration: Date.now() - $json.startTime,
  itemsPerSecond: items.length / ((Date.now() - $json.startTime) / 1000)
};

console.log('Performance:', JSON.stringify(metrics));

return items;
```

### Bottleneck Identification
```yaml
approach:
  1. Enable execution logging
  2. Run workflow with timing
  3. Identify slowest nodes
  4. Profile specific operations
  5. Optimize bottlenecks first

common_bottlenecks:
  - External API calls
  - Database queries
  - Large data transformations
  - Sequential processing
  - Memory-intensive operations
```

## Best Practices Summary

```yaml
parallel_processing:
  - Use batching for independent operations
  - Fan out to parallel branches
  - Merge results efficiently
  - Respect rate limits

batch_optimization:
  - Size batches appropriately
  - Use bulk API operations
  - Batch database writes
  - Balance memory vs speed

memory_management:
  - Stream large datasets
  - Select only needed fields
  - Filter early in workflow
  - Clean up intermediate data

api_efficiency:
  - Consolidate requests
  - Maximize page sizes
  - Use conditional fetching
  - Request only needed fields

caching:
  - Cache reference data
  - Use lookup tables
  - Preload common data
  - Implement TTL policies

workflow_structure:
  - Minimize node count
  - Combine operations in Code nodes
  - Implement early termination
  - Remove unnecessary steps
```

## Anti-Patterns

```yaml
avoid:
  sequential_api_calls:
    problem: "One API call per item"
    solution: "Batch or parallelize"

  full_data_loading:
    problem: "Loading all data into memory"
    solution: "Stream with pagination"

  unused_fields:
    problem: "Keeping large unused objects"
    solution: "Select only needed fields"

  repeated_lookups:
    problem: "Same lookup for each item"
    solution: "Preload and use map"

  late_filtering:
    problem: "Filter after expensive operations"
    solution: "Filter as early as possible"

  synchronous_everything:
    problem: "Processing items one by one"
    solution: "Parallel processing where possible"
```
