# Amazon Selling Partner API Reference

Comprehensive reference for the Amazon SP-API architecture, authentication, and operations.

## Overview

The Selling Partner API (SP-API) is Amazon's REST-based API platform for programmatic access to Amazon seller and vendor operations. It replaces the legacy MWS (Marketplace Web Service) API.

### API Types

| Type | Description | Account Type |
|------|-------------|--------------|
| **Seller APIs** | 3P marketplace sellers | Seller Central |
| **Vendor APIs** | 1P wholesale vendors | Vendor Central |
| **Shared APIs** | Catalog, Reports, Notifications | Both |

---

## Authentication

### Login with Amazon (LWA)

SP-API uses OAuth 2.0 via Login with Amazon (LWA) for authentication.

#### Token Flow
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Refresh Token  │────▶│   LWA Endpoint  │────▶│  Access Token   │
│  (long-lived)   │     │ api.amazon.com  │     │  (1 hour TTL)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

#### LWA Token Request
```http
POST https://api.amazon.com/auth/o2/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&refresh_token=Atzr|xxxxx
&client_id=amzn1.application-oa2-client.xxxxx
&client_secret=xxxxx
```

#### LWA Token Response
```json
{
  "access_token": "Atza|xxxxx",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "Atzr|xxxxx"
}
```

### Restricted Data Tokens (RDT)

For accessing Personally Identifiable Information (PII), you must obtain an RDT.

**When RDT is Required:**
- Buyer shipping address
- Buyer name/email
- Gift messages
- Customization data

#### RDT Request
```http
POST /tokens/2021-03-01/restrictedDataToken
Authorization: Bearer {access_token}

{
  "restrictedResources": [
    {
      "method": "GET",
      "path": "/orders/v0/orders/123-1234567-1234567/address",
      "dataElements": ["shippingAddress"]
    }
  ]
}
```

---

## Regional Endpoints

### Base URLs

| Region | Endpoint | AWS Region |
|--------|----------|------------|
| North America | `sellingpartnerapi-na.amazon.com` | us-east-1 |
| Europe | `sellingpartnerapi-eu.amazon.com` | eu-west-1 |
| Far East | `sellingpartnerapi-fe.amazon.com` | us-west-2 |

### Marketplace IDs

#### North America
| Country | Marketplace ID |
|---------|---------------|
| USA | ATVPDKIKX0DER |
| Canada | A2EUQ1WTGCTBG2 |
| Mexico | A1AM78C64UM0Y8 |
| Brazil | A2Q3Y263D00KWC |

#### Europe
| Country | Marketplace ID |
|---------|---------------|
| UK | A1F83G8C2ARO7P |
| Germany | A1PA6795UKMFR9 |
| France | A13V1IB3VIYZZH |
| Italy | APJ6JRA9NG5V4 |
| Spain | A1RKKUPIHCS9HS |
| Netherlands | A1805IZSGTT6HS |
| Sweden | A2NODRKZP88ZB9 |
| Poland | A1C3SOZRARQ6R3 |
| Turkey | A33AVAJ2PDY3EV |
| UAE | A2VIGQ35RCS4UG |
| India | A21TJRUUN4KGV |

#### Far East
| Country | Marketplace ID |
|---------|---------------|
| Japan | A1VC38T7YXB528 |
| Australia | A39IBJ37TRP1C6 |
| Singapore | A19VAU5U5O7RUS |

---

## API Categories

### Seller APIs

| API | Description | Key Operations |
|-----|-------------|----------------|
| **Orders** | Manage seller orders | getOrders, getOrder, getOrderItems |
| **Listings Items** | CRUD for listings | getListing, putListing, patchListing |
| **FBA Inventory** | FBA stock levels | getInventorySummaries |
| **FBA Inbound** | Shipments to FCs | createShipmentPlan, createShipment |
| **FBA Outbound** | Multi-channel fulfillment | createFulfillmentOrder |
| **Feeds** | Bulk data submission | createFeed, getFeed |
| **Finances** | Financial events | listFinancialEvents |

### Vendor APIs

| API | Description | Key Operations |
|-----|-------------|----------------|
| **Vendor Orders** | Purchase orders | getPurchaseOrders, submitAcknowledgement |
| **Vendor Shipments** | ASN/shipping | submitShipmentConfirmations |
| **Vendor Invoices** | Invoice submission | submitInvoices |
| **Vendor Transaction Status** | Check submissions | getTransaction |

### Shared APIs

