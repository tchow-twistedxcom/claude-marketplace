---
name: shopify-developer
description: "Technical integrations with webhooks, metafields, and custom apps. Use when building Shopify integrations, setting up webhooks, or developing custom functionality."
license: MIT
---

# Shopify Developer Integration Skill

**Purpose**: Technical integration toolkit for webhooks, metafields, app development, and custom API integrations with Shopify.

**Target Users**: Developers, technical integrators, app builders implementing custom Shopify functionality.

**When to Use**:
- Setting up webhooks for event-driven integrations
- Defining and managing metafields for custom data storage
- Building Shopify apps or custom integrations
- Implementing script tags for storefront customization
- Advanced GraphQL API operations requiring technical expertise

---

## Core Integration Patterns

### Shopify Dev MCP Workflow

**MANDATORY FIRST STEP**: Always call `learn_shopify_api` before other Shopify tools.

```javascript
// 1. Initialize conversation with Admin API
learn_shopify_api(api: "admin") → conversationId: "abc123"

// 2. Extract conversationId and use for all subsequent calls
introspect_graphql_schema(conversationId: "abc123", query: "webhook")
search_docs_chunks(conversationId: "abc123", prompt: "metafield best practices")
validate_graphql_codeblocks(conversationId: "abc123", codeblocks: [...])
```

### Authentication & API Access

⚠️ **CRITICAL**: See [../../AUTHENTICATION.md](../../AUTHENTICATION.md) for complete authentication guide.

**Required Scopes**:
- `write_metafields` - Metafield operations
- `write_webhooks` - Webhook subscriptions
- `write_script_tags` - Script tag injection

**Key Points**:
- Shopify Dev MCP validates GraphQL but does NOT execute mutations or handle authentication
- You MUST implement OAuth 2.0 client credentials grant flow yourself
- Tokens expire after 24 hours (86399 seconds) and must be refreshed
- Use access token in `X-Shopify-Access-Token` header for all API requests

**GraphQL Admin API Endpoint**: `https://{shop}.myshopify.com/admin/api/2024-10/graphql.json`

**Rate Limits**:
- Standard: 50 points/second
- Plus: 100 points/second
- Each query costs 1-1000+ points (check `extensions.cost`)
- Throttled queries return 429 with `Retry-After` header

### GraphQL Query Pattern

```javascript
// Always validate with validate_graphql_codeblocks
const query = `
  mutation MyMutation($input: MyMutationInput!) {
    myMutation(input: $input) {
      myObject {
        id
        field
      }
      userErrors {
        field
        message
      }
    }
  }
`;

const variables = {
  input: {
    field: "value"
  }
};

// Validate before execution
validate_graphql_codeblocks(
  conversationId: "abc123",
  codeblocks: [query],
  api: "admin"
);
```

---

## Webhook Operations

### Creating Webhooks

**Common Topics**:
- `ORDERS_CREATE`, `ORDERS_UPDATED`, `ORDERS_PAID`
- `PRODUCTS_CREATE`, `PRODUCTS_UPDATE`, `PRODUCTS_DELETE`
- `CUSTOMERS_CREATE`, `CUSTOMERS_UPDATE`, `CUSTOMERS_DELETE`
- `INVENTORY_LEVELS_UPDATE`
- `APP_UNINSTALLED`, `SHOP_UPDATE`

**Webhook Formats**: `JSON` (recommended), `XML`

