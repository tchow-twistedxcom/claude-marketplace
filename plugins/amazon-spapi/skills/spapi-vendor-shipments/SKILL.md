---
name: spapi-vendor-shipments
description: "Manage Amazon Vendor shipments and ASNs. Use when creating advance ship notices, generating shipping labels, tracking shipment status, or automating vendor fulfillment for 1P operations."
license: MIT
version: 1.0.0
---

# Amazon SP-API Vendor Shipments

This skill provides guidance for managing Amazon Vendor shipments and ASN (Advance Ship Notice) submissions through the Selling Partner API.

## When to Use This Skill

Activate this skill when working with:
- ASN (Advance Ship Notice) creation and submission
- Shipment confirmation workflows
- Transportation label generation
- Shipment status tracking
- Carrier and tracking information

## Core Operations

### Submit ASN (Shipment Confirmation)

```python
from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient
from spapi_vendor import VendorShipmentsAPI, submit_asn

auth = SPAPIAuth()
client = SPAPIClient(auth)
api = VendorShipmentsAPI(client)

# Using helper function
status, data = submit_asn(
    client,
    po_number="PO123456789",
    shipment_id="SHIP-2024-001",
    vendor_code="MYVENDOR",
    ship_from={
        "name": "Vendor Warehouse",
        "addressLine1": "123 Shipping Lane",
        "city": "Los Angeles",
        "stateOrRegion": "CA",
        "postalCode": "90001",
        "countryCode": "US"
    },
    ship_to_fc="PHX7",
    items=[{
        "itemSequenceNumber": "1",
        "amazonProductIdentifier": "B00EXAMPLE",
        "vendorProductIdentifier": "SKU-123",
        "shippedQuantity": {"amount": 100, "unitOfMeasure": "Each"},
        "itemDetails": {
            "purchaseOrderNumber": "PO123456789"
        }
    }],
    carrier_info={
        "carrierScac": "UPSN",
        "carrierShipmentReferenceNumber": "1Z999AA10123456784",
        "transportationMode": "Road",
        "billOfLadingNumber": "BOL123456"
    },
    eta="2024-01-25T00:00:00Z"
)

transaction_id = data.get("payload", {}).get("transactionId")
```

### Full ASN Structure

```python
shipment_confirmation = {
    "purchaseOrderNumber": "PO123456789",
    "shipmentIdentifier": "SHIP-2024-001",
    "shipmentConfirmationType": "Original",  # Original, Replace, Delete
    "shipmentType": "TruckLoad",  # TruckLoad, LessThanTruckLoad, SmallParcel
    "shipmentStructure": "PalletizedAssortmentCase",
    "transportationDetails": {
        "carrierScac": "UPSN",
        "carrierShipmentReferenceNumber": "1Z999AA10123456784",
        "transportationMode": "Road",  # Road, Air, Ocean, Rail
        "billOfLadingNumber": "BOL123456"
    },
    "shipFromParty": {
        "partyId": "MYVENDOR",
        "address": {
            "name": "Vendor Warehouse",
            "addressLine1": "123 Shipping Lane",
            "addressLine2": "Suite 100",
            "city": "Los Angeles",
            "stateOrRegion": "CA",
            "postalCode": "90001",
            "countryCode": "US"
        }
    },
    "shipToParty": {
        "partyId": "PHX7"  # Amazon FC code
    },
    "shipmentConfirmationDate": "2024-01-20T10:00:00Z",
    "shippedDate": "2024-01-20T08:00:00Z",
    "estimatedDeliveryDate": "2024-01-25T00:00:00Z",
    "sellingParty": {
        "partyId": "MYVENDOR"
    },
    "shippedItems": [{
        "itemSequenceNumber": "1",
        "amazonProductIdentifier": "B00EXAMPLE",
        "vendorProductIdentifier": "SKU-123",
        "shippedQuantity": {
            "amount": 100,
            "unitOfMeasure": "Each"
        },
        "itemDetails": {
            "purchaseOrderNumber": "PO123456789",
            "lotNumber": "LOT-2024-001",
            "expiry": "2025-12-31T00:00:00Z",
            "maximumRetailPrice": {
                "currencyCode": "USD",
                "amount": "19.99"
            }
        }
    }],
    "cartons": [{
        "cartonIdentifier": "CARTON-001",
        "cartonSequenceNumber": "1",
        "numberOfCartons": 10,
        "items": [{
            "itemReference": "1",
            "itemQuantity": 10
        }]
    }]
}

status, data = api.submit_shipment_confirmations([shipment_confirmation])
```

### Get Shipment Details

```python
# List shipments with filters
status, data = api.get_shipment_details(
    created_after="2024-01-01T00:00:00Z",
    current_shipment_status="Shipped",
    limit=50
)

# Filter by vendor shipment ID
status, data = api.get_shipment_details(
    vendor_shipment_identifier="SHIP-2024-001"
)

# Filter by Amazon FC
status, data = api.get_shipment_details(
    buyer_warehouse_code="PHX7"
)
```

### Get Transportation Labels

```python
# Get labels for PO
status, data = api.get_shipment_labels(
    purchase_order_number="PO123456789"
)

labels = data.get("payload", {}).get("transportLabels", [])
for label in labels:
    label_format = label.get("labelFormat")  # PDF, PNG, ZPL
    label_data = label.get("labelData")  # Base64 encoded
```

## Shipment Types

| Type | Description | Use Case |
|------|-------------|----------|
| TruckLoad | Full truck | Large shipments |
| LessThanTruckLoad | Partial truck | Medium shipments |
| SmallParcel | Individual boxes | Small shipments |

## Shipment Structures

