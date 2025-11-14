# PRI Application Settings Field Mapping Analysis

**Date:** 2025-11-12
**Purpose:** Trace how Container date updates should flow to Transfer Order line dates through PRI field mapping system

---

## Executive Summary

**THE CRITICAL FINDING:** Field mapping scripts operate **ONLY on record CREATE/EDIT events** of the DESTINATION record (Transfer Order), NOT on source record (Container) changes. When you update `custrecord_pri_frgt_cnt_date_dest_est` on a Container, no automatic propagation occurs to existing Transfer Order lines.

**The Gap:** Container date updated → **NO TRIGGER** → Transfer Order lines unchanged

---

## System Architecture

### Field Mapping Components

#### 1. **Field Mapping Custom Record** (`customrecord_pri_fmapping`)
**Location:** NetSuite Custom Record
**Purpose:** Stores field mapping configurations

**Key Fields:**
- `custrecord_pri_fmapping_rectype` - Destination record type (e.g., "transferorder")
- `custrecord_pri_fmapping_rectype_source` - Source record type (e.g., "customrecord_pri_frgt_cnt")
- `custrecord_pri_fmapping_source` - Field on destination that links to source (e.g., "custbody_pri_frgt_cnt")
- `custrecord_pri_fmapping_fields` - JSON mapping array: `[{"from":"source_field","to":"dest_field"}]`
- `custrecord_pri_fmapping_oncreate` - Boolean: apply on CREATE
- `custrecord_pri_fmapping_onedit` - Boolean: apply on EDIT

**Example Mapping JSON:**
```json
[
  {
    "from": "custrecord_pri_frgt_cnt_date_sail",
    "to": "expectedshipdate"
  },
  {
    "from": "custrecord_pri_frgt_cnt_date_dest_est",
    "to": "expectedreceiptdate"
  }
]
```

---

#### 2. **Field Mapping User Event Scripts**

##### A. **TWX Optimized Version**
**File:** `/SuiteScripts/Twisted X/User Events/twx_FieldMapping.js`
**Type:** UserEventScript (beforeSubmit)
**Optimization:** Uses SuiteQL query instead of loading full records

**Execution Flow:**
```
1. Transfer Order CREATE/EDIT triggered
2. Script searches for field mappings where:
   - isinactive = false
   - rectype = 'transferorder'
   - oncreate/onedit = true
3. For each mapping found:
   - Parse JSON fields
   - Get Container ID from TO field (custbody_pri_frgt_cnt)
   - Run SuiteQL: SELECT fields FROM container WHERE id = ?
   - Set values on TO ONLY IF target field is empty/null
4. Save Transfer Order
```

**Code Snippet (lines 49-105):**
```javascript
settingSearch.run().each(function (setting) {
    fromType = setting.getValue('custrecord_pri_fmapping_rectype_source');
    mapping = JSON.parse(setting.getValue('custrecord_pri_fmapping_fields'));
    fromId = REC.getValue({'fieldId': setting.getValue('custrecord_pri_fmapping_source')});

    if(!mapping) return true;

    // SuiteQL query to get source values
    fromValues = query.runSuiteQL({
        query: 'SELECT ' + fromFields + ' FROM ' + fromType + ' WHERE id = ' + fromId
    }).asMappedResults()[0];

    // Set values on destination record
    for (m = 0; m < mapping.length; m++) {
        value = fromValues[mapping[m].from];

        if (isFalsy(REC.getValue(mapping[m].to))) { // ONLY IF TARGET IS EMPTY
            REC.setValue({'fieldId': mapping[m].to, 'value': value});
        }
    }
});
```

**CRITICAL CONDITION (line 96):**
```javascript
if (isFalsy(REC.getValue(mapping[m].to))) // set only if user has not
```
This means fields are ONLY updated if they're empty/null. Existing values are PRESERVED.

---

##### B. **Original PRI Version**
**File:** `/SuiteScripts/Twisted X/Modified Bundles/Bundle 132118/PRI_FieldMapping.js`
**Type:** UserEventScript (beforeSubmit)
**Difference:** Loads full source record instead of SuiteQL

