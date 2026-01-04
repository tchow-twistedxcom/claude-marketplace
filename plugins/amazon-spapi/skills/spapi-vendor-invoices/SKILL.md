---
name: spapi-vendor-invoices
description: "Submit and manage Amazon Vendor invoices. Use when creating invoices, credit memos, or managing vendor billing for 1P vendor operations."
license: MIT
version: 1.0.0
---

# Amazon SP-API Vendor Invoices

This skill provides guidance for submitting vendor invoices to Amazon through the Selling Partner API.

## When to Use This Skill

Activate this skill when working with:
- Invoice submission to Amazon
- Credit memo/debit memo creation
- Vendor billing automation
- Invoice reconciliation workflows

## Core Operations

### Submit Invoice

```python
from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient
from spapi_vendor import VendorInvoicesAPI, submit_invoice

auth = SPAPIAuth()
client = SPAPIClient(auth)
api = VendorInvoicesAPI(client)

# Using helper function
status, data = submit_invoice(
    client,
    invoice_id="INV-2024-001",
    po_number="PO123456789",
    vendor_code="MYVENDOR",
    vendor_address={
        "name": "Vendor Inc",
        "addressLine1": "456 Business Ave",
        "city": "Dallas",
        "stateOrRegion": "TX",
        "postalCode": "75001",
        "countryCode": "US"
    },
    amazon_fc="PHX7",
    amazon_billing="AMAZON_BILLING",
    items=[{
        "itemSequenceNumber": 1,
        "amazonProductIdentifier": "B00EXAMPLE",
        "invoicedQuantity": {"amount": 100, "unitOfMeasure": "Each"},
        "netCost": {"currencyCode": "USD", "amount": "10.00"}
    }],
    total_amount="1000.00",
    currency="USD"
)

transaction_id = data.get("payload", {}).get("transactionId")
```

### Full Invoice Structure

```python
invoice = {
    "invoiceType": "Invoice",  # Invoice or CreditNote
    "id": "INV-2024-001",  # Your unique invoice ID
    "referenceNumber": "PO123456789",  # Related PO
    "date": "2024-01-25T00:00:00Z",  # Invoice date

    # Vendor receiving payment
    "remitToParty": {
        "partyId": "MYVENDOR",
        "address": {
            "name": "Vendor Inc",
            "addressLine1": "456 Business Ave",
            "addressLine2": "Suite 200",
            "city": "Dallas",
            "stateOrRegion": "TX",
            "postalCode": "75001",
            "countryCode": "US"
        },
        "taxRegistrationDetails": [{
            "taxRegistrationType": "VAT",
            "taxRegistrationNumber": "123456789"
        }]
    },

    # Amazon facility that received goods
    "shipToParty": {
        "partyId": "PHX7"
    },

    # Amazon billing entity
    "billToParty": {
        "partyId": "AMAZON_BILLING",
        "address": {
            "name": "Amazon.com Services LLC",
            "addressLine1": "410 Terry Ave N",
            "city": "Seattle",
            "stateOrRegion": "WA",
            "postalCode": "98109",
            "countryCode": "US"
        }
    },

    # Payment terms
    "paymentTerms": {
        "type": "Net",
        "netDueDays": 30,
        "discountDueDays": 10,
        "discountPercent": "2.00"  # 2% early payment discount
    },

    # Invoice total
    "invoiceTotal": {
        "currencyCode": "USD",
        "amount": "1050.00"  # Including tax
    },

    # Tax details
    "taxDetails": [{
        "taxType": "CGST",
        "taxRate": "5.00",
        "taxAmount": {
            "currencyCode": "USD",
            "amount": "50.00"
        },
        "taxableAmount": {
            "currencyCode": "USD",
            "amount": "1000.00"
        }
    }],

    # Line items
    "items": [{
        "itemSequenceNumber": 1,
        "amazonProductIdentifier": "B00EXAMPLE",
        "vendorProductIdentifier": "SKU-123",
        "invoicedQuantity": {
            "amount": 100,
            "unitOfMeasure": "Each"
        },
        "netCost": {
            "currencyCode": "USD",
            "amount": "10.00"  # Unit price
        },
        "purchaseOrderNumber": "PO123456789",
        "hsnCode": "12345678",  # Harmonized System code
        "creditNoteDetails": None,  # For CreditNote type
        "taxDetails": [{
            "taxType": "CGST",
            "taxRate": "5.00",
            "taxAmount": {
                "currencyCode": "USD",
                "amount": "50.00"
            },
            "taxableAmount": {
                "currencyCode": "USD",
                "amount": "1000.00"
            }
        }]
    }],

    # Additional charges (freight, handling, etc.)
    "additionalDetails": [{
        "type": "Freight",
        "description": "Shipping charges",
        "amount": {
            "currencyCode": "USD",
            "amount": "25.00"
        }
    }],

    # Allowances (discounts)
    "allowanceDetails": [{
        "type": "Discount",
        "description": "Volume discount",
        "amount": {
            "currencyCode": "USD",
            "amount": "25.00"
        }
    }]
}

status, data = api.submit_invoices([invoice])
```

