# PRI Container Tracking - Backend Processing Architecture

**Analysis Date:** 2025-11-12
**System:** PRI Container Tracking (Bundle 125246)
**Focus:** Event-driven workflows, scheduled automation, business logic engines

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Event-Driven Workflows](#event-driven-workflows)
3. [Scheduled Automation Processes](#scheduled-automation-processes)
4. [Business Rule Engines](#business-rule-engines)
5. [State Machine Transitions](#state-machine-transitions)
6. [Integration Points](#integration-points)
7. [Performance Optimizations](#performance-optimizations)

---

## Architecture Overview

### Core Processing Patterns

The PRI Container Tracking system implements a sophisticated multi-layer backend architecture:

```
User Actions → User Event Scripts → Business Logic → Queue Management → Scheduled Scripts
                     ↓                      ↓                ↓                  ↓
              Field Validation      State Transitions    Async Tasks      Batch Processing
                     ↓                      ↓                ↓                  ↓
           NetSuite Records ←────── Container State ←─── Transfer Orders ← Inventory Mgmt
```

### Key Design Principles

1. **Asynchronous Processing**: Heavy operations queued via PRI_QM_Engine for background execution
2. **Event Cascading**: User events trigger chain reactions across related records
3. **State Validation**: Container status gates prevent invalid operations
4. **Audit Trail**: Field changes tracked via note generation system
5. **Idempotency**: Operations designed to handle re-execution safely

---

## Event-Driven Workflows

### 1. Item Receipt Processing (`pri_itemrcpt_ss.js`)

**Primary Purpose:** Manages landed cost allocation, container synchronization, and production management during item receipt lifecycle.

#### beforeLoad Triggers

**TRANSFORM/CREATE Mode:**
- Syncs location fields between body and line items
- Adds distribution management columns
- Enables item group receipt feature
- Sets PO location defaults

**EDIT Mode:**
- Locks container mode switching to prevent data corruption
- Validates container status before allowing edits (must be at origin port)
- Adds sync switch for container updates
- Displays lock messages if container in-transit

**VIEW Mode:**
- Adds recalculate landed cost button
- Shows item group receipts
- Displays queue status messages
- Shows container lock warnings

#### beforeSubmit Triggers

**Validation & Setup:**
```javascript
// Enable landed cost per line for template mode
if (bolCostTemplate == 'T') {
    currentRecord.setValue('landedcostperline', true);
}

// Sync locations unless created from inbound shipment
if (!currentRecord.getValue('inboundshipment')) {
    TRANLIB.pri_itemrcpt_setLocations(scriptContext);
}

// Set and validate transaction dates
TRANLIB.pri_itemrcpt_setTrandate(scriptContext);
```

**Business Rules Applied:**
1. **Container validation**: Non-linker mode containers must have valid freight container reference
2. **Item group quantity**: Exposed from receipts sublist, validated against production PO line balance
3. **Distribution management**: Values validated against parent PO
4. **Landed cost**: Body mode or per-line template mode allocation

**DELETE Operations:**
- Removes related inventory adjustments
- Cleans up transfer orders linked to container

#### afterSubmit Processing

**Landed Cost Template Mode:**
```javascript
if (bolCostTemplate == 'T') {
    TRANLIB.pri_itemrcpt_lc_PerLnTemplateMode(scriptContext);
    // Allocates freight costs from container to item receipt lines
    // Uses cost categories, allocation methods, and templates
}
```

**Container Touch Queue:**
```javascript
TRANLIB.pri_itemrcpt_touchCtnQueue(scriptContext);
// Queues container for async update via pri_containerTouch_sc
// Syncs ownership, departure port, dates from item receipt to container
```

**Transfer Order Workflows:**
- **From Transfer Order**: Updates container status, updates TO fields, handles direct import cases
- **Production Management**: Updates quantity received values on production PO lines

---

### 2. Container Management (`pri_container_ss.js`)

**Primary Purpose:** Orchestrates container lifecycle, transfer order creation, and status transitions.

#### beforeLoad Triggers

**VIEW Mode:**
- **Create Transfer Order Button**: Added if no transfer order exists yet
- **Mark In-Transit Button**: Triggers vessel/container status change workflow
- **Receipts Display**: Shows item group receipts for container items
- **Status Messages**: Displays queue processing status and lock messages

**EDIT Mode:**
- Disables container fields based on status to prevent invalid changes
- Shows touch/mark in-transit queue messages

**COPY Mode:**
- Clears transfer order reference to prevent linking issues

#### beforeSubmit Processing

**Container Name Uniqueness:**
```javascript
// Ensures container name is unique across system
if (strCntName) {
    scriptContext.newRecord.setValue({
        fieldId: 'name',
        value: pri_cntTrnfrord_ctnIdUnique(strCntName, intCntId, intTrnfrordId)
    });
}
```

**Field Population:**
- Populates container fields from related records
- Syncs container values to linked transfer order:
  - Transaction date → Transfer order date
  - Estimated destination date → Expected receipt date
  - Container name → Transfer order memo

**Status Validation:**
- Validates container status transitions
- Prevents edits when container in invalid state

#### afterSubmit Workflows

**Transfer Order Synchronization:**
- Updates transfer order when container modified
- Maintains bidirectional link integrity
- Cascades container dates to transfer order fulfillment

---

### 3. Production Management Line (`pri_cntProdMgmtLn_ss.js`)

**Primary Purpose:** Production purchase order line pricing, item versioning, and quantity tracking.

#### beforeLoad Features

**VIEW Mode:**
```javascript
// Price Lock Tab - Shows locked pricing history
clsProdPoLine.addPriceLockTab();

// PO Line Member Info - Displays item group component details
clsProdPoLine.addPoLnMemInfoSublist();
```

**EDIT/CREATE Mode:**
```javascript
// Sync locked record field display types
clsProdPoLine.syncLockFlds(scriptContext.form);

// Item Version Picker - Filters items by version
clsProdPoLine.addItmVerFilterFld();
```

#### beforeSubmit Logic

**Price Locking Mechanism:**
```javascript
// Hold current price structure when status changes to locked
clsProdPoLine.holdPrice();
// Stores JSON structure of item members, quantities, prices

// Set line number with auto-increment
clsProdPoLine.setLineNum();
// Format: 001, 002, 003... per production PO
```

**Price & Quantity Calculation:**
```javascript
if (intItemId) {
    // Lookup and calculate:
    // - Item member pricing (item groups/kits)
    // - Discount/markup application
    // - Item version pricing overrides
    // - Vendor-specific pricing
    clsProdPoLine.lookupCalcPriceandQty(currentRecord);
}
```

#### afterSubmit Processing

**Quantity Received Calculation:**
```javascript
// Calculate QUANTITY RECEIVED PO and QUANTITY RECEIVED TO
clsProdPoLine.calcQtyReceivedPOTO();
// Aggregates quantities from:
// - Item receipts against PO
// - Item receipts from transfer orders
```

---

### 4. Distribution Management (`pri_cntDistMgmt_ss.js`)

**Primary Purpose:** Plans major demand-based purchase order distribution across locations.

#### beforeLoad/beforeSubmit Processing

**Automatic Naming:**
```javascript
// Format: PO_NUMBER - ITEM_ID - INCREMENT
// Example: 12345 - SHOE001 - 001
strRecName = strPONum + NAME_DELIMITER + strItem + NAME_DELIMITER + strIncId;
```

**Field Validation:**

**Line Number Check:**
```javascript
// Ensures line number exists on parent PO
if (intParent_LineNo > intItmLnCnt) {
    throw 'Error: Distribution management line ' + intParent_LineNo +
          ' not found on parent PO (Total: ' + intItmLnCnt + ')';
}
```

**Quantity Check:**
```javascript
// Prevents over-distribution
if (intPoItmQty < intSumTtlQty) {
    throw 'Error: Distribution total (' + intSumTtlQty +
          ') exceeds PO quantity (' + intPoItmQty + ')';
}
```

**Field Sourcing:**
- Auto-populates `ITEM` from parent PO line
- Auto-populates `PARENT_LINEID` for linkage
- Validates quantity allocations across all distribution records

---

### 5. Item Receipt to Linker (`pri_irToLinker_ss.js`)

**Primary Purpose:** Linkage table connecting item receipts to containers and transfer orders for in-transit distribution.

#### beforeLoad Behavior

**COPY Mode:** Clears critical fields to prevent duplication:
- Item reference
- Item receipt line number
- Quantity
- Transfer order reference
- Transfer order line number

**EDIT Mode:**
```javascript
// Locks fields to prevent modification (display inline only)
currentForm.getField(IDLIB.REC.IRTOLINKER.IRREF).updateDisplayType({
    displayType: ui.FieldDisplayType.INLINE
});
// Locked fields: IR Reference, Line Number, Quantity, Container
```

#### beforeSubmit Logic

**CREATE Operations:**
```javascript
// Validation and automatic transfer order creation
LNKERLIB.pri_irToLinker_CreateTO(scriptContext);
// Creates transfer order for container distribution
// Links item receipt to container and destination
```

**EDIT/XEDIT Operations:**
```javascript
// Prevents updates completely
throw error.create({
    name: 'NOT_ALLOW_UPDATE',
    message: 'Record does not support updates. Please delete and recreate.',
    notifyOff: true
});
```

**DELETE Operations:**
```javascript
// Cleanup existing transfer order
LNKERLIB.pri_irToLinker_delExistTrnfrOrd(scriptContext.newRecord);
```

---

### 6. Field Change Tracking (`pri_cnt_trackNoteChanges_ss.js`)

**Primary Purpose:** Audit trail for critical field changes via automated note creation.

#### afterSubmit Processing

```javascript
// Script parameters define:
// - Field names to track (comma-separated)
// - Note type
// - Note title
// - Note direction

// CREATE Mode: Currently disabled (commented out)
// Would log initial values

// EDIT/XEDIT Mode:
for (var i = 0; i < fieldNames.length; i++) {
    var oldValue = context.oldRecord.getValue(fieldName);
    var newValue = context.newRecord.getValue(fieldName);

    if (oldValue != newValue) {
        logChange(context, {
            noteTitle: noteTitle,
            noteDirection: noteDirection,
            noteText: (oldValue ? oldValue : "'blank'"),
            noteType: noteType
        });
    }
}
```

**Note Creation Logic:**
- Handles different record types (customer, transaction, custom record)
- Creates note with old value as text
- Links note to appropriate parent record
- Preserves audit trail for compliance

---

### 7. Purchase Order Processing (`pri_purchord_ss.js`)

**Primary Purpose:** Item version sourcing, production management PO line validation, direct import handling.

#### beforeLoad Features

**VIEW Mode:**
- Adds item group receipts display

**CREATE Mode:**
```javascript
pri_initialDirectImportPO(scriptContext);
// Initializes direct import fields for manufacturer-to-customer flow
```

**COPY Mode:**
```javascript
pri_clearDirectImportFlds(scriptContext);
// Clears direct import flags to prevent duplication
```

#### beforeSubmit Validation

**Production Management PO Line Processing:**

```javascript
// 1. Default PM PO line for item group components
pri_CntPMPO_defaultInGroupPoLn(scriptContext);
// Auto-assigns production management line to in-group items

// 2. Validate mandatory items have PM PO line
pri_CntPMPO_validateNeedItmPoLn(scriptContext);
// Ensures critical items linked to production management

// 3. Validate non-group item PM PO line values
pri_CntPMPO_validateNonInGrpItmPoLn(scriptContext);
// Verifies standalone items have valid PM references
```

**Item Version Sourcing:**
```javascript
pri_ItmVer_sourceIvPriceNameDesc(scriptContext);
// Sources from item version when available:
// - Price (rate)
// - Vendor name
// - Description
// Overrides standard item fields for procurement flow
```

#### afterSubmit Processing

**Direct Import Synchronization:**
```javascript
// Sync PO to Sales Order
pri_syncDirectImportPOtoSOLn(scriptContext);
// Links PO lines to SO lines for drop-ship scenarios

// Update PO fields
pri_syncDirectImportPOFlds(scriptContext);
// Updates ship-to address and related fields
```

---

## Scheduled Automation Processes

### 1. Production Management Line Queue Processor (`pri_cntProdMgmtLn_sc.js`)

**Queue Name:** `FC_CALC_PPOLNS`
**Purpose:** Calculate quantity received for production PO lines when item receipts created.

#### Execution Flow

```javascript
function execute_calcQtyReceivedPOTO(scriptContext) {
    var MIN_USAGE_THRESHOLD = 500; // Governance threshold
    var QUEUE_NAME = "FC_CALC_PPOLNS";

    while (qEntry = qmEngine.getNextQueueEntry(QUEUE_NAME)) {
        try {
            var arrProdPOLns = JSON.parse(qEntry.parms);

            for (var poLnIdx = 0; poLnIdx < arrProdPOLns.length; poLnIdx++) {
                var clsProdPoLine = new CNTPMLIB.PRODPOLINE(arrProdPOLns[poLnIdx]);

                // Aggregate quantities from:
                // - Item receipts created from PO
                // - Item receipts created from TO
                clsProdPoLine.calcQtyReceivedPOTO();
            }

            qmEngine.markQueueEntryComplete(qEntry.id);

        } catch (e) {
            qmEngine.abandonQueueEntry(qEntry.id, qEntry.parms, "ERROR: " + e.message);
        }

        // Auto-reschedule if running low on governance
        if (runtime.getCurrentScript().getRemainingUsage() < MIN_USAGE_THRESHOLD) {
            rescheduleScript();
            return;
        }
    }
}
```

**Trigger Points:**
- Item receipt afterSubmit (production management lines affected)
- Async to avoid timeout on large receipts

---

### 2. Production PO Copy Queue Processor (`pri_cntProdMgmtPo_sc.js`)

**Queue Name:** `COPY_PPO`
**Purpose:** Copy production purchase order with all detail lines.

#### Processing Logic

```javascript
function execute(context) {
    var qEntry = qmEngine.getNextQueueEntry("COPY_PPO");

    while (qEntry !== null) {
        var objPPO = JSON.parse(qEntry.parms);
        var intCopyPPOId = objPPO.copyppoid;
        var intNewPPOId = objPPO.newppoid;

        // Search all lines from source PPO
        var objContrSrch = search.create({
            type: IDLIB.REC.CNTPRODMGMTLN.ID,
            filters: [
                [IDLIB.REC.CNTPRODMGMTLN.PARENT, 'anyof', [intCopyPPOId]],
                'AND',
                ['isinactive', 'is', 'F']
            ],
            columns: arrPPOCols // All production management line fields
        });

        // Copy each line to new PPO
        objPagedData.pageRanges.forEach(function(pageRange) {
            var objMyCurPage = objPagedData.fetch({index: pageRange.index});

            for (var idx in objMyCurPage.data) {
                var objNewPPOLnId = record.copy({
                    type: IDLIB.REC.CNTPRODMGMTLN.ID,
                    id: intPPOLnId
                });

                // Update parent reference and reset status
                objNewPPOLnId.setValue(IDLIB.REC.CNTPRODMGMTLN.PARENT, intNewPPOId);
                objNewPPOLnId.setValue(IDLIB.REC.CNTPRODMGMTLN.STATUS,
                                       IDLIB.REC.CNTPMLINESTATUS.UNLOCKED);
                objNewPPOLnId.save();
            }
        });

        qmEngine.markQueueEntryComplete(qEntry.id);
    }
}
```

**Use Case:** When copying complex production purchase orders with hundreds of line items.

---

### 3. Container Touch Processor (`pri_containerTouch_sc.js`)

**Queue Name:** `TOUCH_CONTAINER`
**Purpose:** Asynchronous container updates triggered by item receipt processing.

#### Execution Logic

```javascript
function execute(context) {
    var qEntry = qmEngine.getNextQueueEntry("TOUCH_CONTAINER");

    while (qEntry !== null) {
        var objParams = JSON.parse(qEntry.parms);

        var objCtnRec = record.load({
            type: objParams.type,
            id: objParams.id
        });

        // Sync item receipt custom field values to container
        if (objParams.itemreceipt) {
            var objIRFlds = search.lookupFields({
                type: record.Type.ITEM_RECEIPT,
                id: objParams.itemreceipt,
                columns: [
                    'custbody_pri_frgt_cnt_ownership',
                    'custbody_pri_frgt_cnt_departure_port'
                ]
            });

            // Update container ownership
            if (objIRFlds['custbody_pri_frgt_cnt_ownership']) {
                objCtnRec.setValue('custrecord_pri_frgt_cnt_ownership',
                                   objIRFlds['custbody_pri_frgt_cnt_ownership'][0].value);
            }

            // Update departure port
            if (objIRFlds['custbody_pri_frgt_cnt_departure_port']) {
                objCtnRec.setValue('custrecord_pri_frgt_cnt_dept_port',
                                   objIRFlds['custbody_pri_frgt_cnt_departure_port'][0].value);
            }
        }

        // Save triggers container UE which updates related TO dates
        objCtnRec.save({
            enableSourcing: true,
            ignoreMandatoryFields: true
        });

        qmEngine.markQueueEntryComplete(qEntry.id);
    }
}
```

**Trigger:** Item receipt afterSubmit → Queue container touch → Async update

---

### 4. Vessel/Container Mark In-Transit Processor (`pri_veslCtn_markIntransit_sc.js`)

**Queue Name:** `MARK_INTRANSIT`
**Purpose:** Transition vessels/containers to in-transit status, create item fulfillments from transfer orders.

#### Complex Workflow

```javascript
function execute(context) {
    var TRGTSTATUS = ASEngine.readAppSetting('Prolecto Freight Container & Landed Cost',
                                             'Target Status of Mark In-transit');
    var qEntry = qmEngine.getNextQueueEntry("MARK_INTRANSIT");

    while (qEntry !== null) {
        var objVeslCtn = JSON.parse(qEntry.parms);

        switch (objVeslCtn.type) {
            case IDLIB.REC.FRGTCNTVSL.ID: // Vessel
                // Find all containers for vessel
                var objCtnRes = search.create({
                    type: IDLIB.REC.FRGTCNT.ID,
                    filters: [
                        ['isInactive', 'is', 'F'],
                        'and',
                        [IDLIB.REC.FRGTCNT.CNTVSL, 'anyof', [intRecordId]]
                    ]
                });

                objPagedData.pageRanges.forEach(function(pageRange) {
                    for (var idx in objMyCurPage.data) {
                        // For each container:
                        // 1. Load container
                        // 2. Get transfer order
                        // 3. Fulfill transfer order (create item fulfillment)
                        intItmShpId = fulfill_TO(intTrnfrOrdId);
                    }
                });

                // If all containers fulfilled successfully
                if (!bolHasTOFailCreateIF) {
                    // Move vessel to target status
                    record.submitFields({
                        type: IDLIB.REC.FRGTCNTVSL.ID,
                        id: intRecordId,
                        values: {
                            [IDLIB.REC.FRGTCNTVSL.LOGSTATUS]: TRGTSTATUS
                        }
                    });
                }
                break;

            case IDLIB.REC.FRGTCNT.ID: // Single Container
                var objCtnRec = record.load({
                    type: IDLIB.REC.FRGTCNT.ID,
                    id: intRecordId
                });

                var intTrnfrOrdId = objCtnRec.getValue(IDLIB.REC.FRGTCNT.TRANSFERORD);
                var intItmShpId = fulfill_TO(intTrnfrOrdId);

                if (intItmShpId) {
                    // Move container to target status
                    objCtnRec.setValue(IDLIB.REC.FRGTCNT.LOGSTATUS, TRGTSTATUS);
                    objCtnRec.save({
                        ignoreMandatoryFields: true,
                        enablesourcing: true
                    });
                }
                break;
        }

        qmEngine.markQueueEntryComplete(qEntry.id, 'Created/Linked TO Item Fulfillment ID: #' + intItmShpId);
    }
}
```

#### Transfer Order Fulfillment Logic

```javascript
function fulfill_TO(intTrnfrOrdId) {
    if (!intTrnfrOrdId) return;

    var objTrnfrOrdRec = record.load({
        type: record.Type.TRANSFER_ORDER,
        id: intTrnfrOrdId
    });

    // Status check - skip if already received or pending receipt
    switch (objTrnfrOrdRec.getValue('status')) {
        case 'Received':
        case 'Pending Receipt':
            return findExistingTOItemFulfillment(intTrnfrOrdId);
    }

    // Validate items committed to transfer order
    var bolItmCommitedTO = true;
    for (var intTOIdx = 0; intTOIdx < objTrnfrOrdRec.getLineCount('item'); intTOIdx++) {
        var intQty = objTrnfrOrdRec.getSublistValue({
            sublistId: 'item', fieldId: 'quantity', line: intTOIdx
        });
        var intCommitQty = objTrnfrOrdRec.getSublistValue({
            sublistId: 'item', fieldId: 'quantitycommitted', line: intTOIdx
        });
        var intFulfillQty = objTrnfrOrdRec.getSublistValue({
            sublistId: 'item', fieldId: 'quantityfulfilled', line: intTOIdx
        });

        if ((intQty - intFulfillQty) > intCommitQty) {
            bolItmCommitedTO = false;
            break;
        }
    }

    if (!bolItmCommitedTO) return; // Items not committed yet

    // Transform TO to Item Fulfillment
    var objItemShipRec = record.transform({
        fromType: record.Type.TRANSFER_ORDER,
        fromId: intTrnfrOrdId,
        toType: record.Type.ITEM_FULFILLMENT
    });

    objItemShipRec.setValue('trandate', objTrnfrOrdRec.getValue('trandate'));
    objItemShipRec.setValue('shipstatus', 'C'); // Shipped Complete
    objItemShipRec.setValue('memo', 'Auto Generated by Freight Container In-Transit Module');

    // Set all line quantities to remaining quantity
    for (var i = 0; i < objItemShipRec.getLineCount('item'); i++) {
        objItemShipRec.setSublistValue({
            sublistId: 'item',
            fieldId: 'quantity',
            line: i,
            value: objItemShipRec.getSublistValue({
                sublistId: 'item',
                fieldId: 'quantityremaining',
                line: i
            })
        });
    }

    var intItmShpId = objItemShipRec.save();
    log.audit('fulfill_TO', 'Created Item Fulfillment: ' + intItmShpId);

    return intItmShpId;
}
```

**Trigger Points:**
- Button click on vessel/container record
- Queued for async processing to handle multiple containers

---

## Business Rule Engines

### 1. Landed Cost Calculation Engine

**Implementation:** `LCTEMPLATE` class in `pri_itemrcpt_lib.js`

#### Cost Category Structure

```javascript
this.OBJCATDETAILS[intCostCat] = {
    DETAILS: [],        // Array of template detail lines
    ACCOUNT: intAccountId,  // GL account for this cost category
    AMOUNT: 0,          // Total allocated amount
    ALLMTH: {}          // Allocation methods grouped
};
```

#### Allocation Methods

**1. Per Quantity:**
```javascript
LCTEMPLATE.prototype.calcPerQuantity = function(arrObjTemplateDtl, intItemQty) {
    var intAddAmt = 0;
    for (var i = 0; i < arrObjTemplateDtl.length; i++) {
        var objTemplateDtl = arrObjTemplateDtl[i];
        // Factor is cost per unit
        intAddAmt += parseFloat(intItemQty * objTemplateDtl.FACTOR);
    }
    return intAddAmt;
};
```

**2. Flat Amount:**
```javascript
LCTEMPLATE.prototype.calcFlatAmount = function(arrObjTemplateDtl) {
    var intAddAmt = 0;
    for (var i = 0; i < arrObjTemplateDtl.length; i++) {
        var objTemplateDtl = arrObjTemplateDtl[i];
        // Factor is flat dollar amount
        intAddAmt += parseFloat(objTemplateDtl.FACTOR);
    }
    return intAddAmt;
};
```

**3. Percentage Value:**
```javascript
LCTEMPLATE.prototype.calcPercentageVal = function(arrObjTemplateDtl, intItemQty, numItemRate) {
    var intAddAmt = 0;

    // Case 1: Item has rate
    if (numItemRate) {
        for (var i = 0; i < arrObjTemplateDtl.length; i++) {
            var objTemplateDtl = arrObjTemplateDtl[i];
            // Factor is percentage (convert to decimal)
            intAddAmt += parseFloat(objTemplateDtl.FACTOR * 0.01 * intItemQty * numItemRate);
        }
        return intAddAmt;
    }

    // Case 2: Transfer order with no rate - lookup location average cost
    if (!numItemRate && this.strTranFromTranType == record.Type.TRANSFER_ORDER) {
        var intLcRatePrf = this.getItemLC_ratePrf();

        switch (intLcRatePrf.toString()) {
            case IDLIB.REC.FRGTCNTLCRATETYPE.LOCATIONAVERAGE.toString():
                // Use average cost at transfer FROM location
                numItemRate = this.getItemLocAverageCost(this.intItemId, this.intTranTrnfrLoc);
                break;

            case IDLIB.REC.FRGTCNTLCRATETYPE.ITEMRECEIPTCOST.toString():
                // Use cost from originating item receipt
                numItemRate = this.getItemReceiptCost(this.intTranId, this.objTranFrom,
                                                       this.intItemLine);
                break;
        }

        for (var i = 0; i < arrObjTemplateDtl.length; i++) {
            var objTemplateDtl = arrObjTemplateDtl[i];
            intAddAmt += parseFloat(objTemplateDtl.FACTOR * 0.01 * intItemQty * numItemRate);
        }
    }

    return intAddAmt;
};
```

#### Container Cost Mapping

**Body Mode:**
```javascript
// Map container costs to item receipt landed cost fields
// Configuration via script parameter:
[{
    "fromCtn": "custrecord_pri_frgt_cnt_cost_clr_forward",
    "toItmrcpt": "landedcostamount1"
}, {
    "fromCtn": "custrecord_pri_frgt_cnt_cost_freight",
    "toItmrcpt": "landedcostamount2"
}]
```

**Per Line Template Mode:**
- Uses cost templates defined per currency and location
- Allocates costs based on:
  - Item quantity
  - Item value (rate × quantity)
  - Flat fees
  - Percentage of value
- Creates journal entries for landed cost variance

---

### 2. Production Management Pricing Engine

**Implementation:** `PRODPOLINE` class in `pri_cntProdMgmt_lib.js`

#### Price Locking Mechanism

```javascript
PRODPOLINE.prototype.holdPrice = function() {
    // Only update when status NOT locked
    if (this.isStayPriceLocked()) return true;

    // Get current item member structure
    var arrItemMembData = this.getItemMembInfo();

    // Store as JSON in hold price data field
    this.scriptContext.newRecord.setValue(
        IDLIB.REC.CNTPRODMGMTLN.HOLDPRICEDATA,
        JSON.stringify(arrItemMembData)
    );
};
```

#### Item Group Member Pricing

```javascript
PRODPOLINE.prototype.getItemMembInfo = function() {
    var arrItemMembData = [];
    var numSumValue = 0;

    // For item groups and kits:
    var objItemSchRes = search.create({
        type: 'item',
        filters: [['internalid', 'anyof', [intItemId]]],
        columns: [
            search.createColumn({name: 'memberitem', sort: search.Sort.ASC}),
            search.createColumn({name: 'cost', join: 'memberitem'}),
            search.createColumn({name: 'lastpurchaseprice', join: 'memberitem'}),
            search.createColumn({name: 'memberquantity'}),
            search.createColumn({name: IDLIB.REC.N_ITEM.ITEMVERREF, join: 'memberitem'})
        ]
    }).run().getRange(0, 999);

    for (var i = 0; i < objItemSchRes.length; i++) {
        var intMemItemId = objItemSchRes[i].getValue('memberitem');
        var strMembItemType = objItemSchRes[i].getValue({name: 'type', join: 'memberitem'});

        // Get price from cost or last purchase price
        var intItemCost = objItemSchRes[i].getValue({name: 'cost', join: 'memberitem'});
        var numItemLastPrice = objItemSchRes[i].getValue({
            name: 'lastpurchaseprice', join: 'memberitem'
        });
        var strItemDynamicPrice = (intItemCost || numItemLastPrice);

        // Special handling for discount/markup items
        switch (strMembItemType) {
            case 'Discount':
                strItemDynamicPrice = record.load({
                    type: 'discountitem',
                    id: intMemItemId
                }).getValue('rate');
                break;

            case 'Markup':
                strItemDynamicPrice = record.load({
                    type: 'markupitem',
                    id: intMemItemId
                }).getValue('rate');
                break;
        }

        // Override with item version pricing if available
        var intItemVersionId = objItemSchRes[i].getValue({
            name: IDLIB.REC.N_ITEM.ITEMVERREF,
            join: 'memberitem'
        });

        if (intItemVersionId) {
            var objIvFld = search.lookupFields({
                type: IDLIB.REC.ITEMVER.ID,
                id: intItemVersionId,
                columns: [
                    IDLIB.REC.ITEMVER.DESC,
                    IDLIB.REC.ITEMVER.VENDOR_NAME,
                    IDLIB.REC.ITEMVER.RATE
                ]
            });

            strItemDynamicDesc = objIvFld[IDLIB.REC.ITEMVER.DESC];
            strItemDynamicVendName = objIvFld[IDLIB.REC.ITEMVER.VENDOR_NAME];
            strItemDynamicPrice = objIvFld[IDLIB.REC.ITEMVER.RATE] || 0;
        }

        var intMemQty = objItemSchRes[i].getValue('memberquantity');
        var numItemValue = strItemDynamicPrice * intMemQty;

        arrItemMembData.push({
            itemId: intMemItemId,
            itemType: strMembItemType,
            quantity: intMemQty,
            rate: strItemDynamicPrice,
            value: numItemValue,
            description: strItemDynamicDesc,
            vendorName: strItemDynamicVendName
        });

        numSumValue += numItemValue;
    }

    return arrItemMembData;
};
```

#### Quantity Received Calculation

```javascript
PRODPOLINE.prototype.calcQtyReceivedPOTO = function() {
    // Calculate from item receipts created from PO
    var qtyReceivedPO = search.create({
        type: record.Type.ITEM_RECEIPT,
        filters: [
            ['type', 'anyof', 'ItemRcpt'],
            'AND',
            ['createdfrom', 'anyof', [this.intPurchaseOrderId]],
            'AND',
            ['mainline', 'is', 'F'],
            'AND',
            ['item', 'anyof', [this.intItemId]]
        ],
        columns: [
            search.createColumn({
                name: 'quantity',
                summary: search.Summary.SUM
            })
        ]
    }).run().getRange(0, 1);

    // Calculate from item receipts created from TO
    var qtyReceivedTO = search.create({
        type: record.Type.ITEM_RECEIPT,
        filters: [
            ['type', 'anyof', 'ItemRcpt'],
            'AND',
            ['createdfrom.type', 'anyof', 'TrnfrOrd'],
            'AND',
            ['createdfrom.custbody_pri_frgt_cnt', 'anyof', [this.intContainerId]],
            'AND',
            ['mainline', 'is', 'F'],
            'AND',
            ['item', 'anyof', [this.intItemId]]
        ],
        columns: [
            search.createColumn({
                name: 'quantity',
                summary: search.Summary.SUM
            })
        ]
    }).run().getRange(0, 1);

    // Update production PO line record
    record.submitFields({
        type: IDLIB.REC.CNTPRODMGMTLN.ID,
        id: this.intProdPOLnId,
        values: {
            [IDLIB.REC.CNTPRODMGMTLN.QTY_RECEIVED_PO]: qtyReceivedPO || 0,
            [IDLIB.REC.CNTPRODMGMTLN.QTY_RECEIVED_TO]: qtyReceivedTO || 0
        }
    });
};
```

---

### 3. Inventory Count Generation Engine

**Implementation:** `pri_generateInventoryCounts.js`

#### Purpose
Calculates theoretical inventory levels across locations by replaying all transactions from a start date.

#### Transaction Processing Logic

**Purchase Orders:**
```javascript
case record.Type.PURCHASE_ORDER:
    if (location == MANUFACTURER_LOCATION) {
        // For manufacturer POs, track as on-order for ultimate destination
        obj.location = ultimateLocation;
        obj.locationId = ultimateLocationId;
        obj.quantities.onOrder = qty;
    }
    break;
```

**Inventory Adjustments:**
```javascript
case record.Type.INVENTORY_ADJUSTMENT:
    var ultLoc = ultimateLocation;

    if (ultLoc && ultLoc != NO_LOCATION_SELECTED) {
        // Adjustments with ultimate location = in-transit setup (legacy 1.0)
        // FROM location
        obj.location = currentLocation;
        obj.quantities.inTransitFrom = qty;
        accumulateQuantities(itemQuantities, obj);

        // TO location
        obj.location = ultLoc;
        obj.quantities.inTransitTo = qty;
        accumulateQuantities(itemQuantities, obj);
    } else {
        // Standard adjustment
        obj.location = currentLocation;
        obj.quantities.onHand = qty;
        accumulateQuantities(itemQuantities, obj);
    }
    break;
```

**Item Receipts from PO:**
```javascript
case record.Type.ITEM_RECEIPT:
    var createdFromType = searchResult.getValue({name: 'type', join: 'createdFrom'});

    switch (createdFromType) {
        case 'PurchOrd':
            if (location == MANUFACTURER_LOCATION) {
                // Manufacturer receipt = start in-transit
                obj.location = MANUFACTURER_LOCATION;
                obj.quantities.inTransitFrom = qty;
                accumulateQuantities(itemQuantities, obj);

                obj.location = ultimateLocation;
                obj.quantities.inTransitTo = qty;
                obj.quantities.onOrder = -qty; // Reduce on-order
                accumulateQuantities(itemQuantities, obj);
            } else {
                // Direct receipt to location
                obj.location = location;
                obj.quantities.onHand = qty;
                accumulateQuantities(itemQuantities, obj);
            }
            break;

        case 'TrnfrOrd':
            // Receiving location
            obj.location = location; // Destination
            obj.quantities.onHand = qty;
            obj.quantities.inTransitTo = -qty; // Reduce in-transit TO
            accumulateQuantities(itemQuantities, obj);

            // Sending location
            obj.location = transferLocation; // Source
            obj.quantities.inTransitFrom = -qty; // Reduce in-transit FROM
            accumulateQuantities(itemQuantities, obj);
            break;

        case 'RtnAuth':
            // RMA return
            obj.location = location;
            obj.quantities.onHand = qty;
            accumulateQuantities(itemQuantities, obj);
            break;
    }
    break;
```

**Item Fulfillments from TO:**
```javascript
case record.Type.ITEM_FULFILLMENT:
    var createdFromType = searchResult.getValue({name: 'type', join: 'createdFrom'});

    switch (createdFromType) {
        case 'TrnfrOrd':
            if (location == MANUFACTURER_LOCATION) {
                // Manufacturer fulfillments handled via PO flow
            } else {
                // Sending location
                obj.location = location;
                obj.quantities.onHand = qty; // Reduce on-hand (negative qty)
                obj.quantities.inTransitFrom = -qty; // Increase in-transit FROM
                accumulateQuantities(itemQuantities, obj);

                // Receiving location
                obj.location = transferLocation;
                obj.quantities.inTransitTo = -qty; // Increase in-transit TO
                accumulateQuantities(itemQuantities, obj);
            }
            break;

        case 'SalesOrd':
            // Sales order fulfillment
            obj.location = location;
            obj.quantities.onHand = qty; // Reduce on-hand (negative qty)
            accumulateQuantities(itemQuantities, obj);
            break;
    }
    break;
```

#### Accumulation Logic

```javascript
function accumulateQuantities(objList, selectedLocations, obj, tranId, tranInfo, debug) {
    // Filter by selected locations
    if (selectedLocations.length > 0) {
        if (selectedLocations.indexOf(obj.location) < 0) return;
    }

    // Filter by master location list
    if (LOCATION_LIST.length > 0) {
        if (LOCATION_LIST.indexOf(obj.location) < 0) return;
    }

    // Find existing entry or create new
    var ndx = objList.length;
    for (var i = 0; i < objList.length; i++) {
        if (objList[i].item == obj.item && objList[i].location == obj.location) {
            ndx = i;
            break;
        }
    }

    if (ndx == objList.length) {
        // New entry
        objList.push(obj);
    } else {
        // Accumulate to existing
        objList[ndx].quantities.onHand += Number(obj.quantities.onHand);
        objList[ndx].quantities.inTransitFrom += Number(obj.quantities.inTransitFrom);
        objList[ndx].quantities.inTransitTo += Number(obj.quantities.inTransitTo);
        objList[ndx].quantities.onOrder += Number(obj.quantities.onOrder);
    }
}
```

#### Period Caching

**Optimization:** Pre-calculated periods stored in custom record to avoid re-processing old data.

```javascript
if (usePeriodTable) {
    var periodSearch = search.create({
        type: "customrecord_pri_inv_count_prd_sum",
        columns: [
            "custrecord_pri_inv_cnt_prd_sum_period",
            "custrecord_pri_inv_cnt_prd_sum_inv_count"
        ]
    }).run().getRange(0, 1000);

    var periodList = [];

    for (var i = 0; i < periodSearch.length; i++) {
        periodList.push(periodSearch[i].getValue({
            name: "custrecord_pri_inv_cnt_prd_sum_period"
        }));

        var itemsObj = JSON.parse(periodSearch[i].getValue({
            name: "custrecord_pri_inv_cnt_prd_sum_inv_count"
        }));

        // Load cached quantities
        for (var x in itemsObj) {
            var itemObj = itemsObj[x];
            var obj = getItemObject(itemObj.itemId, itemObj.itemName);
            obj.quantities = itemObj.quantities;
            obj.location = itemObj.location;
            obj.locationId = itemObj.locationId;

            accumulateQuantities(itemQuantities, selectedLocations, obj);
        }
    }

    // Exclude cached periods from search
    if (periodList.length > 0) {
        invSearch.filters.push(search.createFilter({
            name: "internalid",
            join: "accountingperiod",
            operator: search.Operator.NONEOF,
            values: periodList
        }));
    }
}
```

---

## State Machine Transitions

### Container Status Lifecycle

```
┌─────────────────┐
│  At Origin Port │ (Initial state)
└────────┬────────┘
         │
         │ Mark In-Transit button
         │ (creates item fulfillment from TO)
         ↓
┌─────────────────┐
│   In Transit    │
└────────┬────────┘
         │
         │ Receive Container button
         │ (creates item receipts from TO)
         ↓
┌─────────────────┐
│ At Destination  │
└────────┬────────┘
         │
         │ Close Container
         ↓
┌─────────────────┐
│     Closed      │ (Terminal state)
└─────────────────┘
```

### Status Validation Rules

**Edit Restrictions:**
```javascript
// Item receipt locked if container not at origin
TRANLIB.pri_itemrcpt_lockByCtnStatus(scriptContext);

// Cannot change container from:
// - In Transit → back to Origin
// - At Destination → back to In Transit
TRANLIB.pri_ctn_validateCtnStatus(scriptContext);
```

**Fulfillment Prerequisites:**
```javascript
// Mark In-Transit validation:
// 1. Transfer order exists
// 2. Transfer order status NOT already fulfilled
// 3. Items committed to transfer order (quantitycommitted >= quantity - quantityfulfilled)
// 4. Container status = At Origin Port

if ((intQty - intFulfillQty) > intCommitQty) {
    bolItmCommitedTO = false;
    // Cannot fulfill - items not committed
}
```

---

### Transfer Order Status Flow

```
┌──────────────┐
│ Pending      │ (Created from container)
│ Approval     │
└──────┬───────┘
       │ Approve
       ↓
┌──────────────┐
│ Pending      │ (Items not yet committed)
│ Fulfillment  │
└──────┬───────┘
       │ Commit inventory
       ↓
┌──────────────┐
│ Pending      │ (Ready for fulfillment)
│ Fulfillment  │
└──────┬───────┘
       │ Mark In-Transit (creates item fulfillment)
       ↓
┌──────────────┐
│ Pending      │ (In-transit to destination)
│ Receipt      │
└──────┬───────┘
       │ Receive Container (creates item receipt)
       ↓
┌──────────────┐
│  Received    │ (Complete)
└──────────────┘
```

---

### Production Management Line Status

```
┌─────────────┐
│  Unlocked   │ (Pricing can change)
└──────┬──────┘
       │ Price Lock action
       ↓
┌─────────────┐
│   Locked    │ (Pricing frozen, stored in JSON)
└──────┬──────┘
       │ Cannot unlock automatically
       ↓
┌─────────────┐
│  Received   │ (Item receipts created, quantities tracked)
└─────────────┘
```

**Lock Behavior:**
```javascript
PRODPOLINE.prototype.isStayPriceLocked = function() {
    var intStatus = currentRecord.getValue(IDLIB.REC.CNTPRODMGMTLN.STATUS);
    var intStatus_old = oldRecord.getValue(IDLIB.REC.CNTPRODMGMTLN.STATUS);

    // If both old and new status = LOCKED, stay locked
    if (intStatus == IDLIB.REC.CNTPMLINESTATUS.LOCKED &&
        intStatus_old == IDLIB.REC.CNTPMLINESTATUS.LOCKED) {
        return true; // Do not recalculate prices
    }

    return false;
};
```

---

## Integration Points

### 1. NetSuite Standard Records

#### Purchase Order Integration
- **Field Extensions:**
  - `custbody_pri_frgt_cnt` - Container reference
  - `custbody_pri_frgt_loc_ult` - Ultimate destination location
  - `custbody_pri_frgt_cnt_ownership` - Ownership type
  - `custbody_pri_frgt_cnt_departure_port` - Port of departure

- **Line Item Extensions:**
  - `custcol_pri_cntprodmgmt_poline` - Production management line reference
  - `custcol_pri_item_version` - Item version for pricing/description overrides

- **Workflows:**
  1. PO creation → Validate PM PO lines → Source item version data
  2. PO for manufacturer → Track as on-order for ultimate location
  3. Direct import POs → Sync to sales order lines

#### Item Receipt Integration
- **Container Linkage:**
  - Body level: Container reference
  - Line level: Distribution management allocation

- **Landed Cost Application:**
  - Body mode: Container costs → IR landed cost fields
  - Per-line template mode: Cost allocation via templates

- **Workflows:**
  1. IR from PO (manufacturer) → Create in-transit adjustments
  2. IR from TO → Update container status, reduce in-transit quantities
  3. IR creation → Queue production PO line quantity updates
  4. IR creation → Touch container (queue async update)

#### Transfer Order Integration
- **Container Linkage:**
  - `custbody_pri_frgt_cnt` - Container driving the transfer

- **Synchronization:**
  - Container dates → TO transaction date
  - Container estimated destination → TO expected receipt date
  - Container name → TO memo

- **Workflows:**
  1. Container created → Button to create TO
  2. Container modified → Sync dates to TO
  3. Mark In-Transit → Create item fulfillment from TO
  4. Receive Container → Create item receipts from TO

#### Item Fulfillment Integration
- **Auto-generation:**
  - Triggered by Mark In-Transit workflow
  - Created from transfer order
  - Ship status = Complete
  - Memo = "Auto Generated by Freight Container In-Transit Module"

- **Quantity Logic:**
  - All lines set to `quantityremaining`
  - Transaction date = Transfer order transaction date

---

### 2. Custom Record Integrations

#### Production Management PO (`customrecord_pri_cntprodmgmt`)
- **Purpose:** Header record for production purchase order
- **Linked To:** NetSuite Purchase Order
- **Children:** Production management lines

#### Production Management PO Line (`customrecord_pri_cntprodmgmtln`)
- **Purpose:** Detailed item/pricing structure for production orders
- **Fields:**
  - Item, quantity, rate
  - Hold price data (JSON of locked pricing)
  - Status (unlocked/locked)
  - Line number
  - Quantity received PO
  - Quantity received TO

- **Calculations:**
  - Item group member pricing
  - Item version overrides
  - Discount/markup application
  - Quantity received aggregation

#### Container Distribution Management (`customrecord_pri_cntdistmgmt`)
- **Purpose:** Allocation of PO line quantities across multiple containers/destinations
- **Naming:** `PO# - Item - Increment` (e.g., "12345 - SHOE001 - 001")
- **Validation:**
  - Line number must exist on parent PO
  - Total allocated quantity ≤ PO line quantity
  - Cannot over-allocate

#### Item Receipt to Linker (`customrecord_pri_irtolinker`)
- **Purpose:** Junction table linking item receipts to containers and transfer orders
- **Immutable:** Cannot edit after creation (delete/recreate only)
- **Auto-creation:** Triggers transfer order generation on save

#### Freight Container (`customrecord_pri_frgt_cnt`)
- **Purpose:** Container tracking master record
- **Key Fields:**
  - Name (must be unique)
  - Status (origin/in-transit/destination/closed)
  - Vessel reference
  - Transfer order reference
  - Dates (departure, arrival estimated, arrival actual)
  - Costs (freight, clearance, forwarding, etc.)
  - Ownership, departure port

- **Workflows:** Lifecycle from creation → mark in-transit → receive → close

#### Vessel Container (`customrecord_pri_frgt_cnt_vsl`)
- **Purpose:** Group multiple containers on same vessel
- **Workflow:** Mark in-transit on vessel → Marks all containers in-transit

---

### 3. Queue Management Engine Integration

**Queue System:** `/.bundle/132118/PRI_QM_Engine`

#### Queue Structure
```javascript
// Queue entry format:
{
    id: queueEntryId,
    parms: JSON.stringify({
        // Queue-specific parameters
    }),
    status: 'pending' | 'processing' | 'complete' | 'abandoned',
    created: timestamp,
    modified: timestamp,
    note: 'Processing note'
}
```

#### Queue Operations

**Add to Queue:**
```javascript
qmEngine.addQueueEntry(QUEUE_NAME, JSON.stringify(params), priority);
```

**Get Next Entry:**
```javascript
var qEntry = qmEngine.getNextQueueEntry(QUEUE_NAME);
// Auto-marks as 'processing'
```

**Complete Entry:**
```javascript
qmEngine.markQueueEntryComplete(qEntry.id, 'Success note');
```

**Abandon Entry:**
```javascript
qmEngine.abandonQueueEntry(qEntry.id, qEntry.parms, 'Error: ' + errorMessage);
// Entry returns to queue for retry
```

**Incomplete Entry:**
```javascript
qmEngine.markQueueEntryIncomplete(qEntry.id, parms, 'Resource limit reached');
// Entry saved for later processing
```

#### Active Queues

| Queue Name | Purpose | Trigger | Processor Script |
|------------|---------|---------|------------------|
| `TOUCH_CONTAINER` | Async container updates | Item receipt afterSubmit | `pri_containerTouch_sc` |
| `FC_CALC_PPOLNS` | Production PO line qty updates | Item receipt afterSubmit | `pri_cntProdMgmtLn_sc` |
| `COPY_PPO` | Copy production PO with lines | User action | `pri_cntProdMgmtPo_sc` |
| `MARK_INTRANSIT` | Vessel/container in-transit | Button click | `pri_veslCtn_markIntransit_sc` |

---

### 4. App Settings Engine Integration

**Settings System:** `/.bundle/132118/PRI_AS_Engine`

#### Usage Pattern
```javascript
// Read setting
var TRGTSTATUS = ASEngine.readAppSetting(
    'Prolecto Freight Container & Landed Cost',
    'Target Status of Mark In-transit'
);

// Example settings:
// - Target status for in-transit transition
// - Default bin for landed cost items
// - Inventory location list for reporting
// - Legacy container handling flags
```

---

## Performance Optimizations

### 1. Governance Management

**Pattern:** Auto-reschedule before hitting limits

```javascript
var MIN_USAGE_THRESHOLD = 500;

if (runtime.getCurrentScript().getRemainingUsage() < MIN_USAGE_THRESHOLD) {
    log.debug(funcName, "Running out of resources, rescheduling");

    try {
        var scriptTask = task.create({
            taskType: task.TaskType.SCHEDULED_SCRIPT
        });
        scriptTask.scriptId = SCRIPT_ID;
        var scriptTaskId = scriptTask.submit();
        log.debug(funcName, "Script rescheduled");
    } catch (e1) {
        log.error(funcName, "Failed to reschedule: " + e1.message);
    }

    return; // Exit current execution
}
```

---

### 2. Batch Processing

**Paged Search Pattern:**
```javascript
var objPagedData = objContrSrch.runPaged({
    pageSize: 1000
});

objPagedData.pageRanges.forEach(function(pageRange) {
    var objMyCurPage = objPagedData.fetch({
        index: pageRange.index
    });

    for (var idx in objMyCurPage.data) {
        var objOneSrchRes = objMyCurPage.data[idx];
        // Process each result
    }
});
```

**Benefits:**
- Processes large datasets without timeout
- Controlled memory usage
- Checkpoint between pages

---

### 3. Cache Utilization

**Landed Cost Template Caching:**
```javascript
// Cache source item receipts during LC calculation
this.objSrcItmRcpt = {};

LCTEMPLATE.prototype.setSrcItmRcpt = function(objOneSrcItmRcpt) {
    if (!objOneSrcItmRcpt) return this.objSrcItmRcpt;

    this.objSrcItmRcpt[objOneSrcItmRcpt.id] = objOneSrcItmRcpt;
    return this.objSrcItmRcpt;
};

// Reuse cached receipts instead of repeated lookups
var cachedReceipt = this.getSrcItmRcpt()[receiptId];
```

**Period Caching for Inventory Counts:**
```javascript
// Pre-calculated periods stored in custom record
var periodSearch = search.create({
    type: "customrecord_pri_inv_count_prd_sum"
}).run().getRange(0, 1000);

// Load cached data, exclude periods from search
// Dramatically reduces transaction processing time
```

---

### 4. Queue-Based Async Processing

**Benefits:**
- Prevents user-facing timeouts
- Retries on failure
- Scalable to high transaction volumes
- Parallel processing across multiple scheduled script instances

**Pattern:**
```javascript
// User event (sync):
TRANLIB.pri_itemrcpt_touchCtnQueue(scriptContext);
// → Adds entry to TOUCH_CONTAINER queue
// → Returns immediately (< 10 governance units)
// → User sees instant response

// Scheduled script (async):
pri_containerTouch_sc executes
// → Processes queue entries
// → Heavy container update logic
// → No user waiting
```

---

### 5. Conditional Processing

**Runtime Validation:**
```javascript
// Skip non-UI triggers for certain operations
if (!TRANLIB.pri_itemrcpt_validUIRuntime()) {
    return true; // Exit for scheduled/workflow/suitelet contexts
}

// Prevents unnecessary processing during:
// - Mass updates
// - CSV imports
// - Scheduled script execution
// - Workflow actions
```

**Field Change Detection:**
```javascript
// Only process if field actually changed
for (var i = 0; i < fieldNames.length; i++) {
    var oldValue = context.oldRecord.getValue(fieldName);
    var newValue = context.newRecord.getValue(fieldName);

    if (oldValue != newValue) {
        // Only create note if value changed
        logChange(context, {...});
    }
}
```

---

### 6. Search Optimization

**Filter Efficiency:**
```javascript
// Use indexed fields first
arrFilters = [
    ['isinactive', 'is', 'F'],  // Indexed
    'AND',
    ['internalid', 'anyof', [specificIds]],  // Primary key
    'AND',
    [IDLIB.REC.CNTPRODMGMTLN.PARENT, 'anyof', [intPPO]]  // Foreign key
];

// Avoid formula filters when possible
// Use summary searches for aggregation
```

**Column Selection:**
```javascript
// Only request needed columns
columns: [
    search.createColumn({name: 'internalid'}),
    search.createColumn({name: IDLIB.REC.CNTPRODMGMTLN.STATUS}),
    // Don't request all fields
]
```

---

### 7. Record Operation Optimization

**submitFields vs load/save:**
```javascript
// Fast (10 units):
record.submitFields({
    type: IDLIB.REC.FRGTCNTVSL.ID,
    id: intRecordId,
    values: {
        [IDLIB.REC.FRGTCNTVSL.LOGSTATUS]: TRGTSTATUS
    }
});

// Slow (20-40 units):
var rec = record.load({type: ..., id: ...});
rec.setValue('status', newStatus);
rec.save();
```

**When to use load/save:**
- Need to trigger user events
- Multiple complex field updates
- Sublist modifications

**When to use submitFields:**
- Simple field updates
- No user event triggers needed
- Batch updates of many records

---

### 8. Error Handling & Retry Logic

**Queue Retry Pattern:**
```javascript
try {
    // Process queue entry
    processEntry(qEntry);
    qmEngine.markQueueEntryComplete(qEntry.id);

} catch (e) {
    if (e.message && e.message.indexOf('SSS_USAGE_LIMIT_EXCEEDED') !== -1) {
        // Governance limit - incomplete for retry
        qmEngine.markQueueEntryIncomplete(qEntry.id, qEntry.parms,
                                          'Governance limit, will retry');
    } else if (isRetryableError(e)) {
        // Temporary error - abandon for retry
        qmEngine.abandonQueueEntry(qEntry.id, qEntry.parms,
                                   'ERROR: ' + e.message);
    } else {
        // Permanent error - mark complete to skip
        qmEngine.markQueueEntryComplete(qEntry.id,
                                       'Skipped due to error: ' + e.message);
    }
}
```

---

## Architecture Patterns Summary

### Event-Driven Processing
- **User events** handle immediate validation and field population
- **After submit** events queue heavy processing
- **Scheduled scripts** process queues asynchronously
- **State transitions** validated at every step

### Data Integrity
- **Uniqueness validation** (container names, distribution names)
- **Quantity validation** (no over-allocation)
- **Status validation** (prevent invalid transitions)
- **Referential integrity** (validate line numbers, parent records)

### Scalability
- **Queue-based architecture** prevents timeouts
- **Paged searches** handle large datasets
- **Auto-rescheduling** manages governance limits
- **Period caching** optimizes repeated calculations

### Audit & Compliance
- **Field change tracking** via automated notes
- **Status history** maintained on containers
- **Price locking** preserves historical pricing
- **Queue logs** track async processing

---

## Key Business Rules

### Container Lifecycle
1. Container created → Transfer order created (manual button)
2. Container status validated before item receipt edits
3. Mark in-transit → Creates item fulfillments → Updates status
4. Receive container → Creates item receipts → Updates status
5. Container dates sync to transfer order dates

### Landed Cost Allocation
1. Container costs allocated to item receipts via templates
2. Allocation methods: per quantity, flat amount, percentage
3. Transfer order receipts use location average cost or original IR cost
4. Journal entries created for landed cost variance

### Production Management
1. Production PO lines track detailed item/pricing
2. Price locking preserves structure at time of lock
3. Quantity received calculated from IR aggregation
4. Item versions override standard item pricing/description

### Inventory Tracking
1. Manufacturer POs tracked for ultimate destination
2. In-transit inventory via transfer orders or adjustments
3. Inventory counts calculated by replaying transactions
4. Period caching optimizes repeated calculations

---

## Deployment Considerations

### Script Deployments Required
- All user event scripts deployed to appropriate records
- Scheduled scripts set with appropriate frequency (every 15 minutes recommended)
- Queue monitoring scheduled script for abandoned entries
- Client scripts for dynamic field updates

### Permissions
- Container Tracking role with access to custom records
- Purchase Order create/edit permissions
- Transfer Order create/edit permissions
- Item Receipt create/edit/delete permissions
- Queue management permissions

### Configuration
- App Settings for status values, locations
- Script parameters for field mappings, thresholds
- Landed cost templates per currency/location
- Queue processor schedules

---

## Monitoring & Troubleshooting

### Queue Health
- Monitor queue entry counts by status
- Alert on abandoned entries
- Track processing times
- Review governance usage patterns

### Common Issues

**Queue Entries Not Processing:**
- Check scheduled script deployment status
- Verify governance limits not exhausted
- Review error logs for abandoned entries

**Container Status Not Updating:**
- Verify transfer order exists and committed
- Check queue for TOUCH_CONTAINER entries
- Review container status validation rules

**Landed Cost Not Allocating:**
- Verify template exists for currency/location
- Check item receipt landed cost per line setting
- Review container cost values

**Production PO Quantities Wrong:**
- Check FC_CALC_PPOLNS queue processing
- Verify item receipts linked to correct PO/container
- Review quantity received calculation logic

---

**End of Backend Processing Documentation**