**Code Snippet (lines 95-114):**
```javascript
var nsRecord = record.load({'type': recType, 'id': fieldValue});

for(var s = 0; s < sourceField.length; s++){
  var v = nsRecord.getValue({'fieldId': sourceField[s].from});
  var f = recordObj.getValue({'fieldId': sourceField[s].to});

  if(v && f == null || f == "") { // SAME CONDITION: only if target is empty
    recordObj.setValue({'fieldId': sourceField[s].to, 'value': v});
  }
}
```

**SAME LIMITATION:** Only updates empty fields.

---

### 3. **Container Edit Interface**

#### Container Date Update Suitelet
**File:** `/SuiteScripts/Prolecto/tx_SL_EditContainer.js`
**Purpose:** Provides UI for bulk container date updates

**Display Fields (lines 100-101):**
```javascript
subList.addField({
    id: "custrecord_pri_frgt_cnt_date_dest_est",
    type: ui.FieldType.DATE,
    label: "Container Estimated Arrival"
}).updateDisplayType({displayType: ui.FieldDisplayType.ENTRY}); // EDITABLE
```

#### Container Date Update Client Script
**File:** `/SuiteScripts/Prolecto/tx_CL_EditContainer.js`
**Purpose:** Handles field changes in Suitelet

**Update Logic (lines 71-89):**
```javascript
function updateField(fieldName) {
    var id = REC.getCurrentSublistValue({sublistId: "custpage_list", fieldId: "id"});

    // DIRECT UPDATE TO CONTAINER - NO TRANSFER ORDER UPDATE
    record.submitFields({
        type: "CUSTOMRECORD_PRI_FRGT_CNT",
        id: id,
        values: {
            custrecord_pri_frgt_cnt_date_dest_est: REC.getCurrentSublistValue({
                sublistId: "custpage_list",
                fieldId: fieldName
            })
        }
    });

    // Refresh page
    submitPage();
}
```

**KEY ISSUE:** Uses `record.submitFields()` which:
- Updates Container directly
- Does NOT trigger field mapping on Transfer Orders
- Does NOT load/edit the Transfer Order record
- No User Event scripts fire on Transfer Order

---

## Container → Transfer Order Relationship

### Database Schema

**Container Custom Record:** `customrecord_pri_frgt_cnt`

**Key Field (from XML definition):**
```xml
<customrecordcustomfield scriptid="custrecord_pri_frgt_cnt_to">
  <fieldtype>SELECT</fieldtype>
  <label>Transfer Order</label>
  <selectrecordtype>-30</selectrecordtype> <!-- Transfer Order -->
  <description>
    Relationship to transfer order. A container comes into existence
    during the creation of a transfer order.
  </description>
</customrecordcustomfield>
```

**Container has Transfer Order:** `custrecord_pri_frgt_cnt_to` → Transfer Order ID
**Transfer Order has Container:** `custbody_pri_frgt_cnt` → Container ID (body field)

**Date Fields on Container:**
- `custrecord_pri_frgt_cnt_date_sail` - Date Sailing
- `custrecord_pri_frgt_cnt_date_dest_est` - **Date Destination Estimated** (THE FIELD IN QUESTION)
- `custrecord_pri_frgt_cnt_date_dest_estcal` - Calculated Estimated Arrival
- `custrecord_pri_frgt_cnt_date_land_est` - Date Landing Estimated
- `custrecord_pri_frgt_cnt_date_land_act` - Date Landing Actual

**Expected Mapping to Transfer Order Lines:**
- Container `custrecord_pri_frgt_cnt_date_sail` → TO line `expectedshipdate`
- Container `custrecord_pri_frgt_cnt_date_dest_est` → TO line `expectedreceiptdate`

---

## The Problem: Why Dates Don't Sync

### Scenario: User Updates Container Date
```
1. User opens "Update Container Dates" Suitelet
2. Finds Container "CONT-2024-001" linked to TO #12345
3. Changes "Date Destination Estimated" from 11/10 to 11/14
4. Client script calls record.submitFields() on Container
5. Container custrecord_pri_frgt_cnt_date_dest_est updated to 11/14
6. ❌ Transfer Order lines STILL show 11/10
```

### Root Cause Analysis

**Why field mapping doesn't execute:**

1. **Field mapping triggers on DESTINATION record events**
   - Scripts listen to Transfer Order CREATE/EDIT
   - Container update does NOT edit the Transfer Order
   - No beforeSubmit event fires on Transfer Order

