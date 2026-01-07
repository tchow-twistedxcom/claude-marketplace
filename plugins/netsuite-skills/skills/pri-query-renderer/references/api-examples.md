# PRI Query Renderer - API Examples

## API Endpoint Configuration

**Endpoint:** `http://localhost:3001/api/suiteapi`

**Headers:**
```
Content-Type: application/json
Origin: http://localhost:3030
```

---

## Creating a New Query

```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query",
    "fields": {
      "name": "Sales Orders by Customer",
      "custrecord_pri_qt_q_query": "SELECT so.id, so.tranid, c.entityid AS customer_name, c.id AS customer_id, so.total, so.trandate FROM transaction so JOIN customer c ON so.entity = c.id WHERE so.type = '\''SalesOrd'\'' AND {customer_filter}",
      "custrecord_pri_qt_q_description": "Lists sales orders with optional customer filtering",
      "custrecord_twx_qt_q_category": "Sales",
      "custrecord_pri_qt_q_paged": true
    }
  }'
```

**Response:**
```json
{
  "id": 205,
  "success": true
}
```

---

## Adding Columns to a Query

### Basic Text Column
```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query_column",
    "fields": {
      "name": "customer_name",
      "custrecord_pri_qt_qc_parent": 205,
      "custrecord_pri_qt_qc_heading": "Customer",
      "custrecord_pri_qt_qc_data_type": "text"
    }
  }'
```

### Reference Column (Hidden, for linking)
```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query_column",
    "fields": {
      "name": "id",
      "custrecord_pri_qt_qc_parent": 205,
      "custrecord_pri_qt_qc_heading": "ID",
      "custrecord_pri_qt_qc_data_type": "number",
      "custrecord_pri_qt_qc_reference": "T"
    }
  }'
```

### Column with Record Detail Link
```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query_column",
    "fields": {
      "name": "tranid",
      "custrecord_pri_qt_qc_parent": 205,
      "custrecord_pri_qt_qc_heading": "Order #",
      "custrecord_pri_qt_qc_data_type": "text",
      "custrecord_pri_qt_qc_link_type": "record_detail",
      "custrecord_pri_qt_qc_recordtype": "salesorder"
    }
  }'
```

### Column with Linked Query
```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query_column",
    "fields": {
      "name": "customer_name",
      "custrecord_pri_qt_qc_parent": 205,
      "custrecord_pri_qt_qc_heading": "Customer",
      "custrecord_pri_qt_qc_data_type": "text",
      "custrecord_pri_qt_qc_link_type": "linked_query",
      "custrecord_pri_qt_qc_linked_query": 150,
      "custrecord_pri_qt_qc_parms": "customer_id={customer_id}"
    }
  }'
```

### Currency Column with Totals
```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query_column",
    "fields": {
      "name": "total",
      "custrecord_pri_qt_qc_parent": 205,
      "custrecord_pri_qt_qc_heading": "Total",
      "custrecord_pri_qt_qc_data_type": "currency",
      "custrecord_pri_qt_qc_totals_row": "T"
    }
  }'
```

### Date Column
```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query_column",
    "fields": {
      "name": "trandate",
      "custrecord_pri_qt_qc_parent": 205,
      "custrecord_pri_qt_qc_heading": "Date",
      "custrecord_pri_qt_qc_data_type": "date"
    }
  }'
```

---

## Adding Filters to a Query

### Select Filter (Record Type)
```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query_filter",
    "fields": {
      "name": "customer_filter",
      "custrecord_pri_qt_qf_parent": 205,
      "custrecord_pri_qt_qf_placeholder": "customer_filter",
      "custrecord_pri_qt_qf_label": "Customer",
      "custrecord_pri_qt_qf_type": "5",
      "custrecord_pri_qt_qf_select_recordtype": "customer",
      "custrecord_pri_qt_qf_filter": "c.id = {customer_filter}",
      "custrecord_pri_qt_qf_help": "Select a customer to filter"
    }
  }'
```

### Text Filter
```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query_filter",
    "fields": {
      "name": "name_search",
      "custrecord_pri_qt_qf_parent": 205,
      "custrecord_pri_qt_qf_placeholder": "name_search",
      "custrecord_pri_qt_qf_label": "Name Contains",
      "custrecord_pri_qt_qf_type": "1",
      "custrecord_pri_qt_qf_filter": "UPPER(name) LIKE '\''%'\'' || UPPER('\''{name_search}'\'') || '\''%'\''",
      "custrecord_pri_qt_qf_help": "Enter text to search in name"
    }
  }'
```

