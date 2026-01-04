---
name: spapi-manage
description: Execute Amazon SP-API operations via Python CLI for Vendor (1P) workflows
---

# Amazon SP-API Management Guide

This guide covers using the SP-API CLI for vendor operations including purchase orders, shipments, invoices, catalog, and reports.

## Quick Reference

### Vendor Operations (Priority Commands)

```bash
cd plugins/amazon-spapi/scripts

# Purchase Orders
python3 spapi_api.py vendor-orders list --created-after 2024-01-01
python3 spapi_api.py vendor-orders get PO123456789
python3 spapi_api.py vendor-orders acknowledge --file ack.json
python3 spapi_api.py vendor-orders status --po-number PO123456789

# Shipments (ASN)
python3 spapi_api.py vendor-shipments submit --file asn.json
python3 spapi_api.py vendor-shipments list --created-after 2024-01-01
python3 spapi_api.py vendor-shipments labels --po-number PO123456789

# Invoices
python3 spapi_api.py vendor-invoices submit --file invoice.json
```

### Catalog & Listings

```bash
# Search catalog
python3 spapi_api.py catalog search --keywords "widget" --marketplace US

# Get item details
python3 spapi_api.py catalog get --asin B00EXAMPLE

# Listings
python3 spapi_api.py listings get --sku MY-SKU-123
python3 spapi_api.py listings put --sku NEW-SKU --file listing.json
```

### Reports

```bash
# Create report request
python3 spapi_api.py reports create --type GET_VENDOR_INVENTORY_REPORT

# List reports
python3 spapi_api.py reports list --status DONE

# Download report
python3 spapi_api.py reports download --id report-123 --output inventory.json
```

## Command Structure

```
python3 spapi_api.py <resource> <action> [options]
```

### Global Options

| Option | Description |
|--------|-------------|
| `--profile, -p` | Profile to use (default: from config) |
| `--marketplace, -m` | Override marketplace (e.g., US, UK, DE) |
| `--format, -f` | Output format: table, json, csv |
| `--output, -o` | Write output to file |
| `--quiet, -q` | Suppress non-essential output |
| `--verbose, -v` | Enable verbose logging |

## Vendor Orders API

### List Purchase Orders

```bash
# Recent orders
python3 spapi_api.py vendor-orders list --created-after 2024-01-01

# With filters
python3 spapi_api.py vendor-orders list \
  --created-after 2024-01-01 \
  --created-before 2024-01-31 \
  --status Acknowledged \
  --limit 50

# Changed orders only
python3 spapi_api.py vendor-orders list \
  --changed-after 2024-01-15 \
  --is-changed true
```

### Get Specific Order

```bash
python3 spapi_api.py vendor-orders get PO123456789
python3 spapi_api.py vendor-orders get PO123456789 --format json > order.json
```

### Acknowledge Orders

Create acknowledgment file (`ack.json`):

```json
{
  "acknowledgements": [{
    "purchaseOrderNumber": "PO123456789",
    "sellingParty": {
      "partyId": "VENDOR_CODE"
    },
    "acknowledgementDate": "2024-01-15T10:00:00Z",
    "items": [{
      "itemSequenceNumber": "1",
      "amazonProductIdentifier": "B00EXAMPLE",
      "vendorProductIdentifier": "SKU-123",
      "orderedQuantity": {
        "amount": 100,
        "unitOfMeasure": "Each"
      },
      "netCost": {
        "currencyCode": "USD",
        "amount": "10.00"
      },
      "acknowledgementStatus": {
        "confirmationStatus": "ACCEPTED",
        "acceptedQuantity": {
          "amount": 100,
          "unitOfMeasure": "Each"
        },
        "scheduledShipDate": "2024-01-20T00:00:00Z",
        "scheduledDeliveryDate": "2024-01-25T00:00:00Z"
      }
    }]
  }]
}
```

Submit:

```bash
python3 spapi_api.py vendor-orders acknowledge --file ack.json
```

### Check Order Status

```bash
python3 spapi_api.py vendor-orders status --po-number PO123456789
python3 spapi_api.py vendor-orders status --updated-after 2024-01-01
```

## Vendor Shipments API

### Submit ASN (Advance Ship Notice)

Create ASN file (`asn.json`):

```json
{
  "shipmentConfirmations": [{
    "purchaseOrderNumber": "PO123456789",
    "shipmentIdentifier": "SHIP-001",
    "shipmentConfirmationType": "Original",
    "shipmentType": "TruckLoad",
    "shipmentStructure": "PalletizedAssortmentCase",
    "transportationDetails": {
      "carrierScac": "UPSN",
      "carrierShipmentReferenceNumber": "1Z999AA10123456784",
      "transportationMode": "Road",
      "billOfLadingNumber": "BOL123456"
    },
    "shipFromParty": {
      "partyId": "WAREHOUSE_CODE",
      "address": {
        "name": "Vendor Warehouse",
        "addressLine1": "123 Shipping Lane",
        "city": "Los Angeles",
        "stateOrRegion": "CA",
        "postalCode": "90001",
        "countryCode": "US"
      }
    },
    "shipToParty": {
      "partyId": "AMAZON_FC_CODE"
    },
    "shipmentConfirmationDate": "2024-01-20T10:00:00Z",
    "shippedDate": "2024-01-20T08:00:00Z",
    "estimatedDeliveryDate": "2024-01-25T00:00:00Z",
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
        "expiry": "2025-12-31T00:00:00Z"
      }
    }]
  }]
}
```

Submit:

```bash
python3 spapi_api.py vendor-shipments submit --file asn.json
```

### Get Shipping Labels

