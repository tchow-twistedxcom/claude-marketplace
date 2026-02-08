---
name: shopify-sales-growth
description: "Sales growth analysis and optimization workflow. Use when analyzing channel attribution, customer segmentation, product performance, conversion funnels, retention/LTV, or generating growth strategies. Orchestrates data-driven sales optimization using Shopify analytics."
license: MIT
---

# Shopify Sales Growth Analysis

Production-ready skill for orchestrating comprehensive sales growth analysis. Combines attribution, segmentation, product performance, conversion, and retention analysis into actionable growth strategies.

## When to Use This Skill

**Use this skill when:**
- Analyzing marketing channel performance and ROI
- Identifying high-value customer segments
- Evaluating product catalog performance
- Optimizing conversion funnels
- Improving customer retention and LTV
- Building data-driven growth strategies
- Generating sales growth reports

**Do NOT use for:**
- Creating/updating products (use merchant-daily)
- Setting up marketing campaigns (use marketing-ops)
- Writing content (use content-creator)
- Basic analytics queries (use analytics skill)

**Target Users:** E-commerce managers, growth marketers, analysts, business owners focused on scaling revenue

---

## Core Integration

### Initial Setup

```javascript
// Step 1: Initialize Shopify Admin API context
learn_shopify_api({
  api: "admin",
  conversationId: undefined // First call generates this
})
// Response includes conversationId - use for all subsequent calls
```

### Authentication

**Required Scopes**:
- `read_orders` - Order data and attribution
- `read_customers` - Customer segmentation
- `read_products` - Product performance
- `read_analytics` - Advanced analytics (Shopify Plus)

---

## Analysis Framework 1: Channel Attribution

### Purpose
Identify which marketing channels drive revenue and optimize budget allocation.

### Key Metrics
| Metric | Formula | Action |
|--------|---------|--------|
| Revenue by Source | SUM(revenue) GROUP BY source | Double down on winners |
| Conversion Rate | Orders / Sessions by channel | Optimize underperformers |
| Days to Convert | AVG(daysToConversion) | Tune nurture timing |
| CAC by Channel | Ad Spend / Conversions | Cut negative ROI |

### Attribution Query

```graphql
query ChannelAttribution($first: Int!, $query: String) {
  orders(first: $first, query: $query) {
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
        customerJourneySummary {
          daysToConversion
          firstVisit {
            source
            sourceType
            utmParameters {
              source
              medium
              campaign
            }
          }
          lastVisit {
            source
            sourceType
            utmParameters {
              source
              medium
              campaign
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

### Variables
```json
{
  "first": 250,
  "query": "created_at:>=2024-12-01 AND financial_status:paid"
}
```

### Analysis Pattern
```typescript
interface ChannelReport {
  source: string;
  orders: number;
  revenue: number;
  avgDaysToConversion: number;
  aov: number;
}

