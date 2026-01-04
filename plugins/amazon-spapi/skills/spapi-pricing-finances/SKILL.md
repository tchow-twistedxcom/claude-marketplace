---
name: spapi-pricing-finances
description: "Manage Amazon pricing and finances. Use when checking competitive pricing, getting fee estimates, or retrieving financial events and settlements."
license: MIT
version: 1.0.0
---

# Amazon SP-API Pricing & Finances

This skill provides guidance for managing pricing data and financial information through the Selling Partner API.

## When to Use This Skill

Activate this skill when working with:
- Competitive pricing analysis
- Fee estimation
- Financial events and transactions
- Settlement reports

## Core APIs

- **Product Pricing API** - Pricing data and estimates
- **Finances API** - Financial events and settlements

## Pricing Operations

```python
from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient

auth = SPAPIAuth()
client = SPAPIClient(auth)

# Get competitive pricing
status, data = client.get(
    "/products/pricing/v0/competitivePrice",
    "pricing",
    params={
        "MarketplaceId": auth.get_marketplace_id(),
        "Asins": "B00EXAMPLE,B00EXAMPLE2",
        "ItemType": "Asin"
    }
)

# Get item offers
status, data = client.get(
    f"/products/pricing/v0/items/{asin}/offers",
    "pricing",
    params={
        "MarketplaceId": auth.get_marketplace_id(),
        "ItemCondition": "New"
    }
)

# Get fee estimates
status, data = client.post(
    "/products/fees/v0/feesEstimate",
    "pricing",
    data={
        "FeesEstimateRequest": {
            "MarketplaceId": auth.get_marketplace_id(),
            "IdType": "ASIN",
            "IdValue": "B00EXAMPLE",
            "PriceToEstimateFees": {
                "ListingPrice": {"CurrencyCode": "USD", "Amount": 25.0}
            },
            "Identifier": "request1"
        }
    }
)
```

## Finance Operations

```python
# List financial events
status, data = client.get(
    "/finances/v0/financialEvents",
    "finances",
    params={
        "PostedAfter": "2024-01-01T00:00:00Z",
        "MaxResultsPerPage": 100
    }
)

# Get financial event groups
status, data = client.get(
    "/finances/v0/financialEventGroups",
    "finances",
    params={
        "FinancialEventGroupStartedAfter": "2024-01-01T00:00:00Z"
    }
)
```

## Rate Limits

| Operation | Rate |
|-----------|------|
| Pricing | 0.5/sec |
| Finances | 0.5/sec |

## Related Skills

- `spapi-vendor-invoices` - Invoice pricing
- `spapi-reports-feeds` - Financial reports
