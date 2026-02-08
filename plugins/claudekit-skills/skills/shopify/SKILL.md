---
name: shopify
description: Guide for implementing Shopify apps, extensions, themes, and integrations using GraphQL/REST APIs, Shopify CLI, Polaris UI, and various extension types (Checkout, Admin, POS). Use when building Shopify apps, implementing checkout extensions, customizing admin interfaces, creating themes with Liquid, or integrating with Shopify's APIs.
---

# Shopify Development

This skill provides comprehensive guidance for building on the Shopify platform, including apps, extensions, themes, and API integrations.

## When to Use This Skill

Use this skill when you need to:
- Build Shopify apps (public or custom)
- Create checkout, admin, or POS UI extensions
- Develop themes using Liquid templating
- Integrate with Shopify APIs (GraphQL Admin API, REST API, Storefront API)
- Implement Shopify Functions (discounts, payments, delivery, validation)
- Build headless storefronts with Hydrogen
- Configure webhooks and metafields
- Use Shopify CLI for development workflows

## App Types (Critical Knowledge)

**Understanding app types prevents 90% of deployment issues.**

### Custom Apps vs Partner Apps

| Aspect | Custom App | Partner App |
|--------|-----------|-------------|
| Created in | Store Admin (dev.shopify.com) | CLI/Partner Dashboard (partners.shopify.com) |
| Distribution | Single store only | Multiple stores |
| CI/CD | Merchant token | `SHOPIFY_CLI_PARTNERS_TOKEN` |

**Key insight:** Extension UUIDs are **app-scoped**. Deploying to wrong app = wrong UUID = CSS not loading.

For complete details, see [App Types and Distribution](reference/app-types-and-distribution.md)

### Critical CLI Commands

> **⚠️ `shopify app init` creates NEW apps with NEW UUIDs**
>
> Use `shopify app config link` to connect to EXISTING apps.
> Using `init` for existing apps creates duplicates and deployment failures.

```bash
# Connect to existing app (99% of cases)
shopify app config link

# Create brand new app ONLY
shopify app init
```

For deployment workflow, see [App Deployment Guide](reference/app-deployment-guide.md)

## Core Platform Components

### 1. Shopify CLI

**Installation:**
```bash
npm install -g @shopify/cli@latest
```

**Essential Commands:**
- `shopify app init` - Create new app
- `shopify app dev` - Start local development server
- `shopify app deploy` - Deploy app to Shopify
- `shopify app generate extension` - Add extension to app
- `shopify theme dev` - Preview theme locally
- `shopify theme pull/push` - Sync theme files

For detailed CLI reference, see [reference/cli-commands.md](reference/cli-commands.md)

### 2. GraphQL Admin API (Recommended)

**Primary API for new development.** Efficient, type-safe, flexible.

**Endpoint:**
```
https://{shop-name}.myshopify.com/admin/api/2025-01/graphql.json
```

**Authentication:**
```javascript
headers: {
  'X-Shopify-Access-Token': 'your-access-token',
  'Content-Type': 'application/json'
}
```

**Common Operations:**
- Query products, orders, customers, inventory
- Create/update/delete resources via mutations
- Bulk operations for large datasets
- Real-time data with subscriptions

For comprehensive GraphQL reference, see [reference/graphql-admin-api.md](reference/graphql-admin-api.md)

### 3. REST Admin API (Maintenance Mode)

**Use only for legacy systems.** Shopify recommends GraphQL for all new development.

**Base URL:**
```
https://{shop-name}.myshopify.com/admin/api/2025-01/{resource}.json
```

**Rate Limits:**
- Standard: 2 requests/second
- Plus: 4 requests/second

### 4. UI Frameworks

#### Polaris (React)
Design system for consistent Shopify UI:
```bash
npm install @shopify/polaris
```

#### Polaris Web Components
Framework-agnostic components:
```html
<script src="https://cdn.shopify.com/shopifycloud/polaris.js"></script>
```

## Extension Types

### Checkout UI Extensions
Customize checkout experience with native-rendered components.

**Generate:**
```bash
shopify app generate extension --type checkout_ui_extension
```

**Configuration:** `shopify.extension.toml`

**Common Components:** View, BlockStack, InlineLayout, Button, TextField, Checkbox, Banner

For detailed extension reference, see [reference/ui-extensions.md](reference/ui-extensions.md)

### Admin UI Extensions
Extend Shopify admin interface.

**Types:**
- App blocks (embedded in native pages)
- App overlays (modal experiences)
- Links (product/collection/order pages)

