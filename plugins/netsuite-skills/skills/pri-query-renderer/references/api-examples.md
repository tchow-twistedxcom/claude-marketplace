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
