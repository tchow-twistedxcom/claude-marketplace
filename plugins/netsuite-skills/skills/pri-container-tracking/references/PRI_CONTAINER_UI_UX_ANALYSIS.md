# PRI Container Tracking - UI/UX Analysis
**System**: PRI Container Tracking (Bundle 125246)
**Analysis Date**: 2025-11-12
**Purpose**: User interface and interaction documentation

---

## Executive Summary

The PRI Container Tracking system provides a comprehensive freight container management interface for NetSuite users. The system features custom Suitelets for data generation, client-side validation and field interactions, and automated workflows through scheduled scripts.

**Key UI Components**: 3 Suitelets, 8 Client Scripts, 14 User Event Scripts, 9 Scheduled Scripts
**Primary Users**: Supply chain managers, inventory controllers, procurement staff
**Core Workflows**: Container tracking, PO generation, inventory receipt management, landed cost allocation

---

## 1. User-Facing Screens (Suitelets)

### 1.1 Production PO Generator (`pri_cntProdPoGenerator_sl.js`)

**Purpose**: Generate Distribution Purchase Orders from Production PO management records

**Screen Elements**:
- **Header Section**:
  - PO Header selector (mandatory, inline display)
  - Dynamic fields from script parameters (transaction date, department, class, location)
  - Ultimate location and date fields for freight tracking
  - Memo field for order notes
  - Success message display (when PO is created)

- **Item Sublist** (`custpage_item`):
  - Checkbox selection for items to include
  - Item name/SKU display
  - Quantity input (editable)
  - Item type indicator
  - PO line internal ID reference
  - Negative rate item warning column

**User Workflow**:
```
1. Access via URL parameter: custparam_poheaderid=[ID]
2. Review pre-populated header and line items
3. Select items to include (checkbox)
4. Adjust quantities as needed
5. Click "Generate & Redirect to Purchase Order"
6. System creates PO and redirects to view
```

**Validation Rules**:
- At least one line item must be checked
- Warning for negative rate items (user confirmation required)
- Quantity must be specified for selected items

**Client-Side Behavior** (`pri_cntProdPoGenerator_cl.js`):
- Auto-check checkbox when quantity is entered
- Auto-redirect to created PO on success
- Dialog alerts for validation errors
- Prevent submission if no items selected

---

### 1.2 Inventory Counts Generator (`pri_SL_generateInventoryCounts.js`)

**Purpose**: Generate inventory count reports across locations with container tracking

**Screen Elements**:
- **Selection Criteria Group**:
  - Multi-select locations (or all if none selected)
  - Multi-select items (filtered to active inventory items, max 1000)
  - Show Intransit Detail checkbox
  - Generate Download (CSV) checkbox
  - Debug mode (admin only)
  - Show Usage checkbox (admin only)

- **Results Display**:
  - HTML table with location-based inventory data
  - Columns: On Order, In Transit From, In Transit To, On Hand
  - Period summary information (from custom records)
  - Debug information panel (when enabled)
  - Performance metrics (time and governance units)

**User Workflow**:
```
1. Select locations (optional - defaults to all)
2. Select items (optional - defaults to all active inventory)
3. Choose display options (intransit detail, CSV download)
4. Click Submit
5. View results table or download CSV file
```

**Special Features**:
- CSV export functionality with automatic download
- Performance monitoring for admin users
- Debug mode for single-item deep analysis
- Dynamic period summary from custom records
- Handles up to 1000 items in search

---

### 1.3 Container Data Generator (`pri_SL_GenerateContainerData.js`)

**Purpose**: Generate detailed container shipping and receipt data

**Screen Elements**:
- **Selection Criteria Group**:
  - Container selector (single select, optional - shows all if blank)
  - Location selector (single select, optional - shows all if blank)
  - 3PL Receipt Date FROM (date field)
  - 3PL Receipt Date THRU (date field)
  - Generate Download (CSV) checkbox
  - Show Usage checkbox (admin only)

- **Results Display**:
  - HTML table with alternating row colors for readability
  - Columns:
    - Location Name
    - Invoice Number
    - Sailing Date
    - ETA Date
    - Container Name
    - Seal Number
    - Item Name/Description
    - Quantity
    - PO Number
    - Order Number
    - Receipts In Transit
    - Receipts Into 3PL
    - 3PL Receipt Date