### POS Extensions
Customize Point of Sale experience.

**Types:**
- Smart Grid Tiles (quick access actions)
- Modals (dialogs and forms)
- Cart modifications (custom discounts/line items)

### Post-Purchase Extensions
Upsell offers after checkout completion.

**Target:** `purchase.thank-you.block.render`

### Customer Account UI Extensions
Customize post-purchase account pages.

**Targets:** Account overview, order status/index

## Shopify Functions

Serverless backend customization running on Shopify infrastructure.

**Function Types:**
- **Discounts:** Cart, product, shipping, order discounts
- **Payment customization:** Hide/rename/reorder payment methods
- **Delivery customization:** Custom shipping options
- **Order routing:** Fulfillment location rules
- **Validation:** Cart and checkout business rules
- **Fulfillment constraints:** Bundle shipping rules

**Languages:** JavaScript, Rust, AssemblyScript

**Generate:**
```bash
shopify app generate extension --type function
```

## Theme Development

### Liquid Templating

**Core Concepts:**
- **Objects:** `{{ product.title }}` - Output dynamic content
- **Filters:** `{{ product.price | money }}` - Transform data
- **Tags:** `{% if %} {% for %} {% case %}` - Control flow

**Common Objects:**
- `product` - Product data
- `collection` - Collection data
- `cart` - Shopping cart
- `customer` - Customer account
- `shop` - Store information

**Architecture:**
- **Layouts:** Base templates
- **Templates:** Page structures
- **Sections:** Reusable content blocks (Online Store 2.0)
- **Snippets:** Smaller components

**Development:**
```bash
shopify theme dev    # Local preview
shopify theme pull   # Download from store
shopify theme push   # Upload to store
```

## Authentication & Security

### OAuth 2.0 Flow
For public apps accessing merchant stores:

1. Redirect merchant to authorization URL
2. Merchant approves access
3. Receive authorization code
4. Exchange code for access token
5. Store token securely

### Access Scopes
Request minimum permissions needed:
- `read_products` - View products
- `write_products` - Modify products
- `read_orders` - View orders
- `write_orders` - Modify orders

Full scope list: https://shopify.dev/api/usage/access-scopes

### Session Tokens
For embedded apps in Shopify admin using App Bridge.

## Webhooks

Real-time event notifications from Shopify.

**Configuration:** `shopify.app.toml`

**Common Topics:**
- `orders/create`, `orders/updated`, `orders/paid`
- `products/create`, `products/update`, `products/delete`
- `customers/create`, `customers/update`
- `app/uninstalled`

**GDPR Mandatory Webhooks:**
- `customers/data_request`
- `customers/redact`
- `shop/redact`

## Metafields

Custom data storage for extending Shopify resources.

**Owners:** Products, variants, customers, orders, collections, shop

**Types:** text, number, date, URL, JSON, file_reference

**Access:** Admin API, Storefront API, Liquid templates

## Best Practices

### Performance
- Use GraphQL instead of REST for efficiency
- Request only needed fields in queries
- Implement pagination for large datasets
- Use bulk operations for batch processing
- Respect rate limits (cost-based for GraphQL)

### User Experience
- Follow Polaris design guidelines
- Implement loading states
- Provide clear error messages
- Support keyboard navigation
- Test across devices

### Security
- Store API credentials securely
- Use environment variables for tokens
- Implement webhook verification
- Follow OAuth best practices
- Request minimal access scopes

### Code Quality
- Use TypeScript for type safety
- Write comprehensive error handling
- Implement retry logic with exponential backoff
- Log errors for debugging
- Keep dependencies updated

### Testing
- Use development stores for testing
- Test across different store plans
- Verify webhook handling
- Test app uninstall flow
- Validate GDPR compliance

## Development Workflow

1. **Initialize App:**
   ```bash
   shopify app init
   ```

2. **Configure Access Scopes:**
   Edit `shopify.app.toml`:
   ```toml
   [access_scopes]
   scopes = "read_products,write_products"
   ```

3. **Start Development Server:**
   ```bash
   shopify app dev
   ```

4. **Generate Extensions:**
   ```bash
   shopify app generate extension
   ```

5. **Test in Development Store:**
   Install app on test store

6. **Deploy to Production:**
   ```bash
   shopify app deploy
   ```

## Common Patterns