| API | Description | Key Operations |
|-----|-------------|----------------|
| **Catalog Items** | Product search | searchCatalogItems, getCatalogItem |
| **Product Type Definitions** | Listing schemas | getDefinitionsProductType |
| **Reports** | Generate reports | createReport, getReport |
| **Notifications** | Event subscriptions | createSubscription |
| **Product Pricing** | Competitive pricing | getCompetitivePricing |

---

## Rate Limiting

SP-API uses a token bucket algorithm for rate limiting.

### Rate Limit Headers
```http
x-amzn-RateLimit-Limit: 0.5        # Requests per second
x-amzn-RequestId: abc123...        # Request tracking ID
```

### Common Rate Limits

| API | Rate (req/sec) | Burst |
|-----|----------------|-------|
| Orders.getOrders | 0.0167 | 20 |
| Orders.getOrder | 0.5 | 30 |
| Catalog.searchItems | 5 | 5 |
| Reports.createReport | 0.0167 | 15 |
| Reports.getReport | 2 | 15 |
| Vendor.getPurchaseOrders | 10 | 10 |

### Handling 429 (Too Many Requests)

```python
# Exponential backoff with jitter
import random
import time

def backoff_retry(attempt):
    base_delay = min(120, 2 ** attempt)  # Max 120 seconds
    jitter = random.uniform(0, base_delay * 0.1)
    return base_delay + jitter
```

---

## Common Operations

### Catalog Search

```http
GET /catalog/2022-04-01/items
  ?keywords=laptop
  &marketplaceIds=ATVPDKIKX0DER
  &includedData=summaries,images,productTypes
```

**Response:**
```json
{
  "items": [
    {
      "asin": "B0EXAMPLE",
      "summaries": [{
        "marketplaceId": "ATVPDKIKX0DER",
        "itemName": "Product Title",
        "brand": "Brand Name"
      }],
      "productTypes": [{
        "productType": "NOTEBOOK_COMPUTER"
      }]
    }
  ]
}
```

### Get Listing with Issues

```http
GET /listings/2021-08-01/items/{sellerId}/{sku}
  ?marketplaceIds=ATVPDKIKX0DER
  &includedData=summaries,attributes,issues,offers
```

**Response with Issues:**
```json
{
  "sku": "MY-SKU-123",
  "summaries": [{
    "marketplaceId": "ATVPDKIKX0DER",
    "asin": "B0EXAMPLE",
    "productType": "NOTEBOOK_COMPUTER",
    "status": ["DISCOVERABLE"]
  }],
  "issues": [
    {
      "code": "MISSING_RECOMMENDED_ATTRIBUTE",
      "message": "bullet_point is recommended",
      "severity": "WARNING",
      "attributeNames": ["bullet_point"]
    }
  ]
}
```

### Update Listing (Patch)

```http
PATCH /listings/2021-08-01/items/{sellerId}/{sku}
  ?marketplaceIds=ATVPDKIKX0DER
Content-Type: application/json

{
  "productType": "NOTEBOOK_COMPUTER",
  "patches": [
    {
      "op": "replace",
      "path": "/attributes/bullet_point",
      "value": [
        {"value": "Feature 1", "marketplace_id": "ATVPDKIKX0DER"},
        {"value": "Feature 2", "marketplace_id": "ATVPDKIKX0DER"}
      ]
    }
  ]
}
```

### Create Report

```http
POST /reports/2021-06-30/reports
Content-Type: application/json

{
  "reportType": "GET_MERCHANT_LISTINGS_ALL_DATA",
  "marketplaceIds": ["ATVPDKIKX0DER"],
  "dataStartTime": "2024-01-01T00:00:00Z",
  "dataEndTime": "2024-01-31T23:59:59Z"
}
```

**Response:**
```json
{
  "reportId": "12345678901"
}
```

### Download Report

```http
GET /reports/2021-06-30/documents/{reportDocumentId}
```

**Response:**
```json
{
  "reportDocumentId": "amzn1.spdoc.1...",
  "url": "https://tortuga-prod-na.s3.amazonaws.com/...",
  "compressionAlgorithm": "GZIP"
}
```

---

## Vendor Operations

### Get Purchase Orders

```http
GET /vendor/orders/v1/purchaseOrders
  ?createdAfter=2024-01-01T00:00:00Z
  &createdBefore=2024-01-31T23:59:59Z
  &limit=100
```

**Response:**
```json
{
  "payload": {
    "orders": [
      {
        "purchaseOrderNumber": "PO123456",
        "purchaseOrderState": "New",
        "orderDetails": {
          "purchaseOrderDate": "2024-01-15T10:00:00Z",
          "purchaseOrderType": "RegularOrder",
          "items": [...]
        }
      }
    ]
  }
}
```

