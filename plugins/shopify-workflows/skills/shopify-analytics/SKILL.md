---
name: shopify-analytics
description: "Analytics reports and data insights (read-only). Use when generating sales reports, analyzing trends, or querying performance metrics."
license: MIT
---

# Shopify Analytics & Reporting Skill

Production-ready skill for querying Shopify analytics data, generating reports, and tracking metrics. **READ-ONLY OPERATIONS ONLY** - use merchant-daily for CRUD, content-creator for content, marketing-ops for campaigns.

## Purpose & When to Use

**Use this skill when:**
- Generating sales, product, or customer analytics reports
- Tracking KPIs and business metrics
- Analyzing trends, cohorts, or performance data
- Creating custom analytics dashboards
- Querying historical data for insights

**Target Users:** Analysts, managers, business intelligence teams, data-driven decision makers

**Don't use for:** Creating/updating products or orders (merchant-daily), content creation (content-creator), setting up campaigns (marketing-ops), webhooks (developer)

---

## Core Integration

### Shopify Dev MCP Setup

**STEP 1: Initialize API Context**
```
MANDATORY: Call learn_shopify_api first to get conversationId
```

**STEP 2: Schema Introspection**
Use `introspect_graphql_schema` to discover analytics-relevant queries:
- Search for: "analytics", "report", "order", "product", "customer", "sales"
- Filter by: `["queries"]` for read-only operations

**STEP 3: Validate Queries**
Always validate GraphQL with `validate_graphql_codeblocks` before execution

### Authentication Pattern

⚠️ **CRITICAL**: See [../../AUTHENTICATION.md](../../AUTHENTICATION.md) for complete authentication guide.

**Required Scopes**:
- `read_analytics` - Analytics API access (Shopify Plus)
- `read_orders` - Order data queries
- `read_products` - Product and inventory data
- `read_customers` - Customer data and segmentation

**Key Points**:
- Shopify Dev MCP validates GraphQL but does NOT execute queries or handle authentication
- You MUST implement OAuth 2.0 client credentials grant flow yourself
- Tokens expire after 24 hours (86399 seconds) and must be refreshed
- Use access token in `X-Shopify-Access-Token` header for all API requests

### GraphQL Query Structure
```graphql
# Standard analytics query pattern
{
  # Use pagination for large datasets
  orders(first: 250, query: "created_at:>=2024-01-01") {
    edges {
      node {
        id
        name
        totalPriceSet { shopMoney { amount currencyCode } }
        createdAt
        # Include only fields needed for analysis
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
```

---

## Report Queries

### Sales Analytics

**Monthly Sales Report**
```graphql
query MonthlySalesReport($startDate: DateTime!, $endDate: DateTime!) {
  orders(first: 250, query: "created_at:>=$startDate AND created_at:<=$endDate AND financial_status:paid") {
    edges {
      node {
        id
        name
        createdAt
        totalPriceSet {
          shopMoney {
            amount
            currencyCode
          }
        }
        lineItems(first: 50) {
          edges {
            node {
              quantity
              originalUnitPriceSet {
                shopMoney { amount }
              }
            }
          }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
```

**Revenue by Product**
```graphql
query ProductRevenueAnalysis {
  products(first: 100, query: "status:active") {
    edges {
      node {
        id
        title
        totalInventory
        variants(first: 10) {
          edges {
            node {
              id
              sku
              price
              inventoryQuantity
            }
          }
        }
      }
    }
  }
}
```

**Top Selling Products (ShopifyQL)**
```shopifyql
FROM products
SHOW product_id, product_title, sum(quantity) as total_sold, sum(net_sales) as revenue
WHERE order_date >= '2024-01-01'
GROUP BY product_id, product_title
ORDER BY revenue DESC
LIMIT 20
```

### Customer Insights

**Customer Segmentation Query**
```graphql
query CustomerSegments {
  customers(first: 250, query: "orders_count:>5") {
    edges {
      node {
        id
        email
        createdAt
        ordersCount
        totalSpentV2 {
          amount
          currencyCode
        }
        lastOrder {
          createdAt
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
```

