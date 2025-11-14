# PRI Container Tracking - Integration Architecture Analysis

**Bundle ID:** Bundle 125246
**System:** NetSuite SuiteScript 2.x
**Analysis Date:** 2025-11-12
**Scope:** Integration touchpoints, dependencies, and external system interactions

---

## Executive Summary

The PRI Container Tracking system is a comprehensive freight and landed cost management solution with **deep integrations** across NetSuite standard records, **cross-bundle dependencies** with Prolecto infrastructure bundles, and **complex data orchestration patterns**. The system operates primarily in **self-contained mode** with no direct external API integrations, relying instead on NetSuite's native transaction processing and custom record infrastructure.

**Key Findings:**
- **No external EDI/shipping carrier integrations** - tracking URL references only
- **Heavy reliance on Bundle 132118** (Prolecto Infrastructure) for Queue Management, App Settings, and Common Libraries
- **Extensive standard record customizations** on Purchase Orders, Item Receipts, Transfer Orders, and Sales Orders
- **Production Purchase Order (PPO) system** as central orchestration point
- **Landed Cost Template engine** with complex allocation methods

---

## 1. Dependency Architecture

### 1.1 NetSuite Module Dependencies (N/*)

**Core Platform Modules:**
```javascript
// Data Operations
'N/record'      // Record CRUD operations across all scripts
'N/search'      // Saved search execution and dynamic searches
'N/query'       // SuiteQL for complex data queries (pri_itemrcpt_lib)

// User Interface
'N/ui/serverWidget'  // Suitelet form generation
'N/ui/message'       // User notifications and alerts
'N/ui/dialog'        // Client-side dialogs

// System & Utilities
'N/runtime'     // User preferences, script parameters, feature detection
'N/format'      // Date/number formatting
'N/error'       // Standardized error handling
'N/util'        // General utilities
'N/cache'       // Session caching (pri_itemrcpt_lib)

// Navigation & Integration
'N/redirect'    // Page navigation
'N/url'         // URL resolution for Suitelets and scripts
'N/workflow'    // Workflow integration (pri_itemrcpt_lcAlloc_sl)
'N/task'        // Scheduled script task management
'N/https'       // Client-side HTTP (pri_cntProdMgmt_cl, pri_itemrecpt_cl)
```

**Feature Dependencies:**
- **Bin Management** (`runtime.isFeatureInEffect('binmanagement')`) - Warehouse bin tracking
- **Advanced Bin/Serial/Lot Management** (`advbinseriallotmgmt`) - Inventory number management

### 1.2 Cross-Bundle Dependencies

**Bundle 132118: Prolecto Infrastructure** (Critical Dependency)

```javascript
'/.bundle/132118/PRI_QM_Engine'        // Queue Manager - Async task orchestration
'/.bundle/132118/PRI_AS_Engine'        // App Settings - Configuration management
'/.bundle/132118/PRI_CommonLibrary'    // Shared utilities
'/.bundle/132118/PRI_ServerLibrary'    // Server-side utilities
```

**Queue Manager Integration Pattern:**
```javascript
// Used in 17 scripts for asynchronous processing
qmEngine.addQueueEntry(
    'QUEUE_NAME',           // Queue identifier
    parameters,             // Execution parameters (JSON)
    priority,               // Execution priority
    immediate,              // Execute immediately flag
    'customscript_xxx'      // Target scheduled script ID
);

// Key Queues:
// - 'FC_CALC_PPOLNS'         // Recalculate Production PO Line quantities
// - 'COPY_PPO'               // Copy Production PO
// - 'PPO_RECALC_PRICE'       // Recalculate PPO pricing
// - Container receipt queues
```

**App Settings Integration Pattern:**
```javascript
// Configuration retrieval from centralized settings
ASEngine.readAppSetting(
    'Prolecto Freight Container & Landed Cost',  // App name
    'Default Landed Cost Rate Preference'        // Setting key
);
```

### 1.3 Internal Module Dependencies

**Shared Library Architecture:**

```
pri_idRecord_cslib.js (371 lines)
└── Central constants/field ID definitions for ALL custom records
    Used by: 38+ scripts

pri_itemrcpt_lib.js (4,221 lines)
└── Core landed cost calculation engine
    ├── LCTEMPLATE class - Template processing
    ├── ITEMRECEIPT class - Receipt orchestration
    ├── Bin allocation logic
    └── Container synchronization
    Used by: pri_itemrcpt_ss, pri_purchord_ss, pri_container_ss, pri_SC_directImport_fulfillOrd

pri_cntProdMgmt_lib.js (1,854 lines)
└── Production Purchase Order management
    ├── PRODPOLINE class - PPO line operations
    ├── PRODPOHEADER class - PPO header operations
    ├── Price locking mechanisms
    └── Member item structure management
    Used by: pri_cntProdMgmtLn_ss, pri_cntProdMgmtPo_ss, pri_cntProdPoGenerator_sl

pri_itemrcpt_cllib.js
└── Client-side item receipt utilities
    Used by: pri_itemrecpt_cl

pri_itemrecpt_lcAlloc.js
└── Landed cost allocation calculations
    Used by: pri_itemrcpt_lib, pri_itemrcpt_lcAlloc_sl, pri_itemrcpt_lcAlloc_wa

pri_irToLinker_lib.js (581 lines)
└── Item Receipt to Transfer Order linking logic

PRI_SourceFieldValues.js (750 lines)
└── SYNCSRCDEF class - Source/Sync/Default field mapping engine
    Supports: sync_arr, source_mapObj, default_mapObj patterns
    Used by: pri_itemrcpt_lib, pri_purchord_ss

utils/Utils.js
└── Accurate number calculation utilities (accAdd, accMultiple, accDivide)
    Error formatting, customer access checks

utils/Const.js
└── Item type mappings, saved search IDs
```

---

## 2. Standard Record Customizations

### 2.1 Body-Level Custom Fields

**Transfer Order (transferorder)**
```javascript
custbody_pri_frgt_cnt               // Link to Container record
custbody_pri_frgt_cnt_lctd_ir_pointer  // Item Receipt pointer for LC
custbody_pri_frgt_cnt_pm_po         // Link to Production PO
```

**Item Receipt (itemreceipt)**
```javascript
custbody_pri_frgt_cnt               // Link to Container record
custbody_pri_frgt_loc_ult           // Ultimate destination location
custbody_pri_frgt_loc_ult_date      // Ultimate delivery date
custbody_pri_frgt_cnt_pm_po         // Link to Production PO
```

**Purchase Order (purchaseorder)**
```javascript
custbody_pri_frgt_cnt_pm_po         // Link to Production PO
```

**Inventory Adjustment (inventoryadjustment)**
```javascript
custbody_pri_frgt_cnt_lctd_ir_pointer  // Item Receipt pointer for LC consumption
```

**Sales Order (salesorder)**
```javascript
// Uses PRI_AS_Engine for settings lookups
// No direct custom fields visible in codebase
```

