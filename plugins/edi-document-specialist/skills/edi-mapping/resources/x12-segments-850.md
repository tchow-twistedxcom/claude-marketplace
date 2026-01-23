# X12 850 Purchase Order Segment Reference

## Document Type
- **Transaction Set**: 850 - Purchase Order
- **Purpose**: Place an order for goods or services
- **Direction**: Buyer → Seller

## Beginning Segment (BEG)

The BEG segment contains header-level purchase order information.

| Element | Description | Template Variable | Notes |
|---------|-------------|-------------------|-------|
| BEG01 | Transaction Set Purpose Code | `orderType` | 00=Original, 01=Cancel, 04=Change |
| BEG02 | Purchase Order Type Code | `poTypeCode` | SA=Stand-Alone, DS=Drop Ship |
| BEG03 | Purchase Order Number | `poNumber` | Primary identifier |
| BEG04 | Release Number | - | Optional |
| BEG05 | Order Date | `orderDate` | Format: YYYYMMDD |
| BEG06 | Contract Number | - | Optional |

### BEG01 Purpose Codes
| Code | Description |
|------|-------------|
| 00 | Original |
| 01 | Cancellation |
| 04 | Change |
| 05 | Replace |

### BEG02 PO Type Codes
| Code | Description |
|------|-------------|
| BK | Blanket Order |
| DS | Drop Ship |
| NE | New Order |
| RE | Re-Order |
| RL | Release |
| SA | Stand-Alone Order |

## Reference Identification (REF)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| REF01 | Reference ID Qualifier | - |
| REF02 | Reference Identification | Varies by qualifier |

### Common REF01 Qualifiers
| Code | Description | Usage |
|------|-------------|-------|
| DP | Department Number | `departmentNumber` |
| IA | Internal Vendor Number | `vendorId` |
| PD | Promotion/Deal Number | `promotionNumber` |

## Administrative Communications (PER)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| PER01 | Contact Function Code | - |
| PER02 | Name | `contact.name` |
| PER03 | Communication Number Qualifier | - |
| PER04 | Communication Number | `contact.phone` or `contact.email` |

## Requested Ship/Delivery Date (DTM)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| DTM01 | Date/Time Qualifier | - |
| DTM02 | Date | Varies by qualifier |

### DTM01 Qualifiers
| Code | Description | Template Variable |
|------|-------------|-------------------|
| 002 | Delivery Requested | `requestedDeliveryDate` |
| 010 | Requested Ship Date | `requestedShipDate` |
| 037 | Ship Not Before | `shipNotBefore` |
| 038 | Ship Not After | `shipNotAfter` |
| 063 | Do Not Deliver After | `cancelDate` |

## Name Loop (N1)

Same structure as 810. Common qualifiers for 850:

| Qualifier | Description | Template Path |
|-----------|-------------|---------------|
| BT | Bill To | `partners[type='BILL TO']` |
| ST | Ship To | `partners[type='SHIP TO']` |
| BY | Buying Party | `partners[type='BUYER']` |
| VN | Vendor | `partners[type='VENDOR']` |

## Line Item Loop (PO1)

The PO1 loop contains line item details for purchase orders.

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| PO101 | Assigned Identification | `orderDetails[].lineNumber` |
| PO102 | Quantity Ordered | `orderDetails[].quantity` |
| PO103 | Unit of Measure | `orderDetails[].uom` |
| PO104 | Unit Price | `orderDetails[].unitPrice` |
| PO105 | Basis of Unit Price | - |
| PO106 | Product/Service ID Qualifier | - |
| PO107 | Product/Service ID | `orderDetails[].itemNumber` |
| PO108-PO125 | Additional Product IDs | - |

### Common Unit of Measure Codes (PO103)
| Code | Description |
|------|-------------|
| CA | Case |
| EA | Each |
| PR | Pair |
| DZ | Dozen |
| CT | Carton |

## Product Description (PID)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| PID01 | Item Description Type | - |
| PID05 | Description | `orderDetails[].description` |

## Summary (CTT)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| CTT01 | Number of Line Items | `orderSummary.totalLines` |
| CTT02 | Hash Total | - |

## Amount Summary (AMT)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| AMT01 | Amount Qualifier Code | - |
| AMT02 | Monetary Amount | `orderSummary.totalAmount` |

## Data Extractor Output Structure

```javascript
{
  documentType: '850',
  partnerName: 'Rocky Brands',
  poNumber: 'PO987654',
  orderDate: '01/10/2026',
  orderType: 'Original Order',
  orderSummary: {
    totalLines: 15,
    totalQuantity: 250,
    totalAmount: '$12,500.00',
    requestedShipDate: '01/25/2026',
    cancelDate: '02/15/2026'
  },
  partners: [
    {
      type: 'BUYER',
      name: 'Rocky Brands Inc',
      address: '123 Main Street',
      city: 'Nelsonville',
      state: 'OH',
      zip: '45764'
    },
    {
      type: 'SHIP TO',
      name: 'Rocky Distribution Center',
      address: '456 Warehouse Blvd',
      city: 'Logan',
      state: 'OH',
      zip: '43138'
    }
  ],
  orderDetails: [
    {
      lineNumber: '1',
      itemNumber: 'SKU-12345',
      description: 'Western Boot - Size 10',
      quantity: 12,
      uom: 'PR',
      unitPrice: '$89.99',
      totalPrice: '$1,079.88'
    }
  ],
  technicalDetails: {
    controlNumber: '000012345',
    testIndicator: 'P'
  }
}
```

## Template Variable Quick Reference

| EDI Element | Description | Template Variable |
|-------------|-------------|-------------------|
| BEG03 | PO Number | `${OVERRIDE.EDI.poNumber}` |
| BEG05 | Order Date | `${OVERRIDE.EDI.orderDate}` |
| DTM02 (002) | Requested Delivery | `${OVERRIDE.EDI.orderSummary.requestedShipDate}` |
| N102 (ST) | Ship To Name | `${partner.name}` (in loop) |
| PO102 | Quantity | `${line.quantity}` (in loop) |
| PO104 | Unit Price | `${line.unitPrice}` (in loop) |
| CTT01 | Total Lines | `${OVERRIDE.EDI.orderSummary.totalLines}` |
