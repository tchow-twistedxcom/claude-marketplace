# X12 856 Advance Ship Notice (ASN) Segment Reference

## Document Type
- **Transaction Set**: 856 - Ship Notice/Manifest
- **Purpose**: Notify of shipment contents before delivery
- **Direction**: Seller → Buyer

## Hierarchical Structure

The 856 uses a hierarchical loop (HL) structure:

```
Shipment Level (HL01=S)
└── Order Level (HL01=O)
    └── Pack Level (HL01=P)
        └── Item Level (HL01=I)
```

## Beginning Segment (BSN)

The BSN segment contains header-level shipment notification information.

| Element | Description | Template Variable | Notes |
|---------|-------------|-------------------|-------|
| BSN01 | Transaction Set Purpose Code | `asnType` | 00=Original, 01=Cancel, 04=Replace |
| BSN02 | Shipment Identification | `shipmentId` | ASN number |
| BSN03 | Date | `shipDate` | Format: YYYYMMDD |
| BSN04 | Time | `shipTime` | Format: HHMM |
| BSN05 | Hierarchical Structure Code | - | 0001=Shipment/Order/Pack/Item |

## Hierarchical Level (HL)

| Element | Description | Notes |
|---------|-------------|-------|
| HL01 | Hierarchical ID Number | Sequential counter |
| HL02 | Hierarchical Parent ID Number | Links to parent level |
| HL03 | Hierarchical Level Code | S=Shipment, O=Order, P=Pack, I=Item |

### HL03 Level Codes
| Code | Description | Template Context |
|------|-------------|-----------------|
| S | Shipment | `shipment.*` |
| O | Order | `shipment.orders[]` |
| P | Pack/Tare | `shipment.orders[].packages[]` |
| I | Item | `shipment.orders[].packages[].items[]` |

## Shipment Level Segments

### TD1 - Carrier Details (Quantity and Weight)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| TD101 | Packaging Code | `shipment.packagingCode` |
| TD102 | Lading Quantity | `shipment.totalCartons` |
| TD106 | Weight Qualifier | - |
| TD107 | Weight | `shipment.totalWeight` |
| TD108 | Unit of Measure | `shipment.weightUom` |

### TD5 - Carrier Details (Routing Sequence/Transit Time)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| TD501 | Routing Sequence Code | - |
| TD502 | Identification Code Qualifier | - |
| TD503 | Identification Code | `shipment.carrierCode` |
| TD504 | Transportation Method | `shipment.transportMethod` |
| TD505 | Routing | `shipment.carrierName` |

### TD3 - Carrier Details (Equipment)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| TD301 | Equipment Description Code | `shipment.equipmentType` |
| TD302 | Equipment Initial | `shipment.trailerPrefix` |
| TD303 | Equipment Number | `shipment.trailerNumber` |

### REF - Reference Identification

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| REF01 | Reference ID Qualifier | - |
| REF02 | Reference Identification | Varies by qualifier |

### Common REF01 Qualifiers for 856
| Code | Description | Template Variable |
|------|-------------|-------------------|
| BM | Bill of Lading Number | `shipment.bolNumber` |
| CN | Carrier's Reference Number | `shipment.proNumber` |
| PK | Packing List Number | `shipment.packingListNumber` |

### DTM - Date/Time Reference

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| DTM01 | Date/Time Qualifier | - |
| DTM02 | Date | Varies by qualifier |

### DTM01 Qualifiers for 856
| Code | Description | Template Variable |
|------|-------------|-------------------|
| 011 | Shipped | `shipment.shipDate` |
| 017 | Estimated Delivery | `shipment.estimatedDeliveryDate` |

## Name Loop (N1) - Shipment Level

| Qualifier | Description | Template Path |
|-----------|-------------|---------------|
| ST | Ship To | `shipment.shipTo` |
| SF | Ship From | `shipment.shipFrom` |

## Order Level Segments

### PRF - Purchase Order Reference

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| PRF01 | Purchase Order Number | `shipment.orders[].poNumber` |
| PRF04 | Date | `shipment.orders[].poDate` |