**Create Webhook Mutation**:
```graphql
mutation CreateWebhook($topic: WebhookSubscriptionTopic!, $webhookSubscription: WebhookSubscriptionInput!) {
  webhookSubscriptionCreate(
    topic: $topic
    webhookSubscription: $webhookSubscription
  ) {
    webhookSubscription {
      id
      topic
      format
      endpoint {
        __typename
        ... on WebhookHttpEndpoint {
          callbackUrl
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

**Variables**:
```json
{
  "topic": "ORDERS_CREATE",
  "webhookSubscription": {
    "format": "JSON",
    "callbackUrl": "https://your-domain.com/webhooks/orders/create"
  }
}
```

### Managing Webhooks

**List All Webhooks**:
```graphql
query GetWebhooks {
  webhookSubscriptions(first: 50) {
    edges {
      node {
        id
        topic
        format
        endpoint {
          __typename
          ... on WebhookHttpEndpoint {
            callbackUrl
          }
        }
      }
    }
  }
}
```

**Update Webhook**:
```graphql
mutation UpdateWebhook($id: ID!, $webhookSubscription: WebhookSubscriptionInput!) {
  webhookSubscriptionUpdate(
    id: $id
    webhookSubscription: $webhookSubscription
  ) {
    webhookSubscription {
      id
      endpoint {
        ... on WebhookHttpEndpoint {
          callbackUrl
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

**Delete Webhook**:
```graphql
mutation DeleteWebhook($id: ID!) {
  webhookSubscriptionDelete(id: $id) {
    deletedWebhookSubscriptionId
    userErrors {
      field
      message
    }
  }
}
```

### Webhook Verification

**Verify HMAC Signature** (Node.js):
```javascript
const crypto = require('crypto');

function verifyWebhook(body, hmacHeader, secret) {
  const hash = crypto
    .createHmac('sha256', secret)
    .update(body, 'utf8')
    .digest('base64');

  return hash === hmacHeader;
}

// Express middleware
app.post('/webhooks/orders/create', express.raw({type: 'application/json'}), (req, res) => {
  const hmac = req.headers['x-shopify-hmac-sha256'];
  const verified = verifyWebhook(req.body, hmac, process.env.SHOPIFY_WEBHOOK_SECRET);

  if (!verified) {
    return res.status(401).send('Unauthorized');
  }

  const payload = JSON.parse(req.body);
  // Process webhook...
  res.status(200).send('OK');
});
```

---

## Metafield Operations

### Metafield Namespace & Key Patterns

**Best Practices**:
- Namespace: `custom`, `app--{app-name}`, or your brand name
- Key: Descriptive, lowercase, underscores (e.g., `installation_date`)
- Type: Choose appropriate type for data validation

**Common Types**:
- `single_line_text_field`, `multi_line_text_field`
- `number_integer`, `number_decimal`
- `date`, `date_time`
- `json`, `boolean`
- `url`, `color`
- `list.single_line_text_field`, `list.number_integer`

### Define Metafield

```graphql
mutation CreateMetafieldDefinition($definition: MetafieldDefinitionInput!) {
  metafieldDefinitionCreate(definition: $definition) {
    createdDefinition {
      id
      name
      namespace
      key
      type {
        name
      }
      ownerType
    }
    userErrors {
      field
      message
    }
  }
}
```

**Variables**:
```json
{
  "definition": {
    "name": "Installation Date",
    "namespace": "custom",
    "key": "installation_date",
    "description": "Date when product was installed",
    "type": "date",
    "ownerType": "PRODUCT"
  }
}
```

**Owner Types**: `PRODUCT`, `VARIANT`, `CUSTOMER`, `ORDER`, `SHOP`, `COLLECTION`

### Set Metafield Values

**Set Product Metafield**:
```graphql
mutation SetProductMetafield($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields {
      id
      namespace
      key
      value
      type
    }
    userErrors {
      field
      message
    }
  }
}
```

**Variables**:
```json
{
  "metafields": [
    {
      "ownerId": "gid://shopify/Product/1234567890",
      "namespace": "custom",
      "key": "installation_date",
      "type": "date",
      "value": "2024-01-15"
    }
  ]
}
```

**Batch Set Multiple Metafields**:
```json
{
  "metafields": [
    {
      "ownerId": "gid://shopify/Product/1234567890",
      "namespace": "custom",
      "key": "warranty_years",
      "type": "number_integer",
      "value": "5"
    },
    {
      "ownerId": "gid://shopify/Product/1234567890",
      "namespace": "custom",
      "key": "manufacturer",
      "type": "single_line_text_field",
      "value": "ACME Corp"
    }
  ]
}
```

### Query Metafields

**Get Product with Metafields**:
```graphql
query GetProductMetafields($id: ID!) {
  product(id: $id) {
    id
    title
    metafields(first: 20, namespace: "custom") {
      edges {
        node {
          id
          namespace
          key
          value
          type
        }
      }
    }
  }
}
```

**Get Specific Metafield**:
```graphql
query GetSpecificMetafield($id: ID!, $namespace: String!, $key: String!) {
  product(id: $id) {
    metafield(namespace: $namespace, key: $key) {
      id
      value
      type
    }
  }
}
```

### Delete Metafield

```graphql
mutation DeleteMetafield($input: MetafieldDeleteInput!) {
  metafieldDelete(input: $input) {
    deletedId
    userErrors {
      field
      message
    }
  }
}
```

**Variables**:
```json
{
  "input": {
    "id": "gid://shopify/Metafield/1234567890"
  }
}
```

---

## App Integration Patterns

### App Installation Flow

**1. OAuth Setup**:
```javascript
// Redirect to OAuth authorization
const authUrl = `https://${shop}/admin/oauth/authorize?client_id=${apiKey}&scope=${scopes}&redirect_uri=${redirectUri}`;

// Required scopes for developer operations
const scopes = [
  'read_products', 'write_products',
  'read_orders', 'write_orders',
  'read_customers', 'write_customers',
  'write_script_tags',
  'write_webhooks'
].join(',');
```

**2. Exchange Code for Access Token**:
```javascript
const response = await fetch(`https://${shop}/admin/oauth/access_token`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    client_id: apiKey,
    client_secret: apiSecret,
    code: authCode
  })
});

const { access_token } = await response.json();
// Store access_token securely
```

**3. Register Mandatory Webhooks**:
```graphql
# GDPR webhooks required for published apps
mutation RegisterGDPRWebhooks {
  customersDataRequest: webhookSubscriptionCreate(
    topic: CUSTOMERS_DATA_REQUEST
    webhookSubscription: { callbackUrl: "https://your-app.com/webhooks/gdpr/customers-data" }
  ) { userErrors { message } }

  customersRedact: webhookSubscriptionCreate(
    topic: CUSTOMERS_REDACT
    webhookSubscription: { callbackUrl: "https://your-app.com/webhooks/gdpr/customers-redact" }
  ) { userErrors { message } }

  shopRedact: webhookSubscriptionCreate(
    topic: SHOP_REDACT
    webhookSubscription: { callbackUrl: "https://your-app.com/webhooks/gdpr/shop-redact" }
  ) { userErrors { message } }
}
```

### Script Tag Management

**Create Script Tag** (REST API):
```javascript
// Note: Script tags use REST API, not GraphQL
const response = await fetch(
  `https://${shop}/admin/api/2024-10/script_tags.json`,
  {
    method: 'POST',
    headers: {
      'X-Shopify-Access-Token': accessToken,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      script_tag: {
        event: 'onload',
        src: 'https://your-cdn.com/app-widget.js',
        display_scope: 'all'
      }
    })
  }
);

const { script_tag } = await response.json();
```

**Events**: `onload` (recommended), `page_view`, `collection_view`, `product_view`

### App Proxy Configuration

**Setup** (in Partner Dashboard):
- Subpath prefix: `/apps/your-app`
- Subpath: `/api`
- Proxy URL: `https://your-backend.com`

**Handle Proxy Requests**:
```javascript
app.get('/proxy/*', (req, res) => {
  // Verify proxy request signature
  const params = req.query;
  const signature = params.signature;
  delete params.signature;

  const queryString = Object.keys(params)
    .sort()
    .map(key => `${key}=${params[key]}`)
    .join('&');

  const hash = crypto
    .createHmac('sha256', process.env.SHOPIFY_API_SECRET)
    .update(queryString)
    .digest('hex');

  if (hash !== signature) {
    return res.status(401).send('Unauthorized');
  }

  // Return Liquid-compatible response
  res.setHeader('Content-Type', 'application/liquid');
  res.send(`
    <div class="app-widget">
      <h3>{{ shop.name }}</h3>
      <p>Custom app content here</p>
    </div>
  `);
});
```

---

## Error Handling

### UserErrors Pattern

**Always Check userErrors**:
```javascript
const response = await executeGraphQL(mutation, variables);

if (response.data.metafieldsSet.userErrors.length > 0) {
  const errors = response.data.metafieldsSet.userErrors;
  console.error('Metafield operation failed:', errors);

  errors.forEach(error => {
    console.error(`Field: ${error.field}, Message: ${error.message}`);
  });

  // Handle specific errors
  const invalidTypeError = errors.find(e => e.message.includes('type'));
  if (invalidTypeError) {
    // Retry with correct type
  }

  throw new Error(`Metafield operation failed: ${errors[0].message}`);
}

const metafields = response.data.metafieldsSet.metafields;
// Continue processing...
```

### Common Error Scenarios

**Invalid Metafield Type**:
```javascript
// Wrong: value doesn't match type
{ type: "number_integer", value: "not a number" }

// Right: value matches type
{ type: "number_integer", value: "42" }
```

**Missing Required Scopes**:
```javascript
// Error: "Access denied for write_webhooks scope"
// Solution: Re-request OAuth with additional scopes
```

**Rate Limit Handling**:
```javascript
async function executeWithRetry(query, variables, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { /* ... */ },
      body: JSON.stringify({ query, variables })
    });

    if (response.status === 429) {
      const retryAfter = response.headers.get('Retry-After') || 2;
      await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
      continue;
    }

    return response.json();
  }

  throw new Error('Rate limit exceeded after retries');
}
```

---

## Complete Workflow Examples

### Example 1: Set Up Order Processing Integration

**Objective**: Create webhook for new orders, store custom fulfillment data in metafields.

```javascript
// Step 1: Initialize Shopify Dev MCP
const { conversationId } = await learn_shopify_api({ api: "admin" });

// Step 2: Create webhook for order creation
const webhookMutation = `
  mutation CreateOrderWebhook($topic: WebhookSubscriptionTopic!, $webhookSubscription: WebhookSubscriptionInput!) {
    webhookSubscriptionCreate(topic: $topic, webhookSubscription: $webhookSubscription) {
      webhookSubscription {
        id
        topic
        endpoint {
          ... on WebhookHttpEndpoint {
            callbackUrl
          }
        }
      }
      userErrors { field message }
    }
  }
`;

const webhookVars = {
  topic: "ORDERS_CREATE",
  webhookSubscription: {
    format: "JSON",
    callbackUrl: "https://your-app.com/webhooks/orders/create"
  }
};

await validate_graphql_codeblocks({
  conversationId,
  codeblocks: [webhookMutation],
  api: "admin"
});

// Step 3: Define metafield for custom fulfillment status
const metafieldDefMutation = `
  mutation CreateFulfillmentMetafield($definition: MetafieldDefinitionInput!) {
    metafieldDefinitionCreate(definition: $definition) {
      createdDefinition {
        id
        namespace
        key
      }
      userErrors { field message }
    }
  }
`;

const metafieldDefVars = {
  definition: {
    name: "External Fulfillment ID",
    namespace: "custom",
    key: "external_fulfillment_id",
    description: "Fulfillment tracking ID from external system",
    type: "single_line_text_field",
    ownerType: "ORDER"
  }
};

// Step 4: Webhook handler sets metafield
app.post('/webhooks/orders/create', async (req, res) => {
  const order = req.body;

  // Process order in external system
  const fulfillmentId = await createExternalFulfillment(order);

  // Set metafield on order
  const setMetafieldMutation = `
    mutation SetOrderMetafield($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields { id value }
        userErrors { field message }
      }
    }
  `;

  const setMetafieldVars = {
    metafields: [{
      ownerId: `gid://shopify/Order/${order.id}`,
      namespace: "custom",
      key: "external_fulfillment_id",
      type: "single_line_text_field",
      value: fulfillmentId
    }]
  };

  await executeGraphQL(setMetafieldMutation, setMetafieldVars);
  res.status(200).send('OK');
});
```

### Example 2: Product Sync with External Inventory System

**Objective**: Sync product inventory levels via webhook, store external SKU in metafields.

```javascript
// Step 1: Define metafield for external SKU
const metafieldDef = `
  mutation DefineExternalSKU($definition: MetafieldDefinitionInput!) {
    metafieldDefinitionCreate(definition: $definition) {
      createdDefinition { id }
      userErrors { message }
    }
  }
`;