**User Workflow**:
```
1. Select container (optional)
2. Select location (optional)
3. Enter date range for 3PL receipts (optional)
4. Choose CSV export if needed
5. Click Submit
6. Review container details in table or download CSV
```

**Data Processing**:
- Loads container master data (seal, vessel, dates)
- Matches transfer orders to containers by location
- Aggregates item receipt data (both PO and TO receipts)
- Filters to show only containers with receipts
- Sorts results by container name

**Special Features**:
- Legacy container handling mode (configurable via script parameter)
- Handles both column-level and body-level container fields
- Performance tracking with governance unit monitoring
- Alternating row colors for better readability

---

## 2. Form Customizations (Client Scripts)

### 2.1 Container Record (`pri_CL_container.js`)

**Record Type**: Custom Record - PRI Freight Container
**Deployment**: Form-level client script

**Field Interactions**:
- **Sailing Date Change**:
  - Auto-calculates Date Destination Estimate
  - Considers transit days from departure port
  - Validates against arrival adjusted date

- **Ownership Type Change**:
  - Recalculates transit time based on ownership
  - Updates destination estimate

- **Departure Port Change**:
  - Looks up transit time from port/ownership combination
  - Updates estimated arrival calculation

**Validation on Save**:
1. **Status Validation**:
   - If status = "Received", Date Destination Actual is REQUIRED
   - Shows notification: "Please enter value for: DATE DESTINATION ACTUAL"

2. **Bin Validation** (PTM17262):
   - If status = "Received" AND destination location uses bins
   - Bin field becomes REQUIRED
   - Shows notification with field label: "Please enter value for: Bin (For Receiving)"
   - Loads location record to check `usebins` setting

**Calculated Fields**:
- **Date Destination Estimate (Calculated)**:
  ```
  = Sailing Date + Transit Days (from port/ownership lookup)
  ```
- **Date Destination Estimate (Adjusted)**:
  - Uses calculated value if not manually set
  - Can be manually overridden by user
  - Validation ensures it's >= calculated estimate (if validation enabled)

**Integration**:
- Uses `PRI_AS_Engine` for application settings
- Calls shared library `pri_itemrcpt_cllib` for transit time lookup
- Integrates with `pri_idRecord_cslib` for field ID constants

---

### 2.2 Vessel Record (`pri_CL_vessel.js`)

**Record Type**: Custom Record - PRI Freight Container Vessel
**Deployment**: Form-level client script

**Field Validation**:
- **Status Field** (`custrecord_pri_frgt_cnt_vsl_log_status`):
  - Validates against allowed statuses from application settings
  - Reads from: `Prolecto Freight Container & Landed Cost > Vessel Allowed Status Manually`
  - Shows notification if invalid: "Vessel Status Validation. Not allow move to: [Status Name]"
  - Prevents field change if not in allowed list

**Validation on Save**:
1. **Date Destination Actual Required**:
   - If status = "Received", date field is REQUIRED
   - Field ID: `custrecord_pri_frgt_cnt_vsl_date_destact`
   - Dynamic field label retrieval for user-friendly messages

2. **Bin Validation** (PTM17546):
   - If status = "Received" AND destination location uses bins
   - Bin field (`custrecord_pri_frgt_cnt_vsl_bin`) is REQUIRED
   - Loads location record dynamically to check bin usage
   - Shows notification with actual field label

**User Experience**:
- Real-time validation prevents invalid status changes
- Dynamic field label resolution for internationalization support
- Notification duration: 5 seconds for all messages
- Validates location bin requirements before save

---

### 2.3 Item Receipt - Freight (`pri_itemrecptFrgt_cl.js`)

**Record Type**: Native Transaction - Item Receipt
**Purpose**: Validate transaction dates against container sailing dates

**Field Validation**:
- **Transaction Date** (`trandate`):
  - Validates on field change AND on save
  - Only applies to Purchase Order-based receipts (not Transfer Orders)
  - Compares transaction date to Container Sailing Date
  - **Rule**: Transaction Date must be ≤ Container Sailing Date

**Validation Logic**:
```javascript
If (Transaction Date > Container Sailing Date) {
  Show Warning: "Transaction Date must be on or before Container Sailing Date: [Date]"
  Clear transaction date field
  Return false
}
```