## Pack/Tare Level Segments

### MAN - Marks and Numbers

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| MAN01 | Marks and Numbers Qualifier | - |
| MAN02 | Marks and Numbers | `shipment.orders[].packages[].sscc18` |

### Common MAN01 Qualifiers
| Code | Description |
|------|-------------|
| CP | Carrier's Package ID |
| GM | SSCC-18 |
| UC | UCC/EAN-128 Serial Shipping Container Code |

### PO4 - Item Physical Details

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| PO401 | Pack | `package.innerPack` |
| PO402 | Size | `package.size` |
| PO403 | Unit of Measure | `package.sizeUom` |
| PO404 | Packaging Code | `package.packagingCode` |
| PO405 | Weight Qualifier | - |
| PO406 | Gross Weight per Pack | `package.weight` |
| PO407 | Unit of Measure | `package.weightUom` |

## Item Level Segments

### SN1 - Item Detail (Shipment)

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| SN101 | Assigned Identification | `item.lineNumber` |
| SN102 | Number of Units Shipped | `item.quantity` |
| SN103 | Unit of Measure | `item.uom` |

### LIN - Item Identification

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| LIN01 | Assigned Identification | `item.lineNumber` |
| LIN02 | Product/Service ID Qualifier | - |
| LIN03 | Product/Service ID | `item.itemNumber` |

### PID - Product/Item Description

| Element | Description | Template Variable |
|---------|-------------|-------------------|
| PID05 | Description | `item.description` |

## Data Extractor Output Structure

```javascript
{
  documentType: '856',
  partnerName: 'Rocky Brands',
  shipmentId: 'ASN123456',
  shipDate: '01/15/2026',
  shipTime: '14:30',
  asnType: 'Original',
  shipment: {
    shipFrom: {
      name: 'Twisted X',
      address: '2800 S. Business Hwy 281',
      city: 'Edinburg',
      state: 'TX',
      zip: '78539'
    },
    shipTo: {
      name: 'Rocky Distribution Center',
      address: '456 Warehouse Blvd',
      city: 'Logan',
      state: 'OH',
      zip: '43138'
    },
    carrierName: 'FedEx Freight',
    carrierCode: 'FEDX',
    transportMethod: 'Motor',
    bolNumber: 'BOL789012',
    proNumber: 'PRO345678',
    totalCartons: 50,
    totalWeight: '1,250 LBS',
    estimatedDeliveryDate: '01/20/2026',
    orders: [
      {
        poNumber: 'PO987654',
        poDate: '01/10/2026',
        packages: [
          {
            sscc18: '(00)123456789012345678',
            cartonNumber: 1,
            weight: '25 LBS',
            items: [
              {
                lineNumber: '1',
                itemNumber: 'SKU-12345',
                description: 'Western Boot - Size 10',
                quantity: 12,
                uom: 'PR'
              }
            ]
          }
        ]
      }
    ]
  },
  technicalDetails: {
    controlNumber: '000012347',
    testIndicator: 'P'
  }
}
```

## Template Variable Quick Reference

| EDI Element | Description | Template Variable |
|-------------|-------------|-------------------|
| BSN02 | Shipment ID | `${OVERRIDE.EDI.shipmentId}` |
| BSN03 | Ship Date | `${OVERRIDE.EDI.shipDate}` |
| TD102 | Total Cartons | `${OVERRIDE.EDI.shipment.totalCartons}` |
| TD107 | Total Weight | `${OVERRIDE.EDI.shipment.totalWeight}` |
| TD505 | Carrier Name | `${OVERRIDE.EDI.shipment.carrierName}` |
| REF02 (BM) | BOL Number | `${OVERRIDE.EDI.shipment.bolNumber}` |
| PRF01 | PO Number | `${order.poNumber}` (in loop) |
| MAN02 | SSCC-18 | `${package.sscc18}` (in loop) |
| SN102 | Quantity | `${item.quantity}` (in loop) |
