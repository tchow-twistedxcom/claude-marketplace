# PRI Application Settings Catalog (customrecord_pri_app_setting)

## Executive Summary

The PRI Container Tracking system uses 23+ configurable application settings stored in the `customrecord_pri_app_setting` custom record type. These settings control field mappings, behavior flags, status values, and JSON-based field synchronization rules throughout the container tracking and landed cost workflow.

**Critical Finding:** Transfer Order LINE-level field mapping from Container records is controlled by setting ID 250: **"TrnfrOrd Line Field Mapping From Container"**

---

## Application Setting Record Schema

### Field Structure
```
customrecord_pri_app_setting
├── name (Name field)                          - Setting identifier/display name
├── custrecord_pri_as_app (Application)        - Links to customrecord_pri_app_list
├── custrecord_pri_as_type (Type)              - Dropdown: Text, Integer, Number, Boolean, JSON Object, Date
├── custrecord_pri_as_value (Value)            - CLOBTEXT field storing the actual setting value
├── custrecord_pri_as_desc (Description)       - TEXTAREA explaining purpose and usage
└── custrecord_pri_as_environment (Environment) - Optional: PRODUCTION, SANDBOX, or specific account ID
```

### Type System
- **Text**: String values
- **Integer**: Whole numbers
- **Number**: Decimal/floating point
- **Boolean**: T or F (returned as native true/false)
- **JSON Object**: Structured field mapping configurations
- **Date**: Date values
- **Date and Time**: Datetime values

---

## Complete Application Settings Catalog

### Transfer Order Field Mappings (CRITICAL for Date Sync)

#### Setting ID 250: TrnfrOrd Line Field Mapping From Container ⭐
**Internal ID:** 250
**Type:** Text (JSON Object)
**Purpose:** Maps Container fields → Transfer Order LINE fields
**Relevant to Date Sync:** **YES - THIS IS THE SETTING YOU NEED**

**Current Configuration:**
```json
{
  "source_mapObj": {
    "expectedreceiptdate": "custrecord_pri_frgt_cnt_date_dest_est",
    "expectedshipdate": "custrecord_pri_frgt_cnt_date_sail"
  }
}
```

**How It Works:**
- Applied in `pri_itemrcpt_lib.js` line 1482-1486 using `renderLineFld()` method
- Copies Container date fields to ALL lines on Transfer Order during creation
- `sublistId_src: ''` means source is record body (Container), NOT sublist
- Target is `sublistId: 'item'` (Transfer Order lines)

**Mapping Details:**
- **Source:** `custrecord_pri_frgt_cnt_date_dest_est` (Container: Date Destination Estimated)
- **Target:** `expectedreceiptdate` (Transfer Order Line: Expected Receipt Date)
- **Source:** `custrecord_pri_frgt_cnt_date_sail` (Container: Sailing Date)
- **Target:** `expectedshipdate` (Transfer Order Line: Expected Ship Date)

**Code Reference:**
```javascript
// pri_itemrcpt_lib.js:1482-1486
// Copy the following dates from the Container to the transfer order.
if (objTrnfrOrd_lineMappingFromCtn)
    objTrnfrOrdRec = new SETFLDVAL.SYNCSRCDEF(objTrnfrOrd_lineMappingFromCtn, {
        sublistId_src: '',
        sublistId: 'item'
    }).renderLineFld(this.objFrgtCtnRec, objTrnfrOrdRec);
```

---

#### Setting ID 257: TRNFRORD LINE FIELD MAPPING ITEMRCPT
**Internal ID:** 257
**Type:** Text (JSON Object)
**Purpose:** Maps Item Receipt fields → Transfer Order LINE fields
**Relevant to Date Sync:** NO (only syncs custom field `custcol_pri_bpa_so_line`)

**Current Configuration:**
```json
{
  "sync_arr": ["custcol_pri_bpa_so_line"]
}
```

**How It Works:**
- Applied using `addLineFld()` method per line (line 1471-1476)
- Copies Item Receipt line-level custom field to Transfer Order line
- Does NOT sync date fields

---

#### Setting ID 258: TRNFRORD BODY FIELD MAPPING ITEMRCPT
**Internal ID:** 258
**Type:** Text (JSON Object)
**Purpose:** Maps Item Receipt BODY fields → Transfer Order BODY fields
**Relevant to Date Sync:** NO (only body-level fields)

