---
name: shopify-merchant-daily
description: "Daily merchant operations for products, inventory, orders, and customers. Includes comprehensive e-commerce optimization: SEO, conversion rate optimization, product listing quality audits, collection strategy, image optimization, and pricing strategies. Use when managing store operations, optimizing product listings, improving conversion rates, or analyzing product quality."
license: MIT
---

# Shopify Merchant Daily Operations

Production-ready skill for daily Shopify merchant operations including product management, inventory tracking, order fulfillment, and customer management.

## When to Use This Skill

**Use this skill for:**
- Creating and updating products with variants
- Managing inventory levels across locations
- Processing orders and fulfillments
- Basic customer management (create, update)
- Daily store operations and maintenance
- **E-Commerce optimization and conversion improvement**
- **Product listing SEO and quality audits**
- **Collection organization and strategy**
- **Pricing optimization and strategy**
- **Image and media optimization**
- **Conversion rate optimization (CRO)**

**Do NOT use for:**
- Blog content, pages (use content-creator skill)
- Discounts, marketing campaigns (use marketing-ops skill)
- Webhooks, metafields, custom data (use developer skill)
- Analytics, reports (use analytics skill)

**Target Users:** Store managers, daily operators, merchants managing day-to-day operations, e-commerce managers focused on conversion optimization

## Core Integration

### Initial Setup

**ALWAYS start with learn_shopify_api:**

```javascript
// Step 1: Initialize Shopify Admin API context
learn_shopify_api({
  api: "admin",
  conversationId: undefined // First call generates this
})
// Response includes conversationId - use for all subsequent calls
```

### GraphQL Workflow Pattern

