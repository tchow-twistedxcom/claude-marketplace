# EDI JSON Structures Reference

The EDI History record (`customrecord_twx_edi_history`) stores parsed EDI data in the
`custrecord_twx_edi_history_json` field as a JSON string. This document describes the
actual JSON structure for each document type.

**⚠️ ALWAYS inspect actual JSON before writing extraction code.** Use:
```bash
python3 analyze_json_fields.py --record-id <ID> --show-structure --env sb2
```

---

## 850 - Purchase Order

### Top-Level Keys

```
Document Type: "850"
Purchase Order Number: "044455970099"
Purchase Order Type Code: "NE" (New Order) | "RO" (Replacement)
Order Date: "20251010"                    ← MAY BE EMPTY
Currency Code: "USD"
Contract Number: "..."                     ← optional
```

### ⚠️ Date/Time Reference (ARRAY - NOT top-level!)

**CRITICAL:** Dates like `Delivery Requested Date` and `Cancel After` are inside an array,
NOT at the top level. Each element is a single-key object.

```json
"Date/Time Reference": [
  { "Delivery Requested Date": "20251113" },
  { "Cancel After": "20251223" }
]
```

**Extraction pattern:**
```javascript
var dateRefs = ediData['Date/Time Reference'] || [];
for (var d = 0; d < dateRefs.length; d++) {
    if (dateRefs[d]['Delivery Requested Date']) {
        result.orderSummary.deliveryRequestedDate = formatDate(dateRefs[d]['Delivery Requested Date']);
    }
    if (dateRefs[d]['Cancel After']) {
        result.orderSummary.cancelAfterDate = formatDate(dateRefs[d]['Cancel After']);
    }
}
```

### Reference Identification (ARRAY)

```json
"Reference Identification": [
  { "Customer Order Number": "123456" },
  { "Department Number": "789" }
]
```

### N1 Loop (Partners - ARRAY of objects)

```json
"N1 Loop": [
  {
    "Entity Identifier Code": "ST",
    "Name": "WAREHOUSE NAME",
    "Identification Code Qualifier": "92",
    "Identification Code": "1234",
    "N3 - Address": { "Address Line 1": "123 MAIN ST" },
    "N4 - Location": {
      "City": "MARSHALL",
      "State": "MN",
      "Postal Code": "562580000"
    }
  }
]
```

Entity Identifier Codes: `ST` (Ship To), `BT` (Bill To), `BY` (Buyer), `SE` (Seller)

### PO1 Loop (Line Items - ARRAY)

```json
"PO1 Loop": [
  {
    "Assigned Identification": "001",
    "Quantity Ordered": "1",
    "Unit of Measure": "EA",
    "Unit Price": "120.90",
    "Product/Service ID Qualifier 1": "UP",
    "Product/Service ID 1": "888877779999",
    "Product/Service ID Qualifier 2": "VN",
    "Product/Service ID 2": "001909663",
    "PID Loop": [
      { "Description": "12\"BOOT WP WSQ ALLOY EH 10D" }
    ]
  }
]
```

### Payment Terms (ITD Segment)

```json
"Terms of Sale/Deferred Terms of Sale": {
  "Terms Type Code": "01",
  "Terms Basis Date Code": "3",
  "Terms Discount Percent": "0",
  "Terms Discount Days Due": "",
  "Terms Net Days": "30",
  "Terms Net Due Date": "",
  "Description": "NET 30 DAYS"
}
```

### CTT/SE Segments

```json
"Transaction Totals": {
  "Number of Line Items": "51"
}
```

---

## 810 - Invoice

### Top-Level Keys

```
Document Type: "810"
Invoice Number: "INV-12345"
Invoice Date: "20251015"
Purchase Order Number: "PO-67890"
Currency Code: "USD"
```

### IT1 Loop (Invoice Items - ARRAY)

```json
"IT1 Loop": [
  {
    "Assigned Identification": "1",
    "Quantity Invoiced": "2",
    "Unit of Measure": "EA",
    "Unit Price": "89.95",
    "Product/Service ID Qualifier 1": "UP",
    "Product/Service ID 1": "888877779999",
    "Product/Service ID Qualifier 2": "VN",
    "Product/Service ID 2": "001909663",
    "PID Loop": [
      { "Description": "12\" BOOT DESCRIPTION" }
    ]
  }
]
```