**Customer Lifetime Value**
```graphql
query CustomerLTV($customerId: ID!) {
  customer(id: $customerId) {
    id
    email
    createdAt
    ordersCount
    totalSpentV2 {
      amount
      currencyCode
    }
    orders(first: 250) {
      edges {
        node {
          createdAt
          totalPriceSet {
            shopMoney { amount }
          }
        }
      }
    }
  }
}
```

### Inventory & Product Performance

**Low Stock Alert Query**
```graphql
query LowStockProducts($threshold: Int!) {
  products(first: 100, query: "status:active") {
    edges {
      node {
        id
        title
        totalInventory
        variants(first: 50) {
          edges {
            node {
              id
              sku
              inventoryQuantity
              inventoryItem {
                id
                tracked
              }
            }
          }
        }
      }
    }
  }
  # Filter in application logic: totalInventory <= threshold
}
```

**Product Performance Metrics**
```graphql
query ProductPerformance($productId: ID!) {
  product(id: $productId) {
    id
    title
    totalInventory
    onlineStoreUrl
    publishedAt
    variants(first: 50) {
      edges {
        node {
          id
          sku
          price
          compareAtPrice
          inventoryQuantity
        }
      }
    }
  }
}
```

---

## Analytics Patterns

### Trend Analysis Pattern

**1. Time-Series Data Collection**
```typescript
// Fetch orders in date ranges, aggregate by period
// Use pagination to handle large datasets
async function collectTimeSeriesData(startDate: string, endDate: string) {
  let hasNextPage = true;
  let cursor = null;
  const results = [];

  while (hasNextPage) {
    const query = `
      query($cursor: String, $query: String!) {
        orders(first: 250, after: $cursor, query: $query) {
          edges {
            node {
              createdAt
              totalPriceSet { shopMoney { amount } }
            }
          }
          pageInfo { hasNextPage endCursor }
        }
      }
    `;

    // Execute query, collect results, update cursor
    // Aggregate by day/week/month in application logic
  }
}
```

**2. Growth Metrics Calculation**
```typescript
// Calculate MoM, YoY growth from time-series data
// Compare current period vs previous period
// Track: revenue growth, order volume growth, AOV trends
```

### Cohort Analysis Pattern

**Customer Cohort by Registration Month**
```graphql
query CustomerCohort($month: DateTime!) {
  customers(first: 250, query: "created_at:>=$month AND created_at:<$nextMonth") {
    edges {
      node {
        id
        email
        createdAt
        ordersCount
        totalSpentV2 { amount }
      }
    }
  }
}
```

**Retention Analysis**
```typescript
// 1. Group customers by signup month (cohort)
// 2. Track orders in subsequent months
// 3. Calculate retention rates per cohort
// Use multiple queries: cohort identification + order history per cohort
```

### Aggregation Patterns

**Average Order Value (AOV)**
```typescript
// Query all orders in period
// Calculate: SUM(totalPrice) / COUNT(orders)
// Segment by: customer type, product category, traffic source
```

**Conversion Rate Analysis**
```graphql
query ConversionMetrics {
  shop {
    name
    currencyCode
    # Note: Checkout data requires Analytics API or Shopify Plus
  }
  # Use orders vs sessions data from Shopify Analytics API
  # Calculate: (orders / sessions) * 100
}
```

---

## Error Handling

### Query Error Patterns

**Rate Limiting**
```typescript
// Shopify Admin API: 2 calls/second bucket (40 point leak rate)
// Handle 429 responses: exponential backoff + retry
if (response.extensions?.cost?.throttleStatus?.currentlyAvailable < 100) {
  await delay(1000); // Wait before next query
}
```

**Data Access Errors**
```graphql
# Missing scopes return user errors
{
  "errors": [
    {
      "message": "Access denied for orders field",
      "extensions": {
        "code": "ACCESS_DENIED"
      }
    }
  ]
}
# Solution: Verify API scopes (read_orders, read_analytics, read_products)
```