**User Workflow**:
```
1. User enters or changes transaction date
2. System checks if container is linked
3. If PO receipt: validates date against container sailing date
4. If invalid: clears field and shows warning
5. On save: re-validates before allowing save
```

**Technical Details**:
- Uses `search.lookupFields` to retrieve container sailing date
- Helper function: `pri_itemrcpt_getCreatedFromType()` determines receipt source
- Warning message display duration: 5 seconds
- Sets `ignoreFieldChange: true` when clearing invalid date

---

### 2.4 Item Receipt - Main (`pri_itemrecpt_cl.js`)

**Record Type**: Native Transaction - Item Receipt
**Purpose**: Container distribution management and receipt quantity validation

**Page Initialization**:
- Auto-selects "Receipt" tab on page load
- Binds dynamic container distribution dropdown events
- Initializes distribution management for each line item

**Field Interactions**:
- **Location Change**:
  - Refreshes container distribution dropdown options
  - Updates available containers based on new location
  - Clears selection if no location specified

- **Receipt Quantity Change** (`custpage_receipts_received`):
  - Validates positive values only
  - Shows error if ≤ 0: "Please specify positive value for 'Received' quantity"
  - Clears field if invalid

**Validation on Save**:

1. **Item Version/LC Template Warning** (PTM12586):
   - Scans all inventory item lines for missing item versions
   - If missing: shows confirmation dialog
   - Message: "An Item Version/LC template is missing... landed cost will not be calculated. Are you sure?"
   - User can proceed or cancel
   - Uses async promise pattern for dialog

2. **Receipt Quantity Validation**:
   - Auto-marks all items (calls native `itemMarkAll(true)`)
   - Checks `custpage_receipts` sublist for received quantities
   - Error if no quantities: "Please specify 'Received' quantity in subtab [Label]"
   - Auto-selects receipt tab to help user

3. **Container Distribution**:
   - Validates distribution selections for each line
   - Ensures container matches location requirements

**Dynamic UI Components**:
- **Container Distribution Dropdown**:
  - Dynamically populated based on:
    - Purchase Order
    - Item
    - Location(s)
    - Order Line
  - Bound to each item line via DOM ID: `custpage_ctndistmgmt_[lineIndex]`
  - Options refresh on location change

**Custom Buttons**:
- **Recalculate Landed Cost** (`btnEvent_recalclandedcost`):
  - Calls Suitelet: `customscript_pri_itemrecpt_lcalloc_sl`
  - Uses HTTPS POST with transaction ID
  - Reloads page after processing
  - Async operation with promise handling

**Technical Details**:
- Uses legacy NetSuite API (`nlapiGetLineItemValue`) for sublist access
- Window variable `window.PROCEEDSAVE` for async dialog handling
- Form submission via native form methods
- Integrates with `pri_itemrcpt_cllib` shared library

---

### 2.5 Purchase Order (`pri_purchord_cs.js`)

**Record Type**: Native Transaction - Purchase Order
**Purpose**: Item version management and price sourcing

**Field Interactions**:

1. **Item Version Change** (`custcol_pri_frgt_cnt_iv`):
   - Auto-sources rate and description from Item Version record
   - Uses async promise pattern for field lookup
   - Updates:
     - Description field (transaction line)
     - Item Version Source field (for tracking)
   - Window variable tracking: `window.priFrgtCtnCurLnItm`

2. **Item Selection** (Post-Sourcing):
   - Filters non-standard item types (EndGroup, Discount, Description, OthCharge)
   - Restores Item Version from Source field if different item
   - Handles item group member synchronization

**Line Initialization**:
- Tracks current line item in window variable
- Used to prevent redundant sourcing operations
- Enables smart field restoration

**Line Validation** (on Commit):
- Syncs Item Version to Item Version Source field
- Preserves selected version for future reference
- Handles empty values gracefully

**Price Sourcing Logic**:
```javascript
When Item Version changes:
1. Lookup Item Version record
2. Retrieve: Rate, Description
3. Set Description field (committed)
4. Item Version Source updated for tracking
5. On error: Clear rate, show alert, restore version
```

**Error Handling**:
- Promise rejection shows user-friendly dialog
- Error message: "Failed on sourcing Item Version's rate value"
- Suggests re-entering item
- Logs error for debugging

**Integration Points**:
- Uses `pri_idRecord_cslib` for field ID constants
- Uses `utils/Const` for application constants
- Works with Item Version custom record type