### Submit PO Acknowledgement

```http
POST /vendor/orders/v1/acknowledgements
Content-Type: application/json

{
  "acknowledgements": [
    {
      "purchaseOrderNumber": "PO123456",
      "acknowledgementDate": "2024-01-15T12:00:00Z",
      "items": [
        {
          "itemSequenceNumber": "1",
          "amazonProductIdentifier": "B0EXAMPLE",
          "vendorProductIdentifier": "VENDOR-SKU",
          "orderedQuantity": {"amount": 100, "unitOfMeasure": "Each"},
          "itemAcknowledgements": [
            {
              "acknowledgementCode": "Accepted",
              "acknowledgedQuantity": {"amount": 100, "unitOfMeasure": "Each"}
            }
          ]
        }
      ]
    }
  ]
}
```

### Submit ASN (Shipment Confirmation)

```http
POST /vendor/shipping/v1/shipmentConfirmations
Content-Type: application/json

{
  "shipmentConfirmations": [
    {
      "shipmentIdentifier": "SHIP123",
      "shipmentConfirmationType": "Original",
      "shipmentType": "TruckLoad",
      "shipmentStructure": "PalletizedAssortmentCase",
      "shipmentConfirmationDate": "2024-01-16T10:00:00Z",
      "shippedDate": "2024-01-16T08:00:00Z",
      "estimatedDeliveryDate": "2024-01-18T08:00:00Z",
      "sellingParty": {...},
      "shipFromParty": {...},
      "shipToParty": {...},
      "shipmentMeasurements": {...},
      "transportationDetails": {...},
      "shippedItems": [...]
    }
  ]
}
```

### Submit Invoice

```http
POST /vendor/payments/v1/invoices
Content-Type: application/json

{
  "invoices": [
    {
      "invoiceType": "Invoice",
      "id": "INV-123456",
      "referenceNumber": "PO123456",
      "date": "2024-01-20T00:00:00Z",
      "billToParty": {...},
      "invoiceTotal": {
        "currencyCode": "USD",
        "amount": "1000.00"
      },
      "items": [...]
    }
  ]
}
```

---

## Error Handling

### Error Response Format

```json
{
  "errors": [
    {
      "code": "InvalidInput",
      "message": "Request has missing or invalid parameters",
      "details": "marketplaceIds is required"
    }
  ]
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| InvalidInput | 400 | Invalid request parameters |
| Unauthorized | 401 | Invalid access token |
| Forbidden | 403 | Missing permissions |
| NotFound | 404 | Resource not found |
| QuotaExceeded | 429 | Rate limit exceeded |
| InternalFailure | 500 | Amazon server error |
| ServiceUnavailable | 503 | Temporary unavailability |

### Retryable Errors

- 429 Too Many Requests (with backoff)
- 500 Internal Server Error
- 503 Service Unavailable

---

## Sandbox Testing

### Sandbox Endpoints

Use the same base URLs with sandbox-specific credentials.

### Static Sandbox Data

Amazon provides predefined test data for sandbox:
- Orders: `TEST_CASE_200`, `TEST_CASE_400`
- Reports: `GET_FLAT_FILE_OPEN_LISTINGS_DATA`

### Sandbox Request Headers

```http
x-amzn-marketplace-id: ATVPDKIKX0DER
```

---

## Best Practices

### 1. Token Management
- Cache access tokens (valid for 1 hour)
- Refresh 5 minutes before expiry
- Handle token refresh failures gracefully

### 2. Rate Limiting
- Implement exponential backoff with jitter
- Track rate limit headers
- Use burst capacity strategically

### 3. Error Handling
- Retry transient errors (429, 5xx)
- Log request IDs for debugging
- Implement circuit breakers for persistent failures

### 4. Data Synchronization
- Use notifications for real-time updates
- Use reports for bulk data
- Implement idempotency for mutations

### 5. Security
- Store credentials securely (not in code)
- Use environment-specific profiles
- Rotate refresh tokens periodically

---

## Resources

- [SP-API Developer Documentation](https://developer-docs.amazon.com/sp-api/)
- [API Models (GitHub)](https://github.com/amzn/selling-partner-api-models)
- [SP-API Swagger Definitions](https://github.com/amzn/selling-partner-api-models/tree/main/models)
- [Rate Limits Reference](https://developer-docs.amazon.com/sp-api/docs/usage-plans-and-rate-limits)
- [Seller Central](https://sellercentral.amazon.com)
- [Vendor Central](https://vendorcentral.amazon.com)