**Pagination Limits**
```typescript
// Max 250 items per query
// Use cursor-based pagination for large datasets
// Monitor query cost points (max 1000 per query)
```

### Validation Failures

**Invalid Date Queries**
```graphql
# Wrong: query: "created_at:2024-01-01"
# Right: query: "created_at:>=2024-01-01 AND created_at:<=2024-01-31"
```

**Field Availability**
```typescript
// Use introspect_graphql_schema to verify field existence
// Analytics fields may require Shopify Plus
// Fallback to basic metrics if advanced analytics unavailable
```

---

## Examples

### Example 1: Generate Monthly Sales Report

**Workflow:**
```
1. learn_shopify_api(api: "admin") → get conversationId
2. introspect_graphql_schema(query: "orders", filter: ["queries"])
3. Build query with date filters
4. validate_graphql_codeblocks(codeblocks: [query])
5. Execute paginated query
6. Aggregate results: total revenue, order count, AOV
7. Format report output
```

**Complete Query:**
```graphql
query MonthlySalesReport {
  orders(first: 250, query: "created_at:>=2024-11-01 AND created_at:<=2024-11-30 AND financial_status:paid") {
    edges {
      node {
        id
        name
        createdAt
        totalPriceSet {
          shopMoney {
            amount
            currencyCode
          }
        }
        customer {
          id
          email
        }
        lineItems(first: 50) {
          edges {
            node {
              quantity
              product { id title }
            }
          }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
```

**Output Format:**
```
Monthly Sales Report - November 2024
-----------------------------------
Total Revenue: $45,230.50 USD
Total Orders: 234
Average Order Value: $193.29
Top Product: [Product Name] (45 units sold)
```

### Example 2: Customer Retention Analysis

**Workflow:**
```
1. Identify cohort: customers created in January 2024
2. Query customer data with ordersCount
3. Query orders for each customer in subsequent months
4. Calculate retention: customers with orders in Feb, Mar, Apr, etc.
5. Present retention curve
```

**Cohort Query:**
```graphql
query JanuaryCohort {
  customers(first: 250, query: "created_at:>=2024-01-01 AND created_at:<=2024-01-31") {
    edges {
      node {
        id
        email
        createdAt
        orders(first: 250) {
          edges {
            node {
              createdAt
            }
          }
        }
      }
    }
  }
}
```

### Example 3: Product Performance Dashboard

**Workflow:**
```
1. Query top 50 products by inventory value
2. For each product, calculate: inventory value, sell-through rate
3. Query recent orders to find best sellers
4. Cross-reference: high inventory + low sales = slow movers
5. Output: dashboard with recommendations
```

**Combined Query:**
```graphql
query ProductDashboard {
  products(first: 50, query: "status:active", sortKey: INVENTORY_TOTAL, reverse: true) {
    edges {
      node {
        id
        title
        totalInventory
        variants(first: 10) {
          edges {
            node {
              id
              sku
              price
              inventoryQuantity
            }
          }
        }
      }
    }
  }
}
```

---

## Best Practices

1. **Always paginate**: Use cursor-based pagination for datasets >250 items
2. **Query optimization**: Request only needed fields to reduce cost points
3. **Date filtering**: Use precise date ranges to limit result sets
4. **Validate first**: Always validate GraphQL before execution
5. **Scope verification**: Check API scopes match analytics needs
6. **Rate limit awareness**: Monitor throttle status, implement backoff
7. **Data aggregation**: Perform aggregations in application logic, not GraphQL
8. **ShopifyQL for reports**: Use ShopifyQL for built-in report types when available

**Scope Requirements:**
- `read_analytics` - Analytics API access (Shopify Plus)
- `read_orders` - Order data queries
- `read_products` - Product and inventory data
- `read_customers` - Customer data and segmentation

**Remember:** This skill is READ-ONLY. For creating/updating data, delegate to appropriate skills (merchant-daily, content-creator, marketing-ops).