---

### 2.6 Production PO Management (`pri_cntProdMgmt_cl.js`)

**Record Type**: Custom Record - PRI Container Production Management PO
**Purpose**: Bulk price lock/unlock operations and recalculation

**Custom Buttons**:

1. **Lock Line Prices** (`pri_cntProdMgmt_locklineprices`):
   - Searches all PO lines for this header
   - Updates status to "Locked" for all lines
   - Disables button during processing
   - Shows wait notification
   - Reloads page after completion
   - Uses promise-based iteration

2. **Unlock Line Prices** (`pri_cntProdMgmt_unlocklineprices`):
   - Searches all PO lines for this header
   - Updates status to "Unlocked" for all lines
   - Disables button during processing
   - Shows wait notification
   - Reloads page after completion

3. **Recalculate Item Receipt** (`pri_cntProdMgmt_recalcItemReceipt`):
   - Triggers backend recalculation via URL parameter
   - Parameter: `custparam_recalcitemrcpt=T`
   - Uses HTTPS GET request
   - Disables button during processing
   - Reloads on success or error

4. **Recalculate Unlocked Lines** (`pri_cntProdMgmt_recalc_unlockedline`):
   - Recalculates prices for unlocked lines only
   - Parameter: `custparam_ppo_recalc_price=T`
   - Shows extended wait message (15 seconds)
   - Auto-reloads after 15 seconds
   - Allows background processing

**Button Behavior**:
- All buttons disabled during processing (primary and secondary)
- User-friendly wait alerts
- Automatic page refresh on completion
- Error handling with fallback refresh

**Status Management**:
- **Locked Status**: Prevents price changes
- **Unlocked Status**: Allows price recalculation
- Bulk operations across all child PO lines
- Uses `record.submitFields` for efficiency

**Technical Details**:
- Uses async search with promise-based iteration
- Disables both primary and secondary button instances
- Console logging for debugging
- setTimeout for delayed reload (recalculation button)

---

### 2.7 Production PO Management Line (`pri_cntProdMgmtLn_cl.js`)

**Record Type**: Custom Record - PRI Production PO Line
**API Version**: 1.0 (Legacy NetSuite API)

**Purpose**: Control Item Version field based on item type

**Field Interactions**:

1. **Item Change** (`custrecord_pri_frgt_cnt_pm_item`):
   - Triggers on field change and post-sourcing
   - Evaluates item type
   - Enables/disables Item Version field

2. **Item Version Field** (`custrecord_pri_frgt_cnt_pm_item_version`):
   - **Disabled** when Item Type = "Item Group"
   - **Enabled** for all other item types

**Logic**:
```javascript
If (Item Type == 'Item Group') {
  Disable Item Version field
} else {
  Enable Item Version field
}
```

**Events**:
- `clientPageInit`: Run on page load
- `clientFieldChanged`: Run on item field change
- `clientPostSourcing`: Run after item sourcing

**User Experience**:
- Prevents invalid item version selection for item groups
- Automatically enables field for individual items
- No user interaction required - handles automatically

**Technical Notes**:
- Uses legacy `nlapiGetFieldText()` and `nlapiDisableField()`
- Simple toggle function for field state
- No validation errors - preventive UI control

---

## 3. User Workflows

### 3.1 Production PO Generation Workflow

```
ACTOR: Procurement Manager

1. Navigate to Production PO Management record
2. Review container items and quantities
3. Click "Open PO Generator" or access Suitelet directly
   └─> URL: [suitelet]?custparam_poheaderid=[ID]

4. PO Generator Screen Displays:
   ├─> Header fields pre-populated
   ├─> Item list with quantities
   └─> All items unchecked by default

5. User Actions:
   ├─> Select items to include (checkboxes)
   ├─> Adjust quantities if needed
   │   └─> Auto-checks checkbox on quantity entry
   └─> Review negative rate warnings

6. Click "Generate & Redirect to Purchase Order"

7. Client-Side Validation:
   ├─> Check: At least one item selected?
   │   └─> NO: Show alert, return to form
   ├─> Check: Any negative rate items?
   │   └─> YES: Confirm with user
   └─> Pass: Submit form

8. Server-Side Processing:
   ├─> Create Purchase Order (dynamic mode)
   ├─> Set header fields (vendor, dates, locations)
   ├─> Add selected items with quantities
   ├─> Handle item groups (sync sub-items)
   ├─> Set item versions and prices
   └─> Save PO

9. Redirect to Created PO:
   ├─> Client script detects success parameter
   ├─> Auto-redirects to PO view
   └─> Shows confirmation dialog

RESULT: Distribution Purchase Order created and ready for processing
```