```javascript
// Step 2: Introspect schema for operations
introspect_graphql_schema({
  conversationId: "your-conversation-id",
  api: "admin",
  query: "productCreate", // or "inventoryAdjust", "orderUpdate", etc.
  filter: ["mutations"]
})

// Step 3: Write mutation with variables
const mutation = `
mutation ProductCreate($input: ProductInput!) {
  productCreate(input: $input) {
    product {
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

// Step 4: Validate before execution
validate_graphql_codeblocks({
  conversationId: "your-conversation-id",
  api: "admin",
  codeblocks: [mutation]
})
```

### Authentication

⚠️ **CRITICAL**: See [../../AUTHENTICATION.md](../../AUTHENTICATION.md) for complete authentication guide.

**Required Scopes**:
- `write_products` - Product CRUD, variants, collections
- `write_inventory` - Inventory adjustments and tracking
- `write_orders` - Order fulfillment and updates
- `write_customers` - Customer management

**Key Points**:
- Shopify Dev MCP validates GraphQL but does NOT execute mutations or handle authentication
- You MUST implement OAuth 2.0 client credentials grant flow yourself
- Tokens expire after 24 hours (86399 seconds) and must be refreshed
- Use access token in `X-Shopify-Access-Token` header for all API requests

### Rate Limiting

Admin API uses bucket-based rate limiting:
- **Standard:** 2 requests/second, 40 points/app/second
- **GraphQL cost:** Query cost calculated based on fields requested
- Check `extensions.cost` in response for cost details
- Implement exponential backoff on 429 responses

## Product Management

### Create Product with Variants

**Operation:** `productCreate`
**Scope Required:** `write_products`

```graphql
mutation CreateProductWithVariants($input: ProductInput!) {
  productCreate(input: $input) {
    product {
      id
      title
      handle
      status
      variants(first: 10) {
        edges {
          node {
            id
            title
            price
            sku
            inventoryQuantity
          }
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

**Variables:**

```json
{
  "input": {
    "title": "Premium Cotton T-Shirt",
    "descriptionHtml": "<p>High-quality cotton t-shirt</p>",
    "vendor": "Acme Apparel",
    "productType": "T-Shirts",
    "status": "ACTIVE",
    "tags": ["cotton", "basic", "summer"],
    "variants": [
      {
        "title": "Small / Blue",
        "price": "29.99",
        "sku": "TSHIRT-S-BLUE",
        "inventoryPolicy": "DENY",
        "inventoryManagement": "SHOPIFY",
        "options": ["Small", "Blue"]
      },
      {
        "title": "Medium / Blue",
        "price": "29.99",
        "sku": "TSHIRT-M-BLUE",
        "inventoryPolicy": "DENY",
        "inventoryManagement": "SHOPIFY",
        "options": ["Medium", "Blue"]
      }
    ],
    "options": [
      {
        "name": "Size",
        "values": [{"name": "Small"}, {"name": "Medium"}, {"name": "Large"}]
      },
      {
        "name": "Color",
        "values": [{"name": "Blue"}, {"name": "Black"}, {"name": "White"}]
      }
    ]
  }
}
```

### Update Product

**Operation:** `productUpdate`
**Scope Required:** `write_products`

```graphql
mutation UpdateProduct($input: ProductInput!) {
  productUpdate(input: $input) {
    product {
      id
      title
      status
      tags
    }
    userErrors {
      field
      message
    }
  }
}
```

**Variables:**

```json
{
  "input": {
    "id": "gid://shopify/Product/8234567890",
    "title": "Premium Cotton T-Shirt - Updated",
    "status": "ACTIVE",
    "tags": ["cotton", "basic", "summer", "bestseller"]
  }
}
```

### Add Product Variant

**Operation:** `productVariantCreate`
**Scope Required:** `write_products`

```graphql
mutation CreateVariant($input: ProductVariantInput!) {
  productVariantCreate(input: $input) {
    productVariant {
      id
      title
      price
      sku
      inventoryQuantity
    }
    userErrors {
      field
      message
    }
  }
}
```

**Variables:**

```json
{
  "input": {
    "productId": "gid://shopify/Product/8234567890",
    "price": "29.99",
    "sku": "TSHIRT-L-BLUE",
    "inventoryPolicy": "DENY",
    "inventoryManagement": "SHOPIFY",
    "options": ["Large", "Blue"]
  }
}
```

### Organize Products in Collections

```graphql
mutation AddProductToCollection($productId: ID!, $collectionId: ID!) {
  collectionAddProducts(
    id: $collectionId
    productIds: [$productId]
  ) {
    collection {
      id
      title
      productsCount
    }
    userErrors {
      field
      message
    }
  }
}
```

## Inventory Operations

### Adjust Inventory Quantities

**Operation:** `inventoryAdjustQuantities`
**Scope Required:** `write_inventory`

```graphql
mutation AdjustInventory($input: InventoryAdjustQuantitiesInput!) {
  inventoryAdjustQuantities(input: $input) {
    inventoryAdjustmentGroup {
      id
      reason
      changes {
        name
        delta
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

**Variables:**

```json
{
  "input": {
    "reason": "received",
    "name": "Warehouse restock - Dec 2025",
    "changes": [
      {
        "inventoryItemId": "gid://shopify/InventoryItem/45678901234",
        "locationId": "gid://shopify/Location/67890123",
        "delta": 50
      },
      {
        "inventoryItemId": "gid://shopify/InventoryItem/45678901235",
        "locationId": "gid://shopify/Location/67890123",
        "delta": 30
      }
    ]
  }
}
```

**Common Reasons:**
- `received` - Stock received from supplier
- `correction` - Inventory count correction
- `cycle_count` - Regular inventory audit
- `damaged` - Items damaged (use negative delta)
- `promotion` - Promotional allocation

### Activate Inventory at Location

**Operation:** `inventoryActivate`
**Scope Required:** `write_inventory`

```graphql
mutation ActivateInventory($inventoryItemId: ID!, $locationId: ID!) {
  inventoryActivate(
    inventoryItemId: $inventoryItemId
    locationId: $locationId
  ) {
    inventoryLevel {
      id
      available
      location {
        id
        name
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

### Query Current Inventory Levels

```graphql
query GetInventoryLevels($productId: ID!) {
  product(id: $productId) {
    title
    variants(first: 10) {
      edges {
        node {
          id
          title
          sku
          inventoryItem {
            id
            inventoryLevels(first: 5) {
              edges {
                node {
                  available
                  location {
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

## Order Fulfillment

### Process Order Fulfillment

**Operation:** `fulfillmentCreate`
**Scope Required:** `write_orders`

```graphql
mutation CreateFulfillment($input: FulfillmentInput!) {
  fulfillmentCreate(input: $input) {
    fulfillment {
      id
      status
      trackingInfo {
        company
        number
        url
      }
      fulfillmentLineItems(first: 10) {
        edges {
          node {
            lineItem {
              title
              quantity
            }
          }
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

**Variables:**

```json
{
  "input": {
    "orderId": "gid://shopify/Order/4567890123",
    "notifyCustomer": true,
    "trackingInfo": {
      "company": "USPS",
      "number": "9400100000000000000000",
      "url": "https://tools.usps.com/go/TrackConfirmAction?tLabels=9400100000000000000000"
    },
    "lineItems": [
      {
        "id": "gid://shopify/LineItem/12345678901234",
        "quantity": 1
      }
    ]
  }
}
```

### Update Tracking Information

**Operation:** `fulfillmentTrackingInfoUpdate`
**Scope Required:** `write_orders`

```graphql
mutation UpdateTracking($fulfillmentId: ID!, $trackingInfo: FulfillmentTrackingInput!) {
  fulfillmentTrackingInfoUpdate(
    fulfillmentId: $fulfillmentId
    trackingInfoInput: $trackingInfo
  ) {
    fulfillment {
      id
      trackingInfo {
        company
        number
        url
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

**Variables:**

```json
{
  "fulfillmentId": "gid://shopify/Fulfillment/3456789012",
  "trackingInfo": {
    "company": "FedEx",
    "number": "123456789012",
    "url": "https://www.fedex.com/apps/fedextrack/?tracknumbers=123456789012"
  }
}
```

### Update Order Status

**Operation:** `orderUpdate`
**Scope Required:** `write_orders`

```graphql
mutation UpdateOrder($input: OrderInput!) {
  orderUpdate(input: $input) {
    order {
      id
      tags
      note
    }
    userErrors {
      field
      message
    }
  }
}
```

**Variables:**

```json
{
  "input": {
    "id": "gid://shopify/Order/4567890123",
    "tags": ["priority", "gift-wrap"],
    "note": "Customer requested gift wrapping with blue ribbon"
  }
}
```

### Cancel Fulfillment

```graphql
mutation CancelFulfillment($id: ID!) {
  fulfillmentCancel(id: $id) {
    fulfillment {
      id
      status
    }
    userErrors {
      field
      message
    }
  }
}
```

## Customer Management

### Create Customer

**Operation:** `customerCreate`
**Scope Required:** `write_customers`

```graphql
mutation CreateCustomer($input: CustomerInput!) {
  customerCreate(input: $input) {
    customer {
      id
      email
      firstName
      lastName
      phone
      tags
    }
    userErrors {
      field
      message
    }
  }
}
```

**Variables:**

```json
{
  "input": {
    "email": "customer@example.com",
    "firstName": "Jane",
    "lastName": "Smith",
    "phone": "+1-555-123-4567",
    "tags": ["wholesale", "vip"],
    "acceptsMarketing": true,
    "addresses": [
      {
        "address1": "123 Main Street",
        "city": "San Francisco",
        "province": "CA",
        "country": "US",
        "zip": "94103"
      }
    ]
  }
}
```

### Update Customer Information

**Operation:** `customerUpdate`
**Scope Required:** `write_customers`

```graphql
mutation UpdateCustomer($input: CustomerInput!) {
  customerUpdate(input: $input) {
    customer {
      id
      email
      tags
      note
    }
    userErrors {
      field
      message
    }
  }
}
```

**Variables:**

```json
{
  "input": {
    "id": "gid://shopify/Customer/5678901234",
    "tags": ["wholesale", "vip", "high-value"],
    "note": "Preferred customer - expedite orders",
    "acceptsMarketing": true
  }
}
```

### Query Customer Orders

```graphql
query GetCustomerOrders($customerId: ID!) {
  customer(id: $customerId) {
    id
    displayName
    email
    orders(first: 10, sortKey: CREATED_AT, reverse: true) {
      edges {
        node {
          id
          name
          createdAt
          totalPrice
          fulfillmentStatus
        }
      }
    }
  }
}
```

## E-Commerce Optimization

⚠️ **ESSENTIAL**: See [../../ECOMMERCE_OPTIMIZATION.md](../../ECOMMERCE_OPTIMIZATION.md) for comprehensive conversion optimization guide.

This guide covers:
- **Product Listing SEO**: Title, description, meta tags, alt text optimization
- **Conversion Rate Optimization**: Trust signals, urgency tactics, mobile optimization
- **Collection Strategy**: Taxonomy planning, smart collections, SEO
- **Image Optimization**: Photography standards, alt text, file optimization
- **Pricing Strategy**: Psychology, compare-at-price, bundles, volume pricing
- **Quality Audit Framework**: Scoring system, automated audits, improvement workflows
- **Complete Workflows**: New product launch, bulk optimization, collection reorganization

**Quick Audit Query** (Check product optimization readiness):
```graphql
query QuickProductAudit($id: ID!) {
  product(id: $id) {
    id
    title
    descriptionHtml
    seo { title description }
    images(first: 10) {
      edges {
        node {
          altText
          width
          height
        }
      }
    }
    variants(first: 10) {
      edges {
        node {
          sku
          price
          compareAtPrice
          inventoryQuantity
        }
      }
    }
    tags
    productType
    vendor
    totalInventory
  }
}
```

**Optimization Priority**:
1. **Best Sellers with Low Scores**: Quick wins, high impact
2. **High-Traffic Products**: Improve conversion on existing traffic
3. **New Products**: Start with high quality from launch
4. **Seasonal Items**: Optimize before peak season

## Error Handling

### UserErrors Pattern

All mutations return `userErrors` array. **ALWAYS check before processing:**

```javascript
const result = await shopifyAdmin.mutation(mutation, variables);

if (result.data.productCreate.userErrors.length > 0) {
  const errors = result.data.productCreate.userErrors;
  console.error("Product creation failed:");
  errors.forEach(err => {
    console.error(`  ${err.field}: ${err.message}`);
  });
  // Handle errors appropriately
  return;
}

// Success - process product
const product = result.data.productCreate.product;
```

### Common Error Scenarios

**Inventory Errors:**
- `Inventory item must be associated with location` - Call `inventoryActivate` first
- `Cannot adjust inventory for untracked item` - Set `inventoryManagement: SHOPIFY`

**Product Errors:**
- `Product variant options exceed limit` - Max 3 options per product
- `Duplicate SKU` - SKUs must be unique across all products
- `Invalid product status` - Use ACTIVE, DRAFT, or ARCHIVED

**Order Errors:**
- `Order already fulfilled` - Check fulfillment status first
- `Line item quantity exceeds available` - Verify inventory before fulfilling

**Customer Errors:**
- `Email has already been taken` - Use `customerUpdate` instead
- `Invalid email format` - Validate email before submission

### Retry Strategy

```javascript
async function retryMutation(mutation, variables, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const result = await shopifyAdmin.mutation(mutation, variables);

      if (result.errors) {
        throw new Error(result.errors[0].message);
      }

      return result;
    } catch (error) {
      if (error.message.includes("Throttled") && i < maxRetries - 1) {
        await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, i)));
        continue;
      }
      throw error;
    }
  }
}
```

## Complete Workflow Examples

### Example 1: Add New Product with Variants and Set Inventory

```javascript
// 1. Initialize API
const { conversationId } = await learn_shopify_api({ api: "admin" });

// 2. Create product with variants
const productMutation = `
mutation CreateProduct($input: ProductInput!) {
  productCreate(input: $input) {
    product {
      id
      title
      variants(first: 10) {
        edges {
          node {
            id
            inventoryItem { id }
            sku
          }
        }
      }
    }
    userErrors { field message }
  }
}`;

const productInput = {
  input: {
    title: "Organic Coffee Blend",
    vendor: "Roastery Co",
    productType: "Coffee",
    variants: [
      { title: "250g", price: "15.99", sku: "COFFEE-250G" },
      { title: "500g", price: "28.99", sku: "COFFEE-500G" },
      { title: "1kg", price: "52.99", sku: "COFFEE-1KG" }
    ]
  }
};

const productResult = await shopifyAdmin.mutation(productMutation, productInput);
const variants = productResult.data.productCreate.product.variants.edges;

// 3. Activate inventory at location
const locationId = "gid://shopify/Location/67890123";

for (const variant of variants) {
  await shopifyAdmin.mutation(`
    mutation ActivateInventory($inventoryItemId: ID!, $locationId: ID!) {
      inventoryActivate(inventoryItemId: $inventoryItemId, locationId: $locationId) {
        inventoryLevel { id }
        userErrors { field message }
      }
    }
  `, {
    inventoryItemId: variant.node.inventoryItem.id,
    locationId: locationId
  });
}

// 4. Set initial inventory quantities
const inventoryChanges = variants.map(v => ({
  inventoryItemId: v.node.inventoryItem.id,
  locationId: locationId,
  delta: 100 // Initial stock
}));

await shopifyAdmin.mutation(`
  mutation AdjustInventory($input: InventoryAdjustQuantitiesInput!) {
    inventoryAdjustQuantities(input: $input) {
      inventoryAdjustmentGroup { id }
      userErrors { field message }
    }
  }
`, {
  input: {
    reason: "received",
    name: "Initial stock - Dec 2025",
    changes: inventoryChanges
  }
});
```

### Example 2: Fulfill Order with Tracking

```javascript
// 1. Get order details
const orderQuery = `
query GetOrder($orderId: ID!) {
  order(id: $orderId) {
    id
    name
    lineItems(first: 50) {
      edges {
        node {
          id
          title
          quantity
          fulfillableQuantity
        }
      }
    }
  }
}`;

const order = await shopifyAdmin.query(orderQuery, {
  orderId: "gid://shopify/Order/4567890123"
});

// 2. Create fulfillment with tracking
const fulfillmentMutation = `
mutation CreateFulfillment($input: FulfillmentInput!) {
  fulfillmentCreate(input: $input) {
    fulfillment {
      id
      status
      trackingInfo { company number url }
    }
    userErrors { field message }
  }
}`;

const fulfillableItems = order.data.order.lineItems.edges
  .filter(item => item.node.fulfillableQuantity > 0)
  .map(item => ({
    id: item.node.id,
    quantity: item.node.fulfillableQuantity
  }));

await shopifyAdmin.mutation(fulfillmentMutation, {
  input: {
    orderId: "gid://shopify/Order/4567890123",
    notifyCustomer: true,
    trackingInfo: {
      company: "UPS",
      number: "1Z999AA10123456784",
      url: "https://www.ups.com/track?tracknum=1Z999AA10123456784"
    },
    lineItems: fulfillableItems
  }
});
```

### Example 3: Bulk Inventory Update from CSV

```javascript
// 1. Parse CSV with inventory updates
const inventoryUpdates = parseCSV(csvContent); // Returns [{sku, quantity}]

// 2. Get inventory item IDs from SKUs
const variantQuery = `
query GetVariantBySKU($query: String!) {
  productVariants(first: 1, query: $query) {
    edges {
      node {
        id
        sku
        inventoryItem { id }
      }
    }
  }
}`;

const changes = [];
for (const update of inventoryUpdates) {
  const result = await shopifyAdmin.query(variantQuery, {
    query: `sku:${update.sku}`
  });

  if (result.data.productVariants.edges.length > 0) {
    const variant = result.data.productVariants.edges[0].node;
    changes.push({
      inventoryItemId: variant.inventoryItem.id,
      locationId: "gid://shopify/Location/67890123",
      delta: update.quantity
    });
  }
}

// 3. Batch update inventory (max 100 items per mutation)
const batchSize = 100;
for (let i = 0; i < changes.length; i += batchSize) {
  const batch = changes.slice(i, i + batchSize);

  await shopifyAdmin.mutation(`
    mutation AdjustInventory($input: InventoryAdjustQuantitiesInput!) {
      inventoryAdjustQuantities(input: $input) {
        inventoryAdjustmentGroup { id }
        userErrors { field message }
      }
    }
  `, {
    input: {
      reason: "correction",
      name: `Bulk update batch ${i / batchSize + 1}`,
      changes: batch
    }
  });
}
```