**Current Configuration:**
```json
{
  "sync_arr": ["custbody_pri_frgt_cnt_ownership", "custbody_pri_frgt_cnt_departure_port"],
  "source_mapObj": {
    "incoterm": "customrecord_pri_frgt_cnt_ownership.custbody_pri_frgt_cnt_ownership.custrecord_pri_frgt_cnt_os_incoterm"
  }
}
```

---

### Item Receipt Field Mappings

#### Setting ID 451: PO Item Receipt Field Mapping From Container
**Internal ID:** 451
**Type:** Text (JSON Object)
**Purpose:** Maps Container fields → PO Item Receipt BODY fields
**Relevant to Date Sync:** NO (body-level only)

**Current Configuration:**
```json
{
  "source_mapObj": {
    "custbody_pri_frgt_loc_ult": "custrecord_pri_frgt_cnt_location_dest",
    "trandate": "custrecord_pri_frgt_cnt_date_sail"
  }
}
```

---

#### Setting ID 452: TO Item Receipt Field Mapping From Container
**Internal ID:** 452
**Type:** Text (JSON Object)
**Purpose:** Maps Container fields → Transfer Order Item Receipt BODY fields
**Relevant to Date Sync:** NO (body-level only)

**Current Configuration:**
```json
{
  "source_mapObj": {
    "custbody_pri_frgt_loc_ult": "custrecord_pri_frgt_cnt_location_dest"
  }
}
```

---

### Direct Import Settings

#### Setting ID 565: Direct Import PO Field Mapping From SO
**Internal ID:** 565
**Type:** Text (JSON Object)
**Purpose:** Maps Sales Order fields → Direct Import Purchase Order fields
**Relevant to Date Sync:** NO

**Current Configuration:**
```json
{
  "sync_arr": [],
  "source_mapObj": {},
  "default_mapObj": {
    "custbody_pri_frgt_cnt_ownership": "1"
  }
}
```

---

#### Direct Import PO default Location Mapping
**Purpose:** Location mapping for Direct Import POs
**Relevant to Date Sync:** NO
**Referenced in:** `pri_purchord_ss.js:592`

---

#### Default Direct Import Sales Order Line Commit Field
**Purpose:** Sales Order line commit field configuration
**Relevant to Date Sync:** NO
**Referenced in:** `pri_purchord_ss.js:728`

---

### Status and Workflow Settings

#### Setting ID 255: Target Status of Transfer Order Received
**Internal ID:** 255
**Type:** Text
**Value:** 7
**Purpose:** Status ID when Transfer Order is received
**Relevant to Date Sync:** NO

**Referenced in:**
- `pri_itemrcpt_lib.js:2030, 4151`
- `pri_CL_vessel.js:255`
- `pri_CL_container.js:242`

---

#### Setting ID 256: Target Status of Mark In-transit
**Internal ID:** 256
**Type:** Text
**Value:** 2
**Purpose:** Status ID for marking containers in-transit
**Relevant to Date Sync:** NO

**Referenced in:** `pri_veslCtn_markIntransit_sc.js:38`

---

#### Setting ID 252: Container Status to Update Parent Vessel
**Internal ID:** 252
**Type:** Text
**Value:** 7
**Purpose:** Container status that triggers parent vessel update
**Relevant to Date Sync:** NO

**Referenced in:** `pri_container_ss.js:819`

---

### Security and Role Settings

#### Setting ID 254: Mark In-transit Show Roles
**Internal ID:** 254
**Type:** JSON Object
**Value:** [3]
**Purpose:** Role IDs allowed to mark containers in-transit
**Relevant to Date Sync:** NO

**Referenced in:** `pri_container_ss.js:795`

---

#### Setting ID 567: Vessel Allowed Status Manually
**Internal ID:** 567
**Type:** JSON Object
**Value:** [1,2,3]
**Purpose:** Vessel status IDs that allow manual updates
**Relevant to Date Sync:** NO

**Referenced in:** `pri_CL_vessel.js:168`

---

### Display and UI Settings

#### Setting ID 566: Item Receipt Queued Message
**Internal ID:** 566
**Type:** Text
**Value:** "Landed Cost or Production Purchase Order Line Logic will run and update item receipt if applicable. This message will disappear when logic has completed, please refresh current page for latest information."
**Purpose:** User notification message for queued processing
**Relevant to Date Sync:** NO