---

### 3.2 Container Receipt Workflow

```
ACTOR: Warehouse Supervisor

1. Receive container at warehouse
2. Update Container Record:
   ├─> Set Sailing Date
   │   └─> Auto-calculates Destination Estimate
   ├─> Set Destination Location
   └─> Update Status to "Received"

3. Client Validation Triggers:
   ├─> Check: Date Destination Actual filled?
   │   └─> NO: Block save, show notification
   ├─> Check: Location uses bins?
   │   ├─> YES: Require bin selection
   │   └─> NO: Allow save
   └─> Pass: Save container record

4. Create Item Receipt from Transfer Order:
   ├─> Select container in body field
   ├─> Auto-populates Receipt tab
   └─> Container distribution dropdown appears

5. For each line item:
   ├─> Select location
   │   └─> Distribution options refresh
   ├─> Select container distribution
   └─> Enter received quantity

6. Enter Transaction Date:
   ├─> Client validates against Container Sailing Date
   ├─> If invalid: Clear field, show warning
   └─> If valid: Accept date

7. Review Item Versions:
   ├─> System checks for missing versions
   ├─> If missing: Show warning dialog
   └─> User confirms or cancels

8. Click Save:
   ├─> Validate receipt quantities > 0
   ├─> Validate container distributions
   ├─> Create item receipt transaction
   └─> Update container tracking data

9. Optional: Recalculate Landed Cost
   └─> Click "Recalculate Landed Cost" button

RESULT: Container received, inventory updated, landed costs allocated
```

---

### 3.3 Inventory Count Analysis Workflow

```
ACTOR: Inventory Controller

1. Navigate to Inventory Counts Generator Suitelet
   └─> Access via custom link or script deployment

2. Selection Criteria Screen:
   ├─> Select Locations (multi-select)
   │   └─> Leave blank for all locations
   ├─> Select Items (multi-select)
   │   └─> Leave blank for all active inventory items
   ├─> Check "Show Intransit Detail" for drill-down
   └─> Check "Generate Download" for CSV export

3. Click Submit

4. Server Processing:
   ├─> Query container tracking data
   ├─> Calculate quantities by location
   │   ├─> On Order (from POs)
   │   ├─> In Transit From (outbound transfers)
   │   ├─> In Transit To (inbound transfers)
   │   └─> On Hand (current stock)
   └─> Generate report

5. View Results:
   ├─> HTML Table View:
   │   ├─> Columns: Location headers
   │   ├─> Rows: Items with quantities
   │   └─> Period summary information
   └─> CSV Download:
       └─> Automatic file download

6. Analysis Options:
   ├─> Review location-specific inventory
   ├─> Identify items in transit
   ├─> Compare on-order vs on-hand
   └─> Export for further analysis

7. Performance Monitoring (Admin):
   ├─> Check execution time
   └─> Review governance units consumed

RESULT: Comprehensive inventory position report across locations
```

---

### 3.4 Production PO Price Management Workflow

```
ACTOR: Procurement Analyst

1. Access Production PO Management record
2. Review line item prices and quantities

3. Initial Price Lock:
   ├─> Click "Lock Line Prices" button
   ├─> System disables button
   ├─> Shows wait notification
   └─> Updates all lines to "Locked" status

4. Item Receipt Processing:
   ├─> Receipts created against linked POs
   ├─> Quantities change on PO lines
   └─> Need to recalculate received amounts

5. Recalculate Receipts:
   ├─> Click "Recalculate Item Receipt" button
   ├─> Backend processes all receipt data
   └─> Page reloads with updated quantities

6. Price Adjustment Phase:
   ├─> Click "Unlock Line Prices" button
   ├─> System unlocks all lines
   └─> Lines now editable

7. Manual Adjustments:
   ├─> Edit specific line items
   ├─> Update prices or quantities
   └─> Save individual line changes

8. Selective Recalculation:
   ├─> Click "Recalculate Unlocked Lines" button
   ├─> Shows 15-second wait message
   ├─> Backend recalculates only unlocked lines
   └─> Page auto-reloads

9. Final Lock:
   └─> Click "Lock Line Prices" again when finalized

RESULT: Production PO prices locked and aligned with receipts
```

