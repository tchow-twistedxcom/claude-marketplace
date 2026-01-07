# PRI Query Renderer - Complete Field Reference

## customrecord_pri_qt_query (Query Definition)

The main query record that defines a SuiteQL query in the Query Catalog.

| Field ID | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | Text | Yes | Display name in Query Catalog |
| `custrecord_pri_qt_q_query` | Long Text | Yes | The SuiteQL query text |
| `custrecord_pri_qt_q_description` | Text | No | User-facing description |
| `custrecord_twx_qt_q_category` | Text | No | Category for organizing queries |
| `custrecord_pri_qt_q_paged` | Checkbox | No | Enable pagination (T/F) |

### Example Query Record
```json
{
  "name": "Customer Sales Summary",
  "custrecord_pri_qt_q_query": "SELECT c.id, c.entityid, SUM(t.total) as total_sales FROM customer c JOIN transaction t ON t.entity = c.id WHERE t.type = 'SalesOrd' GROUP BY c.id, c.entityid",
  "custrecord_pri_qt_q_description": "Shows total sales by customer",
  "custrecord_twx_qt_q_category": "Sales Reports",
  "custrecord_pri_qt_q_paged": true
}
```

---

## customrecord_pri_qt_query_column (Column Definition)

Defines how each field in the query results is displayed.

| Field ID | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | Text | Yes | Column name matching SELECT alias (case-sensitive) |
| `custrecord_pri_qt_qc_parent` | Integer | **Yes** | Foreign key to query record ID |
| `custrecord_pri_qt_qc_heading` | Text | Yes | Display heading for the column |
| `custrecord_pri_qt_qc_data_type` | Text | Yes | Data type for formatting |
| `custrecord_pri_qt_qc_reference` | Checkbox | No | Reference-only column (not displayed) |
| `custrecord_pri_qt_qc_link_type` | Text | No | Link type: `linked_query`, `record_detail`, `none` |
| `custrecord_pri_qt_qc_linked_query` | Integer | No | ID of linked query (for `linked_query` type) |
| `custrecord_pri_qt_qc_recordtype` | Text | No | NetSuite record type (for `record_detail` type) |
| `custrecord_pri_qt_qc_heading_style` | Text | No | CSS styling for column header |
| `custrecord_pri_qt_qc_totals_row` | Checkbox | No | Show column totals (T/F) |
| `custrecord_pri_qt_qc_parms` | Text | No | Parameters for linked query |

### Data Types - Numeric IDs (NetSuite List Field)

**⚠️ CRITICAL:** This is a NetSuite List Field. You MUST use numeric IDs when creating/updating columns via API.

| ID | Description | Frontend Display | Formatting Applied |
|----|-------------|------------------|-------------------|
| 1 | Date | Date formatted | `MM/DD/YYYY` or localized |
| 2 | Integer | Whole numbers | Thousands separators |
| 3 | Currency | Money values | `$X,XXX.XX` |
| 4 | Decimal | Decimal numbers | Decimal places preserved |
| 5 | Checkbox | Boolean | Converts to Yes/No text |
| 6 | Percent | Percentage | `XX.XX%` |
| 7 | Float | Floating point | Numeric, minimal formatting |
| (null/omit) | Text (default) | Plain text | No special formatting |

**Common Mistake - Date Shows Blank:**
If your date column shows blank/empty values, check that `data_type` is set to `1` (Date), NOT `2` (Integer).

```json
// ❌ WRONG - Ship date will be blank because Integer (2) can't format dates
{ "name": "ship_date", "custrecord_pri_qt_qc_data_type": 2 }

// ✅ CORRECT - Date type (1) formats dates properly
{ "name": "ship_date", "custrecord_pri_qt_qc_data_type": 1 }
```

**Frontend Type Mapping:**
The NetSuite Reports frontend (`priColumnUtils.ts`) maps these numeric IDs to internal types:
```typescript
const numericMap: Record<number, ColumnDataType> = {
  1: 'date',      // Date formatting
  2: 'number',    // Integer formatting
  3: 'currency',  // Currency with $ symbol
  4: 'number',    // Decimal as number
  5: 'boolean',   // Checkbox display
  6: 'number',    // Percent formatting
  7: 'number'     // Float as number
};
// Null/undefined → 'text' (default)
```