**Referenced in:** `pri_itemrcpt_lib.js:1177`

---

#### Setting ID 570: Message for PO Item Receipt not at Origin Port
**Internal ID:** 570
**Type:** Text
**Value:** "Item Receipt is associated with a Container that is in Transit, modification to items may not be reflected on the related Transfer Orders Item Fulfillment."
**Purpose:** Warning message for in-transit modifications
**Relevant to Date Sync:** NO

**Referenced in:** `pri_itemrcpt_lib.js:1247`

---

#### Setting ID 569: Lock PO Item Receipt when not at Origin Port
**Internal ID:** 569
**Type:** Text
**Value:** F
**Purpose:** Boolean flag to lock item receipts when container is in transit
**Relevant to Date Sync:** NO

**Referenced in:** `pri_itemrcpt_lib.js:2433`

---

#### Show Override of Freight Container Synchronization on item Receipt
**Type:** Text
**Default Value:** T
**Purpose:** Display override checkbox on Item Receipt
**Relevant to Date Sync:** NO

**Referenced in:** `pri_itemrcpt_lib.js:2523`

---

### Validation and Calculation Settings

#### Date Destination Estimate Calculated Validation
**Type:** Text
**Default Value:** T
**Purpose:** Enable/disable validation for calculated destination dates
**Relevant to Date Sync:** YES (indirectly affects date calculation logic)

**Referenced in:**
- `pri_itemrcpt_lib.js:4126`
- `pri_CL_container.js:308`

**Description:** When enabled (T), validates that calculated destination estimate dates are reasonable before setting them on the Container record.

---

### Operational Settings

#### Setting ID 251: Default Landed Cost Rate Preference
**Internal ID:** 251
**Type:** Text
**Value:** 2
**Purpose:** Default rate type for landed cost calculations
**Relevant to Date Sync:** NO

**Referenced in:** `pri_itemrcpt_lib.js:319`

---

#### Delay Minute for PRI_DIRECT_IMPORT_ORDER Queues belong to Same SO
**Type:** Integer
**Default Value:** 1
**Purpose:** Delay minutes between queue processing for same Sales Order
**Relevant to Date Sync:** NO

**Referenced in:** `pri_itemrcpt_lib.js:2204`

---

#### Purchase Order to Item Receipt Location Field Id Mapping
**Purpose:** Field ID mapping for PO to Item Receipt location sync
**Relevant to Date Sync:** NO

**Referenced in:** `pri_itemrcpt_lib.js:1030`

---

### Search and Reporting Settings

#### Setting ID 253: Change Adjusted Est. Time of Arrival Search
**Internal ID:** 253
**Type:** Text
**Value:** customsearch_pri_change_adjustedest
**Purpose:** Saved search ID for adjusted ETA reporting
**Relevant to Date Sync:** NO

---

## Field Mapping Engine Architecture

### The SYNCSRCDEF Class (PRI_SourceFieldValues.js)

The PRI system uses a sophisticated field mapping engine with three mapping types:

#### 1. sync_arr (Direct Field Copy)
Copies fields with same name from source to target:
```json
{
  "sync_arr": ["field1", "field2"]
}
```
- Source and target must have identical field IDs
- Used for straightforward field synchronization

#### 2. source_mapObj (Field-to-Field Mapping)
Maps different field names between records:
```json
{
  "source_mapObj": {
    "target_field": "source_field"
  }
}
```
- Supports simple mapping: `"targetField": "sourceField"`
- Supports complex sourcing: `"targetField": "recordtype.lookupfield.actualfield"`

**Example from Setting 250:**
```json
{
  "source_mapObj": {
    "expectedreceiptdate": "custrecord_pri_frgt_cnt_date_dest_est"
  }
}
```
Means: Copy Container's `custrecord_pri_frgt_cnt_date_dest_est` → Transfer Order line's `expectedreceiptdate`

#### 3. default_mapObj (Default Values)
Sets hardcoded default values:
```json
{
  "default_mapObj": {
    "target_field": "default_value"
  }
}
```
- Supports eval() expressions for dynamic defaults
- Always executed regardless of source data

### Mapping Methods

#### renderBodyFld() - Body-Level Mapping
- Maps source record body → target record body
- Used for header/transaction-level fields
- Example: Item Receipt header → Transfer Order header

