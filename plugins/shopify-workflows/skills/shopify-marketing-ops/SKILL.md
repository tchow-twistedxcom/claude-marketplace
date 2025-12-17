---
name: shopify-marketing-ops
description: "Marketing campaigns, discounts, and promotions. Use when creating discount codes, setting up campaigns, or managing promotional pricing."
license: MIT
---

# Shopify Marketing Operations Skill

Production-ready skill for marketing coordinators and campaign managers to create discounts, price rules, and marketing campaigns in Shopify.

## Purpose & When to Use

**Use this skill when:**
- Creating discount codes for promotional campaigns
- Setting up automatic discounts (e.g., spend $100 get 10% off)
- Managing price rules and discount combinations
- Launching marketing activities and tracking engagements
- Creating email marketing campaigns

**Target Users:** Marketing coordinators, campaign managers, promotion managers

**NOT covered here:** Product creation (use merchant-daily), blog content (use content-creator), order processing (use merchant-daily), webhooks/metafields (use developer), deep analytics (use analytics)

---

## Core Integration - Shopify Dev MCP

### Authentication & Setup

```javascript
// STEP 1: Always call learn_shopify_api first to get conversationId
const conversationId = await learn_shopify_api({
  api: "admin"
});

// STEP 2: Use conversationId in all subsequent tool calls
```

### GraphQL Schema Discovery

```javascript
// Find discount-related operations
introspect_graphql_schema({
  conversationId: conversationId,
  api: "admin",
  query: "discount", // Returns discountCodeBasicCreate, discountAutomaticBasicCreate, etc.
  filter: ["mutations"]
});

// Find marketing operations
introspect_graphql_schema({
  conversationId: conversationId,
  api: "admin",
  query: "marketing",
  filter: ["mutations", "types"]
});
```

### Validation Pattern

```javascript
// ALWAYS validate GraphQL before executing
validate_graphql_codeblocks({
  conversationId: conversationId,
  api: "admin",
  codeblocks: [yourGraphQLMutation]
});
```

**Authentication**:
⚠️ **CRITICAL**: See [../../AUTHENTICATION.md](../../AUTHENTICATION.md) for complete authentication guide.

**Required Scopes**:
- `write_discounts` - Discount codes and price rules
- `write_price_rules` - Price rule management
- `write_marketing_events` - Marketing campaigns

**Key Points**:
- Shopify Dev MCP validates GraphQL but does NOT execute mutations or handle authentication
- You MUST implement OAuth 2.0 client credentials grant flow yourself
- Tokens expire after 24 hours (86399 seconds) and must be refreshed
- Use access token in `X-Shopify-Access-Token` header for all API requests

---

## Discount Operations

### Discount Code Creation (Manual Codes)

**Use for:** Promotional codes customers enter at checkout (e.g., SUMMER2024, WELCOME10)

```graphql
mutation discountCodeBasicCreate($basicCodeDiscount: DiscountCodeBasicInput!) {
  discountCodeBasicCreate(basicCodeDiscount: $basicCodeDiscount) {
    codeDiscountNode {
      id
      codeDiscount {
        ... on DiscountCodeBasic {
          title
          codes(first: 1) {
            nodes {
              code
            }
          }
          startsAt
          endsAt
          customerSelection {
            __typename
          }
          customerGets {
            value {
              __typename
            }
          }
        }
      }
    }
    userErrors {
      field
      message
      code
    }
  }
}
```

**Variables Example - Percentage Off:**
```json
{
  "basicCodeDiscount": {
    "title": "Summer Sale 2024",
    "code": "SUMMER2024",
    "startsAt": "2024-06-01T00:00:00Z",
    "endsAt": "2024-08-31T23:59:59Z",
    "customerSelection": {
      "all": true
    },
    "customerGets": {
      "value": {
        "percentage": 0.15
      },
      "items": {
        "all": true
      }
    },
    "appliesOncePerCustomer": false,
    "usageLimit": 1000
  }
}
```

**Variables Example - Fixed Amount Off:**
```json
{
  "basicCodeDiscount": {
    "title": "Welcome Discount",
    "code": "WELCOME10",
    "startsAt": "2024-01-01T00:00:00Z",
    "customerSelection": {
      "all": true
    },
    "customerGets": {
      "value": {
        "discountAmount": {
          "amount": "10.00",
          "appliesOnEachItem": false
        }
      },
      "items": {
        "all": true
      }
    },
    "appliesOncePerCustomer": true
  }
}
```

**Variables Example - Specific Products:**
```json
{
  "basicCodeDiscount": {
    "title": "New Product Launch",
    "code": "NEWLAUNCH20",
    "startsAt": "2024-11-07T00:00:00Z",
    "endsAt": "2024-11-14T23:59:59Z",
    "customerSelection": {
      "all": true
    },
    "customerGets": {
      "value": {
        "percentage": 0.20
      },
      "items": {
        "products": {
          "productsToAdd": ["gid://shopify/Product/1234567890"]
        }
      }
    }
  }
}
```

