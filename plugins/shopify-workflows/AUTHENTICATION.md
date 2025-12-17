# Shopify Admin API Authentication Guide

**CRITICAL**: This authentication guide is REQUIRED READING for all Shopify workflow operations. The Shopify Dev MCP validates GraphQL but does NOT execute mutations or handle authentication. You must implement OAuth authentication yourself.

---

## Table of Contents

1. [Overview](#overview)
2. [OAuth 2.0 Client Credentials Grant](#oauth-20-client-credentials-grant)
3. [Getting Client Credentials](#getting-client-credentials)
4. [Token Exchange Implementation](#token-exchange-implementation)
5. [Token Refresh Pattern](#token-refresh-pattern)
6. [Required Scopes by Operation](#required-scopes-by-operation)
7. [Error Handling](#error-handling)
8. [Complete Examples](#complete-examples)

---

## Overview

**Authentication Flow Summary**:
```
1. Get client_id + client_secret from Shopify Partner Dashboard
2. Exchange credentials for access_token via POST request
3. Use access_token in X-Shopify-Access-Token header
4. Refresh token every 24 hours (tokens expire after 86399 seconds)
```

**What Shopify Dev MCP Does**:
- ✅ Learn API structure via `learn_shopify_api()`
- ✅ Introspect GraphQL schema via `introspect_graphql_schema()`
- ✅ Validate GraphQL syntax via `validate_graphql_codeblocks()`
- ❌ Does NOT execute mutations
- ❌ Does NOT handle authentication
- ❌ Does NOT make API requests

**What You Must Implement**:
- ✅ OAuth token exchange
- ✅ HTTP requests to Shopify Admin API
- ✅ Token management and refresh
- ✅ Authentication headers

---

## OAuth 2.0 Client Credentials Grant

Shopify uses OAuth 2.0 client credentials grant ([RFC 6749, section 4.4](https://datatracker.ietf.org/doc/html/rfc6749#section-4.4)) for server-to-server API access.

**Authentication Method**: OAuth 2.0 Client Credentials Grant
**Token Endpoint**: `https://{shop}.myshopify.com/admin/oauth/access_token`
**HTTP Method**: `POST`
**Content-Type**: `application/x-www-form-urlencoded`
**Token Lifetime**: 86399 seconds (24 hours)

**Requirements**:
- App must be developed by your organization
- App must be installed in stores you own
- Public/custom apps must use different auth flows (token exchange or authorization code)

---

## Getting Client Credentials

### Step 1: Access Shopify Partner Dashboard

1. Go to [Shopify Partner Dashboard](https://partners.shopify.com/)
2. Select your app
3. Navigate to **Settings** page

### Step 2: Locate Credentials

You'll find two required values:

- **Client ID**: Public identifier (e.g., `190c6adc23a3e86233d4ad121993efc0`)
- **Client Secret**: Sensitive credential (e.g., `YOUR_CLIENT_SECRET_HERE`)

⚠️ **SECURITY WARNING**: Never expose client secret in:
- Frontend code
- Public repositories
- Client-side JavaScript
- Environment files committed to git

✅ **Safe Storage Options**:
- Environment variables (`.env` file, gitignored)
- Secret management services (AWS Secrets Manager, HashiCorp Vault)
- Server-side configuration only

### Step 3: Configure Access Scopes

Before authentication, configure required scopes in:
- **Partner Dashboard** → App Settings → API access
- **OR** `shopify.app.toml` configuration file

Example scopes configuration:
```toml
[access_scopes]
scopes = "write_products,write_orders,write_customers,write_content"
```

---

## Token Exchange Implementation

### Basic Token Exchange (Node.js)

```javascript
const https = require('https');

const CLIENT_ID = process.env.SHOPIFY_CLIENT_ID;
const CLIENT_SECRET = process.env.SHOPIFY_CLIENT_SECRET;
const SHOP = 'your-store.myshopify.com';

function getAccessToken() {
  return new Promise((resolve, reject) => {
    const data = new URLSearchParams({
      grant_type: 'client_credentials',
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET
    }).toString();

    const options = {
      hostname: SHOP,
      path: '/admin/oauth/access_token',
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Content-Length': Buffer.byteLength(data)
      }
    };

    const req = https.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        if (res.statusCode === 200) {
          const parsed = JSON.parse(body);
          resolve(parsed);
        } else {
          reject(new Error(`HTTP ${res.statusCode}: ${body}`));
        }
      });
    });

    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

// Usage
getAccessToken()
  .then(response => {
    console.log('Access Token:', response.access_token);
    console.log('Scopes:', response.scope);
    console.log('Expires in:', response.expires_in, 'seconds');
  })
  .catch(error => {
    console.error('Auth failed:', error.message);
  });
```

### Token Exchange (curl)

```bash
curl -X POST \
  "https://your-store.myshopify.com/admin/oauth/access_token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

### Response Format

```json
{
  "access_token": "YOUR_ACCESS_TOKEN_HERE",
  "scope": "write_products,write_orders,write_customers,write_content",
  "expires_in": 86399
}
```

**Response Fields**:
- `access_token`: Use in `X-Shopify-Access-Token` header for API requests
- `scope`: Comma-separated list of granted scopes
- `expires_in`: Seconds until expiration (always 86399 = 24 hours)

---

## Token Refresh Pattern

Tokens expire after 24 hours. Implement refresh logic:

### Strategy 1: Refresh Before Expiration

```javascript
class ShopifyAuth {
  constructor(clientId, clientSecret, shop) {
    this.clientId = clientId;
    this.clientSecret = clientSecret;
    this.shop = shop;
    this.token = null;
    this.tokenExpiry = null;
  }

  async getToken() {
    // Check if token is expired or expires in <1 hour
    const now = Date.now();
    const oneHour = 60 * 60 * 1000;

    if (!this.token || !this.tokenExpiry || now + oneHour > this.tokenExpiry) {
      await this.refreshToken();
    }

    return this.token;
  }

  async refreshToken() {
    const response = await this.exchangeCredentials();
    this.token = response.access_token;
    this.tokenExpiry = Date.now() + (response.expires_in * 1000);
    console.log(`Token refreshed, expires at: ${new Date(this.tokenExpiry)}`);
  }

  async exchangeCredentials() {
    // Implementation from previous section
    return getAccessToken();
  }
}

// Usage
const auth = new ShopifyAuth(CLIENT_ID, CLIENT_SECRET, SHOP);
const token = await auth.getToken(); // Auto-refreshes if needed
```

### Strategy 2: Refresh on 401 Error

```javascript
async function makeAuthenticatedRequest(url, options, retries = 1) {
  const token = await auth.getToken();

  options.headers = {
    ...options.headers,
    'X-Shopify-Access-Token': token
  };

  const response = await fetch(url, options);

  // Token expired, refresh and retry
  if (response.status === 401 && retries > 0) {
    console.log('Token expired, refreshing...');
    await auth.refreshToken();
    return makeAuthenticatedRequest(url, options, retries - 1);
  }

  return response;
}
```

---

## Required Scopes by Operation

### Content Creation (shopify-content-creator)
- `write_content` - Blog articles, pages
- `write_themes` - Theme assets (optional)

### Merchant Operations (shopify-merchant-ops)
- `write_products` - Product CRUD
- `write_inventory` - Inventory management
- `write_orders` - Order operations
- `write_customers` - Customer management
- `write_fulfillments` - Fulfillment operations

### Marketing Operations (shopify-marketing-ops)
- `write_discounts` - Discount codes
- `write_price_rules` - Price rules
- `write_marketing_events` - Marketing campaigns
- `read_analytics` - Campaign analytics

### Developer Operations (shopify-developer)
- `write_metafields` - Metafield operations
- `write_webhooks` - Webhook subscriptions
- `write_script_tags` - Script tag injection

### Analytics (shopify-analytics)
- `read_analytics` - Analytics queries
- `read_reports` - Report generation
- `read_orders` - Order analytics
- `read_customers` - Customer analytics

**Request All Scopes**: For multi-purpose tools, request all scopes:
```toml
scopes = "read_all_orders,write_products,write_inventory,write_orders,write_customers,write_content,write_discounts,write_marketing_events,read_analytics,write_metafields,write_webhooks"
```

---

## Error Handling

### Common Authentication Errors

**401 Unauthorized - Invalid Credentials**:
```json
{
  "error": "invalid_client",
  "error_description": "Client authentication failed"
}
```
**Causes**:
- Wrong client_id or client_secret
- Credentials from wrong app
- Credentials expired or revoked

**Solution**: Verify credentials in Partner Dashboard

---

**401 Unauthorized - Invalid Token**:
```json
{
  "errors": "Invalid API key or access token (unrecognized login or wrong password)"
}
```
**Causes**:
- Token expired (>24 hours old)
- Token revoked
- Wrong token for this store

**Solution**: Refresh token using credentials exchange

---

**403 Forbidden - Insufficient Scopes**:
```json
{
  "errors": [
    {
      "message": "Access denied for write_content scope"
    }
  ]
}
```
**Causes**:
- Scope not granted during app installation
- Scope not configured in app settings

**Solution**: Update app scopes in Partner Dashboard, reinstall app

---

**429 Too Many Requests - Rate Limit**:
```
HTTP/1.1 429 Too Many Requests
X-Shopify-Shop-Api-Call-Limit: 40/40
Retry-After: 2
```
**Causes**:
- Exceeded rate limit (40 requests per second)
- Bucket depleted

**Solution**: Implement exponential backoff, respect Retry-After header

---

### Robust Error Handling Pattern

```javascript
async function robustTokenExchange(maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = await getAccessToken();
      return response;
    } catch (error) {
      console.error(`Token exchange attempt ${attempt} failed:`, error.message);

      // Don't retry on client errors (invalid credentials)
      if (error.message.includes('invalid_client')) {
        throw new Error('Invalid client credentials - check your client_id and client_secret');
      }

      // Retry on network errors or server errors
      if (attempt < maxRetries) {
        const backoff = Math.pow(2, attempt) * 1000; // Exponential backoff
        console.log(`Retrying in ${backoff}ms...`);
        await new Promise(resolve => setTimeout(resolve, backoff));
      } else {
        throw new Error(`Token exchange failed after ${maxRetries} attempts`);
      }
    }
  }
}
```

---

## Complete Examples

### Example 1: Complete GraphQL Request with Authentication

```javascript
const https = require('https');

// Step 1: Get access token
const authResponse = await getAccessToken();
const ACCESS_TOKEN = authResponse.access_token;

// Step 2: Validate GraphQL with Shopify Dev MCP
const validationResult = await validate_graphql_codeblocks({
  conversationId: "your-conversation-id",
  api: "admin",
  codeblocks: [`
    mutation createArticle($article: ArticleCreateInput!, $blogId: ID!) {
      articleCreate(article: $article, blogId: $blogId) {
        article { id title }
        userErrors { field message }
      }
    }
  `]
});

if (!validationResult.valid) {
  throw new Error('Invalid GraphQL mutation');
}

// Step 3: Execute authenticated GraphQL request
function graphqlRequest(query, variables) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({ query, variables });

    const options = {
      hostname: 'your-store.myshopify.com',
      path: '/admin/api/2024-10/graphql.json',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Shopify-Access-Token': ACCESS_TOKEN,
        'Content-Length': Buffer.byteLength(data)
      }
    };

    const req = https.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        const parsed = JSON.parse(body);

        if (res.statusCode === 200) {
          resolve(parsed);
        } else {
          reject(new Error(`HTTP ${res.statusCode}: ${body}`));
        }
      });
    });

    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

// Step 4: Execute mutation
const mutation = `
  mutation createArticle($article: ArticleCreateInput!, $blogId: ID!) {
    articleCreate(article: $article, blogId: $blogId) {
      article {
        id
        title
        handle
      }
      userErrors {
        field
        message
      }
    }
  }
`;

const variables = {
  blogId: "gid://shopify/Blog/123456789",
  article: {
    title: "My Blog Post",
    bodyHtml: "<p>Content here</p>",
    author: "John Doe"
  }
};

const response = await graphqlRequest(mutation, variables);

// Step 5: Handle response
if (response.data?.articleCreate?.userErrors?.length > 0) {
  console.error('Mutation failed:', response.data.articleCreate.userErrors);
} else {
  console.log('Article created:', response.data.articleCreate.article);
}
```

### Example 2: Complete Workflow with Token Management

```javascript
class ShopifyClient {
  constructor(clientId, clientSecret, shop) {
    this.clientId = clientId;
    this.clientSecret = clientSecret;
    this.shop = shop;
    this.token = null;
    this.tokenExpiry = null;
  }

  async ensureValidToken() {
    const now = Date.now();
    const oneHour = 60 * 60 * 1000;

    if (!this.token || now + oneHour > this.tokenExpiry) {
      await this.refreshToken();
    }
  }

  async refreshToken() {
    const response = await getAccessToken();
    this.token = response.access_token;
    this.tokenExpiry = Date.now() + (response.expires_in * 1000);
  }

  async graphql(query, variables = {}) {
    await this.ensureValidToken();

    const data = JSON.stringify({ query, variables });

    const options = {
      hostname: this.shop,
      path: '/admin/api/2024-10/graphql.json',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Shopify-Access-Token': this.token,
        'Content-Length': Buffer.byteLength(data)
      }
    };

    return new Promise((resolve, reject) => {
      const req = https.request(options, (res) => {
        let body = '';
        res.on('data', (chunk) => body += chunk);
        res.on('end', () => {
          const parsed = JSON.parse(body);

          // Handle 401 by refreshing token
          if (res.statusCode === 401) {
            this.token = null;
            this.tokenExpiry = null;
            reject(new Error('Token expired, retry with refresh'));
          } else if (res.statusCode === 200) {
            resolve(parsed);
          } else {
            reject(new Error(`HTTP ${res.statusCode}: ${body}`));
          }
        });
      });

      req.on('error', reject);
      req.write(data);
      req.end();
    });
  }
}

// Usage
const client = new ShopifyClient(CLIENT_ID, CLIENT_SECRET, 'your-store.myshopify.com');

// Client automatically manages token refresh
const response = await client.graphql(mutation, variables);
```

---

## Checklist for Every Operation

Before executing any Shopify operation, verify:

- [ ] Client credentials obtained from Partner Dashboard
- [ ] Required scopes configured and granted
- [ ] Token exchange implemented and tested
- [ ] Access token obtained successfully
- [ ] GraphQL mutation validated with Shopify Dev MCP
- [ ] Authentication header included in request
- [ ] Token refresh logic implemented
- [ ] Error handling for 401, 403, 429 responses
- [ ] userErrors checked after mutation
- [ ] Retry logic for transient failures

---

**Documentation References**:
- [Shopify OAuth Client Credentials Grant](https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/client-credentials-grant)
- [Shopify Admin API](https://shopify.dev/docs/api/admin-graphql)
- [Access Scopes](https://shopify.dev/docs/api/usage/access-scopes)
- [Rate Limits](https://shopify.dev/docs/api/usage/rate-limits)