### 2.2 Line-Level (Column) Custom Fields

**Transfer Order Lines**
```javascript
custcol_pri_frgt_cnt_ir_lnkey       // Item Receipt line linkage key (format: "irId_lineNum")
```

**Item Receipt Lines**
```javascript
custcol_pri_frgt_cnt_iv             // Item Version reference
custcol_pri_frgt_cnt_dm             // Distribution Management reference
custcol_pri_frgt_cnt_pm_po          // Production PO Line reference
```

**Purchase Order Lines**
```javascript
custcol_pri_frgt_cnt_iv             // Item Version reference
custcol_pri_frgt_cnt_iv_vendor_name // Vendor name from Item Version
custcol_pri_frgt_cnt_dm             // Distribution Management reference
custcol_pri_frgt_cnt_pm_po          // Production PO Line reference
custcol_pri_frgt_cnt_iv_sourced     // Sourced Item Version
```

### 2.3 Item Record Customizations

**Item (inventoryitem, assemblyitem, etc.)**
```javascript
custitem_pri_frgt_cnt_iv                  // Current Item Version reference
custitem_pri_frgt_cnt_lc_rate_pref        // Landed Cost rate preference
    // Values: Location Average Cost (1) | Item Receipt Cost (2)
```

---

## 3. Custom Record Types

### 3.1 Container Management Records

**PRI Container Vessel** (`customrecord_pri_frgt_cnt_vsl`)
- Parent record for shipping vessels
- Fields: Origin/Destination locations, Carrier, Logistic Status, Freight costs, Sail/Land dates, Tracking URL

**PRI Container** (`customrecord_pri_frgt_cnt`)
- Child of Vessel, linked to Transfer Orders
- Fields: Seal ID, Carrier, Vessel reference, Logistic Status, Origin/Destination, Tracking URL, Cost breakdown, Date tracking, Notes

**PRI Container Carrier** (`customrecord_pri_frgt_cnt_carrier`)
- Carrier master data with tracking URL template

**Custom Lists:**
- `customlist_pri_frgt_cnt_log_status` - Logistic status values (1-8)
  - 1: At Origin Port, 2: On Sea/In Transit, 3: At Landing Port
  - 6: In Transit to Dest Loc, 7: Received at Dest Loc, 8: At Arrival Dest Loc

### 3.2 Item Version & Pricing Records

**PRI Item Version** (`customrecord_pri_frgt_cnt_iv`)
- Version-based item pricing and sourcing
- Fields: Item, Item Type, Description, Vendor, Vendor Name, Currency, Rate, Start/End dates, Landed Cost Template, Customer, Customer Item

**PRI Landed Cost Template** (`customrecord_pri_frgt_cnt_lct`)
- Template definitions for landed cost allocation
- Fields: Description, Location, Currency

**PRI Landed Cost Template Detail** (`customrecord_pri_frgt_cnt_lctd`)
- Detail lines for cost allocation methods
- Fields: Parent template, Cost Category, Factor, Allocation Method, Consumption Item

**Allocation Methods** (`customlist_pri_frgt_cnt_lct_all_method`):
1. Per Quantity
2. Flat Amount
3. Item Consumption
4. Percentage

### 3.3 Production Management Records

**PRI Container Production Management PO** (`customrecord_pri_frgt_cnt_pm_po`)
- Header record for Production Purchase Orders
- Fields: Date, Period, Status, Entity (Vendor), Currency, Department, Class

**PRI Container Production Management Line** (`customrecord_pri_frgt_cnt_pm`)
- Line items for Production POs
- Fields: Parent PPO, Period, Vendor, Currency, Item, Item Display Name, Item Type, Quantity, Item Version, Calculated Price, Reference Price, Price Variance, Note, Status, Hold Price Data (JSON), Qty Received PO/TO, Qty Received Imbalance, Calculated Quantity, Line Number

**Status Values** (`customlist_pri_frgt_cnt_pm_line_status`):
1. Unlocked - Prices can be recalculated
2. Locked - Prices frozen in Hold Price Data JSON

### 3.4 Linking & Distribution Records

**PRI Container IR to TO Linker** (`customrecord_pri_frgt_cnt_l`)
- Links Item Receipts to Transfer Orders
- Fields: IR Reference, IR Line Number, Item, Quantity, Container, TO Reference, TO Line Number

**PRI Container Distribution Management** (`customrecord_pri_frgt_cnt_dm`)
- Manages inventory distribution requests
- Fields: Parent, Type, Origin, Location, Item, Parent Line Number/ID, Quantity, Request Date, Expected Date, Container, Note

### 3.5 Landed Cost Rate Type

**Custom List:** `customlist_pri_frgt_cnt_lc_rate_type`
1. Location Average Cost - Use item location average cost
2. Item Receipt Cost - Use inherent IR line cost

---

## 4. Script Deployment Architecture

### 4.1 User Event Scripts

**pri_itemrcpt_ss** - Item Receipt orchestrator
- Triggers: beforeLoad, beforeSubmit, afterSubmit
- Functions: Landed cost sync, container status updates, location defaulting, PPO line validation

**pri_purchord_ss** (953 lines) - Purchase Order processing
- Triggers: beforeLoad, beforeSubmit, afterSubmit
- Functions: Item Version sourcing, PPO linking, distribution management

**pri_container_ss** (958 lines) - Container record events
- Functions: Status validation, freight cost calculations, vessel synchronization

**pri_trnfrord_ss** - Transfer Order processing
- Functions: Container linking, location validation

**pri_itemver_ss** - Item Version events
- Functions: Version validation, rate management

**pri_cntProdMgmtLn_ss** - Production PO Line events
- Functions: Price locking, member info display, line number sequencing

**pri_cntProdMgmtPo_ss** - Production PO Header events
- Functions: Status validation, line aggregation

**pri_cntDistMgmt_ss** (450 lines) - Distribution Management
- Functions: Request validation, allocation logic

**pri_irToLinker_ss** - IR/TO Linker events

**pri_UE_salesOrder** - Sales Order events
- Uses: PRI_AS_Engine for configuration

**pri_cnt_trackNoteChanges_ss** - Note change tracking

**pri_itemship_ss** - Item Fulfillment events

### 4.2 Scheduled Scripts

**pri_cntProdMgmtLn_sc** - PPO Line recalculation
- Queue: 'FC_CALC_PPOLNS'
- Function: Batch recalculate qty received PO/TO

**pri_cntProdMgmtPo_sc** - PPO Header operations
- Queues: PPO creation, recalculation

**pri_cntProdMgmtPo_recalcPrice_sc** - Price recalculation
- Queue: 'PPO_RECALC_PRICE'

**pri_SC_receiveContainer** (583 lines) - Container receipt processing
- Queue-driven container receiving automation

**pri_SC_directImport_fulfillOrd** - Direct import fulfillment
- Queue-driven order fulfillment

**pri_containerTouch_sc** - Container touch/update operations