2. **record.submitFields() bypasses User Events**
   - `record.submitFields()` is a lightweight API call
   - Does NOT trigger User Event scripts on the updated record
   - Only updates specified fields directly in database
   - NetSuite optimization: faster but no workflow execution

3. **Field mapping only updates EMPTY fields**
   - Even if mapping executed, line 96 condition prevents updates:
   ```javascript
   if (isFalsy(REC.getValue(mapping[m].to))) // only if empty
   ```
   - Transfer Order lines already have `expectedreceiptdate` values
   - Mapping logic: "Don't overwrite user data"
   - Design philosophy: Field mapping is for INITIALIZATION not SYNCHRONIZATION

4. **No reverse mapping exists**
   - Field mappings are UNIDIRECTIONAL: Source → Destination
   - No mapping definition for: Container change → trigger TO update
   - No "cascade update" mechanism in PRI field mapping framework

---

## Current System Behavior

### What DOES Work

**✅ New Transfer Order Creation:**
```
1. User creates new Transfer Order
2. Sets custbody_pri_frgt_cnt = Container A
3. beforeSubmit fires on Transfer Order
4. Field mapping loads Container A dates
5. Sets TO header fields from Container
6. Sets TO line fields from Container (if empty)
7. Save completes with Container dates populated
```

**✅ Transfer Order Edit (adding new lines):**
```
1. User edits existing Transfer Order
2. Adds new line item
3. beforeSubmit fires on Transfer Order
4. Field mapping runs for new lines
5. New line expectedreceiptdate populated from Container
6. Existing lines unchanged (already have values)
```

### What DOESN'T Work

**❌ Container Date Update:**
```
1. Container date changed via Suitelet
2. record.submitFields() updates Container
3. Transfer Order NOT touched
4. TO line dates remain stale
5. No synchronization occurs
```

**❌ Manual TO Edit After Container Change:**
```
1. Container updated to 11/14
2. User edits Transfer Order
3. beforeSubmit fires but line 96 condition fails:
   if (isFalsy(REC.getValue('expectedreceiptdate'))) // FALSE - field has value
4. Existing date NOT overwritten
5. Line still shows 11/10
```

---

## Required Field Mapping Configuration

### Check Existing Mapping

**Search in NetSuite:**
```
Customization > Lists, Records, & Fields > Record Types > PRI Field Mapping

Filters:
- Inactive = False
- Record Type = Transfer Order
- On Edit = True
```

**Expected Record:**
- **Name:** "Container to Transfer Order"
- **Record Type:** Transfer Order
- **Source Record Type:** PRI Container
- **Source Field:** Container (custbody_pri_frgt_cnt)
- **On Create:** ☑ True
- **On Edit:** ☑ True
- **Fields (JSON):**
```json
[
  {"from": "custrecord_pri_frgt_cnt_date_sail", "to": "expectedshipdate"},
  {"from": "custrecord_pri_frgt_cnt_date_dest_est", "to": "expectedreceiptdate"}
]
```

**QUESTION FOR USER:** Does this mapping record exist? What does the JSON look like?

---

## Solution Options

### Option 1: Add Container afterSubmit User Event (RECOMMENDED)
**Create new script that propagates Container changes to Transfer Order**

**File:** `TWX_UE_Container_Sync.js`
```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType UserEventScript
 * @NModuleScope Public
 */
define(['N/record', 'N/search', 'N/log'], function(record, search, log) {

    function afterSubmit(context) {
        if (context.type !== context.UserEventType.EDIT) return;

        const container = context.newRecord;
        const containerId = container.id;
        const oldContainer = context.oldRecord;

        // Check if date changed
        const newDate = container.getValue('custrecord_pri_frgt_cnt_date_dest_est');
        const oldDate = oldContainer.getValue('custrecord_pri_frgt_cnt_date_dest_est');

        if (newDate === oldDate) return; // No change

        // Get linked Transfer Order
        const transferOrderId = container.getValue('custrecord_pri_frgt_cnt_to');
        if (!transferOrderId) return;

        log.audit('Container Date Changed', {
            container: containerId,
            transferOrder: transferOrderId,
            oldDate: oldDate,
            newDate: newDate
        });

        // Update Transfer Order lines
        const toRecord = record.load({
            type: record.Type.TRANSFER_ORDER,
            id: transferOrderId
        });

        const lineCount = toRecord.getLineCount({sublistId: 'item'});
        let updated = 0;

        for (let i = 0; i < lineCount; i++) {
            // Update expectedreceiptdate on each line
            toRecord.setSublistValue({
                sublistId: 'item',
                fieldId: 'expectedreceiptdate',
                line: i,
                value: newDate
            });
            updated++;
        }

        if (updated > 0) {
            toRecord.save({
                enableSourcing: false,
                ignoreMandatoryFields: true
            });

            log.audit('Transfer Order Updated', {
                transferOrder: transferOrderId,
                linesUpdated: updated,
                newDate: newDate
            });
        }
    }

    return {
        afterSubmit: afterSubmit
    };
});
```