### TDS - Total Monetary Value Summary

```json
"Total Monetary Value Summary": {
  "Amount 1": "17990"
}
```
Note: Amount is in cents (17990 = $179.90)

---

## 855 - PO Acknowledgment

### Top-Level Keys

```
Document Type: "855"
Acknowledgment Type: "AC" (Acknowledge with changes) | "AD" (Acknowledge with detail)
Purchase Order Number: "PO-12345"
Date: "20251020"
```

### ACK Loop (Acknowledgment Items - ARRAY)

```json
"ACK Loop": [
  {
    "Line Item Status Code": "IA" (Item Accepted) | "IR" (Item Rejected),
    "Quantity": "2",
    "Unit of Measure": "EA",
    "Date/Time Qualifier": "068",
    "Date": "20251115"
  }
]
```

---

## 856 - Advance Ship Notice

### Top-Level Keys

```
Document Type: "856"
Shipment Identification: "ASN-12345"
Date: "20251025"
```

### Hierarchical Levels (HL Loop)

```json
"HL Loop": [
  {
    "Hierarchical Level": {
      "HL ID": "1",
      "HL Parent ID": "",
      "HL Level Code": "S"  ← Shipment level
    },
    "TD1": { ... },  ← Carrier details
    "TD5": { ... },  ← Routing
    "REF": [ ... ],  ← References
    "DTM": [ ... ]   ← Dates
  },
  {
    "Hierarchical Level": {
      "HL ID": "2",
      "HL Parent ID": "1",
      "HL Level Code": "O"  ← Order level
    },
    "PRF": { "Purchase Order Number": "PO-12345" }
  },
  {
    "Hierarchical Level": {
      "HL ID": "3",
      "HL Parent ID": "2",
      "HL Level Code": "I"  ← Item level
    },
    "SN1": {
      "Number of Units Shipped": "2",
      "Unit of Measure": "EA"
    },
    "LIN": {
      "Product/Service ID Qualifier 1": "UP",
      "Product/Service ID 1": "888877779999"
    }
  }
]
```

HL Level Codes: `S` (Shipment), `O` (Order), `P` (Pack), `I` (Item)

---

## 824 - Application Advice

### Top-Level Keys

```
Document Type: "824"
Transaction Set Purpose Code: "00"
Application Type: "TX" (Text)
```

### OTI Loop (Original Transaction - ARRAY)

```json
"OTI": [
  {
    "Original Transaction Identifier": "...",
    "Application Acknowledgment Code": "TA" (Accepted) | "TR" (Rejected),
    "Reference Identification": "...",
    "Date": "20251010"
  }
]
```

### TED Loop (Technical Error - ARRAY)

```json
"TED": [
  {
    "Application Error Condition Code": "E01",
    "Free-Form Message": "Error description text"
  }
]
```

---

## 860 - PO Change

### Top-Level Keys

```
Document Type: "860"
Purchase Order Number: "PO-12345"
Change Request Date: "20251028"
Purpose Code: "04" (Change)
```

### POC Loop (PO Change Items - ARRAY)

```json
"POC Loop": [
  {
    "Assigned Identification": "001",
    "Change or Response Code": "QI" (Quantity Increase) | "QD" (Quantity Decrease),
    "Quantity Ordered": "3",
    "Quantity Left to Receive": "3",
    "Unit of Measure": "EA",
    "Unit Price": "120.90"
  }
]
```

---

## Common Patterns Across All Doc Types

### Date Format
All raw dates are `YYYYMMDD` strings. Use `formatDate()` to convert to `MM/DD/YYYY`.

### Nested Arrays with Single-Key Objects
Many EDI fields use arrays of single-key objects:
```json
"Some Array": [
  { "Field Name A": "value1" },
  { "Field Name B": "value2" }
]
```
**Always iterate the array and check for each key name.**

### Field Name Gotchas
- Field names contain spaces: `"Purchase Order Number"` not `purchaseOrderNumber`
- Field names may include slashes: `"Product/Service ID Qualifier 1"`
- Some fields have numeric suffixes: `"Product/Service ID 1"`, `"Product/Service ID 2"`
- Segment names vs. human names vary by parser output

### Missing Data
- A field may be absent entirely (not just empty)
- Always use defensive access: `ediData['Field Name'] || ''`
- Arrays may be empty or undefined: `ediData['Array Name'] || []`