### Automatic Discounts

**Use for:** Discounts applied automatically without codes (e.g., "Spend $100, save 15%")

```graphql
mutation discountAutomaticBasicCreate($automaticBasicDiscount: DiscountAutomaticBasicInput!) {
  discountAutomaticBasicCreate(automaticBasicDiscount: $automaticBasicDiscount) {
    automaticDiscountNode {
      id
      automaticDiscount {
        ... on DiscountAutomaticBasic {
          title
          startsAt
          endsAt
          minimumRequirement {
            __typename
          }
          customerGets {
            value {
              __typename
            }
          }
        }
      }
    }
    userErrors {
      field
      message
      code
    }
  }
}
```

**Variables Example - Minimum Purchase Amount:**
```json
{
  "automaticBasicDiscount": {
    "title": "Spend $100 Save 15%",
    "startsAt": "2024-11-07T00:00:00Z",
    "customerGets": {
      "value": {
        "percentage": 0.15
      },
      "items": {
        "all": true
      }
    },
    "minimumRequirement": {
      "subtotal": {
        "greaterThanOrEqualToSubtotal": "100.00"
      }
    }
  }
}
```

**Variables Example - Minimum Quantity:**
```json
{
  "automaticBasicDiscount": {
    "title": "Buy 3 or More Save 20%",
    "startsAt": "2024-11-07T00:00:00Z",
    "customerGets": {
      "value": {
        "percentage": 0.20
      },
      "items": {
        "all": true
      }
    },
    "minimumRequirement": {
      "quantity": {
        "greaterThanOrEqualToQuantity": "3"
      }
    }
  }
}
```

### Price Rule Management

**Query Existing Price Rules:**
```graphql
query {
  priceRules(first: 50) {
    edges {
      node {
        id
        title
        valueType
        value
        startsAt
        endsAt
        usageCount
        usageLimit
      }
    }
  }
}
```

**Update Price Rule:**
```graphql
mutation priceRuleUpdate($id: ID!, $priceRule: PriceRuleInput!) {
  priceRuleUpdate(id: $id, priceRule: $priceRule) {
    priceRule {
      id
      title
      value
      endsAt
    }
    userErrors {
      field
      message
    }
  }
}
```

---

## Campaign Management

### Marketing Activities

**Create Marketing Activity:**
```graphql
mutation marketingActivityCreate($input: MarketingActivityCreateInput!) {
  marketingActivityCreate(input: $input) {
    marketingActivity {
      id
      title
      status
      activityListUrl
      marketingChannelType
      createdAt
    }
    userErrors {
      field
      message
      code
    }
  }
}
```

**Variables Example:**
```json
{
  "input": {
    "title": "Black Friday 2024 Campaign",
    "status": "ACTIVE",
    "marketingChannelType": "EMAIL",
    "budget": {
      "budgetType": "DAILY",
      "total": {
        "amount": "100.00",
        "currencyCode": "USD"
      }
    },
    "utm": {
      "campaign": "black-friday-2024",
      "source": "email",
      "medium": "newsletter"
    }
  }
}
```

### Marketing Engagements

**Track Campaign Performance:**
```graphql
mutation marketingEngagementCreate($marketingActivityId: ID!, $marketingEngagement: MarketingEngagementInput!) {
  marketingEngagementCreate(
    marketingActivityId: $marketingActivityId,
    marketingEngagement: $marketingEngagement
  ) {
    marketingEngagement {
      id
      occurredOn
      impressionsCount
      viewsCount
      clicksCount
      utcOffset
    }
    userErrors {
      field
      message
      code
    }
  }
}
```

**Variables Example:**
```json
{
  "marketingActivityId": "gid://shopify/MarketingActivity/1234567890",
  "marketingEngagement": {
    "occurredOn": "2024-11-07",
    "impressionsCount": 5000,
    "viewsCount": 2500,
    "clicksCount": 300,
    "sharesCount": 50,
    "favoritesCount": 75,
    "commentsCount": 20
  }
}
```

### Query Campaign Metrics

```graphql
query getMarketingActivities($first: Int!) {
  marketingActivities(first: $first) {
    edges {
      node {
        id
        title
        status
        marketingChannelType
        budget {
          budgetType
          total {
            amount
            currencyCode
          }
        }
        marketingEvents(first: 10) {
          edges {
            node {
              type
              occurredOn
              impressionsCount
              clicksCount
              utmParameters {
                campaign
                source
                medium
              }
            }
          }
        }
      }
    }
  }
}
```

---

## Email Marketing

### Create Email Marketing Activity