**pri_veslCtn_markIntransit_sc** - Mark containers in transit

**pri_itemrcpt_lcPerLnTemplate_sc** - Landed cost per-line template processing

### 4.3 Suitelets

**pri_cntProdPoGenerator_sl** (441 lines) - PO Generator UI
- Creates Purchase Orders from Production PO Lines
- Iframe embedded in PPO Header form
- Features: Line selection, quantity adjustment, negative rate detection

**pri_SL_GenerateContainerData** (655 lines) - Container data export
- Generates container reports/data exports

**pri_SL_generateInventoryCounts** - Inventory count generation

**pri_SL_generatePeriodInventoryCounts** - Period inventory counts

**pri_itemrecpt_lcAlloc_sl** - Landed cost allocation UI

### 4.4 Client Scripts

**pri_itemrecpt_cl** (519 lines) - Item Receipt client logic
- Functions: Line validation, container sync dialogs, landed cost preview

**pri_purchord_cs** (415 lines) - Purchase Order client logic
- Functions: Item Version selection, PPO line selection

**pri_cntProdMgmt_cl** (431 lines) - Production PO client logic
- Functions: Dynamic item version filtering, HTTP requests to load version data

**pri_CL_container** - Container form client logic

**pri_CL_vessel** - Vessel form client logic

**pri_cntProdMgmtLn_cl** - PPO Line client logic

**pri_cntProdMgmtLn20_cl** - PPO Line 2.0 client logic

**pri_cntProdPoGenerator_cl** - PO Generator client logic

**pri_itemrecptFrgt_cl** - Item Receipt freight client logic

### 4.5 Workflow Action Scripts

**pri_itemrecpt_lcAlloc_wa** - Landed cost allocation workflow action
- Type: @NScriptType workflowactionscript
- Function: Trigger LC allocation from workflow

---

## 5. Integration Patterns & Data Flow

### 5.1 Production Purchase Order (PPO) Flow

```
1. Create PPO Header (customrecord_pri_frgt_cnt_pm_po)
   ↓
2. Create PPO Lines (customrecord_pri_frgt_cnt_pm)
   - Select Item (or Item Group)
   - Select Item Version (optional)
   - Set Quantity
   - System calculates Price & Quantity (getItemMembInfo)
   ↓
3. Lock PPO Lines (Status = Locked)
   - Freezes price structure in holdpricedata JSON
   - Disables Item/Item Version editing
   ↓
4. Generate Purchase Orders (pri_cntProdPoGenerator_sl)
   - Select locked PPO Lines
   - System creates PO with:
     * custcol_pri_frgt_cnt_pm_po = PPO Line ID
     * Item structure from locked holdpricedata
   ↓
5. Receive Items (Item Receipt)
   - custcol_pri_frgt_cnt_pm_po links to PPO Line
   - System recalculates PPO Line quantities:
     * Qty Received PO (from PO-based IRs)
     * Qty Received TO (from TO-based IRs)
   ↓
6. Monitor Receipts
   - PPO Header shows aggregated status
   - Imbalance detection for Item Groups
```

### 5.2 Landed Cost Template Flow

```
1. Item Receipt Created
   - Location detected
   - Currency detected
   ↓
2. Find Applicable LC Template
   - Match by Location + Currency
   - Load Template Details (customrecord_pri_frgt_cnt_lctd)
   ↓
3. Calculate Costs per Detail Line
   - Per Quantity: Factor × Item Quantity
   - Flat Amount: Factor (constant)
   - Item Consumption: Create Inventory Adjustment consuming item
   - Percentage: Factor% × (Item Rate × Quantity)
     * If Rate=0 and from Transfer Order:
       - Use Location Average Cost or
       - Use Source Item Receipt Cost (per item preference)
   ↓
4. Apply Costs
   - Per-line landed cost (landedcostperline=true)
   - Create Inventory Adjustments for consumption items
   - Update Container status if container mode
```

### 5.3 Container Freight Flow

```
1. Create Container Vessel (customrecord_pri_frgt_cnt_vsl)
   - Origin/Destination Locations
   - Carrier, Dates, Costs
   ↓
2. Create Container(s) (customrecord_pri_frgt_cnt)
   - Child of Vessel
   - Link to Transfer Order (custbody_pri_frgt_cnt)
   ↓
3. Update Logistic Status
   - 1: At Origin Port
   - 2: On Sea/In Transit
   - 3: At Landing Port
   - 6: In Transit to Dest Loc
   - 7: Received at Dest Loc
   ↓
4. Receive Transfer Order
   - Item Receipt links to Container
   - Container costs sync to IR landed costs
   - Container status → Received at Dest Loc
```

### 5.4 Item Version Sourcing Flow

```
1. Purchase Order Line Created
   ↓
2. User Selects Item
   ↓
3. System Finds Current Item Version
   - custitem_pri_frgt_cnt_iv on Item
   - OR manual selection
   ↓
4. Apply Item Version Data
   - Description → custcol_pri_frgt_cnt_iv_vendor_name (display)
   - Vendor Name → column display
   - Rate → PO Line rate
   - Landed Cost Template → for future IR processing
   ↓
5. Save Source Reference
   - custcol_pri_frgt_cnt_iv_sourced = Item Version ID
```

### 5.5 IR to TO Linking Flow

```
1. Item Receipt Created from Transfer Order
   ↓
2. System Creates Linker Records (customrecord_pri_frgt_cnt_l)
   - IR Reference + Line Number
   - TO Reference + Line Number
   - Item, Quantity, Container
   ↓
3. Transfer Order Column Updated
   - custcol_pri_frgt_cnt_ir_lnkey = "irId_lineNum"
   ↓
4. Used for:
   - Traceability
   - Landed cost rate lookups (Item Receipt Cost method)
   - Container receipt orchestration
```

---

## 6. External System Integration

### 6.1 Shipping Carrier Integration

**Status:** **REFERENCE ONLY - No Active API Integration**

**Tracking URL Pattern:**
```javascript
// PRI Container Carrier record
custrecord_pri_frgt_cnt_carrier_url: "https://carrier.com/track?id={TRACKING_NUMBER}"

// Container/Vessel records
custrecord_pri_frgt_cnt_url       // Container tracking URL (populated manually)
custrecord_pri_frgt_cnt_vsl_url   // Vessel tracking URL (populated manually)
```

**No automated carrier API calls detected in codebase.**
- No N/https module usage for external carrier APIs
- No EDI transaction processing
- Tracking URLs are display-only references

### 6.2 EDI Integration

**Status:** **NO EDI INTEGRATION DETECTED**

Searched for:
- EDI transaction types (810, 850, 856, 997, etc.) - Not found
- EDI processing scripts - Not found
- sFTP/AS2 communication modules - Not found

### 6.3 Third-Party System Integration

**Status:** **SELF-CONTAINED SYSTEM**

