---
name: spapi-notifications
description: "Manage Amazon SP-API notifications. Use when setting up event subscriptions, managing destinations, or processing real-time notifications for orders, inventory, and other events."
license: MIT
version: 1.0.0
---

# Amazon SP-API Notifications

This skill provides guidance for managing event notifications through the Selling Partner API.

## When to Use This Skill

Activate this skill when working with:
- Event subscription setup
- SQS/EventBridge destinations
- Real-time order notifications
- Inventory change alerts
- Pricing notifications

## Notification Types

| Type | Description |
|------|-------------|
| ANY_OFFER_CHANGED | Buy Box or pricing changes |
| BRANDED_ITEM_CONTENT_CHANGE | Brand content updates |
| FBA_OUTBOUND_SHIPMENT_STATUS | FBA shipment updates |
| FEE_PROMOTION_NOTIFICATION | Fee changes |
| FEED_PROCESSING_FINISHED | Feed completion |
| FULFILLMENT_ORDER_STATUS | MCF status updates |
| ITEM_INVENTORY_EVENT_CHANGE | Inventory changes |
| ORDER_CHANGE | Order status changes |
| ORDER_STATUS_CHANGE | Order lifecycle events |
| REPORT_PROCESSING_FINISHED | Report ready |

## Setup Workflow

```python
from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient

auth = SPAPIAuth()
client = SPAPIClient(auth)

# 1. Create destination (SQS)
status, dest = client.post(
    "/notifications/v1/destinations",
    "notifications",
    data={
        "name": "my-sqs-destination",
        "resourceSpecification": {
            "sqs": {
                "arn": "arn:aws:sqs:us-east-1:123456789:my-queue"
            }
        }
    }
)
destination_id = dest.get("payload", {}).get("destinationId")

# 2. Create subscription
status, sub = client.post(
    "/notifications/v1/subscriptions/ORDER_CHANGE",
    "notifications",
    data={
        "destinationId": destination_id,
        "payloadVersion": "1.0"
    }
)

# 3. List subscriptions
status, subs = client.get(
    "/notifications/v1/subscriptions/ORDER_CHANGE",
    "notifications"
)
```

## Rate Limits

| Operation | Rate |
|-----------|------|
| Subscriptions | 1/sec |
| Destinations | 1/sec |

## Related Skills

- `spapi-vendor-orders` - Order event handling
- `spapi-integration-patterns` - Event processing patterns