```bash
python3 spapi_api.py vendor-shipments labels --po-number PO123456789
python3 spapi_api.py vendor-shipments labels --po-number PO123456789 --output labels.pdf
```

### List Shipments

```bash
python3 spapi_api.py vendor-shipments list --created-after 2024-01-01
python3 spapi_api.py vendor-shipments list --status Shipped
```

## Vendor Invoices API

### Submit Invoice

Create invoice file (`invoice.json`):

```json
{
  "invoices": [{
    "invoiceType": "Invoice",
    "id": "INV-2024-001",
    "referenceNumber": "PO123456789",
    "date": "2024-01-25T00:00:00Z",
    "remitToParty": {
      "partyId": "VENDOR_CODE",
      "address": {
        "name": "Vendor Inc",
        "addressLine1": "456 Business Ave",
        "city": "Dallas",
        "stateOrRegion": "TX",
        "postalCode": "75001",
        "countryCode": "US"
      }
    },
    "shipToParty": {
      "partyId": "AMAZON_FC_CODE"
    },
    "billToParty": {
      "partyId": "AMAZON_BILLING"
    },
    "invoiceTotal": {
      "currencyCode": "USD",
      "amount": "1000.00"
    },
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
        "amount": "10.00"
      }
    }]
  }]
}
```

Submit:

```bash
python3 spapi_api.py vendor-invoices submit --file invoice.json
```

## Reports API

### Available Vendor Report Types

| Report Type | Description |
|-------------|-------------|
| GET_VENDOR_INVENTORY_REPORT | Current inventory levels |
| GET_VENDOR_SALES_REPORT | Sales data |
| GET_VENDOR_TRAFFIC_REPORT | Traffic and conversion data |
| GET_VENDOR_FORECASTING_REPORT | Demand forecasting |
| GET_VENDOR_REAL_TIME_INVENTORY_REPORT | Real-time inventory |

### Create Report

```bash
# Inventory report
python3 spapi_api.py reports create \
  --type GET_VENDOR_INVENTORY_REPORT \
  --start-date 2024-01-01 \
  --end-date 2024-01-31

# Sales report
python3 spapi_api.py reports create \
  --type GET_VENDOR_SALES_REPORT \
  --start-date 2024-01-01
```

### Check Report Status

```bash
python3 spapi_api.py reports get --id report-123
python3 spapi_api.py reports list --type GET_VENDOR_INVENTORY_REPORT --status DONE
```

### Download Report

```bash
python3 spapi_api.py reports download --id report-123 --output report.json
```

## Output Formats

### Table Format (default)

```bash
python3 spapi_api.py vendor-orders list --format table
```

### JSON Format

```bash
python3 spapi_api.py vendor-orders list --format json
python3 spapi_api.py vendor-orders get PO123 --format json > order.json
```

### CSV Format

```bash
python3 spapi_api.py vendor-orders list --format csv > orders.csv
```

## Profile Switching

### Use Different Profile

```bash
# Use UK profile
python3 spapi_api.py --profile uk_production vendor-orders list

# Use sandbox for testing
python3 spapi_api.py --profile sandbox vendor-orders list
```

### Override Marketplace

```bash
# Query German marketplace with EU profile
python3 spapi_api.py --profile eu_production --marketplace DE vendor-orders list
```

## Error Handling

### Rate Limiting

The CLI automatically handles rate limiting with exponential backoff:

- Waits when approaching limits
- Retries on 429 errors
- Reports wait times in verbose mode

### Common Errors

| Error | Meaning | Action |
|-------|---------|--------|
| 401 | Auth failed | Check credentials, re-authorize |
| 403 | No permission | Add required API scope |
| 404 | Not found | Check resource ID |
| 429 | Rate limited | Auto-retry (wait) |
| 500+ | Server error | Auto-retry |

### Debug Mode

```bash
python3 spapi_api.py --verbose vendor-orders list
```

## Workflow Examples

### Complete PO Lifecycle

```bash
# 1. Get new purchase orders
python3 spapi_api.py vendor-orders list --created-after $(date -d "yesterday" +%Y-%m-%d)

# 2. Acknowledge orders
python3 spapi_api.py vendor-orders acknowledge --file acknowledgments.json

# 3. Submit ASN when shipping
python3 spapi_api.py vendor-shipments submit --file asn.json

# 4. Submit invoice after delivery
python3 spapi_api.py vendor-invoices submit --file invoice.json

# 5. Check transaction status
python3 spapi_api.py vendor-transactions status --id txn-123
```

### Daily Operations Script

```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)

# Get today's new orders
python3 spapi_api.py vendor-orders list \
  --created-after $DATE \
  --format json > new_orders_$DATE.json

# Get pending shipments
python3 spapi_api.py vendor-orders status \
  --status Acknowledged \
  --format json > pending_shipments_$DATE.json

# Generate inventory report
python3 spapi_api.py reports create \
  --type GET_VENDOR_INVENTORY_REPORT
```

## Tips & Best Practices

1. **Start with Sandbox**: Test all operations in sandbox before production
2. **Batch Operations**: Use JSON files for bulk submissions
3. **Monitor Rate Limits**: Use `--verbose` to see rate limit warnings
4. **Cache Results**: Save JSON output for offline analysis
5. **Automate Daily Checks**: Script routine operations
6. **Version Control**: Keep JSON templates in git (without credentials)

## Related Skills

- `spapi-vendor-orders` - Detailed PO management patterns
- `spapi-vendor-shipments` - ASN and label workflows
- `spapi-vendor-invoices` - Invoice submission patterns
- `spapi-reports-feeds` - Report generation and feeds
- `spapi-integration-patterns` - Rate limiting, error handling