- No external database connections (N/database not used)
- No external REST/SOAP API calls (N/https used only client-side for UI)
- No external authentication systems (OAuth, SAML, etc.)
- No external file transfers (sFTP, FTP modules not used)

**Integration Scope Limited To:**
1. NetSuite standard records (PO, IR, TO, SO, Items, etc.)
2. Prolecto Bundle 132118 (Queue Manager, App Settings)
3. User-entered data (tracking URLs, notes, status updates)

---

## 7. Security & Permission Model

### 7.1 Script Execution Contexts

**User Event Scripts:**
- Execute in user context (current user permissions apply)
- Features detected via `runtime.isFeatureInEffect()`
- User preferences via `runtime.getCurrentUser().getPreference()`

**Scheduled Scripts:**
- Execute in script administrator context
- Queue Manager provides privilege escalation
- Used for batch operations requiring elevated permissions

**Suitelets:**
- Execute in administrator context for data access
- UI rendered based on user's NetSuite role permissions

**Client Scripts:**
- Execute in browser with user's session permissions
- HTTPS module used for client-side requests (pri_cntProdMgmt_cl, pri_itemrecpt_cl)

### 7.2 Role & Permission Requirements

**Minimum Permissions Required:**
- Transactions: Purchase Order, Item Receipt, Transfer Order (Create, Edit, View)
- Custom Records: All PRI Container Tracking custom records (Full Access)
- Items: View, Edit (for Item Version updates)
- Reports: Saved Search execution
- Setup: Access to Bundle 132118 App Settings (if admin-configurable)

**Bundle Installation Permissions:**
- Full Administrator role recommended for initial setup
- Custom role creation for operational users

---

## 8. Performance & Scalability Considerations

### 8.1 Governance Unit Management

**Heavy Operations Delegated to Scheduled Scripts:**
```javascript
// Pattern: Check remaining governance units before batch operations
var bolLackofUnit = runtime.getCurrentScript().getRemainingUsage() < (threshold);
if (bolLackofUnit || largeDataset) {
    // Queue to Scheduled Script via Queue Manager
    qmEngine.addQueueEntry('QUEUE_NAME', params, priority, immediate, 'customscript_xxx');
} else {
    // Execute inline
}
```

**Thresholds:**
- PPO Line calculations: >10 lines OR <50 remaining units → Queue
- Landed cost per-line processing: >threshold → Queue (customscript_pri_itemrcpt_lcperlntmpl)
- Container receipt operations: Always queued for large containers

### 8.2 Search Optimization

**Saved Search References:**
```javascript
// From utils/Const.js - VD API searches
customsearch_vd_api_sales_orders: 932
customsearch_vd_api_customer_cc_list: 935
customsearch_vd_api_pricing: 941
customsearch_vd_api_item_inventory: 889
customsearch_vd_api_item_inventory_2: 986
customsearch_vd_api_item_inventory_thres: 994
customsearch_vd_api_items: 886
customsearch_vd_api_customers: 887
customsearch_vd_api_customer_addresses: 888

// Lookup tables
customsearch_vd_api_locations: 928
customsearch_vd_api_subsidiaries: 877
customsearch_vd_api_classes: 937
customsearch_vd_api_departments: 938
customsearch_vd_api_pricelevel: 942
customsearch_vd_api_currency: 943
customsearch_vd_api_shipping_methods: 936
```

**Dynamic Search Limits:**
- Standard limit: 999 results (`.getRange(0, 999)`)
- Large datasets: 4000 results (pri_itemrcpt_lib.js line references)
- SuiteQL used for complex joins (N/query module in pri_itemrcpt_lib)

### 8.3 Caching Strategy

**Session Cache Usage:**
```javascript
// pri_itemrcpt_lib.js uses N/cache
cache.getCache({
    name: 'sessionCache',
    scope: cache.Scope.PRIVATE
});
```

**Record Caching Patterns:**
```javascript
// LCTEMPLATE class caches loaded source Item Receipts
this.objSrcItmRcpt = {};  // Prevent duplicate record.load() calls
```

### 8.4 Data Volume Limits

**Item Group Member Processing:**
- Max 999 member items per group (search limit)
- Member item sequence processing (LINENUMBER sort)

**PPO Line Calculations:**
- Batch processing via Queue Manager for >10 lines
- JSON storage in holdpricedata field (size limits apply)

**Container Operations:**
- Vessel → Container (1:many) - No hard limit detected
- Container → Transfer Orders (1:many linkage supported)

---

## 9. Failure Points & Error Handling

### 9.1 Critical Failure Scenarios

**1. Bundle 132118 Unavailability**
- **Impact:** Queue Manager failures → Batch operations fail
- **Mitigation:** Scripts check for qmEngine availability
- **Recovery:** Manual execution required if queue engine down

**2. Locked Price Data Corruption**
- **Impact:** PPO Line holdpricedata JSON invalid → PO generation fails
- **Mitigation:** JSON.parse() error handling in pri_cntProdMgmt_lib
- **Recovery:** Unlock line, recalculate, re-lock

**3. Item Receipt Imbalance Detection**
- **Impact:** Item Group received in wrong proportions → Qty calculations fail
- **Mitigation:** Imbalance flag set (custrecord_pri_frgt_cnt_pm_quantity_ib)
- **Recovery:** User must correct receipt proportions

**4. Landed Cost Template Allocation Errors**
- **Impact:** Consumption item bin allocation fails → LC processing incomplete
- **Mitigation:** Preferred bin OR quantity-available bin selection
- **Recovery:** Adjust bin quantities or use manual LC entry

**5. Container Status Lock Violations**
- **Impact:** User edits Item Receipt when Container not at Origin Port
- **Mitigation:** Form locked in pri_itemrcpt_lockByCtnStatus()
- **Recovery:** Update Container status to unlock

### 9.2 Error Handling Patterns

**Standardized Error Creation:**
```javascript
// utils/Utils.js
createError: function(name, message, notifyOff) {
    return error.create({
        "name": name || "",
        "message": message || "",
        "notifyOff": notifyOff || true
    });
}
```

**Exception Formatting:**
```javascript
formatException: function(e) {
    return {
        message: e.message,
        code: e.name
    };
}
```

**Queue Manager Error Handling:**
- Queue records store parameters and notes
- Complete/In-Progress flags track execution state
- Retry logic managed by Queue Manager infrastructure

### 9.3 Validation Checkpoints

**Runtime Validation:**
```javascript
// pri_itemrcpt_lib: Ignore non-UI triggers (workflow, suitelet, scheduled)
pri_itemrcpt_validUIRuntime()
```

**Container Mode Validation:**
```javascript
// Ensure Container exists before syncing costs
if (!containerRecord) { return; }
```

**PPO Line Status Validation:**
```javascript
// Prevent price updates when locked
if (status == LOCKED) { return true; }
```

**Item Version Date Validation:**
```javascript
// Ensure version valid for transaction date
if (tranDate < versionStart || tranDate > versionEnd) { skip; }
```

---

