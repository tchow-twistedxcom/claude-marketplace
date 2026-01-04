# Error Handling Patterns

Patterns for graceful failure handling and recovery in n8n workflows.

## Error Classification

### Error Categories
```yaml
transient_errors:
  description: "Temporary failures that may succeed on retry"
  examples:
    - Network timeouts
    - Rate limiting (429)
    - Service unavailable (503)
    - Connection reset
  strategy: "Retry with backoff"

permanent_errors:
  description: "Failures that won't succeed on retry"
  examples:
    - Invalid credentials (401)
    - Not found (404)
    - Validation errors (400)
    - Forbidden (403)
  strategy: "Fail fast, alert, manual intervention"

data_errors:
  description: "Issues with the data being processed"
  examples:
    - Missing required fields
    - Invalid format
    - Constraint violations
  strategy: "Skip, queue for review, or transform"

system_errors:
  description: "Infrastructure or code issues"
  examples:
    - Out of memory
    - Disk full
    - Code bugs
  strategy: "Alert immediately, investigate"
```

### Error Detection Code
```javascript
// Classify errors
const statusCode = $json.statusCode || 0;
const errorMessage = $json.error?.message || '';

let errorType = 'unknown';
let retryable = false;

if (statusCode === 429 || statusCode >= 500) {
  errorType = 'transient';
  retryable = true;
} else if (statusCode === 401 || statusCode === 403) {
  errorType = 'auth';
  retryable = false;
} else if (statusCode === 400 || statusCode === 422) {
  errorType = 'validation';
  retryable = false;
} else if (statusCode === 404) {
  errorType = 'not_found';
  retryable = false;
} else if (errorMessage.includes('ECONNREFUSED') ||
           errorMessage.includes('ETIMEDOUT')) {
  errorType = 'network';
  retryable = true;
}

return [{
  json: {
    ...item.json,
    errorType,
    retryable,
    originalError: $json.error
  }
}];
```

## Retry Patterns

### Simple Retry
```yaml
pattern: simple_retry
description: "Fixed delay between retries"
configuration:
  maxRetries: 3
  delayMs: 1000
use_case: "Quick operations, stable APIs"
```

### Exponential Backoff
```javascript
// Calculate delay with exponential backoff
const attempt = $json.retryAttempt || 1;
const baseDelay = 1000; // 1 second
const maxDelay = 60000; // 60 seconds
const jitter = Math.random() * 1000; // Random 0-1 second

const delay = Math.min(
  baseDelay * Math.pow(2, attempt - 1) + jitter,
  maxDelay
);

return [{
  json: {
    ...item.json,
    retryAttempt: attempt,
    nextRetryDelay: delay,
    shouldRetry: attempt < 5 // Max 5 attempts
  }
}];
```

### Retry with Circuit Breaker
```javascript
// Circuit breaker pattern
const failureThreshold = 5;
const resetTimeout = 60000; // 1 minute

// Get circuit state (from memory/cache)
const circuitState = $json.circuitState || {
  failures: 0,
  state: 'closed', // closed, open, half-open
  lastFailure: null
};

if (circuitState.state === 'open') {
  const timeSinceFailure = Date.now() - circuitState.lastFailure;
  if (timeSinceFailure < resetTimeout) {
    return [{
      json: {
        action: 'skip',
        reason: 'Circuit breaker open',
        retryAfter: resetTimeout - timeSinceFailure
      }
    }];
  }
  // Move to half-open
  circuitState.state = 'half-open';
}

// Proceed with call
// On success: reset to closed
// On failure: increment failures, open if threshold reached
```

## Error Branch Pattern

### Node Error Output Configuration
```json
{
  "id": "http-1",
  "name": "HTTP Request",
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4.2,
  "position": [400, 300],
  "parameters": {
    "url": "https://api.example.com/data"
  },
  "onError": "continueErrorOutput"
}
```

### Branching on Error
```yaml
workflow_structure:
  HTTP Request:
    outputs:
      success: [Process Data]
      error: [Handle Error]

  Handle Error:
    logic:
      - Classify error
      - IF retryable → Retry Queue
      - IF validation → Log and Skip
      - IF critical → Alert and Fail
```

## Fallback Patterns

### Primary/Secondary Source
```yaml
pattern: fallback_source
workflow:
  - Try primary API
  - On error → Try secondary API
  - On error → Try cached data
  - On error → Return default
```

### Degraded Operation
```javascript
// Attempt full operation, fall back to partial
let result;

try {
  // Full operation with all features
  result = await fullOperation($json);
} catch (error) {
  console.log('Full operation failed, trying degraded mode');
  try {
    // Degraded operation with essential features only
    result = await degradedOperation($json);
    result.degraded = true;
  } catch (fallbackError) {
    // Ultimate fallback
    result = {
      success: false,
      degraded: true,
      cached: true,
      data: getCachedData($json.id)
    };
  }
}

return [{ json: result }];
```

### Default Value Fallback
```javascript
// Provide sensible defaults on error
return [{
  json: {
    id: $json.id,
    name: $json.name || 'Unknown',
    email: $json.email || null,
    status: $json.status || 'pending',
    metadata: $json.metadata || {},
    _error: $json.error?.message
  }
}];
```

## Dead Letter Queue Pattern

### Structure
```yaml
pattern: dead_letter_queue
purpose: "Store failed items for later processing"
components:
  - Main workflow (with error handling)
  - DLQ storage (database, queue, or file)
  - DLQ processor workflow
  - Retry/purge mechanism
```