#### renderLineFld() - Line-Level Mapping from Body
- Maps source record **BODY** → target record **LINES**
- Applies same value to ALL lines
- **This is what Setting 250 uses**
- Example: Container dates → ALL Transfer Order lines

#### addLineFld() - Line-by-Line Mapping
- Maps source record line → target record line (same line index)
- One-to-one line correspondence
- Example: Item Receipt line 1 → Transfer Order line 1

---

## Date Synchronization Analysis

### Current Container Date Fields

From `custrecord_pri_frgt_cnt` (Freight Container record):

| Field ID | Label | Purpose |
|----------|-------|---------|
| `custrecord_pri_frgt_cnt_date_sail` | Sailing Date | Departure from origin port |
| `custrecord_pri_frgt_cnt_date_dest_est` | Date Destination Estimated | Estimated arrival at destination |
| `custrecord_pri_frgt_cnt_date_dest_estcal` | Date Destination Estimated (Calculated) | System-calculated ETA |
| `custrecord_pri_frgt_cnt_date_dest_act` | Date Destination Actual | Actual arrival date |

### Current Transfer Order Line Date Fields

Standard NetSuite fields on Transfer Order line items:

| Field ID | Label | Synced? |
|----------|-------|---------|
| `expectedshipdate` | Expected Ship Date | ✅ YES (from Container Sailing Date) |
| `expectedreceiptdate` | Expected Receipt Date | ✅ YES (from Container Date Dest Est) |

### Date Synchronization Flow

```
Container Record (customrecord_pri_frgt_cnt)
├── custrecord_pri_frgt_cnt_date_sail (Sailing Date)
│   └─> Transfer Order Lines: expectedshipdate
│
└── custrecord_pri_frgt_cnt_date_dest_est (Date Dest Estimated)
    └─> Transfer Order Lines: expectedreceiptdate

Applied via Setting 250: "TrnfrOrd Line Field Mapping From Container"
Method: SYNCSRCDEF.renderLineFld()
Timing: During Transfer Order creation (pri_itemrcpt_lib.js:1482-1486)
```

---

## Adding "Date Destination Estimated" to Transfer Order Lines

### Current State
❌ **NOT SYNCED**: Container's `custrecord_pri_frgt_cnt_date_dest_est` is NOT visible on Transfer Order lines as a custom column field.

✅ **ALREADY SYNCED**: It IS copied to standard field `expectedreceiptdate` on Transfer Order lines.

### If You Need a Custom Date Column

To add Container's estimated destination date as a **separate custom column** on Transfer Order lines:

#### Option 1: Modify Setting 250 (Recommended)
Update the JSON configuration in Setting ID 250:

**Current:**
```json
{
  "source_mapObj": {
    "expectedreceiptdate": "custrecord_pri_frgt_cnt_date_dest_est",
    "expectedshipdate": "custrecord_pri_frgt_cnt_date_sail"
  }
}
```

**Proposed (if you create custcol_container_eta_date):**
```json
{
  "source_mapObj": {
    "expectedreceiptdate": "custrecord_pri_frgt_cnt_date_dest_est",
    "expectedshipdate": "custrecord_pri_frgt_cnt_date_sail",
    "custcol_container_eta_date": "custrecord_pri_frgt_cnt_date_dest_est"
  }
}
```

#### Option 2: Create New Setting (Not Recommended)
You could create a new application setting, but Setting 250 already exists for this exact purpose and is designed to handle multiple date field mappings.

---

## Key Files and References

### Core Field Mapping Engine
- **PRI_SourceFieldValues.js** - SYNCSRCDEF class (lines 44-750)
  - `renderBodyFld()` - Body field mapping
  - `renderLineFld()` - Line field mapping from body source
  - `addLineFld()` - Line-by-line mapping

### Transfer Order Creation Logic
- **pri_itemrcpt_lib.js** - FRGTCTNTRST class
  - Line 1277-1287: Loads all three TO mapping settings
  - Line 1296-1519: `createTrnfrOrd()` method
  - Line 1471-1476: Applies line mapping from Item Receipt
  - Line 1482-1486: **Applies line mapping from Container (Setting 250)**
  - Line 1618-1892: `healTrnfrOrd()` method (updates existing TOs)
  - Line 1878-1882: Also applies Setting 250 during healing