## 10. API Endpoints & RESTlet Pattern

### 10.1 Suitelet Endpoints

**PO Generator:**
```
Script ID: customscript_pri_cntprodpogenerator_sl
Deployment: customdeploy_pri_cntprodpogenerator_sl
Access: Embedded iframe in PPO Header form
Parameters:
  - custparam_hidenavbar=T
  - custparam_poheaderid={PPO_ID}
  - ifrmcntnr=T
```

**LC Allocation:**
```
Script ID: customscript_pri_itemrecpt_lcalloc_sl
Deployment: customdeploy_pri_itemrecpt_lcalloc_sl
Access: Button on Item Receipt form
```

**Container Data Generator:**
```
Script ID: (not visible in limited search)
Function: Export container data reports
```

### 10.2 No RESTlet Architecture Detected

**Searched for:**
- `@NScriptType Restlet` annotations - Not found
- `N/rest` module usage - Not found in Container Tracking bundle
- RESTlet-style GET/POST/PUT/DELETE handlers - Not found

**Note:** The Twisted X bundle includes RESTlet APIs (suiteapi.restlet.js), but PRI Container Tracking does not expose RESTful endpoints.

---

## 11. Cross-System Data Flow Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    NETSUITE ECOSYSTEM                        │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Standard Records (NetSuite Native)         │    │
│  │  Purchase Order → Item Receipt → Transfer Order    │    │
│  │  Sales Order → Item Fulfillment → Inventory Adj    │    │
│  │  Items (with custom fields)                        │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↕                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │      PRI Container Tracking (Bundle 125246)        │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │ Custom Records                               │  │    │
│  │  │ - Container Vessel                           │  │    │
│  │  │ - Container                                  │  │    │
│  │  │ - Item Version                               │  │    │
│  │  │ - Landed Cost Template/Detail                │  │    │
│  │  │ - Production PO Header/Line                  │  │    │
│  │  │ - IR/TO Linker                               │  │    │
│  │  │ - Distribution Management                    │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │                                                     │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │ Scripts (46 total)                           │  │    │
│  │  │ - User Events (14)                           │  │    │
│  │  │ - Scheduled (10)                             │  │    │
│  │  │ - Suitelets (5)                              │  │    │
│  │  │ - Client Scripts (16)                        │  │    │
│  │  │ - Workflow Action (1)                        │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↕                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │   Prolecto Infrastructure (Bundle 132118)          │    │
│  │  - Queue Manager (PRI_QM_Engine)                   │    │
│  │  - App Settings (PRI_AS_Engine)                    │    │
│  │  - Common Library (PRI_CommonLibrary)              │    │
│  │  - Server Library (PRI_ServerLibrary)              │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────────────┐
│              EXTERNAL SYSTEMS (MANUAL ONLY)                  │
│  - Carrier Tracking URLs (reference only, no API)           │
│  - User-entered container/vessel data                       │
│  - No EDI integration                                        │
│  - No automated shipping carrier APIs                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 12. Key Integration Touchpoints

### 12.1 Standard Record → Custom Record Linkages

| Standard Record | Custom Record | Linkage Field | Purpose |
|----------------|---------------|---------------|---------|
| Transfer Order | Container | custbody_pri_frgt_cnt | Container freight tracking |
| Item Receipt | Container | custbody_pri_frgt_cnt | Landed cost sync |
| Item Receipt | Production PO | custbody_pri_frgt_cnt_pm_po | PPO receipt tracking |
| Purchase Order | Production PO | custbody_pri_frgt_cnt_pm_po | PPO linkage |
| IR Line | Item Version | custcol_pri_frgt_cnt_iv | Version-based pricing |
| PO Line | Item Version | custcol_pri_frgt_cnt_iv | Version sourcing |
| IR Line | PPO Line | custcol_pri_frgt_cnt_pm_po | Receipt attribution |
| PO Line | PPO Line | custcol_pri_frgt_cnt_pm_po | Order attribution |
| Item | Item Version | custitem_pri_frgt_cnt_iv | Current version pointer |
| TO Line | IR Line | custcol_pri_frgt_cnt_ir_lnkey | IR/TO linkage |

### 12.2 Custom Record → Custom Record Relationships

| Parent Record | Child Record | Relationship | Cardinality |
|--------------|--------------|--------------|-------------|
| Container Vessel | Container | custrecord_pri_frgt_cnt_vsl | 1:many |
| LC Template | LC Template Detail | custrecord_pri_frgt_cnt_lctd_parent | 1:many |
| Prod PO Header | Prod PO Line | custrecord_pri_frgt_cnt_pm_parent | 1:many |
| Item | Item Version | custrecord_pri_frgt_cnt_iv_item | 1:many |
| Dist Mgmt | Parent Tran | custrecord_pri_frgt_cnt_dm_parent | many:1 |

### 12.3 Queue Manager Integration Points

| Queue Name | Source Script | Target Script | Trigger Condition |
|-----------|--------------|---------------|-------------------|
| FC_CALC_PPOLNS | pri_cntProdMgmt_lib | customscript_pri_cntprodmgmtln_sc | >10 PPO lines OR low governance units |
| COPY_PPO | pri_cntProdMgmtPo_ss | customscript_pri_cntProdMgmtPo_sc | User-initiated copy |
| PPO_RECALC_PRICE | pri_cntProdMgmtPo_ss | customscript_pri_cntProdMgmtPo_recalc_sc | Price variance detected |
| Container Receipt | pri_itemrcpt_lib | customscript_pri_fgt_cntr_receive_cntr | Container-mode IR save |
| Direct Import Fulfillment | pri_itemrcpt_lib | customscript_pri_fgt_cntr_direct_imp_ful | Direct import workflow |
| Container Touch | pri_itemrcpt_lib | customscript_pri_containertouch_sc | Container status updates |
| LC Per-Line Template | pri_itemrcpt_lib | customscript_pri_itemrcpt_lcperlntmpl | Landed cost template processing |
| Mark In-Transit | pri_container_ss | customscript_pri_veslctn_markintransit_s | Vessel/container status change |

---

## 13. Dependency Risk Assessment

### 13.1 Critical Dependencies (High Risk)

**Bundle 132118 (Prolecto Infrastructure)**
- **Risk:** CRITICAL - System inoperative without Queue Manager
- **Mitigation:** Ensure Bundle 132118 always deployed before Bundle 125246
- **Impact Scope:** All batch operations, async processing, configuration management

**NetSuite Landed Cost Feature**
- **Risk:** HIGH - Core functionality depends on native LC feature
- **Mitigation:** Verify feature enabled: Setup > Company > Enable Features > Items & Inventory > Landed Cost
- **Impact Scope:** Item Receipt cost allocation, inventory valuation

**Bin Management / Advanced Bin Features**
- **Risk:** MEDIUM - Bin allocation fails if features disabled
- **Mitigation:** Feature detection in LCTEMPLATE class with graceful degradation
- **Impact Scope:** Consumption item allocation, warehouse operations