const skuDefVars = {
  definition: {
    name: "External SKU",
    namespace: "app--inventory-sync",
    key: "external_sku",
    type: "single_line_text_field",
    ownerType: "PRODUCT"
  }
};

// Step 2: Set external SKU on products
const setExternalSKU = async (productId, externalSku) => {
  const mutation = `
    mutation SetExternalSKU($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields { id }
        userErrors { field message }
      }
    }
  `;

  const vars = {
    metafields: [{
      ownerId: `gid://shopify/Product/${productId}`,
      namespace: "app--inventory-sync",
      key: "external_sku",
      type: "single_line_text_field",
      value: externalSku
    }]
  };

  return executeGraphQL(mutation, vars);
};

// Step 3: Create inventory update webhook
const inventoryWebhook = `
  mutation CreateInventoryWebhook {
    webhookSubscriptionCreate(
      topic: INVENTORY_LEVELS_UPDATE
      webhookSubscription: {
        format: JSON
        callbackUrl: "https://your-app.com/webhooks/inventory"
      }
    ) {
      webhookSubscription { id }
      userErrors { message }
    }
  }
`;

// Step 4: Handle inventory updates
app.post('/webhooks/inventory', async (req, res) => {
  const inventoryLevel = req.body;

  // Get product with external SKU metafield
  const query = `
    query GetProductBySKU($id: ID!) {
      inventoryLevel(id: $id) {
        item {
          variant {
            product {
              id
              metafield(namespace: "app--inventory-sync", key: "external_sku") {
                value
              }
            }
          }
        }
        available
      }
    }
  `;

  const result = await executeGraphQL(query, { id: inventoryLevel.inventory_item_id });
  const externalSku = result.data.inventoryLevel.item.variant.product.metafield?.value;

  if (externalSku) {
    // Sync to external system
    await updateExternalInventory(externalSku, inventoryLevel.available);
  }

  res.status(200).send('OK');
});
```

### Example 3: Custom App Installation with Setup Wizard

**Objective**: Complete app installation flow with metafield setup and initial configuration.

```javascript
// OAuth callback handler
app.get('/auth/callback', async (req, res) => {
  const { shop, code } = req.query;

  // Exchange code for access token
  const tokenResponse = await fetch(
    `https://${shop}/admin/oauth/access_token`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_id: process.env.SHOPIFY_API_KEY,
        client_secret: process.env.SHOPIFY_API_SECRET,
        code
      })
    }
  );

  const { access_token } = await tokenResponse.json();

  // Store access token for shop
  await db.shops.upsert({ shop, accessToken: access_token });

  // Run setup wizard
  await setupApp(shop, access_token);

  res.redirect(`https://${shop}/admin/apps/${process.env.APP_HANDLE}`);
});

