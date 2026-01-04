# Webhook Patterns

Patterns for designing robust webhook endpoints in n8n.

## Webhook Types

### Synchronous Webhook
```yaml
pattern: synchronous
description: "Respond immediately after processing"
configuration:
  responseMode: "lastNode"
  timeout: 30s
use_case: "Quick validations, simple transformations"

workflow:
  - Webhook (trigger)
  - Process Data
  - Respond to Webhook
```

### Asynchronous Webhook
```yaml
pattern: asynchronous
description: "Acknowledge immediately, process later"
configuration:
  responseMode: "onReceived"
use_case: "Long-running processes, external API calls"

workflow:
  - Webhook (immediate response)
  - Queue processing (background)
```

### Respond-Later Webhook
```yaml
pattern: respond_later
description: "Control exactly when to respond"
configuration:
  responseMode: "responseNode"
use_case: "Complex branching, conditional responses"

workflow:
  - Webhook
  - IF (condition)
  - Branch A → Respond (200)
  - Branch B → Respond (400)
```

## Authentication Patterns

### No Authentication
```json
{
  "parameters": {
    "authentication": "none",
    "path": "simple-webhook"
  }
}
```
Use case: Internal networks, development

### Basic Authentication
```json
{
  "parameters": {
    "authentication": "basicAuth"
  },
  "credentials": {
    "httpBasicAuth": {
      "id": "credential-id",
      "name": "Webhook Auth"
    }
  }
}
```
Use case: Simple external integrations

### Header Authentication
```json
{
  "parameters": {
    "authentication": "headerAuth"
  },
  "credentials": {
    "httpHeaderAuth": {
      "id": "credential-id",
      "name": "API Key Auth"
    }
  }
}
```
Use case: API key validation

### HMAC Signature Validation
```javascript
// Code node for HMAC validation
const crypto = require('crypto');
const secret = $env.WEBHOOK_SECRET;
const payload = JSON.stringify($json);
const signature = $json.headers['x-signature'];

const expected = crypto
  .createHmac('sha256', secret)
  .update(payload)
  .digest('hex');

if (signature !== `sha256=${expected}`) {
  throw new Error('Invalid signature');
}

return items;
```
Use case: GitHub, Stripe, Shopify webhooks

## Request Validation Pattern

### Input Schema Validation
```javascript
// Code node for validation
const required = ['id', 'email', 'action'];
const errors = [];

for (const field of required) {
  if (!$json[field]) {
    errors.push(`Missing required field: ${field}`);
  }
}

if ($json.email && !$json.email.includes('@')) {
  errors.push('Invalid email format');
}

if (errors.length > 0) {
  throw new Error(`Validation failed: ${errors.join(', ')}`);
}

return items;
```

### Type Coercion Pattern
```javascript
// Normalize incoming data
return [{
  json: {
    id: String($json.id),
    amount: Number($json.amount) || 0,
    active: Boolean($json.active),
    tags: Array.isArray($json.tags) ? $json.tags : [],
    metadata: $json.metadata || {}
  }
}];
```

## Response Patterns

### Standard Success Response
```json
{
  "type": "n8n-nodes-base.respondToWebhook",
  "parameters": {
    "respondWith": "json",
    "responseBody": "={{ { \"success\": true, \"id\": $json.id } }}"
  }
}
```

### Error Response Pattern
```javascript
// In error branch
return [{
  json: {
    success: false,
    error: {
      code: 'VALIDATION_ERROR',
      message: $json.errorMessage,
      details: $json.errorDetails
    }
  }
}];
```

### Conditional Response Status
```json
{
  "parameters": {
    "respondWith": "json",
    "responseCode": "={{ $json.success ? 200 : 400 }}",
    "responseBody": "={{ $json }}"
  }
}
```

## Security Patterns

### IP Allowlisting
```javascript
// Code node for IP check
const allowedIPs = ['1.2.3.4', '5.6.7.8'];
const clientIP = $json.headers['x-forwarded-for'] ||
                 $json.headers['x-real-ip'];

if (!allowedIPs.includes(clientIP)) {
  throw new Error(`IP ${clientIP} not allowed`);
}

return items;
```

### Rate Limiting Check
```javascript
// Use with external rate limiter (Redis, etc.)
const clientId = $json.headers['x-api-key'];
const rateLimitKey = `ratelimit:${clientId}`;

// Check rate limit via HTTP Request to rate limiter
// Throw error if exceeded
```