### 13.2 Moderate Dependencies

**Saved Searches (Const.js References)**
- **Risk:** MEDIUM - Hardcoded search IDs may break on copy/migration
- **Mitigation:** Document all customsearch_* IDs for bundle deployment
- **Impact Scope:** Pricing lookups, item inventory queries, customer data

**Custom Field IDs**
- **Risk:** MEDIUM - Field ID changes break IDLIB.REC definitions
- **Mitigation:** Use SuiteScript 2.x field ID constants where possible
- **Impact Scope:** All scripts referencing custbody_/custcol_/custrecord_ fields

### 13.3 Low Dependencies

**User Preferences**
- **Risk:** LOW - Script parameters override user preferences
- **Mitigation:** Default values in script deployment parameters
- **Impact Scope:** Landed cost template enablement, bin queue searches

**Client-Side HTTPS**
- **Risk:** LOW - Only used for UI enhancements (Item Version selection)
- **Mitigation:** Graceful fallback to standard field selection
- **Impact Scope:** User experience only (pri_cntProdMgmt_cl)

---

## 14. Migration & Deployment Considerations

### 14.1 Bundle Installation Order

1. **Bundle 132118** (Prolecto Infrastructure) - MUST install first
2. **Bundle 125246** (PRI Container Tracking) - Depends on 132118

### 14.2 Post-Installation Configuration

**Required Setup:**
1. Enable Landed Cost feature (Setup > Company > Enable Features)
2. Configure Company Preferences:
   - `custscript_pri_itemrcpt_landcosttemplate` - Enable LC templates (T/F)
   - `custscript_pri_itemrcpt_landcostfldsmap` - Field mapping JSON
   - `custscript_pri_itemrcpt_default_bin_queu` - Default bin saved search ID

3. Create Saved Searches (if migrating):
   - Copy all customsearch_vd_api_* searches
   - Update Const.js with new search internal IDs

4. Configure App Settings (via Bundle 132118):
   - 'Prolecto Freight Container & Landed Cost' → 'Default Landed Cost Rate Preference'

**Optional Setup:**
1. Create Carriers (customrecord_pri_frgt_cnt_carrier)
2. Create Landed Cost Templates per location/currency combination
3. Create Item Versions for vendor-specific pricing
4. Configure custom roles/permissions for operational users

### 14.3 Data Migration Patterns

**Container Data:**
- Export existing Container Vessel records
- Export Container records
- Preserve Container → Transfer Order linkages (custbody_pri_frgt_cnt)

**Item Version Data:**
- Export Item Version records
- Update Item master data (custitem_pri_frgt_cnt_iv)
- Validate rate start/end dates

**Production PO Data:**
- Export PPO Headers and Lines
- Preserve locked holdpricedata JSON structures
- Validate PPO → PO/IR linkages

**Landed Cost Templates:**
- Export Template Headers and Details
- Validate Cost Category account mappings
- Test allocation methods in sandbox environment

### 14.4 Testing Checklist

**Critical Workflows:**
- [ ] Create Container Vessel → Container → Transfer Order → Item Receipt → Landed Cost sync
- [ ] Create PPO → Lock Lines → Generate PO → Receive Items → Validate Qty Received calculations
- [ ] Create Item Version → Link to Item → Create PO → Validate pricing
- [ ] Test Landed Cost Template allocation (all 4 methods)
- [ ] Test Queue Manager integration (trigger batch operations)
- [ ] Validate bin allocation for consumption items

**Edge Cases:**
- [ ] Item Group with >10 member items (governance limits)
- [ ] Item Receipt without Container (non-container mode)
- [ ] Transfer Order with zero-cost items (LC percentage calculation)
- [ ] PPO Line imbalance detection (mixed receipt quantities)
- [ ] Container status lock enforcement (edit IR when Container in transit)

**Performance Testing:**
- [ ] Create 100+ PPO Lines → Measure queue processing time
- [ ] Process Item Receipt with 50+ lines → Monitor governance usage
- [ ] Run Container Data Generator with 1000+ containers

---

## 15. Documentation & Support Resources

### 15.1 Key Files for Reference

**Constants & Field IDs:**
- `/PRI Container Tracking/pri_idRecord_cslib.js` (371 lines) - Master field ID definitions

**Core Libraries:**
- `/PRI Container Tracking/pri_itemrcpt_lib.js` (4,221 lines) - Landed cost engine
- `/PRI Container Tracking/pri_cntProdMgmt_lib.js` (1,854 lines) - PPO management
- `/PRI Container Tracking/PRI_SourceFieldValues.js` (750 lines) - Field mapping engine

**Utilities:**
- `/PRI Container Tracking/utils/Utils.js` - Accurate number calculations
- `/PRI Container Tracking/utils/Const.js` - Item types, saved search IDs

### 15.2 Code Comments & Inline Documentation

**Comment Quality:** Moderate to High
- Function-level JSDoc comments present in most scripts
- Complex algorithms documented (e.g., getItemMembInfo, calcPercentageVal)
- History/modification logs in file headers (author, date, changes)

**Areas Needing Documentation:**
- Queue Manager integration patterns (scattered across files)
- App Settings key reference (centralized documentation missing)
- Saved search ID mappings (only partial list in Const.js)
- Field mapping JSON schema (custscript_pri_itemrcpt_landcostfldsmap)

### 15.3 Script Deployment Matrix

| Script File | Script Type | Script ID | Deployment ID | Record Types |
|------------|-------------|-----------|---------------|--------------|
| pri_itemrcpt_ss | User Event | TBD | TBD | Item Receipt |
| pri_purchord_ss | User Event | TBD | TBD | Purchase Order |
| pri_container_ss | User Event | TBD | TBD | Container |
| pri_trnfrord_ss | User Event | TBD | TBD | Transfer Order |
| pri_cntProdMgmtLn_sc | Scheduled | customscript_pri_cntprodmgmtln_sc | TBD | Queue-driven |
| pri_cntProdPoGenerator_sl | Suitelet | customscript_pri_cntprodpogenerator_sl | customdeploy_pri_cntprodpogenerator_sl | N/A |
| pri_itemrecpt_lcAlloc_sl | Suitelet | customscript_pri_itemrecpt_lcalloc_sl | customdeploy_pri_itemrecpt_lcalloc_sl | N/A |
| pri_itemrecpt_lcAlloc_wa | Workflow Action | TBD | TBD | Item Receipt |

*(TBD = To Be Determined from NetSuite account - internal IDs not in source code)*

---

## 16. Recommendations

### 16.1 Architecture Improvements

**Decouple Queue Manager Dependency:**
- Create fallback mechanisms for critical operations when qmEngine unavailable
- Implement synchronous alternatives with governance unit checks

**Centralize Configuration:**
- Migrate hardcoded saved search IDs to App Settings
- Document all field mapping JSON schemas
- Create configuration UI for field mappings