async function setupApp(shop, accessToken) {
  const graphqlClient = createGraphQLClient(shop, accessToken);

  // 1. Register GDPR webhooks
  await graphqlClient.request(`
    mutation RegisterGDPR {
      w1: webhookSubscriptionCreate(
        topic: CUSTOMERS_DATA_REQUEST
        webhookSubscription: { callbackUrl: "${process.env.APP_URL}/webhooks/gdpr/customers-data" }
      ) { userErrors { message } }

      w2: webhookSubscriptionCreate(
        topic: CUSTOMERS_REDACT
        webhookSubscription: { callbackUrl: "${process.env.APP_URL}/webhooks/gdpr/customers-redact" }
      ) { userErrors { message } }

      w3: webhookSubscriptionCreate(
        topic: SHOP_REDACT
        webhookSubscription: { callbackUrl: "${process.env.APP_URL}/webhooks/gdpr/shop-redact" }
      ) { userErrors { message } }

      w4: webhookSubscriptionCreate(
        topic: APP_UNINSTALLED
        webhookSubscription: { callbackUrl: "${process.env.APP_URL}/webhooks/uninstall" }
      ) { userErrors { message } }
    }
  `);

  // 2. Define app metafields
  const metafieldDefinitions = [
    {
      name: "App Configuration",
      namespace: "app--my-app",
      key: "config",
      type: "json",
      ownerType: "SHOP"
    },
    {
      name: "Sync Status",
      namespace: "app--my-app",
      key: "last_sync",
      type: "date_time",
      ownerType: "PRODUCT"
    }
  ];

  for (const def of metafieldDefinitions) {
    await graphqlClient.request(`
      mutation CreateMetafieldDef($definition: MetafieldDefinitionInput!) {
        metafieldDefinitionCreate(definition: $definition) {
          createdDefinition { id }
          userErrors { message }
        }
      }
    `, { definition: def });
  }

  // 3. Set initial shop configuration
  await graphqlClient.request(`
    mutation SetShopConfig($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields { id }
        userErrors { message }
      }
    }
  `, {
    metafields: [{
      ownerId: `gid://shopify/Shop/${await getShopGid(graphqlClient)}`,
      namespace: "app--my-app",
      key: "config",
      type: "json",
      value: JSON.stringify({
        enabled: true,
        syncInterval: 3600,
        features: { autoSync: true }
      })
    }]
  });
}
```

---

## Best Practices

**Security**:
- Always verify webhook HMAC signatures
- Store access tokens encrypted at rest
- Use environment variables for secrets
- Implement proper OAuth flow validation

**Performance**:
- Batch metafield operations (up to 25 per request)
- Use GraphQL cost analysis to optimize queries
- Implement exponential backoff for rate limits
- Cache frequently accessed metafield definitions

**Reliability**:
- Validate all GraphQL operations with `validate_graphql_codeblocks`
- Check `userErrors` in every mutation response
- Implement webhook retry logic (Shopify retries 19 times over 48 hours)
- Log all API errors with correlation IDs

**Maintenance**:
- Monitor webhook delivery success rates
- Clean up unused metafield definitions
- Version your API requests (`2024-10`)
- Track API deprecations and migrations