```graphql
mutation emailMarketingActivityCreate($input: EmailMarketingActivityInput!) {
  emailMarketingActivityCreate(input: $input) {
    emailMarketingActivity {
      id
      title
      status
      emailCampaignId
      subject
      fromEmail
      sentAt
      scheduledToSendAt
    }
    userErrors {
      field
      message
      code
    }
  }
}
```

**Variables Example - Newsletter:**
```json
{
  "input": {
    "title": "November Newsletter - New Arrivals",
    "emailCampaignId": "newsletter-nov-2024",
    "subject": "Check out our new arrivals this November!",
    "fromEmail": "marketing@yourstore.com",
    "scheduledToSendAt": "2024-11-15T10:00:00Z",
    "utmParameters": {
      "campaign": "newsletter-nov-2024",
      "source": "email",
      "medium": "newsletter"
    }
  }
}
```

**Variables Example - Promotional Email:**
```json
{
  "input": {
    "title": "Flash Sale - 24 Hours Only",
    "emailCampaignId": "flash-sale-nov-07",
    "subject": "⚡ Flash Sale: 30% Off Everything - Today Only!",
    "fromEmail": "sales@yourstore.com",
    "scheduledToSendAt": "2024-11-07T09:00:00Z",
    "marketingActivityId": "gid://shopify/MarketingActivity/1234567890",
    "utmParameters": {
      "campaign": "flash-sale-nov-07",
      "source": "email",
      "medium": "promotional"
    }
  }
}
```

### Query Email Campaign Performance

```graphql
query getEmailCampaigns {
  emailMarketingActivities(first: 20, sortKey: SENT_AT, reverse: true) {
    edges {
      node {
        id
        title
        subject
        status
        sentAt
        emailsSent
        emailsOpened
        emailsClicked
        unsubscribedCount
        marketingActivity {
          utmParameters {
            campaign
            source
          }
        }
      }
    }
  }
}
```

---

## Error Handling

### UserErrors Pattern

**All Shopify mutations return `userErrors`** - always check before proceeding:

```javascript
const result = await executeGraphQL(mutation, variables);

if (result.data.discountCodeBasicCreate.userErrors.length > 0) {
  const errors = result.data.discountCodeBasicCreate.userErrors;
  console.error('Discount creation failed:', errors);

  errors.forEach(err => {
    console.error(`Field: ${err.field}, Message: ${err.message}, Code: ${err.code}`);
  });

  return { success: false, errors };
}

// Success path
const discount = result.data.discountCodeBasicCreate.codeDiscountNode;
return { success: true, discount };
```

### Common Error Codes

- **INVALID**: Invalid input value (check field for specifics)
- **BLANK**: Required field is missing
- **TAKEN**: Discount code already exists
- **TOO_LONG**: Value exceeds maximum length
- **GREATER_THAN_OR_EQUAL_TO**: Minimum value validation failed
- **INVALID_DATE**: Date format or range issue

### Validation Before Execution

```javascript
// Step 1: Validate GraphQL syntax
const validation = await validate_graphql_codeblocks({
  conversationId: conversationId,
  api: "admin",
  codeblocks: [mutation]
});

if (!validation.valid) {
  console.error('GraphQL validation failed:', validation.errors);
  return;
}

// Step 2: Execute mutation
const result = await executeGraphQL(mutation, variables);

// Step 3: Check userErrors
if (result.data.yourMutation.userErrors.length > 0) {
  // Handle errors
}
```

---

## Complete Workflow Examples

### Example 1: Product Launch Discount Campaign

**Scenario:** Launch new product with 20% discount code, track via marketing activity

```javascript
// Step 1: Learn API
const conversationId = await learn_shopify_api({ api: "admin" });

// Step 2: Create discount code
const discountMutation = `
mutation discountCodeBasicCreate($basicCodeDiscount: DiscountCodeBasicInput!) {
  discountCodeBasicCreate(basicCodeDiscount: $basicCodeDiscount) {
    codeDiscountNode {
      id
      codeDiscount {
        ... on DiscountCodeBasic {
          title
          codes(first: 1) {
            nodes { code }
          }
        }
      }
    }
    userErrors { field message code }
  }
}`;

const discountVars = {
  basicCodeDiscount: {
    title: "New Widget Launch 2024",
    code: "NEWWIDGET20",
    startsAt: "2024-11-07T00:00:00Z",
    endsAt: "2024-11-21T23:59:59Z",
    customerSelection: { all: true },
    customerGets: {
      value: { percentage: 0.20 },
      items: {
        products: {
          productsToAdd: ["gid://shopify/Product/7654321"]
        }
      }
    },
    usageLimit: 500
  }
};

// Step 3: Validate before executing
await validate_graphql_codeblocks({
  conversationId,
  api: "admin",
  codeblocks: [discountMutation]
});

// Step 4: Execute
const discountResult = await executeGraphQL(discountMutation, discountVars);

// Step 5: Create marketing activity
const marketingMutation = `
mutation marketingActivityCreate($input: MarketingActivityCreateInput!) {
  marketingActivityCreate(input: $input) {
    marketingActivity { id title status }
    userErrors { field message }
  }
}`;

const marketingVars = {
  input: {
    title: "New Widget Launch Campaign",
    status: "ACTIVE",
    marketingChannelType: "EMAIL",
    utm: {
      campaign: "new-widget-2024",
      source: "email",
      medium: "launch"
    }
  }
};

const marketingResult = await executeGraphQL(marketingMutation, marketingVars);
```

