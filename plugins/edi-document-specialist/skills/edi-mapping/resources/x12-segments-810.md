# X12 810 Invoice Segment Reference

## Document Type
- **Transaction Set**: 810 - Invoice
- **Purpose**: Request payment for goods/services delivered
- **Direction**: Seller → Buyer

## Beginning Segment (BIG)

The BIG segment contains header-level invoice information.

| Element | Description | Template Variable | Notes |
|---------|-------------|-------------------|-------|
| BIG01 | Invoice Date | `invoiceDate` | Format: YYYYMMDD |
| BIG02 | Invoice Number | `invoiceNumber` | Primary identifier |
| BIG03 | Date (optional) | - | Purchase order date |
| BIG04 | Purchase Order Number | `invoiceSummary.poNumber` | Reference to original PO |
| BIG05 | Release Number | - | Optional |
| BIG06 | Change Order Sequence | - | Optional |
| BIG07 | Transaction Type Code | `invoiceSummary.invoiceType` | DR=Debit, CR=Credit |

### Example BIG Segment
```
BIG*20260115*INV123456**PO987654***DR~
```
Parsed: Invoice date 2026-01-15, Invoice# INV123456, PO# PO987654, Type: Debit

## Name Loop (N1)

The N1 loop identifies parties involved in the transaction.

| Qualifier | Description | Template Path |
|-----------|-------------|---------------|
| BT | Bill To | `partners[type='BILL TO']` |
| ST | Ship To | `partners[type='SHIP TO']` |
| SE | Selling Party | `partners[type='SELLER']` |
| BY | Buying Party | `partners[type='BUYER']` |
| RI | Remit To | `partners[type='REMIT TO']` |

### N1 Segment Elements

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| N101 | Entity Identifier Code | `partners[].type` |
| N102 | Name | `partners[].name` |
| N103 | ID Code Qualifier | - |
| N104 | Identification Code | - |

### N3 Address Segment

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| N301 | Address Line 1 | `partners[].address` |
| N302 | Address Line 2 | `partners[].address2` |

### N4 Geographic Location

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| N401 | City | `partners[].city` |
| N402 | State/Province | `partners[].state` |
| N403 | Postal Code | `partners[].zip` |
| N404 | Country Code | `partners[].country` |

## Line Item Loop (IT1)

The IT1 loop contains line item details.

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| IT101 | Assigned Identification | `invoiceDetails[].lineNumber` |
| IT102 | Quantity Invoiced | `invoiceDetails[].quantity` |
| IT103 | Unit of Measure | `invoiceDetails[].uom` |
| IT104 | Unit Price | `invoiceDetails[].unitPrice` |
| IT105 | Basis of Unit Price | - |
| IT106 | Product/Service ID Qualifier | - |
| IT107 | Product/Service ID | `invoiceDetails[].itemNumber` |
| IT108-IT125 | Additional Product IDs | - |

### PID Product Description Segment

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| PID01 | Item Description Type | - |
| PID05 | Description | `invoiceDetails[].description` |

### Line Item Calculation
```javascript
// Total price per line
totalPrice = quantity * unitPrice
// Template variable: invoiceDetails[].totalPrice
```

## Payment Terms (ITD)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| ITD01 | Terms Type Code | `paymentTerms.description` |
| ITD02 | Terms Basis Date Code | - |
| ITD03 | Terms Discount Percent | `paymentTerms.discountPercent` |
| ITD04 | Terms Discount Due Date | - |
| ITD05 | Terms Discount Days Due | `paymentTerms.discountDays` |
| ITD06 | Terms Net Due Date | `paymentTerms.dueDate` |
| ITD07 | Terms Net Days | `paymentTerms.netDays` |
| ITD12 | Description | `paymentTerms.description` |

### Common Terms Type Codes
| Code | Description |
|------|-------------|
| 01 | Basic |
| 02 | End of Month |
| 05 | Discount Not Applicable |
| 08 | Basic Discount Offered |
| 14 | Previously Agreed Upon |

## Service/Promotion/Allowance (SAC)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| SAC01 | Allowance or Charge Indicator | - |
| SAC02 | Service/Promotion/Allowance Code | - |
| SAC05 | Amount | `invoiceSummary.discount` or `invoiceSummary.shipping` |
| SAC15 | Description | - |

### SAC01 Values
| Code | Description |
|------|-------------|
| A | Allowance (discount) |
| C | Charge (fee) |

## Summary Segment (TDS)

| Element | Description | Template Variable | Notes |
|---------|-------------|-------------------|-------|
| TDS01 | Total Invoice Amount | `invoiceSummary.totalAmount` | **Stored in cents!** Divide by 100 |
| TDS02 | Amount Subject to Terms Discount | - | |
| TDS03 | Discounted Amount Due | - | |
| TDS04 | Amount of Terms Discount | - | |

### Important: TDS01 Conversion
```javascript
// Raw EDI value is in cents
const rawAmount = 123456; // = $1,234.56
const displayAmount = rawAmount / 100;
```

## Control Totals (CTT)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| CTT01 | Number of Line Items | `invoiceSummary.totalItems` |
| CTT02 | Hash Total | - |

## Data Extractor Output Structure

The JavaScript hook (`twx_CRE2_EDI_DataExtractor.js`) transforms raw EDI JSON into this template structure:

```javascript
{
  documentType: '810',
  partnerName: 'Rocky Brands',
  invoiceNumber: 'INV123456',
  invoiceDate: '01/15/2026',
  invoiceSummary: {
    poNumber: 'PO987654',
    invoiceType: 'Debit Invoice',
    totalItems: 25,
    totalAmount: '$1,234.56',
    subtotal: '$1,200.00',
    discount: '$0.00',
    shipping: '$34.56',
    tax: '$0.00'
  },
  partners: [
    {
      type: 'BILL TO',
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
  invoiceDetails: [
    {
      lineNumber: '1',
      itemNumber: 'SKU-12345',
      description: 'Western Boot - Size 10',
      quantity: 12,
      unitPrice: '$89.99',
      totalPrice: '$1,079.88'
    }
  ],
  paymentTerms: {
    description: 'Net 30',
    netDays: 30,
    dueDate: '02/14/2026',
    discountPercent: '2%',
    discountDays: 10
  },
  technicalDetails: {
    controlNumber: '000012345',
    testIndicator: 'P'
  },
  twistedXLogo: '/core/media/media.nl?id=36100&c=4138030',
  tradingPartnerLogo: '/core/media/media.nl?id=[tp_logo_id]&c=4138030'
}
```

## Template Variable Quick Reference

| EDI Element | Description | Template Variable |
|-------------|-------------|-------------------|
| BIG01 | Invoice Date | `${OVERRIDE.EDI.invoiceDate}` |
| BIG02 | Invoice Number | `${OVERRIDE.EDI.invoiceNumber}` |
| BIG04 | PO Number | `${OVERRIDE.EDI.invoiceSummary.poNumber}` |
| BIG07 | Transaction Type | `${OVERRIDE.EDI.invoiceSummary.invoiceType}` |
| N102 (BT) | Bill To Name | `${partner.name}` (in loop) |
| IT102 | Quantity | `${line.quantity}` (in loop) |
| IT104 | Unit Price | `${line.unitPrice}` (in loop) |
| ITD07 | Net Days | `${OVERRIDE.EDI.paymentTerms.netDays}` |
| TDS01 | Total Amount | `${OVERRIDE.EDI.invoiceSummary.totalAmount}` |