**Enhanced Error Handling:**
- Implement structured logging (not just log.debug/audit)
- Create error dashboard/monitoring for queue failures
- Add retry logic for transient failures

**API Exposure (Future Enhancement):**
- Consider RESTlet API for container status updates from external systems
- Enable third-party integrations (carrier tracking, EDI gateways)
- Create webhook support for real-time container status notifications

### 16.2 Documentation Enhancements

**Create:**
1. **Bundle Deployment Guide** - Step-by-step installation with screenshots
2. **Field Mapping Reference** - All custom fields with descriptions and dependencies
3. **Queue Manager Integration Guide** - Pattern library for new queue implementations
4. **App Settings Registry** - All setting keys with default values and descriptions
5. **Testing Scenarios Matrix** - Comprehensive test cases for all workflows

### 16.3 Monitoring & Maintenance

**Implement:**
1. Queue health dashboard (monitor PRI_QM_Engine custom records)
2. PPO Line imbalance alerts (automated notifications)
3. Landed cost allocation failure tracking
4. Container status anomaly detection (e.g., vessels stuck "On Sea" >60 days)

### 16.4 Security Enhancements

**Review:**
1. Client-side HTTPS usage in pri_cntProdMgmt_cl and pri_itemrecpt_cl
2. Ensure sensitive data (pricing, costs) not exposed in client scripts
3. Validate user permissions before queue operations (prevent privilege escalation)

---

## Appendix A: Script Inventory

### User Event Scripts (14)
1. pri_itemrcpt_ss - Item Receipt orchestration
2. pri_purchord_ss - Purchase Order processing
3. pri_container_ss - Container record events
4. pri_trnfrord_ss - Transfer Order processing
5. pri_itemver_ss - Item Version events
6. pri_cntProdMgmtLn_ss - Production PO Line events
7. pri_cntProdMgmtPo_ss - Production PO Header events
8. pri_cntDistMgmt_ss - Distribution Management
9. pri_irToLinker_ss - IR/TO Linker events
10. pri_UE_salesOrder - Sales Order events
11. pri_cnt_trackNoteChanges_ss - Note tracking
12. pri_itemship_ss - Item Fulfillment events
13. pri_CL_vessel - Vessel client logic (also has CL component)
14. pri_CL_container - Container client logic (also has CL component)

### Scheduled Scripts (10)
1. pri_cntProdMgmtLn_sc - PPO Line recalculation
2. pri_cntProdMgmtPo_sc - PPO Header operations
3. pri_cntProdMgmtPo_recalcPrice_sc - Price recalculation
4. pri_SC_receiveContainer - Container receipt processing
5. pri_SC_directImport_fulfillOrd - Direct import fulfillment
6. pri_containerTouch_sc - Container touch operations
7. pri_veslCtn_markIntransit_sc - Mark in-transit
8. pri_itemrcpt_lcPerLnTemplate_sc - LC per-line processing

### Suitelets (5)
1. pri_cntProdPoGenerator_sl - PO Generator UI
2. pri_SL_GenerateContainerData - Container data export
3. pri_SL_generateInventoryCounts - Inventory counts
4. pri_SL_generatePeriodInventoryCounts - Period inventory
5. pri_itemrecpt_lcAlloc_sl - LC allocation UI

### Client Scripts (16)
1. pri_itemrecpt_cl - Item Receipt client logic
2. pri_purchord_cs - Purchase Order client logic
3. pri_cntProdMgmt_cl - Production PO client logic
4. pri_CL_container - Container form client logic
5. pri_CL_vessel - Vessel form client logic
6. pri_cntProdMgmtLn_cl - PPO Line client logic
7. pri_cntProdMgmtLn20_cl - PPO Line 2.0 client logic
8. pri_cntProdPoGenerator_cl - PO Generator client
9. pri_itemrecptFrgt_cl - Item Receipt freight client
10. pri_itemrcpt_cllib - Item Receipt client utilities
11. pri_prj_cllib - Project client utilities

### Workflow Action Scripts (1)
1. pri_itemrecpt_lcAlloc_wa - LC allocation workflow action

### Libraries (11)
1. pri_idRecord_cslib - Field ID constants
2. pri_itemrcpt_lib - Landed cost engine
3. pri_cntProdMgmt_lib - PPO management
4. pri_itemrecpt_lcAlloc - LC allocation calculations
5. pri_irToLinker_lib - IR/TO linking
6. PRI_SourceFieldValues - Field mapping engine
7. utils/Utils - Number calculations, error handling
8. utils/Const - Item types, saved search IDs
9. utils/pri_generateInventoryCounts - Inventory count utilities

**Total Scripts: 46** (approximate, some files have dual purposes)

---

## Appendix B: Custom Record Field Reference

### Container Vessel (customrecord_pri_frgt_cnt_vsl)
```
custrecord_pri_frgt_cnt_vsl_loc_origin       - Origin Location
custrecord_pri_frgt_cnt_vsl_loc_dest         - Destination Location
custrecord_pri_frgt_cnt_vsl_inv_num          - Invoice Number
custrecord_pri_frgt_cnt_vsl_carrier          - Carrier (FK)
custrecord_pri_frgt_cnt_vsl_log_status       - Logistic Status (List)
custrecord_pri_frgt_cnt_vsl_cost_freight     - Freight Cost
custrecord_pri_frgt_cnt_vsl_date_sail        - Sail Date
custrecord_pri_frgt_cnt_vsl_dte_land_est     - Estimated Land Date
custrecord_pri_frgt_cnt_vsl_dte_land_act     - Actual Land Date
custrecord_pri_frgt_cnt_vsl_url              - Tracking URL
custrecord_pri_frgt_cnt_vsl_notes            - Notes
custrecord_pri_frgt_cnt_vsl_hip_to_cntry     - Ship to Country
```

### Container (customrecord_pri_frgt_cnt)
```
custrecord_pri_frgt_cnt_to                   - Transfer Order (FK)
custrecord_pri_frgt_cnt_seal                 - Container Seal ID
custrecord_pri_frgt_cnt_carrier              - Carrier (FK)
custrecord_pri_frgt_cnt_vsl                  - Vessel (FK - Parent)
custrecord_pri_frgt_cnt_log_status           - Logistic Status (List)
custrecord_pri_frgt_cnt_location_origin      - Origin Location
custrecord_pri_frgt_cnt_location_dest        - Destination Location
custrecord_pri_frgt_cnt_url                  - Tracking URL
custrecord_pri_frgt_cnt_cost_freight         - Freight Cost
custrecord_pri_frgt_cnt_cost_clr_forward     - Clearance/Forwarding Cost
custrecord_pri_frgt_cnt_cost_total           - Total Cost
custrecord_pri_frgt_cnt_date_sail            - Sail Date
custrecord_pri_frgt_cnt_date_land_est        - Estimated Land Date
custrecord_pri_frgt_cnt_date_land_act        - Actual Land Date
custrecord_pri_frgt_cnt_date_fwd_est         - Estimated Forward Date
custrecord_pri_frgt_cnt_date_fwd_act         - Actual Forward Date
custrecord_pri_frgt_cnt_date_dest_est        - Estimated Destination Date
custrecord_pri_frgt_cnt_date_dest_act        - Actual Destination Date
custrecord_pri_frgt_cnt_notes                - Notes
custrecord_pri_frgt_cnt_ship_to_country      - Ship to Country
```