**Deployment:**
- Script Record: Create UserEventScript
- Deployments: One for Container record type
- Execution Context: User Interface, Web Services, CSV Import
- Status: Testing initially, then Released

**Pros:**
- Automatic synchronization
- Works for any Container date update method
- Centralized logic
- Audit trail in logs

**Cons:**
- Governance units (loads TO record)
- Additional script to maintain
- Need to handle bulk updates carefully

---

### Option 2: Modify Container Edit Suitelet
**Add TO update logic to existing tx_CL_EditContainer.js**

**Modify updateField() function:**
```javascript
function updateField(fieldName) {
    var id = REC.getCurrentSublistValue({sublistId: "custpage_list", fieldId: "id"});
    var newDate = REC.getCurrentSublistValue({sublistId: "custpage_list", fieldId: fieldName});

    // Update Container
    record.submitFields({
        type: "CUSTOMRECORD_PRI_FRGT_CNT",
        id: id,
        values: {custrecord_pri_frgt_cnt_date_dest_est: newDate}
    });

    // NEW: Get Transfer Order and update lines
    var containerRec = record.load({
        type: 'CUSTOMRECORD_PRI_FRGT_CNT',
        id: id
    });

    var toId = containerRec.getValue('custrecord_pri_frgt_cnt_to');

    if (toId) {
        var toRec = record.load({
            type: record.Type.TRANSFER_ORDER,
            id: toId
        });

        var lineCount = toRec.getLineCount({sublistId: 'item'});
        for (var i = 0; i < lineCount; i++) {
            toRec.setSublistValue({
                sublistId: 'item',
                fieldId: 'expectedreceiptdate',
                line: i,
                value: newDate
            });
        }

        toRec.save();
        console.log("Transfer Order " + toId + " updated with " + lineCount + " lines");
    }

    submitPage();
}
```

**Pros:**
- Localized to Container edit flow
- User sees immediate update
- No additional script deployment

**Cons:**
- Only works through Suitelet (not API, CSV, etc.)
- Duplicates logic if other Container update methods exist
- Client script governance limits

---

### Option 3: Scheduled Script for Batch Sync
**Nightly or on-demand synchronization**

**Script:** Map/Reduce to find Container/TO mismatches and sync

**Pros:**
- Handles historical data
- Batch processing efficient
- Can include validation/reporting

**Cons:**
- Not real-time
- Requires scheduling
- Potential timing issues

---

### Option 4: Modify Field Mapping Logic
**Change twx_FieldMapping.js to ALWAYS update (remove empty check)**

**Current (line 96):**
```javascript
if (isFalsy(REC.getValue(mapping[m].to))) // only if empty
    REC.setValue({'fieldId': mapping[m].to, 'value': value});
```

**Modified:**
```javascript
// Always set value from source
REC.setValue({'fieldId': mapping[m].to, 'value': value});
```

**Pros:**
- Uses existing framework
- Works on TO edit

**Cons:**
- **BREAKING CHANGE**: Overwrites user edits on ALL field mappings
- Still requires TO edit to trigger
- Not specific to Container date updates
- Could affect other field mapping behaviors negatively

---

## Recommended Approach

**OPTION 1 is recommended** because:

1. **Automatic and reliable:** Triggers on any Container edit
2. **Isolated logic:** Doesn't affect other field mappings
3. **Audit trail:** Logs all synchronizations
4. **Extensible:** Can handle other Container fields in future
5. **Respects framework:** Doesn't modify core field mapping behavior

**Implementation Steps:**

1. Create `TWX_UE_Container_Sync.js` script
2. Deploy as User Event on `customrecord_pri_frgt_cnt`
3. Test in sandbox with:
   - Single Container update
   - Bulk Container updates
   - Container with multiple Transfer Orders (if possible)