### Submit Credit Note

```python
credit_note = {
    "invoiceType": "CreditNote",
    "id": "CN-2024-001",
    "referenceNumber": "INV-2024-001",  # Original invoice reference
    "date": "2024-02-01T00:00:00Z",

    "remitToParty": {
        "partyId": "MYVENDOR",
        "address": vendor_address
    },
    "shipToParty": {"partyId": "PHX7"},
    "billToParty": {"partyId": "AMAZON_BILLING"},

    "invoiceTotal": {
        "currencyCode": "USD",
        "amount": "-100.00"  # Negative for credit
    },

    "items": [{
        "itemSequenceNumber": 1,
        "amazonProductIdentifier": "B00EXAMPLE",
        "invoicedQuantity": {
            "amount": -10,  # Negative quantity
            "unitOfMeasure": "Each"
        },
        "netCost": {"currencyCode": "USD", "amount": "10.00"},
        "creditNoteDetails": {
            "referenceInvoiceNumber": "INV-2024-001",
            "debitNoteNumber": None,
            "returnsReferenceNumber": "RET-2024-001",
            "coopReferenceNumber": None
        }
    }]
}

status, data = api.submit_invoices([credit_note])
```

## Invoice Types

| Type | Description | Use Case |
|------|-------------|----------|
| Invoice | Standard invoice | Normal billing |
| CreditNote | Credit memo | Returns, adjustments |

## Payment Terms

| Type | Description |
|------|-------------|
| Net | Payment due in X days |
| Basic | Basic payment terms |
| EndOfMonth | Due at end of month |
| FixedDate | Due on specific date |

## Tax Types

| Tax Type | Region |
|----------|--------|
| CGST | India - Central GST |
| SGST | India - State GST |
| CESS | India - Cess |
| UTGST | India - Union Territory GST |
| MwSt | Germany - VAT |
| GST | Australia, Canada |
| VAT | EU countries |
| HST | Canada |
| PST | Canada |

## Best Practices

### Invoice Timing

1. **Submit after delivery confirmation** - Wait until Amazon receives goods
2. **Match PO quantities** - Invoice only what was actually shipped and received
3. **Use correct dates** - Invoice date should be shipment/delivery date
4. **Unique invoice IDs** - Never reuse invoice numbers

### Validation Before Submission

```python
def validate_invoice(invoice_data, po_data):
    errors = []

    # Required fields
    required = ["invoiceType", "id", "referenceNumber", "date",
                "remitToParty", "billToParty", "invoiceTotal", "items"]
    for field in required:
        if field not in invoice_data:
            errors.append(f"Missing required field: {field}")

    # Validate items against PO
    po_items = {item["amazonProductIdentifier"]: item
                for item in po_data.get("items", [])}

    invoice_total = 0
    for item in invoice_data.get("items", []):
        asin = item.get("amazonProductIdentifier")
        inv_qty = item.get("invoicedQuantity", {}).get("amount", 0)
        unit_price = float(item.get("netCost", {}).get("amount", 0))

        # Check ASIN exists in PO
        if asin not in po_items:
            errors.append(f"ASIN {asin} not in PO")
            continue

        # Check quantity doesn't exceed PO
        po_qty = po_items[asin].get("orderedQuantity", {}).get("amount", 0)
        if inv_qty > po_qty:
            errors.append(f"Invoice qty {inv_qty} exceeds PO qty {po_qty} for {asin}")

        invoice_total += inv_qty * unit_price

    # Validate total matches items
    stated_total = float(invoice_data.get("invoiceTotal", {}).get("amount", 0))
    if abs(invoice_total - stated_total) > 0.01:
        errors.append(f"Invoice total {stated_total} doesn't match item sum {invoice_total}")

    return errors
```