---

## 4. Validation Rules Summary

### 4.1 Client-Side Validations

| Screen/Record | Field/Trigger | Validation Rule | Error Message | Action |
|---------------|---------------|-----------------|---------------|--------|
| **PO Generator** | Save | At least one item checked | "Please check at least one line item to generate Purchase Order" | Block save |
| **PO Generator** | Save | Negative rate items | Confirmation: "Are you sure would like to generate a PO with negative rate item(s)?" | Require confirmation |
| **Container** | Save | Status = Received | Date Destination Actual required | Block save, show notification |
| **Container** | Save | Status = Received + Bin location | Bin field required | Block save, show notification |
| **Vessel** | Field Change | Status field | Must be in allowed statuses | Block change, show notification |
| **Vessel** | Save | Status = Received | Date Destination Actual required | Block save, show notification |
| **Vessel** | Save | Status = Received + Bin location | Bin field required | Block save, show notification |
| **Item Receipt** | Field Change | Transaction Date | Must be ≤ Container Sailing Date | Clear field, show warning |
| **Item Receipt** | Save | Receipt Quantity | Must be > 0 | Block save, show alert |
| **Item Receipt** | Save | Receipt Quantity | At least one line must have quantity | Block save, show alert |
| **Item Receipt** | Save | Item Version | Warning if missing on inventory items | Show confirmation dialog |
| **Purchase Order** | Line Commit | Item Version | Must be valid for item type | (Preventive - no error) |

### 4.2 Field-Level Validations

| Field Type | Validation | User Experience |
|------------|-----------|-----------------|
| **Date Fields** | Must be valid date format | Native NetSuite validation |
| **Numeric Fields** | Must be positive numbers (quantities) | Client-side check, clear if invalid |
| **Select Fields** | Must be in dropdown options | Native NetSuite validation |
| **Required Fields** | Cannot be empty | Block save, show field label in message |
| **Calculated Fields** | Auto-calculated, may be overridden | Visual indicator of calculation |

### 4.3 Business Logic Validations

1. **Container-PO Relationship**:
   - Transaction date must respect container sailing date
   - Location must match container destination
   - Item must be on container manifest

2. **Item Version Logic**:
   - Disabled for item groups
   - Required for individual items (soft requirement)
   - Auto-sources from item master if not specified

3. **Status Transitions**:
   - Vessel status limited to allowed values
   - Received status requires actual date
   - Bin required if location uses bins

4. **Price Management**:
   - Locked lines prevent price changes
   - Unlocked lines allow recalculation
   - Global operations affect all lines

---

## 5. User Interaction Patterns

### 5.1 Auto-Selection Patterns

| Trigger | Auto-Action | Purpose |
|---------|------------|---------|
| Quantity entered | Check item checkbox | Indicate item will be included |
| Location changed | Refresh container dropdown | Show valid containers for location |
| Item selected (PO) | Set item version from source | Restore previous version selection |
| Sailing date set | Calculate destination estimate | Provide automatic ETA |
| Page load (receipt) | Select Receipt tab | Focus on data entry area |

### 5.2 Feedback Mechanisms

| Event Type | Feedback Method | Duration/Behavior |
|------------|----------------|-------------------|
| **Validation Error** | Modal dialog alert | User must acknowledge |
| **Field Warning** | Message notification | 5 seconds auto-dismiss |
| **Confirmation** | Modal dialog confirm | User choice required |
| **Processing** | Disabled button + alert | Until completion |
| **Success** | Inline message + redirect | Immediate redirect |
| **Async Operation** | Promise-based notification | Error or success callback |

### 5.3 Navigation Patterns

| Pattern | Implementation | User Experience |
|---------|----------------|-----------------|
| **Auto-Redirect** | Client-side location.href change | Seamless transition to created record |
| **Tab Selection** | ShowTab() and ShowitemsMachine() | Auto-focus on data entry area |
| **Page Reload** | location.href = location.href | Refresh to show updated data |
| **Delayed Reload** | setTimeout(reload, 15000) | Allow backend processing time |
| **Modal Dialog** | N/ui/dialog module | Block interaction during confirmation |