4. Verify logs show:
   - Date changes detected
   - Transfer Orders updated
   - Line counts correct
5. Deploy to production

---

## Verification Queries

### Find Containers with Stale TO Dates
```sql
SELECT
    cnt.id AS container_id,
    cnt.name AS container_name,
    cnt.custrecord_pri_frgt_cnt_date_dest_est AS container_date,
    to.id AS transfer_order_id,
    to.tranid AS transfer_order_number,
    toline.expectedreceiptdate AS line_receipt_date,
    CASE
        WHEN cnt.custrecord_pri_frgt_cnt_date_dest_est != toline.expectedreceiptdate
        THEN 'MISMATCH'
        ELSE 'MATCH'
    END AS sync_status
FROM
    customrecord_pri_frgt_cnt cnt
INNER JOIN
    transaction to ON cnt.custrecord_pri_frgt_cnt_to = to.id
INNER JOIN
    transactionline toline ON to.id = toline.transaction
WHERE
    to.type = 'TrnfrOrd'
    AND toline.mainline = 'F'
    AND cnt.custrecord_pri_frgt_cnt_date_dest_est IS NOT NULL
    AND toline.expectedreceiptdate IS NOT NULL
    AND cnt.custrecord_pri_frgt_cnt_date_dest_est != toline.expectedreceiptdate
ORDER BY
    cnt.id DESC
```

### Find Recent Container Date Changes
```sql
SELECT
    systemnotes.recordid AS container_id,
    systemnotes.name AS change_date,
    systemnotes.field AS field_changed,
    systemnotes.oldvalue AS old_value,
    systemnotes.newvalue AS new_value,
    BUILTIN.DF(systemnotes.recordtypeid) AS record_type
FROM
    systemnotes
WHERE
    systemnotes.recordtypeid = (
        SELECT id FROM customrecordtype
        WHERE scriptid = 'customrecord_pri_frgt_cnt'
    )
    AND systemnotes.field = 'Date Destination Estimated'
    AND systemnotes.name >= CURRENT_DATE - 30
ORDER BY
    systemnotes.name DESC
```

---

## Questions for User

1. **What is the expected behavior?**
   - Should Container date changes ALWAYS update TO lines?
   - Or only when TO lines match old Container date (selective sync)?
   - Should header level dates update too?

2. **Field Mapping Configuration:**
   - Can you export the existing Field Mapping record?
   - Does mapping include line-level fields or only header?

3. **Update Frequency:**
   - How often are Container dates updated?
   - Are updates typically one-off or bulk?
   - Is real-time sync required or nightly acceptable?

4. **Scope:**
   - Should this sync other Container date fields (sail date, landing date)?
   - Are there other Container fields that should sync?

5. **Business Logic:**
   - Can Transfer Orders have lines from multiple Containers?
   - Should sync respect line-level Container associations?
   - What happens if TO is already fulfilled/closed?

---

## Files Referenced

| File Path | Purpose | Key Lines |
|-----------|---------|-----------|
| `/SuiteScripts/Twisted X/User Events/twx_FieldMapping.js` | Field mapping UE (optimized) | 14-115 |
| `/SuiteScripts/Twisted X/Modified Bundles/Bundle 132118/PRI_FieldMapping.js` | Field mapping UE (original) | 34-124 |
| `/SuiteScripts/Twisted X/Modules/TWXServerLibrary.js` | Settings management library | 357-422 |
| `/SuiteScripts/Prolecto/tx_SL_EditContainer.js` | Container edit Suitelet | 44-189 |
| `/SuiteScripts/Prolecto/tx_CL_EditContainer.js` | Container edit client script | 71-89 |
| `/Objects/customrecordtype/customrecord_pri_frgt_cnt.xml` | Container record definition | Full file |

---

## Next Steps

1. **Immediate:** Query NetSuite for existing Field Mapping records
2. **Testing:** Run verification queries to quantify the issue
3. **Decision:** Choose Option 1, 2, 3, or 4 based on requirements
4. **Implementation:** Create/modify scripts as needed
5. **Validation:** Test in sandbox with sample Containers/TOs
6. **Deployment:** Roll out to production with monitoring

---

**Analysis Complete**
**Status:** Awaiting user input on questions and preferred solution approach
