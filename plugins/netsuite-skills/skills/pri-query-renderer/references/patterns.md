# PRI Query Renderer - Common Patterns

## Column Configuration Patterns

### Basic Column Set for Transaction Queries

```json
[
  {"name": "id", "heading": "ID", "data_type": "number", "reference": "T"},
  {"name": "tranid", "heading": "Document #", "data_type": "text", "link_type": "record_detail", "recordtype": "salesorder"},
  {"name": "entity_name", "heading": "Entity", "data_type": "text"},
  {"name": "trandate", "heading": "Date", "data_type": "date"},
  {"name": "total", "heading": "Total", "data_type": "currency", "totals_row": "T"},
  {"name": "status", "heading": "Status", "data_type": "text"}
]
```

### Master-Detail Navigation Pattern

**Master Query Columns:**
```json
[
  {"name": "customer_id", "heading": "ID", "data_type": "number", "reference": "T"},
  {"name": "customer_name", "heading": "Customer", "data_type": "text", "link_type": "linked_query", "linked_query": 150, "parms": "customer_id={customer_id}"},
  {"name": "order_count", "heading": "Orders", "data_type": "number"},
  {"name": "total_revenue", "heading": "Revenue", "data_type": "currency"}
]
```

**Detail Query (ID 150) - receives customer_id as filter:**
```json
{
  "query": "SELECT * FROM transaction WHERE entity = {customer_id}",
  "filter": {
    "placeholder": "customer_id",
    "type": "1",
    "hidden": "T"
  }
}
```

### Multi-Record Link Pattern

When a column should link to different record types based on context:
```json
{
  "name": "document_number",
  "heading": "Document",
  "data_type": "text",
  "link_type": "record_detail",
  "recordtype": "transaction"
}
```

### Record Link via linkParams Pattern

**⚠️ Important:** There are TWO ways to configure record links. The frontend supports both.

**Method 1: Separate Fields (Standard)**
```json
{
  "name": "invoice_number",
  "custrecord_pri_qt_qc_heading": "Invoice #",
  "custrecord_pri_qt_qc_link_type": 2,
  "custrecord_pri_qt_qc_recordtype": "invoice",
  "custrecord_pri_qt_qc_parms": "id={invoice_id}"
}
```

**Method 2: Combined linkParams (Also Supported)**

When `recordType` is null/empty, the frontend extracts the record type from `linkParams`:
```json
{
  "name": "invoice_number",
  "custrecord_pri_qt_qc_heading": "Invoice #",
  "custrecord_pri_qt_qc_link_type": 2,
  "custrecord_pri_qt_qc_recordtype": null,
  "custrecord_pri_qt_qc_parms": "type=invoice&id={invoice_id}"
}
```

**Frontend Handling (QueryResults.tsx):**
```typescript
// Extract recordType from linkParams if not set directly
let recordType = col.recordType;
if (!recordType && col.linkParams) {
  const typeMatch = col.linkParams.match(/type=([^&]+)/);
  if (typeMatch) recordType = typeMatch[1];
}
```

**When to Use Each Method:**
- **Method 1**: Cleaner, recommended for new columns
- **Method 2**: Useful when configuring via UI that only has one params field

**Common NetSuite Record Types for Links:**
| Type | NetSuite Page | URL Suffix |
|------|---------------|------------|
| `salesorder` | Sales Order | salesord.nl |
| `invoice` | Invoice | custinvc.nl |
| `itemfulfillment` | Item Fulfillment | itemship.nl |
| `customer` | Customer | custjob.nl |
| `purchaseorder` | Purchase Order | purchord.nl |
| `itemreceipt` | Item Receipt | itemrcpt.nl |
| `transferorder` | Transfer Order | trnfrord.nl |
| `inventoryitem` | Inventory Item | invtitem.nl |
| `vendor` | Vendor | vendor.nl |

---

## Filter Configuration Patterns

### Standard Filter Set for Reports

```json
[
  {
    "name": "date_from",
    "placeholder": "start_date",
    "label": "From Date",
    "type": "3",
    "filter": "trandate >= TO_DATE('{start_date}', 'MM/DD/YYYY')"
  },
  {
    "name": "date_to",
    "placeholder": "end_date",
    "label": "To Date",
    "type": "3",
    "filter": "trandate <= TO_DATE('{end_date}', 'MM/DD/YYYY')"
  },
  {
    "name": "customer_select",
    "placeholder": "customer_id",
    "label": "Customer",
    "type": "5",
    "select_recordtype": "customer",
    "filter": "entity = {customer_id}"
  }
]
```

### Conditional Filter Pattern (Optional Filters)

Structure the query to handle optional filters:
```sql
SELECT * FROM transaction t
WHERE t.type = 'SalesOrd'
  AND {customer_filter}
  AND {date_filter}
  AND {status_filter}
```

For each optional filter, provide an "all" default:
```json
{
  "name": "customer_filter",
  "placeholder": "customer_filter",
  "label": "Customer",
  "type": "5",
  "select_recordtype": "customer",
  "filter": "(t.entity = {customer_filter} OR '{customer_filter}' = '')",
  "default_value": ""
}
```

### Preset/Hidden Filter Pattern