### DLQ Entry Creation
```javascript
// Create DLQ entry
return [{
  json: {
    dlqId: `dlq_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    originalItem: $json.originalItem,
    error: {
      message: $json.error?.message,
      code: $json.error?.code,
      stack: $json.error?.stack
    },
    metadata: {
      workflowId: $workflow.id,
      workflowName: $workflow.name,
      executionId: $execution.id,
      failedAt: new Date().toISOString(),
      retryCount: $json.retryCount || 0,
      lastRetry: $json.lastRetry || null
    }
  }
}];
```

### DLQ Processor
```yaml
workflow: dlq_processor
schedule: "Every 15 minutes"
steps:
  1. Fetch failed items from DLQ
  2. Filter retryable items
  3. Attempt reprocessing
  4. On success → Remove from DLQ
  5. On failure → Update retry count
  6. Remove expired items (>7 days)
```

## Error Notification Pattern

### Immediate Alert
```javascript
// Format error for notification
return [{
  json: {
    channel: '#alerts',
    text: `:rotating_light: Workflow Error`,
    blocks: [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*Workflow:* ${$workflow.name}\n*Error:* ${$json.error.message}\n*Time:* ${new Date().toISOString()}`
        }
      },
      {
        type: 'actions',
        elements: [
          {
            type: 'button',
            text: { type: 'plain_text', text: 'View Execution' },
            url: `https://n8n.example.com/execution/${$execution.id}`
          }
        ]
      }
    ]
  }
}];
```

### Aggregated Error Report
```javascript
// Collect errors during execution
// Send summary at end
const errors = $json.collectedErrors || [];

if (errors.length > 0) {
  return [{
    json: {
      subject: `Workflow Errors: ${errors.length} failures`,
      body: {
        summary: `${errors.length} errors in ${$workflow.name}`,
        timeRange: {
          start: errors[0].timestamp,
          end: errors[errors.length - 1].timestamp
        },
        errorBreakdown: groupBy(errors, 'errorType'),
        samples: errors.slice(0, 5)
      }
    }
  }];
}

return [];
```

## Compensation Pattern

### Saga with Compensation
```yaml
pattern: saga_compensation
description: "Rollback partial changes on failure"

transaction_steps:
  step1:
    action: "Create order"
    compensation: "Delete order"
  step2:
    action: "Reserve inventory"
    compensation: "Release inventory"
  step3:
    action: "Charge payment"
    compensation: "Refund payment"

on_failure:
  - Execute compensations in reverse order
  - Log compensation results
  - Report final state
```

### Compensation Implementation
```javascript
// Track completed steps for compensation
const completedSteps = $json.completedSteps || [];
const compensations = {
  'create_order': async (data) => { /* delete order */ },
  'reserve_inventory': async (data) => { /* release inventory */ },
  'charge_payment': async (data) => { /* refund payment */ }
};

// On failure: compensate in reverse
const failedStep = $json.failedStep;
const stepsToCompensate = completedSteps
  .slice(0, completedSteps.indexOf(failedStep))
  .reverse();

const compensationResults = [];
for (const step of stepsToCompensate) {
  try {
    await compensations[step]($json.stepData[step]);
    compensationResults.push({ step, status: 'compensated' });
  } catch (error) {
    compensationResults.push({ step, status: 'failed', error: error.message });
  }
}

return [{
  json: {
    originalError: $json.error,
    compensations: compensationResults
  }
}];
```

## Error Recovery Workflow

### Error Trigger Setup
```json
{
  "id": "error-trigger-1",
  "name": "Error Trigger",
  "type": "n8n-nodes-base.errorTrigger",
  "typeVersion": 1,
  "position": [100, 300],
  "parameters": {}
}
```

### Centralized Error Handler
```yaml
workflow: error_handler
trigger: Error Trigger
steps:
  1. Parse error context
  2. Classify error severity
  3. Route by severity:
     - Critical → Page on-call, pause workflow
     - High → Slack alert, create ticket
     - Medium → Log, aggregate
     - Low → Log only
  4. Store in error database
  5. Update monitoring dashboard
```

## Best Practices

```yaml
design:
  - Enable error output on all HTTP nodes
  - Classify errors before handling
  - Implement retries for transient errors
  - Use dead letter queues for persistence

implementation:
  - Log errors with full context
  - Include correlation IDs for tracing
  - Set appropriate retry limits
  - Implement circuit breakers for external APIs

monitoring:
  - Track error rates by type
  - Alert on error spikes
  - Review DLQ regularly
  - Measure mean time to recovery

testing:
  - Test error paths explicitly
  - Simulate network failures
  - Verify compensation logic
  - Test DLQ processing
```

## Error Context Template

```javascript
// Standard error context
return [{
  json: {
    error: {
      type: errorType,
      code: errorCode,
      message: errorMessage,
      stack: error.stack
    },
    context: {
      workflowId: $workflow.id,
      workflowName: $workflow.name,
      executionId: $execution.id,
      nodeName: 'Node Name',
      timestamp: new Date().toISOString()
    },
    input: {
      // Original input that caused error
      itemId: $json.id,
      payload: $json
    },
    recovery: {
      retryable: true,
      retryCount: 0,
      maxRetries: 3,
      nextRetry: null
    }
  }
}];
```