**API Usage:**
```json
// Creating a column via twxUpsertRecord
{
  "procedure": "twxUpsertRecord",
  "type": "customrecord_pri_qt_query_column",
  "fields": {
    "name": "ship_date",
    "custrecord_pri_qt_qc_parent": 302,
    "custrecord_pri_qt_qc_heading": "Ship Date",
    "custrecord_pri_qt_qc_data_type": 1  // ← Use numeric ID, not "date"
  }
}
```

### Link Types (List Field - Use Numeric IDs)

| ID | Value | Description | Required Fields |
|----|-------|-------------|-----------------|
| (null) | None | No link (default) | None |
| 1 | Query | Opens another PRI Query | `custrecord_pri_qt_qc_linked_query`, `custrecord_pri_qt_qc_parms` |
| 2 | Record | Opens NetSuite record | `custrecord_pri_qt_qc_recordtype`, `custrecord_pri_qt_qc_parms` |

**Important**: Use the numeric ID when setting via API (e.g., `"custrecord_pri_qt_qc_link_type": 2` for Record link).

### Example Column Records

**Basic Text Column:**
```json
{
  "name": "customer_name",
  "custrecord_pri_qt_qc_parent": 202,
  "custrecord_pri_qt_qc_heading": "Customer Name",
  "custrecord_pri_qt_qc_data_type": "text"
}
```

**Reference Column (for linking):**
```json
{
  "name": "customer_id",
  "custrecord_pri_qt_qc_parent": 202,
  "custrecord_pri_qt_qc_heading": "Customer ID",
  "custrecord_pri_qt_qc_data_type": 2,
  "custrecord_pri_qt_qc_reference": true
}
```

**Column with Record Link:**
```json
{
  "name": "tranid",
  "custrecord_pri_qt_qc_parent": 202,
  "custrecord_pri_qt_qc_heading": "Order #",
  "custrecord_pri_qt_qc_link_type": 2,
  "custrecord_pri_qt_qc_recordtype": "salesorder",
  "custrecord_pri_qt_qc_parms": "id={order_id}"
}
```

**Column with Linked Query:**
```json
{
  "name": "customer_name",
  "custrecord_pri_qt_qc_parent": 202,
  "custrecord_pri_qt_qc_heading": "Customer",
  "custrecord_pri_qt_qc_link_type": 1,
  "custrecord_pri_qt_qc_linked_query": 150,
  "custrecord_pri_qt_qc_parms": "customer_id={customer_id}"
}
```

**Currency Column with Totals:**
```json
{
  "name": "total_amount",
  "custrecord_pri_qt_qc_parent": 202,
  "custrecord_pri_qt_qc_heading": "Amount",
  "custrecord_pri_qt_qc_data_type": 3,
  "custrecord_pri_qt_qc_totals_row": true
}
```

**Integer Column (numeric display):**
```json
{
  "name": "quantity",
  "custrecord_pri_qt_qc_parent": 202,
  "custrecord_pri_qt_qc_heading": "Qty",
  "custrecord_pri_qt_qc_data_type": 2
}
```

**Checkbox Column (boolean):**
```json
{
  "name": "is_active",
  "custrecord_pri_qt_qc_parent": 202,
  "custrecord_pri_qt_qc_heading": "Active",
  "custrecord_pri_qt_qc_data_type": 5
}
```

---

## customrecord_pri_qt_query_filter (Filter Definition)

Defines user-selectable filters for query customization.

| Field ID | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | Text | Yes | Filter internal name |
| `custrecord_pri_qt_qf_parent` | Integer | **Yes** | Foreign key to query record ID |
| `custrecord_pri_qt_qf_placeholder` | Text | Yes | Placeholder in query (e.g., `customer_id`) |
| `custrecord_pri_qt_qf_label` | Text | Yes | Display label for user |
| `custrecord_pri_qt_qf_type` | Text | Yes | Filter type (1-6) |
| `custrecord_pri_qt_qf_filter` | Text | Yes | WHERE clause template |
| `custrecord_pri_qt_qf_default_value` | Text | No | Default value |
| `custrecord_pri_qt_qf_hidden` | Checkbox | No | Hide filter from user (T/F) |
| `custrecord_pri_qt_qf_show_operator` | Checkbox | No | Show operator selector (T/F) |
| `custrecord_pri_qt_qf_select_recordtype` | Text | No | Record type for select dropdown |
| `custrecord_pri_qt_qf_custom_select_query` | Long Text | No | Custom SuiteQL for dropdown options |
| `custrecord_pri_qt_qf_help` | Text | No | Help text for user |
| `custrecord_pri_qt_qf_startcolumn` | Checkbox | No | Start new column in filter layout (T/F) |