### Fetch Products (GraphQL)
```graphql
query {
  products(first: 10) {
    edges {
      node {
        id
        title
        handle
        variants(first: 5) {
          edges {
            node {
              id
              price
              inventoryQuantity
            }
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

### Create Product (GraphQL)
```graphql
mutation {
  productCreate(input: {
    title: "New Product"
    productType: "Clothing"
    variants: [{
      price: "29.99"
      sku: "SKU123"
    }]
  }) {
    product {
      id
      title
    }
    userErrors {
      field
      message
    }
  }
}
```

### Checkout Extension (React)
```javascript
import { useState } from 'react';
import {
  render,
  BlockStack,
  TextField,
  Checkbox,
  useApi
} from '@shopify/ui-extensions-react/checkout';

function Extension() {
  const { extensionPoint } = useApi();
  const [checked, setChecked] = useState(false);

  return (
    <BlockStack>
      <TextField label="Gift Message" />
      <Checkbox checked={checked} onChange={setChecked}>
        This is a gift
      </Checkbox>
    </BlockStack>
  );
}

render('Checkout::Dynamic::Render', () => <Extension />);
```

## Resources

### Documentation
- Official docs: https://shopify.dev/docs
- GraphQL API: https://shopify.dev/docs/api/admin-graphql
- Shopify CLI: https://shopify.dev/docs/api/shopify-cli
- Polaris: https://polaris.shopify.com

### Tools
- GraphiQL Explorer: Built into Shopify admin
- Shopify CLI: Development workflow
- Partner Dashboard: App management
- Development stores: Free testing environments

### Learning
- Shopify Developer Changelog: API updates and deprecations
- Built for Shopify: Quality program for apps
- Community forums: Help and discussions

## Reference Documentation

This skill includes detailed reference documentation:

### Deployment & App Management (Start Here for Issues)
- [App Deployment Guide](reference/app-deployment-guide.md) - **init vs config link, troubleshooting**
- [App Types and Distribution](reference/app-types-and-distribution.md) - Custom vs Partner apps
- [Theme App Extensions](reference/theme-app-extensions.md) - **UUIDs, CDN paths, embeds**

### API & Development
- [GraphQL Admin API Reference](reference/graphql-admin-api.md) - Comprehensive API guide
- [Shopify CLI Commands](reference/cli-commands.md) - Complete CLI reference
- [UI Extensions](reference/ui-extensions.md) - Extension types and components

## Troubleshooting

### Deployment Issues (Most Common)

**CSS Not Loading After Deployment:**
1. **Wrong app linked?** Run `shopify app info` - check `client_id` matches expected app
2. **App not installed?** App must be installed on store for extensions to appear
3. **Embed disabled?** Theme Customizer → App embeds → Toggle ON
4. **Wrong UUID?** Compare local `extensions/*/shopify.extension.toml` UUID with live site source

**CDN Returns 404:**
1. Verify version exists in Partner Dashboard → Versions tab
2. Check extension was included in deployment
3. Verify asset filename matches exactly (case-sensitive)

**Extension Not Appearing in Theme Customizer:**
1. Is app installed? (Check store admin → Apps)
2. Is extension deployed? (`shopify app versions list`)
3. Is extension type `"theme"`?

**Deployed to Wrong App (Duplicate App Created):**
- **Cause:** Used `shopify app init` instead of `shopify app config link`
- **Fix:** Link to correct app with `shopify app config link`, redeploy

See [App Deployment Guide](reference/app-deployment-guide.md) for complete troubleshooting.

### API Issues

**Rate Limit Errors:**
- Monitor `X-Shopify-Shop-Api-Call-Limit` header
- Implement exponential backoff
- Use bulk operations for large datasets

**Authentication Failures:**
- Verify access token is valid
- Check required scopes are granted
- Ensure OAuth flow completed correctly

**Webhook Not Receiving Events:**
- Verify webhook URL is accessible
- Check webhook signature validation
- Review webhook logs in Partner Dashboard

**Extension Not Appearing:**
- Verify extension target is correct
- Check extension is published
- Ensure app is installed on store

## Version Management

Shopify uses quarterly API versioning (YYYY-MM format):
- Current: 2025-01
- Each version supported for 12 months
- Test updates before quarterly releases
- Use version-specific endpoints

## App Distribution

### Custom Apps
Single merchant installation, no review required.

### Public Apps
App Store listing with Shopify review:
- Follow app requirements
- Complete Built for Shopify criteria
- Define pricing model
- Submit for review

---

**Note:** This skill covers the Shopify platform as of January 2025. Always refer to official Shopify documentation for the latest updates and API versions.