### Container Scheduled Script
- **pri_container_ss.js**
  - Line 489-503: Error handling for TO field mapping failures

### Application Setting Defaults
- **ProlectoFreightContainer_AppSettingDefault20220715.csv**
  - Contains all 17 default settings with values

### Setting Record Definition
- **/Objects/customrecordtype/customrecord_pri_app_setting.xml**
  - Schema for application settings custom record

---

## Environment-Specific Settings

Application settings support environment targeting via `custrecord_pri_as_environment` field:

### Environment Priority (Highest to Lowest)
1. **Specific Account ID** (e.g., "123456_SB1")
2. **Environment Type** (e.g., "SANDBOX", "PRODUCTION")
3. **Blank** (applies to all environments)

### Example Use Cases
- Different field mappings in SANDBOX vs PRODUCTION
- Testing configuration changes in SB1 before promoting to PROD
- Account-specific customizations for multi-tenant scenarios

---

## Summary and Recommendations

### Critical Findings

1. **Setting ID 250 is THE setting** that controls Transfer Order line-level date synchronization from Containers.

2. **Current mapping is complete** for standard NetSuite date fields:
   - Container Sailing Date → TO Line Expected Ship Date ✅
   - Container Estimated Destination → TO Line Expected Receipt Date ✅

3. **If you need custom date columns**, modify Setting 250's JSON to include additional mappings.

### Settings NOT Relevant to Date Sync
- Settings 257, 258: Only sync non-date custom fields
- Settings 451, 452: Body-level mappings only
- Settings 565, 566, 569, 570: Display/behavior flags
- Settings 250-256: Status and role configurations
- Settings 251, 253: Landed cost and search settings

### Verification Steps

To confirm current date synchronization is working:

1. Check a Container record for `custrecord_pri_frgt_cnt_date_dest_est`
2. Find associated Transfer Order
3. Open Transfer Order line item details
4. Verify `expectedreceiptdate` matches Container's estimated destination date
5. Verify `expectedshipdate` matches Container's sailing date

### Modification Guidance

To add additional date field mappings to Transfer Order lines:

1. Create custom Transfer Order line field (if needed)
2. Navigate to: Lists → PRI App Setting → ID 250
3. Update JSON in `custrecord_pri_as_value` field
4. Test in SANDBOX environment first
5. Verify during Transfer Order creation from Item Receipt

---

## Appendix: All Referenced Settings by File

### pri_itemrcpt_lib.js (Primary TO Logic)
- Default Landed Cost Rate Preference (line 319)
- TO Item Receipt Field Mapping From Container (line 944)
- PO Item Receipt Field Mapping From Container (line 946)
- Purchase Order to Item Receipt Location Field Id Mapping (line 1030)
- Item Receipt Queued Message (line 1177)
- Message for PO Item Receipt not at Origin Port (line 1247)
- **TRNFRORD BODY FIELD MAPPING ITEMRCPT (line 1277)**
- **TRNFRORD LINE FIELD MAPPING ITEMRCPT (line 1281)**
- **TrnfrOrd Line Field Mapping From Container (line 1285)** ⭐
- Target Status of Transfer Order Received (lines 2030, 4151)
- Delay Minute for PRI_DIRECT_IMPORT_ORDER Queues (line 2204)
- Lock PO Item Receipt when not at Origin Port (line 2433)
- Show Override of Freight Container Synchronization (line 2523)
- Date Destination Estimate Calculated Validation (line 4126)

### pri_container_ss.js
- Mark In-transit Show Roles (line 795)
- Container Status to Update Parent Vessel (line 819)

### pri_purchord_ss.js
- Direct Import PO default Location Mapping (line 592)
- Direct Import PO Field Mapping From SO (line 604)
- Default Direct Import Sales Order Line Commit Field (line 728)

### pri_CL_vessel.js
- Vessel Allowed Status Manually (line 168)
- Target Status of Transfer Order Received (line 255)

### pri_CL_container.js
- Target Status of Transfer Order Received (line 242)
- Date Destination Estimate Calculated Validation (line 308)

### pri_veslCtn_markIntransit_sc.js
- Target Status of Mark In-transit (line 38)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-12
**NetSuite Environment:** Production (Account: 4138030)
**Bundle:** 125246 - PRI Container Tracking
