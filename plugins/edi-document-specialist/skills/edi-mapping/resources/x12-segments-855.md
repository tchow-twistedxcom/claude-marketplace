# X12 855 Purchase Order Acknowledgment Segment Reference

## Document Type
- **Transaction Set**: 855 - Purchase Order Acknowledgment
- **Purpose**: Confirm receipt and acceptance of purchase order
- **Direction**: Seller → Buyer

## Beginning Segment (BAK)

The BAK segment contains header-level acknowledgment information.

| Element | Description | Template Variable | Notes |
|---------|-------------|-------------------|-------|
| BAK01 | Transaction Set Purpose Code | `ackType` | 00=Original, 01=Cancel, 04=Change |
| BAK02 | Acknowledgment Type | `ackStatus` | AC=Acknowledged, AD=Rejected, etc. |
| BAK03 | Purchase Order Number | `poNumber` | From original PO |
| BAK04 | Acknowledgment Date | `ackDate` | Format: YYYYMMDD |
| BAK05 | Release Number | - | Optional |
| BAK06 | Request Reference Number | - | Optional |
| BAK07 | Contract Number | - | Optional |
| BAK08 | Reference Identification | `sellerOrderNumber` | Seller's order number |

### BAK02 Acknowledgment Types
| Code | Description | Template Variable Value |
|------|-------------|------------------------|
| AC | Acknowledge - With Detail and Change | 'Acknowledged with Changes' |
| AD | Acknowledge - With Detail, No Change | 'Acknowledged' |
| AE | Acknowledge - With Exception Detail Only | 'Acknowledged with Exceptions' |
| AK | Acknowledge - No Detail or Change | 'Acknowledged' |
| AP | Accepted | 'Accepted' |
| AT | Accepted, But 855 Contains Changes | 'Accepted with Changes' |
| RD | Rejected with Detail | 'Rejected' |
| RF | Rejected, First Submittal | 'Rejected' |
| RJ | Rejected - No Detail | 'Rejected' |
| RO | Rejected with Counter Offer | 'Rejected - Counter Offer' |

## Date/Time Reference (DTM)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| DTM01 | Date/Time Qualifier | - |
| DTM02 | Date | Varies by qualifier |

### DTM01 Qualifiers for 855
| Code | Description | Template Variable |
|------|-------------|-------------------|
| 002 | Delivery Requested | `requestedDeliveryDate` |
| 010 | Requested Ship Date | `requestedShipDate` |
| 017 | Estimated Delivery | `estimatedDeliveryDate` |
| 068 | Current Schedule Ship | `scheduledShipDate` |

## Name Loop (N1)

Same structure as 810/850. Common qualifiers for 855:

| Qualifier | Description | Template Path |
|-----------|-------------|---------------|
| BT | Bill To | `partners[type='BILL TO']` |
| ST | Ship To | `partners[type='SHIP TO']` |
| SE | Selling Party | `partners[type='SELLER']` |

## Line Item Acknowledgment (ACK)

The ACK segment provides line-level acknowledgment status.

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| ACK01 | Line Item Status Code | `ackDetails[].status` |
| ACK02 | Quantity | `ackDetails[].quantity` |
| ACK03 | Unit of Measure | `ackDetails[].uom` |
| ACK04 | Date/Time Qualifier | - |
| ACK05 | Date | `ackDetails[].promiseDate` |

### ACK01 Line Status Codes
| Code | Description | Template Display |
|------|-------------|-----------------|
| IA | Item Accepted | 'Accepted' |
| IB | Item Backordered | 'Backordered' |
| IC | Item Accepted - Changes Made | 'Accepted with Changes' |
| ID | Item Deleted | 'Deleted' |
| IF | Item On Hold | 'On Hold' |
| IP | Item Accepted - Price Pending | 'Price Pending' |
| IQ | Item Accepted - Qty Changed | 'Quantity Changed' |
| IR | Item Rejected | 'Rejected' |
| IS | Item Accepted - Substitution Made | 'Substituted' |

## Line Item Loop (PO1)

Same structure as 850 PO1 segment.

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| PO101 | Line Number | `ackDetails[].lineNumber` |
| PO102 | Quantity | `ackDetails[].orderedQuantity` |
| PO103 | Unit of Measure | `ackDetails[].uom` |
| PO104 | Unit Price | `ackDetails[].unitPrice` |
| PO107 | Product ID | `ackDetails[].itemNumber` |

## Summary (CTT)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| CTT01 | Number of Line Items | `ackSummary.totalLines` |

## Data Extractor Output Structure

```javascript
{
  documentType: '855',
  partnerName: 'Rocky Brands',
  poNumber: 'PO987654',
  ackDate: '01/11/2026',
  ackType: 'Original',
  ackStatus: 'Acknowledged',
  sellerOrderNumber: 'SO123456',
  ackSummary: {
    totalLines: 15,
    acceptedLines: 14,
    rejectedLines: 0,
    backorderedLines: 1,
    estimatedShipDate: '01/20/2026'
  },
  partners: [
    {
      type: 'SELLER',
      name: 'Twisted X',
      address: '2800 S. Business Hwy 281',
      city: 'Edinburg',
      state: 'TX',
      zip: '78539'
    }
  ],
  ackDetails: [
    {
      lineNumber: '1',
      itemNumber: 'SKU-12345',
      description: 'Western Boot - Size 10',
      orderedQuantity: 12,
      acknowledgedQuantity: 12,
      status: 'Accepted',
      unitPrice: '$89.99',
      promiseDate: '01/20/2026'
    },
    {
      lineNumber: '15',
      itemNumber: 'SKU-67890',
      description: 'Work Boot - Size 11',
      orderedQuantity: 6,
      acknowledgedQuantity: 0,
      status: 'Backordered',
      unitPrice: '$129.99',
      promiseDate: '02/01/2026'
    }
  ],
  technicalDetails: {
    controlNumber: '000012346',
    testIndicator: 'P'
  }
}
```

## Template Variable Quick Reference

| EDI Element | Description | Template Variable |
|-------------|-------------|-------------------|
| BAK02 | Ack Status | `${OVERRIDE.EDI.ackStatus}` |
| BAK03 | PO Number | `${OVERRIDE.EDI.poNumber}` |
| BAK04 | Ack Date | `${OVERRIDE.EDI.ackDate}` |
| BAK08 | Seller Order# | `${OVERRIDE.EDI.sellerOrderNumber}` |
| ACK01 | Line Status | `${line.status}` (in loop) |
| ACK02 | Ack Quantity | `${line.acknowledgedQuantity}` (in loop) |
| ACK05 | Promise Date | `${line.promiseDate}` (in loop) |