### 5.4 Error Recovery Patterns

| Error Scenario | Recovery Mechanism | User Guidance |
|----------------|-------------------|---------------|
| **Invalid date entry** | Clear field, show warning | Re-enter valid date |
| **Missing required field** | Block save, show field name | Fill required field |
| **Negative quantity** | Clear field, show error | Enter positive quantity |
| **No items selected** | Block save, show alert | Select at least one item |
| **Item version sourcing failure** | Show error, restore value | Try re-entering item |
| **Backend processing error** | Show error, reload page | Contact support if persists |

---

## 6. Client-Side vs Server-Side Logic Distribution

### 6.1 Client-Side Responsibilities

**Validation**:
- Positive number checks (quantities)
- Date format validation
- Required field checks (before save)
- Business rule enforcement (date <= sailing date)
- Item selection validation (at least one)

**UI Manipulation**:
- Dynamic dropdown population/refresh
- Field enable/disable based on item type
- Auto-selection of related fields
- Tab selection and focus management
- Progress indicators during processing

**User Feedback**:
- Validation error messages
- Warning notifications
- Confirmation dialogs
- Success messages
- Wait notifications during async operations

**State Management**:
- Window variables for tracking (priFrgtCtnCurLnItm)
- Button enable/disable states
- Form submission flags (PROCEEDSAVE)

### 6.2 Server-Side Responsibilities

**Data Retrieval**:
- Search operations (containers, items, receipts)
- Record loading (container, vessel, location)
- Field lookups (item version rate, transit days)
- Related record queries (PO lines, receipts)

**Business Logic**:
- Transit time calculation
- Container-item matching
- Receipt quantity aggregation
- Landed cost allocation
- Price locking/unlocking

**Data Persistence**:
- Record creation (Purchase Orders)
- Field updates (status changes, prices)
- Bulk updates (lock/unlock operations)
- Transaction saving

**Report Generation**:
- Inventory count calculations
- Container data aggregation
- CSV file generation
- HTML table rendering

### 6.3 Interaction Patterns

**Client → Server → Client Loop**:
```
1. User Action (client)
2. Validation (client)
3. Submit Request (client → server)
4. Process Logic (server)
5. Return Result (server → client)
6. Update UI / Show Feedback (client)
```

**Async Pattern**:
```javascript
// Client-side async request
https.post.promise({...})
  .then(success => {
    // Show success, reload
  })
  .catch(error => {
    // Show error, reload
  });
```

**Promise-Based Validation**:
```javascript
// Client-side promise for user confirmation
dialog.confirm({...})
  .then(result => {
    if (result) submitForm();
  })
  .catch(() => {
    return false;
  });
```

---

## 7. Accessibility and Usability Considerations

### 7.1 Current Implementation

**Strengths**:
- Clear field labels
- Required field indicators
- Error messages reference field labels
- Confirmation dialogs for destructive actions
- Auto-focus on data entry areas
- Visual feedback during processing

**Gaps**:
- Limited keyboard navigation support
- No screen reader optimizations
- No ARIA labels on custom dropdowns
- Notification duration not configurable
- No high-contrast mode support

### 7.2 User Experience Enhancements

**Implemented**:
- Auto-calculation of dates/quantities
- Intelligent field defaulting
- Progressive disclosure (tab selection)
- Bulk operations with feedback
- CSV export for external analysis
- Performance monitoring for admins

**Recommended**:
- Keyboard shortcuts for common actions
- Configurable notification durations
- Undo functionality for bulk operations
- Inline help text for complex fields
- Mobile-responsive layouts
- Accessibility audit and WCAG compliance

### 7.3 Performance Optimizations

**Current Optimizations**:
- Promise-based async operations
- Bulk field updates vs individual record saves
- Pagination in search results (1000 records/page)
- Governance unit monitoring
- Execution time tracking

**Additional Recommendations**:
- Cache frequently accessed lookups
- Debounce dropdown refresh operations
- Lazy load item lists (>1000 items)
- Client-side caching of container data
- Background processing for bulk operations

---

## 8. Integration Points

### 8.1 External Systems

| Integration Type | Method | Purpose |
|-----------------|--------|---------|
| **3PL Systems** | Date fields | Track 3PL receipt dates |
| **Shipping Carriers** | Container/Vessel records | Track container status |
| **ERP/Planning** | CSV exports | Inventory planning data |