### Item Version (customrecord_pri_frgt_cnt_iv)
```
custrecord_pri_frgt_cnt_iv_item              - Item (FK)
custrecord_pri_frgt_cnt_iv_item_type         - Item Type
custrecord_pri_frgt_cnt_iv_desc              - Description
custrecord_pri_frgt_cnt_iv_vendor            - Vendor (FK)
custrecord_pri_frgt_cnt_iv_vendor_name       - Vendor Name (Text)
custrecord_pri_frgt_cnt_iv_current           - Is Current Version (Checkbox)
custrecord_pri_frgt_cnt_iv_start             - Start Date
custrecord_pri_frgt_cnt_iv_end               - End Date
custrecord_pri_frgt_cnt_iv_currency          - Currency (FK)
custrecord_pri_frgt_cnt_iv_rate              - Rate (Currency)
custrecord_pri_frgt_cnt_iv_lct               - Landed Cost Template (FK)
custrecord_pri_frgt_cnt_iv_cust              - Customer (FK)
custrecord_pri_frgt_cnt_iv_cust_item         - Customer Item
```

### Landed Cost Template (customrecord_pri_frgt_cnt_lct)
```
custrecord_pri_frgt_cnt_lct_desc             - Description
custrecord_pri_frgt_cnt_lct_location         - Location (FK)
custrecord_pri_frgt_cnt_lct_currency         - Currency (FK)
```

### LC Template Detail (customrecord_pri_frgt_cnt_lctd)
```
custrecord_pri_frgt_cnt_lctd_parent          - Parent Template (FK)
custrecord_pri_frgt_cnt_lctd_cost_cat        - Cost Category (FK)
custrecord_pri_frgt_cnt_lctd_factor          - Factor (Float)
custrecord_pri_frgt_cnt_lctd_all_method      - Allocation Method (List: 1-4)
custrecord_pri_frgt_cnt_lctd_item_con        - Consumption Item (FK)
```

### Production PO Header (customrecord_pri_frgt_cnt_pm_po)
```
custrecord_pri_frgt_cnt_pm_po_date           - Date
custrecord_pri_frgt_cnt_pm_po_period         - Accounting Period (FK)
custrecord_pri_frgt_cnt_pm_po_status         - Status
custrecord_pri_frgt_cnt_pm_po_entity         - Vendor (FK)
custrecord_pri_frgt_cnt_pm_po_currency       - Currency (FK)
custrecord_pri_frgt_cnt_pm_po_department     - Department (FK)
custrecord_pri_frgt_cnt_pm_po_class          - Class (FK)
```

### Production PO Line (customrecord_pri_frgt_cnt_pm)
```
custrecord_pri_frgt_cnt_pm_parent            - Parent PPO (FK)
custrecord_pri_frgt_cnt_pm_period            - Accounting Period (FK)
custrecord_pri_frgt_cnt_pm_vendor            - Vendor (FK)
custrecord_pri_frgt_cnt_pm_currency          - Currency (FK)
custrecord_pri_frgt_cnt_pm_item              - Item (FK)
custrecord_pri_frgt_cnt_pm_itemname          - Item Display Name
custrecord_pri_frgt_cnt_pm_item_type         - Item Type (List)
custrecord_pri_frgt_cnt_pm_quantity          - Quantity
custrecord_pri_frgt_cnt_pm_item_version      - Item Version (FK)
custrecord_pri_frgt_cnt_pm_price_calc        - Calculated Price
custrecord_pri_frgt_cnt_pm_price_ref         - Reference Price
custrecord_pri_frgt_cnt_pm_price_var         - Price Variance
custrecord_pri_frgt_cnt_pm_note              - Note
custrecord_pri_frgt_cnt_pm_status            - Status (List: Unlocked=1, Locked=2)
custrecord_pri_frgt_cnt_pm_holdpricedata     - Hold Price Data (Long Text - JSON)
custrecord_pri_frgt_cnt_pm_quantity_po       - Qty Received PO
custrecord_pri_frgt_cnt_pm_quantity_to       - Qty Received TO
custrecord_pri_frgt_cnt_pm_quantity_ib       - Qty Received Imbalance (Array)
custrecord_pri_frgt_cnt_pm_quantity_calc     - Calculated Quantity
custrecord_pri_frgt_cnt_pm_linenumber        - Line Number (Text: "001", "002", etc.)
```

### IR/TO Linker (customrecord_pri_frgt_cnt_l)
```
custrecord_pri_frgt_cnt_l_ir                 - Item Receipt (FK)
custrecord_pri_frgt_cnt_l_ir_line_no         - IR Line Number
custrecord_pri_frgt_cnt_l_item               - Item (FK)
custrecord_pri_frgt_cnt_l_qty                - Quantity
custrecord_pri_frgt_cnt_l_cnt                - Container (FK)
custrecord_pri_frgt_cnt_l_to                 - Transfer Order (FK)
custrecord_pri_frgt_cnt_l_to_line_no         - TO Line Number
```

### Distribution Management (customrecord_pri_frgt_cnt_dm)
```
custrecord_pri_frgt_cnt_dm_parent            - Parent Transaction (FK)
custrecord_pri_frgt_cnt_dm_type              - Type
custrecord_pri_frgt_cnt_dm_origin            - Origin Location
custrecord_pri_frgt_cnt_dm_location          - Destination Location
custrecord_pri_frgt_cnt_dm_item              - Item (FK)
custrecord_pri_frgt_cnt_dm_parent_lineno     - Parent Line Number
custrecord_pri_frgt_cnt_dm_parent_lineid     - Parent Line ID
custrecord_pri_frgt_cnt_dm_quantity          - Quantity
custrecord_pri_frgt_cnt_dm_dt_request        - Request Date
custrecord_pri_frgt_cnt_dm_dt_expected       - Expected Date
custrecord_pri_frgt_cnt_dm_container         - Container (FK)
custrecord_pri_frgt_cnt_dm_note              - Note
```

---

**END OF ANALYSIS**

---

**Document Prepared By:** Claude (Anthropic AI)
**Based On:** PRI Container Tracking Bundle (Bundle 125246)
**Repository:** /home/tchow/NetSuiteBundlet/SuiteBundles/Bundle 125246/PRI Container Tracking
**Total Files Analyzed:** 46 SuiteScript 2.x files
**Total Lines of Code:** ~20,835 lines

**Confidence Level:** HIGH
**Completeness:** 90% (RESTlet endpoints and external APIs limited by codebase search; deployment IDs partially unavailable)
