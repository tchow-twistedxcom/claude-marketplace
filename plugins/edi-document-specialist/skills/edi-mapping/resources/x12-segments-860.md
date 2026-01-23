# X12 860 Purchase Order Change Request Segment Reference

## Document Type
- **Transaction Set**: 860 - Purchase Order Change Request - Buyer Initiated
- **Purpose**: Request changes to an existing purchase order
- **Direction**: Buyer → Seller

## Beginning Segment (BCH)

The BCH segment contains header-level change request information.

| Element | Description | Template Variable | Notes |
|---------|-------------|-------------------|-------|
| BCH01 | Transaction Set Purpose Code | `changeType` | 01=Cancel, 04=Change, 05=Replace |
| BCH02 | Purchase Order Type Code | `poTypeCode` | Same as BEG02 in 850 |
| BCH03 | Purchase Order Number | `poNumber` | Original PO number |
| BCH04 | Release Number | - | Optional |
| BCH05 | Change Order Sequence Number | `changeSequence` | Increments with each change |
| BCH06 | Order Date | `originalOrderDate` | Original order date |
| BCH10 | Change Request Date | `changeRequestDate` | Date of this change |

### BCH01 Purpose Codes
| Code | Description | Template Display |
|------|-------------|-----------------|
| 01 | Cancellation | 'Order Cancellation' |
| 04 | Change | 'Order Change' |
| 05 | Replace | 'Order Replacement' |

## Date/Time Reference (DTM)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| DTM01 | Date/Time Qualifier | - |
| DTM02 | Date | Varies by qualifier |

### DTM01 Qualifiers for 860
| Code | Description | Template Variable |
|------|-------------|-------------------|
| 002 | Delivery Requested | `newRequestedDeliveryDate` |
| 010 | Requested Ship Date | `newRequestedShipDate` |
| 063 | Do Not Deliver After | `newCancelDate` |

## Name Loop (N1)

Same structure as 850. Used if ship-to or other party changes.

## Line Item Change Loop (POC)

The POC segment identifies line-level changes. This is the key segment for 860.

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| POC01 | Assigned Identification | `changeDetails[].lineNumber` |
| POC02 | Line Item Change Code | `changeDetails[].changeCode` |
| POC03 | Quantity Ordered | `changeDetails[].newQuantity` |
| POC04 | Quantity Left to Receive | `changeDetails[].quantityLeft` |
| POC05 | Unit of Measure | `changeDetails[].uom` |
| POC06 | Unit Price | `changeDetails[].newUnitPrice` |
| POC07 | Basis of Unit Price | - |
| POC08 | Product/Service ID Qualifier | - |
| POC09 | Product/Service ID | `changeDetails[].itemNumber` |

### POC02 Line Item Change Codes
| Code | Description | Template Display |
|------|-------------|-----------------|
| AI | Add Item | 'Add' |
| CA | Changes to Line Item | 'Change' |
| CT | Change Request Line Added | 'Added' |
| DI | Delete Item | 'Delete' |
| PC | Price Change | 'Price Change' |
| PQ | Price and Quantity Change | 'Price & Qty Change' |
| QD | Quantity Decrease | 'Qty Decrease' |
| QI | Quantity Increase | 'Qty Increase' |
| RR | Re-Route | 'Re-Route' |

## Product Description (PID)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| PID05 | Description | `changeDetails[].description` |

## Reference Identification (REF) - Line Level

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| REF01 | Reference ID Qualifier | - |
| REF02 | Reference Identification | Varies |

### Common REF01 for Line Level
| Code | Description |
|------|-------------|
| FI | Original Line Number |
| LI | Line Item Identifier |

## Summary (CTT)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| CTT01 | Number of Line Items | `changeSummary.totalLines` |

## Data Extractor Output Structure

```javascript
{
  documentType: '860',
  partnerName: 'Rocky Brands',
  poNumber: 'PO987654',
  changeSequence: 1,
  originalOrderDate: '01/10/2026',
  changeRequestDate: '01/12/2026',
  changeType: 'Order Change',
  changeSummary: {
    totalLines: 3,
    addedLines: 1,
    changedLines: 1,
    deletedLines: 1,
    newRequestedShipDate: '01/28/2026'
  },
  changeDetails: [
    {
      lineNumber: '1',
      changeCode: 'QI',
      changeDescription: 'Qty Increase',
      itemNumber: 'SKU-12345',
      description: 'Western Boot - Size 10',
      originalQuantity: 12,
      newQuantity: 24,
      quantityChange: '+12',
      uom: 'PR',
      unitPrice: '$89.99'
    },
    {
      lineNumber: '5',
      changeCode: 'DI',
      changeDescription: 'Delete',
      itemNumber: 'SKU-54321',
      description: 'Casual Boot - Size 9',
      originalQuantity: 6,
      newQuantity: 0,
      quantityChange: '-6',
      uom: 'PR',
      unitPrice: '$79.99'
    },
    {
      lineNumber: '16',
      changeCode: 'AI',
      changeDescription: 'Add',
      itemNumber: 'SKU-99999',
      description: 'NEW: Safety Boot - Size 10',
      originalQuantity: 0,
      newQuantity: 10,
      quantityChange: '+10',
      uom: 'PR',
      unitPrice: '$149.99'
    }
  ],
  technicalDetails: {
    controlNumber: '000012348',
    testIndicator: 'P'
  }
}
```

## Change Visualization Patterns

### Quantity Changes
```html
<#if line.changeCode == 'QI'>
  <span style="color:green;">▲ ${line.quantityChange}</span>
<#elseif line.changeCode == 'QD'>
  <span style="color:red;">▼ ${line.quantityChange}</span>
</#if>
```

### Line Status Badges
```html
<#if line.changeCode == 'AI'>
  <span class="badge-success">NEW</span>
<#elseif line.changeCode == 'DI'>
  <span class="badge-danger">DELETED</span>
<#elseif line.changeCode == 'CA'>
  <span class="badge-warning">CHANGED</span>
</#if>
```

## Template Variable Quick Reference

| EDI Element | Description | Template Variable |
|-------------|-------------|-------------------|
| BCH01 | Change Type | `${OVERRIDE.EDI.changeType}` |
| BCH03 | PO Number | `${OVERRIDE.EDI.poNumber}` |
| BCH05 | Change Sequence | `${OVERRIDE.EDI.changeSequence}` |
| BCH10 | Change Date | `${OVERRIDE.EDI.changeRequestDate}` |
| POC02 | Line Change Code | `${line.changeCode}` (in loop) |
| POC03 | New Quantity | `${line.newQuantity}` (in loop) |
| POC06 | New Unit Price | `${line.newUnitPrice}` (in loop) |