### 8.2 NetSuite Native Features

| Feature | Integration | Impact on UI |
|---------|------------|--------------|
| **Location Bins** | Dynamic validation | Show/hide bin requirement |
| **Item Groups** | Field enable/disable | Control item version field |
| **Purchase Orders** | Transaction creation | Generate PO from Suitelet |
| **Transfer Orders** | Receipt processing | Container distribution |
| **Item Receipts** | Custom fields/tabs | Receipt subtab injection |

### 8.3 Custom Records

| Custom Record | UI Component | Purpose |
|---------------|--------------|---------|
| **PRI Freight Container** | Form customization | Container tracking |
| **PRI Vessel** | Form customization | Vessel status management |
| **PRI Production PO** | Suitelet + Form | PO generation workflow |
| **PRI Production PO Line** | Form customization | Line-level price control |
| **Item Version** | Lookup/sourcing | Price and description sourcing |

---

## 9. Key Findings and Recommendations

### 9.1 Strengths

1. **Comprehensive Validation**: Multi-layer validation prevents data integrity issues
2. **User-Friendly Workflows**: Auto-calculations and intelligent defaulting reduce errors
3. **Bulk Operations**: Efficient handling of multi-line price management
4. **Flexible Reporting**: Multiple export formats and filtering options
5. **Performance Monitoring**: Governance tracking helps optimize operations
6. **Error Recovery**: Clear error messages with field-level guidance

### 9.2 Areas for Improvement

1. **Accessibility**: Add ARIA labels, keyboard navigation, screen reader support
2. **Mobile Experience**: Responsive layouts for tablet/mobile users
3. **Inline Help**: Contextual help for complex fields and workflows
4. **Undo Functionality**: Allow reversal of bulk lock/unlock operations
5. **Advanced Filtering**: More granular search options in Suitelets
6. **Progress Indicators**: Better feedback during long-running operations

### 9.3 Technical Debt

1. **Legacy API Usage**: Some scripts use NetSuite 1.0 API (nlapiX functions)
2. **Global Variables**: Window-scoped variables for state management
3. **Mixed Async Patterns**: Combination of callbacks and promises
4. **Hard-coded Timeouts**: setTimeout with fixed durations
5. **Form Submission Methods**: Mixed native and NetSuite methods

### 9.4 Modernization Opportunities

1. **React/Vue Components**: Replace Suitelet forms with modern UI
2. **RESTlet APIs**: Standardize backend communication
3. **WebSocket Updates**: Real-time status updates for containers
4. **Batch Processing**: Queue-based bulk operations
5. **Mobile App**: Native mobile app for warehouse operations
6. **API-First Design**: Expose functionality via documented APIs

---

## Appendix A: File Reference

### Suitelets
- `/pri_cntProdPoGenerator_sl.js` - Production PO Generator
- `/pri_SL_generateInventoryCounts.js` - Inventory Counts Generator
- `/pri_SL_GenerateContainerData.js` - Container Data Generator

### Client Scripts
- `/pri_cntProdPoGenerator_cl.js` - PO Generator client-side
- `/pri_CL_container.js` - Container record form
- `/pri_CL_vessel.js` - Vessel record form
- `/pri_itemrecptFrgt_cl.js` - Item Receipt date validation
- `/pri_itemrecpt_cl.js` - Item Receipt main form
- `/pri_purchord_cs.js` - Purchase Order form
- `/pri_cntProdMgmt_cl.js` - Production PO Management form
- `/pri_cntProdMgmtLn_cl.js` - Production PO Line form

### Shared Libraries
- `/pri_idRecord_cslib.js` - Field ID constants
- `/pri_itemrcpt_cllib.js` - Item Receipt shared functions
- `/pri_cntProdMgmt_lib.js` - Production PO shared functions
- `/utils/Const.js` - Application constants
- `/utils/Utils.js` - Utility functions

### User Event Scripts (Server-Side)
- 14 User Event scripts handling record lifecycle events
- See full list in `/SuiteBundles/Bundle 125246/PRI Container Tracking/`

### Scheduled Scripts (Automated Workflows)
- 9 Scheduled scripts for batch processing
- See full list in `/SuiteBundles/Bundle 125246/PRI Container Tracking/`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-12
**Analyst**: Claude (Frontend Architect)
