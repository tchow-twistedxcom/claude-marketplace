---
name: spapi-orders-fulfillment
description: "Manage Amazon orders and fulfillment. Use when retrieving orders, managing FBA inventory, creating inbound shipments, or handling multi-channel fulfillment."
license: MIT
version: 1.0.0
---

# Amazon SP-API Orders & Fulfillment

This skill provides guidance for managing Amazon orders and fulfillment operations through the Selling Partner API.

## When to Use This Skill

Activate this skill when working with:
- Order retrieval and management
- FBA inventory tracking
- Inbound shipment creation
- Multi-channel fulfillment (MCF)
- Inventory level monitoring

## Core APIs

- **Orders API** - Retrieve and manage orders
- **FBA Inventory API** - FBA inventory levels
- **Fulfillment Inbound API** - Shipments to Amazon FCs
- **Fulfillment Outbound API** - Multi-channel fulfillment

## Quick Reference

```python
from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient

auth = SPAPIAuth()
client = SPAPIClient(auth)

# List orders
status, data = client.get(
    "/orders/v0/orders",
    "orders",
    params={
        "MarketplaceIds": auth.get_marketplace_id(),
        "CreatedAfter": "2024-01-01T00:00:00Z"
    }
)

# Get order details
status, data = client.get(
    f"/orders/v0/orders/{order_id}",
    "orders.getOrder"
)

# Get order items
status, data = client.get(
    f"/orders/v0/orders/{order_id}/orderItems",
    "orders.getOrderItems"
)

# Get buyer info (requires RDT)
status, data = client.get(
    f"/orders/v0/orders/{order_id}/buyerInfo",
    "orders",
    use_rdt=True,
    rdt_path=f"/orders/v0/orders/{order_id}/buyerInfo",
    rdt_elements=["buyerInfo"]
)

# FBA inventory
status, data = client.get(
    "/fba/inventory/v1/summaries",
    "fbaInventory",
    params={
        "granularityType": "Marketplace",
        "granularityId": auth.get_marketplace_id(),
        "marketplaceIds": auth.get_marketplace_id()
    }
)
```

## Rate Limits

| Operation | Rate | Notes |
|-----------|------|-------|
| getOrders | 0.0167/sec | 1/minute |
| getOrder | 0.5/sec | Per order |
| getOrderItems | 0.5/sec | Per order |
| FBA inventory | 2/sec | |

## Related Skills

- `spapi-vendor-orders` - Vendor PO management
- `spapi-reports-feeds` - Order reports
- `spapi-integration-patterns` - Rate limiting