// Aggregation logic:
// 1. Group orders by firstVisit.source (first-touch) or lastVisit.source (last-touch)
// 2. Calculate: SUM(totalPrice), COUNT(orders), AVG(daysToConversion)
// 3. Sort by revenue DESC to find top channels
// 4. Compare first-touch vs last-touch to understand journey
```

---

## Analysis Framework 2: Customer Segmentation

### Purpose
Identify high-value customer segments and build targeted strategies.

### Segment Definitions
| Segment | Criteria | Strategy |
|---------|----------|----------|
| **VIPs** | Top 10% by LTV | Exclusive offers, early access |
| **At-Risk** | No order 60+ days, was active | Win-back campaigns |
| **One-Time High-Value** | 1 order, AOV > 2x average | Nurture to repeat |
| **Frequent Low-Spend** | 3+ orders, LTV < average | Upsell, bundles |
| **New Promising** | First order, high AOV | Fast nurture sequence |

### Segmentation Query

```graphql
query CustomerSegmentation($first: Int!, $query: String) {
  customers(first: $first, query: $query) {
    edges {
      node {
        id
        email
        createdAt
        numberOfOrders
        amountSpent {
          amount
          currencyCode
        }
        lastOrder {
          id
          createdAt
          totalPriceSet {
            shopMoney {
              amount
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

### Segment Queries
```json
// VIPs (high spenders)
{ "query": "total_spent:>500" }

// At-Risk (no recent orders)
{ "query": "orders_count:>1 AND last_order_date:<2024-11-01" }

// One-Time Buyers
{ "query": "orders_count:1" }

// Repeat Customers
{ "query": "orders_count:>2" }
```

### Analysis Pattern
```typescript
interface CustomerSegment {
  name: string;
  count: number;
  totalLTV: number;
  avgLTV: number;
  avgOrdersCount: number;
  strategy: string;
}

// Segmentation logic:
// 1. Calculate average LTV across all customers
// 2. Apply segment rules (VIP = top 10%, At-Risk = no order 60d, etc.)
// 3. For each segment: count, total LTV, avg metrics
// 4. Prioritize segments by revenue potential
```

---

## Analysis Framework 3: Product Performance

### Purpose
Identify star products, underperformers, and optimization opportunities.

### Performance Matrix
| Category | Characteristics | Action |
|----------|-----------------|--------|
| **Stars** | High sales, high margin | Feature prominently, increase inventory |
| **Cash Cows** | Steady sales, established | Maintain, use for cross-sell |
| **Question Marks** | New, uncertain performance | Test with ads, gather data |
| **Dogs** | Low sales, low margin | Bundle, discount, or discontinue |

### Product Query

```graphql
query ProductPerformance($first: Int!) {
  products(first: $first, query: "status:active") {
    edges {
      node {
        id
        title
        handle
        totalInventory
        publishedAt
        variants(first: 20) {
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
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

### Sales by Product (via Orders)

```graphql
query ProductSalesAnalysis($first: Int!, $query: String) {
  orders(first: $first, query: $query) {
    edges {
      node {
        id
        createdAt
        lineItems(first: 50) {
          edges {
            node {
              quantity
              originalTotalSet {
                shopMoney {
                  amount
                }
              }
              product {
                id
                title
              }
              variant {
                id
                sku
              }
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

### Analysis Pattern
```typescript
interface ProductMetrics {
  productId: string;
  title: string;
  unitsSold: number;
  revenue: number;
  avgPrice: number;
  inventoryTurnover: number;
  category: 'star' | 'cashCow' | 'questionMark' | 'dog';
}

// Performance logic:
// 1. Aggregate sales by product from order line items
// 2. Calculate: units sold, revenue, avg selling price
// 3. Cross-reference with inventory levels
// 4. Categorize using performance matrix rules
// 5. Generate recommendations per category
```

---

## Analysis Framework 4: Conversion Funnel

### Purpose
Understand buying behavior and optimize the path to purchase.

### Conversion Windows
| Window | Behavior | Strategy |
|--------|----------|----------|
| Same-day | Impulse buyers | Reduce friction, urgency tactics |
| 1-7 days | Quick considerers | Retargeting, social proof |
| 8-30 days | Researchers | Email nurture, comparison content |
| 30+ days | Long-cycle | Remarketing, price alerts |

### Journey Analysis Query

```graphql
query ConversionAnalysis($orderId: ID!) {
  order(id: $orderId) {
    id
    name
    createdAt
    customerJourneySummary {
      customerOrderIndex
      daysToConversion
      ready
      momentsCount {
        count
      }
      firstVisit {
        occurredAt
        source
        landingPage
      }
      lastVisit {
        occurredAt
        source
        landingPage
      }
      moments(first: 20) {
        edges {
          node {
            occurredAt
            ... on CustomerVisit {
              source
              landingPage
              referrerUrl
            }
          }
        }
      }
    }
  }
}
```

### Analysis Pattern
```typescript
interface ConversionMetrics {
  conversionWindow: string;
  orderCount: number;
  revenue: number;
  avgTouchpoints: number;
  topSources: string[];
  recommendations: string[];
}

// Funnel logic:
// 1. Segment orders by daysToConversion
// 2. For each segment: count, revenue, avg touchpoints
// 3. Identify patterns (which sources have shorter cycles?)
// 4. Generate optimization recommendations
```

---

## Analysis Framework 5: Retention & LTV

### Purpose
Maximize customer lifetime value and improve retention rates.

### Key Metrics
| Metric | Formula | Target |
|--------|---------|--------|
| Repeat Purchase Rate | Customers with 2+ orders / Total | >30% |
| Time to 2nd Order | AVG days between 1st and 2nd order | <60 days |
| Customer LTV | Total revenue / Total customers | Growing |
| LTV:CAC Ratio | LTV / Customer Acquisition Cost | >3:1 |

### Retention Query

```graphql
query RetentionAnalysis($first: Int!, $query: String) {
  customers(first: $first, query: $query) {
    edges {
      node {
        id
        email
        createdAt
        numberOfOrders
        amountSpent {
          amount
        }
        orders(first: 10) {
          edges {
            node {
              id
              createdAt
              totalPriceSet {
                shopMoney {
                  amount
                }
              }
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

### Cohort Analysis
```json
// January 2024 cohort
{ "query": "created_at:>=2024-01-01 AND created_at:<=2024-01-31" }

// Track their orders in subsequent months to calculate retention
```

### Analysis Pattern
```typescript
interface RetentionMetrics {
  cohort: string;
  totalCustomers: number;
  repeatCustomers: number;
  repeatRate: number;
  avgTimeTo2ndOrder: number;
  avgLTV: number;
  retentionByMonth: { month: number; retained: number }[];
}

// Retention logic:
// 1. Define cohort by signup month
// 2. Track orders in subsequent months
// 3. Calculate: repeat rate, time to 2nd order, LTV
// 4. Compare cohorts to identify trends
// 5. Identify what drives retention (source, product, etc.)
```

---

## Growth Workflow Orchestration

### Full Analysis Sequence

```
1. CHANNEL ATTRIBUTION
   → Run ChannelAttribution query
   → Aggregate by source (first-touch & last-touch)
   → Identify top performers and budget allocation

2. CUSTOMER SEGMENTATION
   → Run CustomerSegmentation query
   → Apply segment rules
   → Size each segment and calculate value

3. PRODUCT PERFORMANCE
   → Run ProductPerformance + ProductSalesAnalysis
   → Cross-reference sales with inventory
   → Categorize into performance matrix

4. CONVERSION FUNNEL
   → Sample orders with ConversionAnalysis
   → Segment by conversion window
   → Identify friction points

5. RETENTION ANALYSIS
   → Run RetentionAnalysis by cohort
   → Calculate repeat rates and LTV
   → Identify retention drivers

6. SYNTHESIS
   → Combine insights across all frameworks
   → Prioritize opportunities by impact
   → Generate actionable recommendations
```

### Quick Wins Checklist

| Priority | Analysis | Likely Finding | Action |
|----------|----------|----------------|--------|
| P0 | Top 3 channels | 80/20 revenue concentration | Increase budget on winners |
| P0 | Negative ROI campaigns | Wasted ad spend | Cut immediately |
| P1 | VIP segment size | Small but high-value | Create VIP program |
| P1 | Repeat purchase rate | <30% typical | Launch retention emails |
| P2 | Dog products | Low performers | Bundle or discontinue |
| P2 | Long conversion cycles | >7 days average | Add nurture sequence |

---

## Best Practices

1. **Start with attribution** - Know where revenue comes from before optimizing
2. **Segment before targeting** - Don't treat all customers the same
3. **Use both first-touch and last-touch** - They tell different stories
4. **Cohort for retention** - Compare apples to apples
5. **Prioritize by impact** - Focus on highest-value opportunities
6. **Test before scaling** - Validate strategies with small tests
7. **Refresh monthly** - Patterns change, re-analyze regularly

---

## Output Templates

### Executive Summary Template
```
SALES GROWTH ANALYSIS - [Date Range]

TOP CHANNELS (by revenue):
1. [Source]: $X (Y% of total)
2. [Source]: $X (Y% of total)
3. [Source]: $X (Y% of total)

CUSTOMER HEALTH:
- VIPs: X customers ($Y LTV)
- At-Risk: X customers (intervention needed)
- Repeat Rate: X%

TOP PRODUCTS:
- Stars: [List top 3]
- Action Items: [Specific recommendations]

CONVERSION INSIGHTS:
- Avg Days to Convert: X
- Most common journey: [Source] → [Source] → Purchase

RECOMMENDATIONS:
1. [Highest impact action]
2. [Second priority]
3. [Third priority]
```

---

**Required Scopes:** `read_orders`, `read_customers`, `read_products`
**Skill Type:** Orchestration / Analysis
**Related Skills:** shopify-analytics, shopify-marketing-ops