### Handle Multiple POs in One Invoice

```python
# Consolidate multiple POs into single invoice
consolidated_invoice = {
    "invoiceType": "Invoice",
    "id": "INV-2024-CONSOLIDATED-001",
    "referenceNumber": "MULTIPLE",  # Indicate consolidated
    "date": "2024-01-31T00:00:00Z",

    "remitToParty": vendor_party,
    "billToParty": amazon_billing,
    "shipToParty": {"partyId": "PHX7"},

    "invoiceTotal": {
        "currencyCode": "USD",
        "amount": str(total_all_pos)
    },

    "items": []
}

# Add items from each PO
item_seq = 1
for po_number, po_items in po_data_dict.items():
    for item in po_items:
        consolidated_invoice["items"].append({
            "itemSequenceNumber": item_seq,
            "amazonProductIdentifier": item["asin"],
            "invoicedQuantity": item["quantity"],
            "netCost": item["price"],
            "purchaseOrderNumber": po_number  # Track original PO
        })
        item_seq += 1
```

## Rate Limits

| Operation | Rate | Burst |
|-----------|------|-------|
| submitInvoices | 10/sec | 10 |

## Error Handling

```python
from spapi_client import SPAPIError

try:
    status, data = api.submit_invoices([invoice])
except SPAPIError as e:
    if e.error_code == "InvalidInput":
        print(f"Invalid invoice data: {e.details}")
    elif e.error_code == "DuplicateInvoice":
        print(f"Invoice {invoice['id']} already submitted")
    elif e.error_code == "InvoiceAmountMismatch":
        print("Invoice total doesn't match line items")
    else:
        print(f"Error: {e.message}")
```

## Complete Workflow

```python
from datetime import datetime, timezone
from spapi_vendor import (
    VendorOrdersAPI, VendorShipmentsAPI,
    VendorInvoicesAPI, VendorTransactionStatusAPI
)

def complete_po_lifecycle(client, po_number):
    """Process PO from receipt to invoice."""

    orders_api = VendorOrdersAPI(client)
    invoices_api = VendorInvoicesAPI(client)
    txn_api = VendorTransactionStatusAPI(client)

    # 1. Get PO details
    status, po_data = orders_api.get_purchase_order(po_number)
    po = po_data.get("payload", {})

    # 2. Verify shipment was received (check order status)
    status, status_data = orders_api.get_purchase_orders_status(
        purchase_order_number=po_number
    )

    order_status = status_data.get("payload", {}).get("ordersStatus", [{}])[0]
    if order_status.get("purchaseOrderStatus") != "RECEIVED":
        print("Order not yet received by Amazon")
        return None

    # 3. Calculate invoice
    items = []
    total = 0.0
    for idx, item in enumerate(po.get("items", []), 1):
        qty = item["orderedQuantity"]["amount"]
        price = float(item["netCost"]["amount"])

        items.append({
            "itemSequenceNumber": idx,
            "amazonProductIdentifier": item["amazonProductIdentifier"],
            "invoicedQuantity": {
                "amount": qty,
                "unitOfMeasure": "Each"
            },
            "netCost": {
                "currencyCode": "USD",
                "amount": str(price)
            }
        })
        total += qty * price

    # 4. Create and submit invoice
    invoice = {
        "invoiceType": "Invoice",
        "id": f"INV-{po_number}",
        "referenceNumber": po_number,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z"),
        "remitToParty": {
            "partyId": "MYVENDOR",
            "address": vendor_address
        },
        "shipToParty": {"partyId": po["shipToParty"]["partyId"]},
        "billToParty": {"partyId": "AMAZON_BILLING"},
        "invoiceTotal": {
            "currencyCode": "USD",
            "amount": f"{total:.2f}"
        },
        "items": items
    }

    status, result = invoices_api.submit_invoices([invoice])
    txn_id = result.get("payload", {}).get("transactionId")

    # 5. Verify submission
    time.sleep(2)  # Wait for processing
    status, txn_status = txn_api.get_transaction(txn_id)

    return txn_status

# Run workflow
result = complete_po_lifecycle(client, "PO123456789")
print(f"Invoice status: {result}")
```

## Related Skills

- `spapi-vendor-orders` - Get PO details for invoicing
- `spapi-vendor-shipments` - Verify shipment before invoicing
- `spapi-integration-patterns` - Error handling patterns