For queries that should always filter by a specific value:
```json
{
  "name": "type_preset",
  "placeholder": "trans_type",
  "label": "Transaction Type",
  "type": "1",
  "filter": "type = '{trans_type}'",
  "default_value": "SalesOrd",
  "hidden": "T"
}
```

### Search Filter Pattern (LIKE)

```json
{
  "name": "name_search",
  "placeholder": "search_term",
  "label": "Name Contains",
  "type": "1",
  "filter": "UPPER(name) LIKE '%' || UPPER('{search_term}') || '%'",
  "help": "Enter partial text to search"
}
```

### Custom Dropdown Options Pattern

```json
{
  "name": "status_filter",
  "placeholder": "status_id",
  "label": "Status",
  "type": "5",
  "custom_select_query": "SELECT id, name FROM customlist_order_status WHERE isinactive = 'F' ORDER BY name",
  "filter": "status = {status_id}"
}
```

---

## Complete Query Templates

### Customer Orders Report

**Query:**
```sql
SELECT
  so.id,
  so.tranid,
  c.entityid AS customer_name,
  c.id AS customer_id,
  so.total,
  so.trandate,
  BUILTIN.DF(so.status) AS status_name
FROM transaction so
JOIN customer c ON so.entity = c.id
WHERE so.type = 'SalesOrd'
  AND {customer_filter}
  AND {date_filter}
ORDER BY so.trandate DESC
```

**Columns:**
| Name | Heading | Type | Options |
|------|---------|------|---------|
| id | ID | number | reference: T |
| tranid | Order # | text | link_type: record_detail, recordtype: salesorder |
| customer_name | Customer | text | link_type: linked_query, linked_query: [customer_detail_id] |
| customer_id | Customer ID | number | reference: T |
| total | Amount | currency | totals_row: T |
| trandate | Date | date | |
| status_name | Status | text | |

**Filters:**
| Name | Label | Type | Configuration |
|------|-------|------|---------------|
| customer_filter | Customer | 5 (select) | select_recordtype: customer, filter: c.id = {customer_filter} |
| date_filter | From Date | 3 (date) | filter: so.trandate >= TO_DATE('{date_filter}', 'MM/DD/YYYY') |

---

### Inventory Summary Report

**Query:**
```sql
SELECT
  i.id,
  i.itemid,
  i.displayname,
  SUM(ib.quantityavailable) AS total_qty,
  SUM(ib.quantityonhand) AS on_hand,
  SUM(ib.quantityonorder) AS on_order
FROM item i
JOIN inventorybalance ib ON ib.item = i.id
WHERE i.isinactive = 'F'
  AND {item_filter}
GROUP BY i.id, i.itemid, i.displayname
ORDER BY i.itemid
```

**Columns:**
| Name | Heading | Type | Options |
|------|---------|------|---------|
| id | ID | number | reference: T |
| itemid | Item | text | link_type: record_detail, recordtype: inventoryitem |
| displayname | Description | text | |
| total_qty | Available | number | totals_row: T |
| on_hand | On Hand | number | totals_row: T |
| on_order | On Order | number | totals_row: T |

**Filters:**
| Name | Label | Type | Configuration |
|------|-------|------|---------------|
| item_filter | Item Contains | 1 (text) | filter: UPPER(i.itemid) LIKE '%' || UPPER('{item_filter}') || '%' |

---

### Custom Record with Status Workflow

**Query:**
```sql
SELECT
  r.id,
  r.name,
  r.custrecord_status AS status_id,
  BUILTIN.DF(r.custrecord_status) AS status_name,
  r.custrecord_assignee AS assignee_id,
  BUILTIN.DF(r.custrecord_assignee) AS assignee_name,
  r.created AS created_date
FROM customrecord_my_record r
WHERE {status_filter}
  AND {assignee_filter}
ORDER BY r.created DESC
```

**Columns:**
| Name | Heading | Type | Options |
|------|---------|------|---------|
| id | ID | number | reference: T, link_type: record_detail, recordtype: customrecord_my_record |
| name | Name | text | |
| status_id | Status ID | number | reference: T |
| status_name | Status | text | |
| assignee_id | Assignee ID | number | reference: T |
| assignee_name | Assigned To | text | |
| created_date | Created | date | |

**Filters:**
| Name | Label | Type | Configuration |
|------|-------|------|---------------|
| status_filter | Status | 5 (select) | custom_select_query: SELECT id, name FROM customlist_status, filter: r.custrecord_status = {status_filter} |
| assignee_filter | Assignee | 5 (select) | select_recordtype: employee, filter: r.custrecord_assignee = {assignee_filter} |

---

## Best Practices

### Query Writing
1. Always alias columns to lowercase names
2. Use BUILTIN.DF() for list/record fields to get display names
3. Include both ID and display columns for linked entities
4. Use proper date functions for date comparisons

### Column Configuration
1. Create reference columns for all IDs used in linking
2. Set totals_row only on numeric columns
3. Use meaningful heading names (not field IDs)
4. Order columns logically for the user

### Filter Configuration
1. Provide sensible defaults when possible
2. Use hidden filters for preset values
3. Include help text for complex filters
4. Test filter expressions with edge cases

### Linking
1. Always have a reference column for the record ID when using record_detail links
2. Map parameters correctly in linked_query connections
3. Test drill-down navigation end-to-end