### Date Filter
```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query_filter",
    "fields": {
      "name": "date_from",
      "custrecord_pri_qt_qf_parent": 205,
      "custrecord_pri_qt_qf_placeholder": "start_date",
      "custrecord_pri_qt_qf_label": "From Date",
      "custrecord_pri_qt_qf_type": "3",
      "custrecord_pri_qt_qf_filter": "trandate >= TO_DATE('\''{start_date}'\'', '\''MM/DD/YYYY'\'')",
      "custrecord_pri_qt_qf_help": "Start date for report"
    }
  }'
```

### Hidden Filter (Preset)
```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query_filter",
    "fields": {
      "name": "type_preset",
      "custrecord_pri_qt_qf_parent": 205,
      "custrecord_pri_qt_qf_placeholder": "type_value",
      "custrecord_pri_qt_qf_label": "Type",
      "custrecord_pri_qt_qf_type": "1",
      "custrecord_pri_qt_qf_filter": "type = '\''{type_value}'\''",
      "custrecord_pri_qt_qf_default_value": "SalesOrd",
      "custrecord_pri_qt_qf_hidden": "T"
    }
  }'
```

---

## Updating Existing Records

To update an existing record, provide the record ID instead of null:

```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": 205,
    "type": "customrecord_pri_qt_query",
    "fields": {
      "custrecord_pri_qt_q_description": "Updated description for the query"
    }
  }'
```

---

## Querying Records

### List All Queries
```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "queryRun",
    "query": "SELECT id, name, custrecord_pri_qt_q_description, custrecord_twx_qt_q_category FROM customrecord_pri_qt_query ORDER BY name"
  }'
```

### List Columns for Query ID 205
```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "queryRun",
    "query": "SELECT id, name, custrecord_pri_qt_qc_heading, custrecord_pri_qt_qc_data_type FROM customrecord_pri_qt_query_column WHERE custrecord_pri_qt_qc_parent = 205"
  }'
```

### List Filters for Query ID 205
```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "queryRun",
    "query": "SELECT id, name, custrecord_pri_qt_qf_label, custrecord_pri_qt_qf_type, custrecord_pri_qt_qf_placeholder FROM customrecord_pri_qt_query_filter WHERE custrecord_pri_qt_qf_parent = 205"
  }'
```

### Get Query Details
```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "queryRun",
    "query": "SELECT id, name, custrecord_pri_qt_q_query, custrecord_pri_qt_q_description FROM customrecord_pri_qt_query WHERE id = 205"
  }'
```

---

## Complete Query Setup Example

This example creates a complete query with columns and filters:

### Step 1: Create Query
```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query",
    "fields": {
      "name": "Inventory by Location",
      "custrecord_pri_qt_q_query": "SELECT i.id, i.itemid, i.displayname, l.id AS location_id, l.name AS location_name, ib.quantityavailable FROM item i JOIN inventorybalance ib ON ib.item = i.id JOIN location l ON ib.location = l.id WHERE {location_filter} AND {item_filter}",
      "custrecord_pri_qt_q_description": "Shows inventory levels by location",
      "custrecord_twx_qt_q_category": "Inventory",
      "custrecord_pri_qt_q_paged": true
    }
  }'
# Returns id: 206
```

### Step 2: Add Columns
```bash
# ID column (reference)
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{"procedure":"twxUpsertRecord","id":null,"type":"customrecord_pri_qt_query_column","fields":{"name":"id","custrecord_pri_qt_qc_parent":206,"custrecord_pri_qt_qc_heading":"ID","custrecord_pri_qt_qc_data_type":"number","custrecord_pri_qt_qc_reference":"T"}}'

# Item ID with record link
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{"procedure":"twxUpsertRecord","id":null,"type":"customrecord_pri_qt_query_column","fields":{"name":"itemid","custrecord_pri_qt_qc_parent":206,"custrecord_pri_qt_qc_heading":"Item","custrecord_pri_qt_qc_data_type":"text","custrecord_pri_qt_qc_link_type":"record_detail","custrecord_pri_qt_qc_recordtype":"inventoryitem"}}'

# Display name
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{"procedure":"twxUpsertRecord","id":null,"type":"customrecord_pri_qt_query_column","fields":{"name":"displayname","custrecord_pri_qt_qc_parent":206,"custrecord_pri_qt_qc_heading":"Description","custrecord_pri_qt_qc_data_type":"text"}}'

# Location name
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{"procedure":"twxUpsertRecord","id":null,"type":"customrecord_pri_qt_query_column","fields":{"name":"location_name","custrecord_pri_qt_qc_parent":206,"custrecord_pri_qt_qc_heading":"Location","custrecord_pri_qt_qc_data_type":"text"}}'

# Quantity with totals
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{"procedure":"twxUpsertRecord","id":null,"type":"customrecord_pri_qt_query_column","fields":{"name":"quantityavailable","custrecord_pri_qt_qc_parent":206,"custrecord_pri_qt_qc_heading":"Qty Available","custrecord_pri_qt_qc_data_type":"number","custrecord_pri_qt_qc_totals_row":"T"}}'
```

