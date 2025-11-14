# PRI Container Tracking - Quick Reference Guide

## Custom Record Types - Script IDs

```
Production Management:
  customrecord_pri_frgt_cnt_pm_po      - Production PO Header
  customrecord_pri_frgt_cnt_pm         - Production Line (child of PM PO)
  customrecord_pri_frgt_cnt_iv         - Item Version

Container Logistics:
  customrecord_pri_frgt_cnt            - Container
  customrecord_pri_frgt_cnt_vsl        - Vessel (parent of containers)
  customrecord_pri_frgt_cnt_carrier    - Carrier

In-Transit Management:
  customrecord_pri_frgt_cnt_l          - IR to TO Linker
  customrecord_pri_frgt_cnt_dm         - Distribution Management

Landed Cost:
  customrecord_pri_frgt_cnt_lct        - LC Template
  customrecord_pri_frgt_cnt_lctd       - LC Template Detail (child of template)
```

## Key Relationships

```
Production Management PO Header (1) ──> (N) Production Lines
Production Line ──> Item Version (for pricing)
Production Line ──> Purchase Order (generated)

Vessel (1) ──> (N) Containers
Carrier ──> Vessel, Container (provides tracking URL)

Container ──> Transfer Order (auto-created)
IR to TO Linker ──> Transfer Order (auto-creates/fulfills)

Purchase Order ──> Item Receipt
Item Receipt ──> IR to TO Linker
IR to TO Linker ──> Transfer Order
Transfer Order ──> Item Fulfillment (auto-created)

Distribution Management (child of) ──> Container
Distribution Management ──> Purchase Order line
```

## Status Values

### Logistic Status (customlist_pri_frgt_cnt_log_status)
- 1 = At Origin Port
- 2 = On Sea In Transit
- 3 = At Landing Port
- 6 = In Transit to Dest Location
- 7 = Received at Dest Location
- 8 = At Arrival Dest Location

### Production Line Status (customlist_pri_frgt_cnt_pm_line_status)
- 1 = Unlocked (prices dynamic)
- 2 = Locked (prices frozen in JSON)

### LC Allocation Method (customlist_pri_frgt_cnt_lct_all_method)
- 1 = Per Quantity
- 2 = Flat Amount
- 3 = Item Consumption
- 4 = Percentage

## Critical Fields by Record

### Production Line (customrecord_pri_frgt_cnt_pm)
```javascript
Parent Relationship:
  custrecord_pri_frgt_cnt_pm_parent                - Parent PO header (mandatory)

Item/Pricing:
  custrecord_pri_frgt_cnt_pm_item                  - Item
  custrecord_pri_frgt_cnt_pm_item_type             - Item type
  custrecord_pri_frgt_cnt_pm_item_version          - Item version (for pricing)
  custrecord_pri_frgt_cnt_pm_quantity              - Planned quantity
  custrecord_pri_frgt_cnt_pm_price_calc            - Calculated price

Status/Locking:
  custrecord_pri_frgt_cnt_pm_status                - Status (1=Unlocked, 2=Locked)
  custrecord_pri_frgt_cnt_pm_holdpricedata         - JSON locked structure

Received Tracking:
  custrecord_pri_frgt_cnt_pm_quantity_po           - Qty received from PO
  custrecord_pri_frgt_cnt_pm_quantity_to           - Qty received from TO
  custrecord_pri_frgt_cnt_pm_quantity_ib           - Imbalanced IRs
  custrecord_pri_frgt_cnt_pm_quantity_calc         - Calculated qty
```

### Container (customrecord_pri_frgt_cnt)
```javascript
Logistics:
  custrecord_pri_frgt_cnt_vsl                      - Parent vessel
  custrecord_pri_frgt_cnt_carrier                  - Carrier
  custrecord_pri_frgt_cnt_log_status               - Logistic status (1-8)
  custrecord_pri_frgt_cnt_seal                     - Container seal ID

Locations:
  custrecord_pri_frgt_cnt_location_origin          - Origin location
  custrecord_pri_frgt_cnt_location_dest            - Destination location

Linkage:
  custrecord_pri_frgt_cnt_to                       - Transfer order

Dates (6 critical dates):
  custrecord_pri_frgt_cnt_date_sail                - Sail date
  custrecord_pri_frgt_cnt_date_land_est            - Estimated landing
  custrecord_pri_frgt_cnt_date_land_act            - Actual landing
  custrecord_pri_frgt_cnt_date_fwd_est             - Estimated forward
  custrecord_pri_frgt_cnt_date_fwd_act             - Actual forward
  custrecord_pri_frgt_cnt_date_dest_est            - Estimated destination
  custrecord_pri_frgt_cnt_date_dest_act            - Actual destination

Costs:
  custrecord_pri_frgt_cnt_cost_freight             - Freight cost
  custrecord_pri_frgt_cnt_cost_clr_forward         - Clearance/forward cost
  custrecord_pri_frgt_cnt_cost_total               - Total cost (formula)
```

