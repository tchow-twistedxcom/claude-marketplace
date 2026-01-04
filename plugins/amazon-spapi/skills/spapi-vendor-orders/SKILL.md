---
name: spapi-vendor-orders
description: "Manage Amazon Vendor Central purchase orders. Use when processing POs, acknowledging orders, checking order status, or automating vendor order workflows for 1P vendor operations."
license: MIT
version: 1.0.0
---

# Amazon SP-API Vendor Orders

This skill provides guidance for managing Amazon Vendor Central purchase orders through the Selling Partner API.

## When to Use This Skill

Activate this skill when working with:
- Purchase order retrieval and listing
- Order acknowledgment submission
- Order status tracking
- Vendor order automation workflows
- PO lifecycle management

## Core Operations

### List Purchase Orders

```python
from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient
from spapi_vendor import VendorOrdersAPI

auth = SPAPIAuth()
client = SPAPIClient(auth)
api = VendorOrdersAPI(client)

# Get recent orders
status, data = api.get_purchase_orders(
    created_after="2024-01-01T00:00:00Z",
    limit=50
)

# Get changed orders
status, data = api.get_purchase_orders(
    changed_after="2024-01-15T00:00:00Z",
    is_po_changed=True
)

# Filter by status
status, data = api.get_purchase_orders(
    purchase_order_state="Acknowledged"
)
```

### Get Specific Order

```python
status, data = api.get_purchase_order("PO123456789")
order = data.get("payload", {})

# Access order details
po_number = order.get("purchaseOrderNumber")
order_date = order.get("orderDate")
items = order.get("items", [])
```

### Acknowledge Orders

```python
from spapi_vendor import acknowledge_purchase_order

# Simple acknowledgment
status, data = acknowledge_purchase_order(
    client,
    po_number="PO123456789",
    vendor_code="MYVENDOR",
    items=[{
        "itemSequenceNumber": "1",
        "amazonProductIdentifier": "B00EXAMPLE",
        "orderedQuantity": {"amount": 100, "unitOfMeasure": "Each"},
        "netCost": {"currencyCode": "USD", "amount": "10.00"},
        "acknowledgementStatus": {
            "confirmationStatus": "ACCEPTED",
            "acceptedQuantity": {"amount": 100, "unitOfMeasure": "Each"},
            "scheduledShipDate": "2024-01-20T00:00:00Z",
            "scheduledDeliveryDate": "2024-01-25T00:00:00Z"
        }
    }]
)

# Check transaction result
transaction_id = data.get("payload", {}).get("transactionId")
```

### Check Order Status

```python
# Get status for specific PO
status, data = api.get_purchase_orders_status(
    purchase_order_number="PO123456789"
)

# Get all pending orders
status, data = api.get_purchase_orders_status(
    purchase_order_status="OPEN",
    item_confirmation_status="PENDING"
)
```

## PO Lifecycle States

| State | Description | Next Action |
|-------|-------------|-------------|
| New | Just received | Acknowledge within 24h |
| Acknowledged | Confirmed receipt | Ship when ready |
| Shipped | ASN submitted | Track delivery |
| Received | Amazon received | Invoice |
| Closed | Complete | Archive |

## Acknowledgment Status Codes

| Status | Meaning | Use When |
|--------|---------|----------|
| ACCEPTED | Full acceptance | Can fulfill entire qty |
| PARTIALLY_ACCEPTED | Partial acceptance | Can only fulfill part |
| REJECTED | Cannot fulfill | Out of stock, discontinued |
| BACK_ORDERED | Will ship later | Temporary stock issue |

## Best Practices

### Timing Requirements

1. **Acknowledge within 24 hours** of PO receipt
2. **Ship within the delivery window** specified
3. **Submit ASN** before or at time of shipment
4. **Invoice** after goods are received by Amazon

### Error Prevention

```python
# Always validate PO before acknowledging
def validate_po_items(po_data):
    items = po_data.get("items", [])
    valid_items = []

    for item in items:
        asin = item.get("amazonProductIdentifier")
        qty = item.get("orderedQuantity", {}).get("amount", 0)

        # Check inventory
        if check_inventory(asin, qty):
            valid_items.append({
                **item,
                "acknowledgementStatus": {
                    "confirmationStatus": "ACCEPTED",
                    "acceptedQuantity": item["orderedQuantity"]
                }
            })
        else:
            valid_items.append({
                **item,
                "acknowledgementStatus": {
                    "confirmationStatus": "REJECTED",
                    "rejectionReason": "OutOfStock"
                }
            })

    return valid_items
```

### Pagination

```python
from spapi_client import paginate

# Get all orders across pages
all_orders = paginate(
    client,
    "/vendor/orders/v1/purchaseOrders",
    "vendorOrders",
    params={"createdAfter": "2024-01-01T00:00:00Z"},
    next_token_key="nextToken",
    response_key="orders"
)
```

## Common Workflows

### Daily PO Processing

```python
from datetime import datetime, timedelta, timezone

# 1. Get new orders from last 24 hours
yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
status, data = api.get_purchase_orders(created_after=yesterday)

# 2. Process each order
for order in data.get("payload", {}).get("orders", []):
    po_number = order["purchaseOrderNumber"]

    # 3. Validate inventory and prepare acknowledgment
    items = validate_po_items(order)

    # 4. Submit acknowledgment
    ack_status, ack_data = acknowledge_purchase_order(
        client, po_number, "MYVENDOR", items
    )

    # 5. Log transaction ID for tracking
    txn_id = ack_data.get("payload", {}).get("transactionId")
    print(f"PO {po_number} acknowledged: {txn_id}")
```

### Monitor Changed Orders

```python
# Check for PO modifications
status, data = api.get_purchase_orders(
    changed_after=last_check_time,
    is_po_changed=True
)

for order in data.get("payload", {}).get("orders", []):
    # Handle changes (qty updates, cancellations)
    handle_po_change(order)
```

## Rate Limits

| Operation | Rate | Burst |
|-----------|------|-------|
| getPurchaseOrders | 10/sec | 10 |
| getPurchaseOrder | 10/sec | 10 |
| submitAcknowledgement | 10/sec | 10 |
| getPurchaseOrdersStatus | 10/sec | 10 |

## Error Handling

```python
from spapi_client import SPAPIError

try:
    status, data = api.get_purchase_order(po_number)
except SPAPIError as e:
    if e.error_code == "InvalidInput":
        print(f"Invalid PO number: {po_number}")
    elif e.error_code == "NotFound":
        print(f"PO not found: {po_number}")
    elif e.is_rate_limited():
        print("Rate limited - will retry automatically")
    else:
        print(f"Error: {e.message}")
```

## Related Skills

- `spapi-vendor-shipments` - Submit ASN after acknowledgment
- `spapi-vendor-invoices` - Submit invoice after delivery
- `spapi-reports-feeds` - Generate vendor reports
- `spapi-integration-patterns` - Rate limiting, error handling