### Step 3: Add Filters
```bash
# Location filter
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{"procedure":"twxUpsertRecord","id":null,"type":"customrecord_pri_qt_query_filter","fields":{"name":"location_filter","custrecord_pri_qt_qf_parent":206,"custrecord_pri_qt_qf_placeholder":"location_filter","custrecord_pri_qt_qf_label":"Location","custrecord_pri_qt_qf_type":"5","custrecord_pri_qt_qf_select_recordtype":"location","custrecord_pri_qt_qf_filter":"l.id = {location_filter}","custrecord_pri_qt_qf_help":"Select a location"}}'

# Item filter
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{"procedure":"twxUpsertRecord","id":null,"type":"customrecord_pri_qt_query_filter","fields":{"name":"item_filter","custrecord_pri_qt_qf_parent":206,"custrecord_pri_qt_qf_placeholder":"item_filter","custrecord_pri_qt_qf_label":"Item Contains","custrecord_pri_qt_qf_type":"1","custrecord_pri_qt_qf_filter":"UPPER(i.itemid) LIKE '\''%'\'' || UPPER('\''{item_filter}'\'') || '\''%'\''","custrecord_pri_qt_qf_help":"Enter item ID to search"}}'
```

---

## Complete Filter Field Reference

All available fields for `customrecord_pri_qt_query_filter`:

### Filter Types Quick Reference

| Type | ID | Input Control | Use Case |
|------|------|---------------|----------|
| Text | `1` | Text input | Free-form search, LIKE patterns |
| Number | `2` | Numeric input | Numeric comparisons |
| Date | `3` | Date picker | Date range filters |
| Boolean | `4` | Checkbox | True/False toggles |
| Select | `5` | Dropdown (single) | Record type or custom query |
| Multiselect | `6` | Dropdown (multiple) | Multiple selections |

### Complete Text Filter (All Fields)
```json
{
  "procedure": "twxUpsertRecord",
  "id": null,
  "type": "customrecord_pri_qt_query_filter",
  "fields": {
    "name": "invoice_number",
    "custrecord_pri_qt_qf_parent": 302,
    "custrecord_pri_qt_qf_placeholder": "invoice_number",
    "custrecord_pri_qt_qf_label": "Invoice #",
    "custrecord_pri_qt_qf_type": "1",
    "custrecord_pri_qt_qf_filter": "REPLACE(BUILTIN.DF(T.custbody_pri_bpa_ff_inv_link), 'Invoice #', '') LIKE '%{invoice_number}%'",
    "custrecord_pri_qt_qf_default_value": "",
    "custrecord_pri_qt_qf_hidden": "F",
    "custrecord_pri_qt_qf_show_operator": "F",
    "custrecord_pri_qt_qf_help": "Enter partial or complete invoice number",
    "custrecord_pri_qt_qf_startcolumn": "F"
  }
}
```

### Complete Select Filter (Record Type)
```json
{
  "procedure": "twxUpsertRecord",
  "id": null,
  "type": "customrecord_pri_qt_query_filter",
  "fields": {
    "name": "customer",
    "custrecord_pri_qt_qf_parent": 302,
    "custrecord_pri_qt_qf_placeholder": "customer",
    "custrecord_pri_qt_qf_label": "Customer",
    "custrecord_pri_qt_qf_type": "5",
    "custrecord_pri_qt_qf_select_recordtype": "customer",
    "custrecord_pri_qt_qf_filter": "T.entity = {customer}",
    "custrecord_pri_qt_qf_default_value": "",
    "custrecord_pri_qt_qf_hidden": "F",
    "custrecord_pri_qt_qf_help": "Select a customer"
  }
}
```