| Structure | Description |
|-----------|-------------|
| PalletizedAssortmentCase | Mixed items on pallets |
| LoosePallet | Single SKU pallets |
| LooseCase | Individual cases |
| MasterPallet | Master cases on pallets |
| MasterCase | Master case containing inner packs |

## Carrier SCAC Codes

| Carrier | SCAC |
|---------|------|
| UPS | UPSN |
| FedEx | FDEG, FXFE |
| USPS | USPS |
| DHL | DHLC |
| ABF | ABFS |
| YRC | RDWY |
| XPO | CNWY |

## ASN Timing Requirements

1. **Submit ASN** at or before time of shipment
2. **Include tracking** as soon as available
3. **Update ASN** if shipment changes (use Replace type)
4. **Cancel ASN** if shipment canceled (use Delete type)

## Best Practices

### Validate Before Submission

```python
def validate_asn(asn_data):
    errors = []

    # Required fields
    required = ["purchaseOrderNumber", "shipmentIdentifier",
                "shipFromParty", "shipToParty", "shippedItems"]
    for field in required:
        if field not in asn_data:
            errors.append(f"Missing required field: {field}")

    # Validate items
    items = asn_data.get("shippedItems", [])
    if not items:
        errors.append("No items in shipment")

    for item in items:
        if not item.get("amazonProductIdentifier") and not item.get("vendorProductIdentifier"):
            errors.append(f"Item {item.get('itemSequenceNumber')} missing product identifier")

        qty = item.get("shippedQuantity", {}).get("amount", 0)
        if qty <= 0:
            errors.append(f"Item {item.get('itemSequenceNumber')} has invalid quantity")

    return errors
```

### Handle Partial Shipments

```python
# Split shipment for same PO
def create_partial_asn(po_number, items, shipment_num):
    return {
        "purchaseOrderNumber": po_number,
        "shipmentIdentifier": f"SHIP-{po_number}-{shipment_num}",
        "shipmentConfirmationType": "Original",
        # ... rest of shipment details
        "shippedItems": items
    }

# Ship items in multiple shipments
shipment_1 = create_partial_asn(po, items[:50], 1)
shipment_2 = create_partial_asn(po, items[50:], 2)

api.submit_shipment_confirmations([shipment_1])
api.submit_shipment_confirmations([shipment_2])
```

### Update Shipment (Replace)

```python
# Correct tracking number
updated_asn = {
    **original_asn,
    "shipmentConfirmationType": "Replace",  # Changed from Original
    "transportationDetails": {
        **original_asn["transportationDetails"],
        "carrierShipmentReferenceNumber": "CORRECTED_TRACKING"
    }
}

status, data = api.submit_shipment_confirmations([updated_asn])
```

### Cancel Shipment

```python
cancel_asn = {
    "purchaseOrderNumber": "PO123456789",
    "shipmentIdentifier": "SHIP-2024-001",
    "shipmentConfirmationType": "Delete"
}

status, data = api.submit_shipment_confirmations([cancel_asn])
```

## Rate Limits

| Operation | Rate | Burst |
|-----------|------|-------|
| submitShipmentConfirmations | 10/sec | 10 |
| getShipmentDetails | 10/sec | 10 |
| getTransportLabels | 10/sec | 10 |

## Error Handling

```python
from spapi_client import SPAPIError

try:
    status, data = api.submit_shipment_confirmations([asn])
except SPAPIError as e:
    if e.error_code == "InvalidInput":
        print(f"Invalid ASN data: {e.details}")
    elif e.error_code == "DuplicateShipment":
        print("Shipment already submitted - use Replace to update")
    else:
        print(f"Error: {e.message}")
```

## Workflow: PO to ASN

```python
from datetime import datetime, timezone

def process_po_to_shipment(client, po_number, warehouse_inventory):
    """Complete workflow from PO acknowledgment to ASN."""
    from spapi_vendor import VendorOrdersAPI, VendorShipmentsAPI

    orders_api = VendorOrdersAPI(client)
    shipments_api = VendorShipmentsAPI(client)

    # 1. Get PO details
    status, po_data = orders_api.get_purchase_order(po_number)
    po = po_data.get("payload", {})

    # 2. Prepare items for shipment
    shipped_items = []
    for item in po.get("items", []):
        asin = item["amazonProductIdentifier"]
        ordered_qty = item["orderedQuantity"]["amount"]

        # Check warehouse inventory
        available = warehouse_inventory.get(asin, 0)
        ship_qty = min(ordered_qty, available)

        if ship_qty > 0:
            shipped_items.append({
                "itemSequenceNumber": item["itemSequenceNumber"],
                "amazonProductIdentifier": asin,
                "shippedQuantity": {
                    "amount": ship_qty,
                    "unitOfMeasure": "Each"
                }
            })

    # 3. Create and submit ASN
    now = datetime.now(timezone.utc).isoformat()
    asn = {
        "purchaseOrderNumber": po_number,
        "shipmentIdentifier": f"SHIP-{po_number}",
        "shipmentConfirmationType": "Original",
        "shipmentType": "SmallParcel",
        "shipmentStructure": "LooseCase",
        "shipFromParty": {
            "partyId": "MYVENDOR",
            "address": warehouse_address
        },
        "shipToParty": {"partyId": po["shipToParty"]["partyId"]},
        "shipmentConfirmationDate": now,
        "shippedDate": now,
        "shippedItems": shipped_items
    }

    status, result = shipments_api.submit_shipment_confirmations([asn])
    return result
```

## Related Skills

- `spapi-vendor-orders` - Get PO details before shipping
- `spapi-vendor-invoices` - Invoice after delivery
- `spapi-integration-patterns` - Error handling, rate limits