### IR to TO Linker (customrecord_pri_frgt_cnt_l)
```javascript
Source:
  custrecord_pri_frgt_cnt_l_ir                     - Item receipt
  custrecord_pri_frgt_cnt_l_ir_line_no             - IR line number (1-based)
  custrecord_pri_frgt_cnt_l_item                   - Item (auto-populated)
  custrecord_pri_frgt_cnt_l_qty                    - Quantity

Destination:
  custrecord_pri_frgt_cnt_l_cnt                    - Container (mandatory)

Generated:
  custrecord_pri_frgt_cnt_l_to                     - Transfer order (auto-created)
  custrecord_pri_frgt_cnt_l_to_line_no             - TO line number (1-based)
```

## Transaction Custom Fields

### Purchase Order
```javascript
Body:
  custbody_pri_frgt_cnt_pm_po                      - Production PO reference

Column:
  custcol_pri_frgt_cnt_iv                          - Item version
  custcol_pri_frgt_cnt_dm                          - Distribution mgmt
  custcol_pri_frgt_cnt_pm_po                       - Production line
  custcol_pri_frgt_cnt_iv_sourced                  - IV sourced flag
```

### Item Receipt
```javascript
Body:
  custbody_pri_frgt_cnt                            - Container (Non-Linker Mode)
  custbody_pri_frgt_loc_ult                        - Ultimate location
  custbody_pri_frgt_loc_ult_date                   - Ultimate delivery date
  custbody_pri_frgt_cnt_pm_po                      - Production PO

Column:
  custcol_pri_frgt_cnt_iv                          - Item version
  custcol_pri_frgt_cnt_dm                          - Distribution mgmt
  custcol_pri_frgt_cnt_pm_po                       - Production line
```

### Transfer Order
```javascript
Body:
  custbody_pri_frgt_cnt                            - Container
  custbody_pri_frgt_cnt_lctd_ir_pointer            - IR pointer
  custbody_pri_frgt_cnt_pm_po                      - Production PO

Column:
  custcol_pri_frgt_cnt_ir_lnkey                    - IR line key
  custcol_pri_frgt_cnt_iv                          - Item version
  custcol_pri_frgt_cnt_dm                          - Distribution mgmt
  custcol_pri_frgt_cnt_pm_po                       - Production line
```

## Common Code Patterns

### Load Production Line with Item Info
```javascript
const IDLIB = require('./pri_idRecord_cslib');
const PRODLIB = require('./pri_cntProdMgmt_lib');

// Load line
const prodLine = new PRODLIB.PRODPOLINE(lineId, {
    scriptContext: scriptContext,
    intItemId: itemId,
    strItemType: itemType
});

// Get item member info (dynamic, respects current pricing)
const itemMemberInfo = prodLine.getItemMembInfo();

// Get locked info (frozen structure from JSON)
const lockedInfo = prodLine.getLockedItemMembInfo();

// Calculate received quantities
prodLine.calcQtyReceivedPOTO();
```

### Create IR to TO Linker
```javascript
const LINKERLIB = require('./pri_irToLinker_lib');

// Validation
const isValid = LINKERLIB.pri_irToLinker_Validate(scriptContext);

// Create TO and IF automatically
const updatedRecord = LINKERLIB.pri_irToLinker_CreateTO(scriptContext);
```

### Search Production Lines by Parent
```javascript
const search = require('N/search');

const prodLines = search.create({
    type: IDLIB.REC.CNTPRODMGMTLN.ID,
    filters: [
        [IDLIB.REC.CNTPRODMGMTLN.PARENT, 'anyof', [parentId]],
        'AND', ['isinactive', 'is', 'F']
    ],
    columns: [
        'internalid',
        IDLIB.REC.CNTPRODMGMTLN.ITEM,
        IDLIB.REC.CNTPRODMGMTLN.QUANTITY,
        IDLIB.REC.CNTPRODMGMTLN.STATUS,
        IDLIB.REC.CNTPRODMGMTLN.HOLDPRICEDATA
    ]
}).run().getRange(0, 999);
```

### Calculate Received Quantities
```javascript
const receivedQty = search.create({
    type: 'itemreceipt',
    filters: [
        ['mainline', 'is', 'F'],
        'AND', [IDLIB.REC.N_ITEMRCPT.COL_CNTPMPO, 'anyof', [prodLineId]]
    ],
    columns: [
        search.createColumn({
            name: 'formulanumeric',
            summary: search.Summary.SUM,
            formula: '{quantity}/{custcol_pri_frgt_cnt_pm_po.custrecord_pri_frgt_cnt_pm_quantity_calc}'
        })
    ]
}).run().getRange(0, 1);
```