### Request Deduplication
```javascript
// Prevent duplicate processing
const requestId = $json.headers['x-request-id'] ||
                  $json.headers['idempotency-key'];

if (!requestId) {
  throw new Error('Request ID required for deduplication');
}

// Check if already processed (via database/cache)
// If exists, return cached response
// Otherwise, process and store

return [{
  json: {
    ...item.json,
    requestId,
    isNewRequest: true
  }
}];
```

## Webhook URL Patterns

### Path Design
```yaml
patterns:
  resource_based:
    format: "/webhooks/{resource}/{action}"
    example: "/webhooks/orders/created"

  version_based:
    format: "/v1/webhooks/{resource}"
    example: "/v1/webhooks/customers"

  tenant_based:
    format: "/webhooks/{tenant_id}/{resource}"
    example: "/webhooks/acme-corp/invoices"

  uuid_based:
    format: "/webhooks/{uuid}"
    example: "/webhooks/a1b2c3d4-e5f6-7890"
```

### URL Security
```yaml
recommendations:
  - Use unique, non-guessable paths
  - Include version in path for evolution
  - Never include secrets in URL
  - Use short, memorable paths for manual testing
```

## Common Webhook Sources

### GitHub Webhooks
```javascript
// Validate GitHub signature
const crypto = require('crypto');
const signature = $json.headers['x-hub-signature-256'];
const payload = JSON.stringify($json.body);
const secret = $env.GITHUB_WEBHOOK_SECRET;

const expected = 'sha256=' + crypto
  .createHmac('sha256', secret)
  .update(payload)
  .digest('hex');

if (signature !== expected) {
  throw new Error('Invalid GitHub signature');
}

// Extract event type
const event = $json.headers['x-github-event'];
return [{ json: { event, ...item.json.body } }];
```

### Stripe Webhooks
```javascript
// Stripe signature validation
const crypto = require('crypto');
const payload = $json.rawBody;
const signature = $json.headers['stripe-signature'];
const secret = $env.STRIPE_WEBHOOK_SECRET;

const parts = signature.split(',').reduce((acc, part) => {
  const [key, value] = part.split('=');
  acc[key] = value;
  return acc;
}, {});

const signedPayload = `${parts.t}.${payload}`;
const expected = crypto
  .createHmac('sha256', secret)
  .update(signedPayload)
  .digest('hex');

if (parts.v1 !== expected) {
  throw new Error('Invalid Stripe signature');
}

return items;
```

### Shopify Webhooks
```javascript
// Shopify HMAC validation
const crypto = require('crypto');
const hmac = $json.headers['x-shopify-hmac-sha256'];
const body = $json.rawBody;
const secret = $env.SHOPIFY_WEBHOOK_SECRET;

const calculated = crypto
  .createHmac('sha256', secret)
  .update(body, 'utf8')
  .digest('base64');

if (hmac !== calculated) {
  throw new Error('Invalid Shopify signature');
}

return items;
```

## Testing Webhooks

### Development Patterns
```yaml
strategies:
  test_url:
    description: "Use n8n test webhook URL during development"
    url_format: "https://n8n.example.com/webhook-test/{path}"
    note: "Works without activating workflow"

  ngrok_tunnel:
    description: "Expose local n8n via tunnel"
    command: "ngrok http 5678"
    use_case: "Testing with real external services"

  manual_testing:
    tool: "curl, Postman, or webhook.site"
    example: "curl -X POST -d '{\"test\": true}' https://..."
```

### Mock Data Pattern
```json
{
  "id": "webhook-test",
  "name": "Webhook",
  "type": "n8n-nodes-base.webhook",
  "parameters": {
    "path": "test-endpoint",
    "httpMethod": "POST"
  },
  "webhookId": "test-id"
}
```

## Best Practices

```yaml
design:
  - Always implement authentication
  - Validate all input data
  - Return meaningful error messages
  - Use appropriate HTTP status codes
  - Log incoming requests for debugging

security:
  - Use HTTPS exclusively
  - Implement signature validation for known sources
  - Set appropriate timeouts
  - Rate limit incoming requests
  - Never expose internal errors

reliability:
  - Handle duplicates idempotently
  - Return fast, process async when possible
  - Implement health check endpoint
  - Monitor webhook failures
  - Document expected request format
```