### Filter Types

| Value | Type | Description |
|-------|------|-------------|
| `1` | Text | Free-form text input |
| `2` | Number | Numeric input |
| `3` | Date | Date picker |
| `4` | Boolean | Checkbox |
| `5` | Select | Dropdown (single selection) |
| `6` | Multiselect | Dropdown (multiple selection) |

### Example Filter Records

**Text Filter:**
```json
{
  "name": "name_filter",
  "custrecord_pri_qt_qf_parent": 202,
  "custrecord_pri_qt_qf_placeholder": "name_search",
  "custrecord_pri_qt_qf_label": "Name Contains",
  "custrecord_pri_qt_qf_type": "1",
  "custrecord_pri_qt_qf_filter": "UPPER(name) LIKE '%' || UPPER('{name_search}') || '%'",
  "custrecord_pri_qt_qf_help": "Enter partial name to search"
}
```

**Select Filter (Record Type):**
```json
{
  "name": "customer_filter",
  "custrecord_pri_qt_qf_parent": 202,
  "custrecord_pri_qt_qf_placeholder": "customer_id",
  "custrecord_pri_qt_qf_label": "Customer",
  "custrecord_pri_qt_qf_type": "5",
  "custrecord_pri_qt_qf_select_recordtype": "customer",
  "custrecord_pri_qt_qf_filter": "entity = {customer_id}",
  "custrecord_pri_qt_qf_help": "Select a customer"
}
```

**Select Filter (Custom Query):**
```json
{
  "name": "status_filter",
  "custrecord_pri_qt_qf_parent": 202,
  "custrecord_pri_qt_qf_placeholder": "status_id",
  "custrecord_pri_qt_qf_label": "Status",
  "custrecord_pri_qt_qf_type": "5",
  "custrecord_pri_qt_qf_custom_select_query": "SELECT id, name FROM customlist_status ORDER BY name",
  "custrecord_pri_qt_qf_filter": "status = {status_id}"
}
```

**Date Filter:**
```json
{
  "name": "date_from",
  "custrecord_pri_qt_qf_parent": 202,
  "custrecord_pri_qt_qf_placeholder": "start_date",
  "custrecord_pri_qt_qf_label": "From Date",
  "custrecord_pri_qt_qf_type": "3",
  "custrecord_pri_qt_qf_filter": "trandate >= TO_DATE('{start_date}', 'MM/DD/YYYY')",
  "custrecord_pri_qt_qf_help": "Start date for report"
}
```

**Boolean Filter:**
```json
{
  "name": "active_only",
  "custrecord_pri_qt_qf_parent": 202,
  "custrecord_pri_qt_qf_placeholder": "is_active",
  "custrecord_pri_qt_qf_label": "Active Only",
  "custrecord_pri_qt_qf_type": "4",
  "custrecord_pri_qt_qf_filter": "isinactive = 'F'",
  "custrecord_pri_qt_qf_default_value": "T"
}
```

**Hidden Filter (Preset Value):**
```json
{
  "name": "preset_type",
  "custrecord_pri_qt_qf_parent": 202,
  "custrecord_pri_qt_qf_placeholder": "type_filter",
  "custrecord_pri_qt_qf_label": "Type",
  "custrecord_pri_qt_qf_type": "1",
  "custrecord_pri_qt_qf_filter": "type = '{type_filter}'",
  "custrecord_pri_qt_qf_default_value": "SalesOrd",
  "custrecord_pri_qt_qf_hidden": "T"
}
```

---

## Querying Records

### List All Queries
```sql
SELECT id, name, custrecord_pri_qt_q_description, custrecord_twx_qt_q_category
FROM customrecord_pri_qt_query
ORDER BY name
```

### List Columns for a Query
```sql
SELECT id, name, custrecord_pri_qt_qc_heading, custrecord_pri_qt_qc_data_type,
       custrecord_pri_qt_qc_link_type, custrecord_pri_qt_qc_reference
FROM customrecord_pri_qt_query_column
WHERE custrecord_pri_qt_qc_parent = 202
ORDER BY id
```

### List Filters for a Query
```sql
SELECT id, name, custrecord_pri_qt_qf_label, custrecord_pri_qt_qf_type,
       custrecord_pri_qt_qf_placeholder, custrecord_pri_qt_qf_default_value
FROM customrecord_pri_qt_query_filter
WHERE custrecord_pri_qt_qf_parent = 202
ORDER BY id
```