## Business Process Workflows

### Production to PO Workflow
```
1. Create Production PO Header → Set vendor, currency
2. Create Production Lines → Select items, quantities
3. Lock Lines → Freezes pricing structure
4. Use PO Generator → Creates NetSuite POs
5. Receive POs → Updates received quantities
```

### Container Tracking Workflow
```
1. Create Carrier → Set tracking URL
2. Create Vessel → Set route, dates, carrier
3. Create Containers → Inherit vessel data
4. Track Progress → Update status (1→2→3→6→7→8)
5. Update Dates → Syncs to TOs and IFs
```

### In-Transit Distribution Workflow
```
1. Receive PO at Port → Create Item Receipt
2. Create Linker → Link IR line to container
3. Auto-Create TO → System creates transfer order
4. Auto-Fulfill → System fulfills immediately
5. Track Container → Container shows in-transit inventory
```

## Validation Rules

### Production Line Locking
- Status must be Unlocked to change item/version
- Status must be Locked to generate POs
- holdpricedata must contain valid JSON when locked

### IR to TO Linker
- Line number ≤ IR line count
- Quantity ≤ IR line quantity
- Sum of linker quantities ≤ IR line quantity
- Container must have origin location
- Container must have destination location
- IR cannot have body-level container field set

### Container Status Progression
- Typical flow: 1 → 2 → 3 → 6 → 7 → 8
- Cannot skip required statuses
- Date fields must align with status

## JSON Structures

### Production Line Hold Price Data
```json
[
  {
    "LINENUMBER": 100,
    "TYPE": "InvtPart",
    "SUBTYPE": "Purchase",
    "ISFULFILLABLE": true,
    "MEMBERITEM": "12345",
    "ITEMVERSION": "678",
    "DESCRIPTION": "Widget 2000",
    "VENDORNAME": "ACME Corp",
    "MEMBERQTY": 10,
    "PURCHASEPRICE": 15.50,
    "PURCHASEPRICE_DISPLAY": "<p style=\"text-align:right\">15.50</p>",
    "VALUE": 155.00,
    "VALUE_DISPLAY": "<p style=\"text-align:right\">155.00</p>"
  }
]
```

## Key Scripts

```
User Events:
  pri_container_ss.js              - Container record events
  pri_cntProdMgmtPo_ss.js          - Production PO header events
  pri_cntProdMgmtLn_ss.js          - Production line events
  pri_irToLinker_ss.js             - Linker record events
  pri_cntDistMgmt_ss.js            - Distribution mgmt events

Libraries:
  pri_idRecord_cslib.js            - Central ID definitions
  pri_cntProdMgmt_lib.js           - Production logic
  pri_irToLinker_lib.js            - Linking logic
  pri_itemrcpt_lib.js              - Item receipt utilities

Client Scripts:
  pri_cntProdMgmtLn20_cl.js        - Production line client
  pri_CL_container.js              - Container client
  pri_CL_vessel.js                 - Vessel client

Suitelets:
  pri_cntProdPoGenerator_sl.js     - PO generator UI
  pri_SL_GenerateContainerData.js  - Container data UI

Scheduled Scripts:
  pri_SC_receiveContainer.js       - Container receipt automation
```

## Dependencies

```
External Bundles:
  Bundle 132118 - Queue Manager (PRI_QM_Engine)
  Bundle 132118 - Application Settings (PRI_AS_Engine)
  Bundle 132118 - Server Library (PRI_ServerLibrary)

NetSuite Features Required:
  - Advanced Purchase Orders
  - Multi-Location Inventory
  - Transfer Orders
  - Item Fulfillments
  - Custom Records
  - Custom Fields
  - User Event Scripts
  - Client Scripts
```

## Common Issues & Troubleshooting

### Production Line Price Not Calculating
- Check if item has item version assigned
- For item groups, verify member items have versions
- Ensure item version has rate populated
- Check item type is supported (1=Inventory, 6=Kit, 7=Item Group)

### IR to TO Linker Validation Failing
- Verify IR line number is 1-based (not 0-based)
- Check quantity doesn't exceed IR line quantity
- Ensure container has both origin and destination locations
- Verify IR doesn't have custbody_pri_frgt_cnt populated

### Container Not Creating Transfer Order
- Check if container already has TO linked
- Verify locations are set (origin and destination)
- Check for script errors in pri_container_ss.js beforeSubmit

### Received Quantities Not Updating
- Check if item receipt has custcol_pri_frgt_cnt_pm_po populated
- Verify quantity_calc is not zero on production line
- For item groups, ensure no imbalances (non-integer results)
- Check Queue Manager if >10 lines need updating

---

## Contact & Support

**Bundle:** 125246 - PRI Container Tracking
**Vendor:** Prolecto Resources, Inc.
**Documentation Date:** 2025-11-12