### Complete Select Filter (Custom Query)
```json
{
  "procedure": "twxUpsertRecord",
  "id": null,
  "type": "customrecord_pri_qt_query_filter",
  "fields": {
    "name": "company_group",
    "custrecord_pri_qt_qf_parent": 302,
    "custrecord_pri_qt_qf_placeholder": "company_group",
    "custrecord_pri_qt_qf_label": "Company",
    "custrecord_pri_qt_qf_type": "5",
    "custrecord_pri_qt_qf_custom_select_query": "SELECT id, companyname AS name FROM customer WHERE isperson = 'F' ORDER BY companyname",
    "custrecord_pri_qt_qf_filter": "C.companyname = '{company_group}'",
    "custrecord_pri_qt_qf_help": "Select company from list"
  }
}
```

### Complete Date Filter
```json
{
  "procedure": "twxUpsertRecord",
  "id": null,
  "type": "customrecord_pri_qt_query_filter",
  "fields": {
    "name": "date_from",
    "custrecord_pri_qt_qf_parent": 302,
    "custrecord_pri_qt_qf_placeholder": "start_date",
    "custrecord_pri_qt_qf_label": "From Date",
    "custrecord_pri_qt_qf_type": "3",
    "custrecord_pri_qt_qf_filter": "T.TranDate >= TO_DATE('{start_date}', 'MM/DD/YYYY')",
    "custrecord_pri_qt_qf_default_value": "",
    "custrecord_pri_qt_qf_show_operator": "T",
    "custrecord_pri_qt_qf_help": "Start date for filtering"
  }
}
```

### Complete Boolean Filter
```json
{
  "procedure": "twxUpsertRecord",
  "id": null,
  "type": "customrecord_pri_qt_query_filter",
  "fields": {
    "name": "with_tracking",
    "custrecord_pri_qt_qf_parent": 302,
    "custrecord_pri_qt_qf_placeholder": "has_tracking",
    "custrecord_pri_qt_qf_label": "Has Tracking #",
    "custrecord_pri_qt_qf_type": "4",
    "custrecord_pri_qt_qf_filter": "T.custbody_twx_master_tracking_num IS NOT NULL",
    "custrecord_pri_qt_qf_default_value": "T"
  }
}
```

### Filter Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `name` | Text | Internal filter name (required) |
| `custrecord_pri_qt_qf_parent` | Integer | **REQUIRED** - Query ID this filter belongs to |
| `custrecord_pri_qt_qf_placeholder` | Text | Placeholder name used in `{placeholder}` in query |
| `custrecord_pri_qt_qf_label` | Text | Display label shown to user |
| `custrecord_pri_qt_qf_type` | Text | Filter type: 1-6 (see table above) |
| `custrecord_pri_qt_qf_filter` | Text | WHERE clause template with `{placeholder}` |
| `custrecord_pri_qt_qf_default_value` | Text | Default value when filter loads |
| `custrecord_pri_qt_qf_hidden` | Checkbox | T/F - Hide from user (for preset values) |
| `custrecord_pri_qt_qf_show_operator` | Checkbox | T/F - Show comparison operator dropdown |
| `custrecord_pri_qt_qf_select_recordtype` | Text | NetSuite record type for Select dropdowns |
| `custrecord_pri_qt_qf_custom_select_query` | LongText | Custom SuiteQL for dropdown options (requires `id` and `name` columns) |
| `custrecord_pri_qt_qf_help` | Text | Help text shown to user |
| `custrecord_pri_qt_qf_startcolumn` | Checkbox | T/F - Start new column in filter layout |

### Common Patterns for Filter WHERE Clauses

**Exact Match:**
```sql
"custrecord_pri_qt_qf_filter": "T.entity = {customer_id}"
```

**LIKE Pattern (Contains):**
```sql
"custrecord_pri_qt_qf_filter": "UPPER(T.TranID) LIKE '%' || UPPER('{search}') || '%'"
```

**Date Comparison:**
```sql
"custrecord_pri_qt_qf_filter": "T.TranDate >= TO_DATE('{start_date}', 'MM/DD/YYYY')"
```

**Optional Filter (Empty = All):**
```sql
"custrecord_pri_qt_qf_filter": "('{customer}' = '' OR T.entity = {customer})"
```

**Boolean Check:**
```sql
"custrecord_pri_qt_qf_filter": "T.isinactive = 'F'"
```