### Example 2: Automated Holiday Sale

**Scenario:** Automatic tiered discounts for holiday shopping (no code needed)

```javascript
// Tier 1: Spend $50, save 10%
const tier1Mutation = `
mutation discountAutomaticBasicCreate($automaticBasicDiscount: DiscountAutomaticBasicInput!) {
  discountAutomaticBasicCreate(automaticBasicDiscount: $automaticBasicDiscount) {
    automaticDiscountNode {
      id
      automaticDiscount {
        ... on DiscountAutomaticBasic { title }
      }
    }
    userErrors { field message }
  }
}`;

const tier1Vars = {
  automaticBasicDiscount: {
    title: "Holiday Sale - Spend $50 Save 10%",
    startsAt: "2024-12-01T00:00:00Z",
    endsAt: "2024-12-25T23:59:59Z",
    customerGets: {
      value: { percentage: 0.10 },
      items: { all: true }
    },
    minimumRequirement: {
      subtotal: { greaterThanOrEqualToSubtotal: "50.00" }
    }
  }
};

// Tier 2: Spend $100, save 15%
const tier2Vars = {
  automaticBasicDiscount: {
    title: "Holiday Sale - Spend $100 Save 15%",
    startsAt: "2024-12-01T00:00:00Z",
    endsAt: "2024-12-25T23:59:59Z",
    customerGets: {
      value: { percentage: 0.15 },
      items: { all: true }
    },
    minimumRequirement: {
      subtotal: { greaterThanOrEqualToSubtotal: "100.00" }
    }
  }
};

// Execute both tiers
await executeGraphQL(tier1Mutation, tier1Vars);
await executeGraphQL(tier1Mutation, tier2Vars);
```

### Example 3: Email Campaign with Performance Tracking

**Scenario:** Weekly newsletter with engagement tracking

```javascript
// Step 1: Create email marketing activity
const emailMutation = `
mutation emailMarketingActivityCreate($input: EmailMarketingActivityInput!) {
  emailMarketingActivityCreate(input: $input) {
    emailMarketingActivity {
      id
      title
      emailCampaignId
    }
    userErrors { field message }
  }
}`;

const emailVars = {
  input: {
    title: "Weekly Newsletter - Week of Nov 7",
    emailCampaignId: "weekly-nov-07-2024",
    subject: "This Week's Deals + New Arrivals",
    fromEmail: "newsletter@yourstore.com",
    scheduledToSendAt: "2024-11-07T10:00:00Z",
    utmParameters: {
      campaign: "weekly-newsletter",
      source: "email",
      medium: "newsletter"
    }
  }
};

const emailResult = await executeGraphQL(emailMutation, emailVars);
const emailActivityId = emailResult.data.emailMarketingActivityCreate.emailMarketingActivity.id;

// Step 2: After campaign runs, track engagement
const engagementMutation = `
mutation marketingEngagementCreate($marketingActivityId: ID!, $marketingEngagement: MarketingEngagementInput!) {
  marketingEngagementCreate(
    marketingActivityId: $marketingActivityId,
    marketingEngagement: $marketingEngagement
  ) {
    marketingEngagement { id clicksCount }
    userErrors { field message }
  }
}`;

const engagementVars = {
  marketingActivityId: emailActivityId,
  marketingEngagement: {
    occurredOn: "2024-11-07",
    impressionsCount: 10000,
    viewsCount: 4500,
    clicksCount: 680
  }
};

await executeGraphQL(engagementMutation, engagementVars);
```

---

## Best Practices

1. **Always validate GraphQL** using `validate_graphql_codeblocks` before execution
2. **Check userErrors** in every mutation response
3. **Use UTM parameters** for all marketing activities to track performance
4. **Set usage limits** on discount codes to control budget
5. **Use automatic discounts** for promotions that don't require codes
6. **Track engagement metrics** for all campaigns to measure ROI
7. **Schedule emails** during optimal send times for your audience
8. **Reference products by GID** when creating product-specific discounts
9. **Set clear start/end dates** for all time-limited promotions
10. **Test discount combinations** before launching to customers
