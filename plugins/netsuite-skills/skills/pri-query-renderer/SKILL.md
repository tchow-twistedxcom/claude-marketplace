---
name: pri-query-renderer
description: Expert knowledge for creating and managing PRI Query Renderer definitions in NetSuite. Includes comprehensive understanding of query records, column configurations, filter definitions, and the API procedures for record creation. This skill should be used when working with PRI Query Catalog, creating query definitions, adding columns to queries, configuring filters, linking queries together, or setting up record detail links. Essential for building complete, functional queries in the PRI Query Renderer system.
---

# PRI Query Renderer Expert

## Overview

Provide specialized knowledge for creating and managing **PRI Query Renderer** definitions in NetSuite. The PRI Query Renderer system allows users to define SuiteQL-based queries with configurable columns, filters, and linked navigation.

## When to Use This Skill

Activate this skill when:

- **Creating Query Definitions:** Building new PRI Query Catalog entries with SuiteQL
- **Adding Columns:** Configuring display columns with headings, data types, and links
- **Configuring Filters:** Setting up user-selectable filters with placeholders
- **Linking Queries:** Creating drill-down navigation between related queries
- **Record Detail Links:** Adding clickable links to NetSuite record views
- **Troubleshooting:** Debugging query execution or configuration issues

**Keywords that trigger this skill:**
- PRI Query, Query Renderer, Query Catalog
- Query column, query filter, query definition
- custrecord_pri_qt_query, custrecord_pri_qt_query_column, custrecord_pri_qt_query_filter
- linked_query, record_detail, data_type
- twxUpsertRecord, queryRun
- SuiteQL report, SuiteQL query builder

## System Architecture

**Record Types:**
- `customrecord_pri_qt_query` - Query definition (main record)
- `customrecord_pri_qt_query_column` - Column definitions (child of query)
- `customrecord_pri_qt_query_filter` - Filter definitions (child of query)

**API Access:**
- Endpoint: `http://localhost:3001/api/suiteapi`
- Headers: `Origin: http://localhost:3030`, `Content-Type: application/json`
- Procedures: `twxUpsertRecord` (create/update), `queryRun` (execute SuiteQL)

## Core Capabilities

### 1. Creating Query Definitions

Create a new query using the `twxUpsertRecord` procedure:

```json
{
  "procedure": "twxUpsertRecord",
  "id": null,
  "type": "customrecord_pri_qt_query",
  "fields": {
    "name": "Query Name Here",
    "custrecord_pri_qt_q_query": "SELECT id, name FROM entity WHERE ...",
    "custrecord_pri_qt_q_description": "Description of what this query does",
    "custrecord_twx_qt_q_category": "CategoryName",
    "custrecord_pri_qt_q_paged": true
  }
}
```

**Key Fields:**
- `name` - Display name in the Query Catalog
- `custrecord_pri_qt_q_query` - The SuiteQL query text
- `custrecord_pri_qt_q_description` - User-facing description
- `custrecord_twx_qt_q_category` - Category for organizing queries
- `custrecord_pri_qt_q_paged` - Enable pagination for large result sets

### 2. Adding Columns

Add columns to define how query results are displayed:

```json
{
  "procedure": "twxUpsertRecord",
  "id": null,
  "type": "customrecord_pri_qt_query_column",
  "fields": {
    "name": "field_name",
    "custrecord_pri_qt_qc_parent": 202,
    "custrecord_pri_qt_qc_heading": "Display Heading",
    "custrecord_pri_qt_qc_data_type": "text"
  }
}
```

**Critical Requirements:**
- `name` MUST match the column name in the SuiteQL SELECT (case-sensitive, typically lowercase)
- `custrecord_pri_qt_qc_parent` MUST be set to the query ID (required foreign key)

**Data Types:**
- `text` - Plain text display
- `number` - Numeric formatting
- `currency` - Currency formatting with symbols
- `date` - Date formatting
- `boolean` - Yes/No display
- `url` - Clickable hyperlink
- `email` - Mailto link

**Column Options:**
- `custrecord_pri_qt_qc_reference` - Set to "T" for reference-only columns (not displayed but available for linking)
- `custrecord_pri_qt_qc_totals_row` - Set to "T" to show column totals
- `custrecord_pri_qt_qc_heading_style` - CSS styling for the column header

### 3. Configuring Filters

Add filters to allow user-driven query customization:

```json
{
  "procedure": "twxUpsertRecord",
  "id": null,
  "type": "customrecord_pri_qt_query_filter",
  "fields": {
    "name": "customer_filter",
    "custrecord_pri_qt_qf_parent": 202,
    "custrecord_pri_qt_qf_placeholder": "customer_id",
    "custrecord_pri_qt_qf_label": "Customer",
    "custrecord_pri_qt_qf_type": "5",
    "custrecord_pri_qt_qf_select_recordtype": "customer",
    "custrecord_pri_qt_qf_filter": "customer.id = {customer_id}"
  }
}
```

**Filter Types:**
- `1` - Text input
- `2` - Number input
- `3` - Date input
- `4` - Boolean (checkbox)
- `5` - Select dropdown (record type)
- `6` - Multiselect dropdown

**Filter Configuration:**
- `custrecord_pri_qt_qf_placeholder` - The placeholder in the query (e.g., `{customer_id}`)
- `custrecord_pri_qt_qf_filter` - The WHERE clause to apply when filter has a value
- `custrecord_pri_qt_qf_default_value` - Default value if no selection
- `custrecord_pri_qt_qf_hidden` - Set to "T" to hide filter (for preset values)
- `custrecord_pri_qt_qf_show_operator` - Set to "T" to show operator selector (=, !=, >, <, etc.)
- `custrecord_pri_qt_qf_select_recordtype` - NetSuite record type for select dropdowns
- `custrecord_pri_qt_qf_custom_select_query` - Custom SuiteQL for dropdown options

### 4. Linking Queries (Drill-Down)

Create clickable links that open another query with filtered results.

**⚠️ See "Two-Level Placeholder System" section below for critical details!**

#### Step 1: Create the Target (Drill-Down) Query

The target query must have:
1. A query placeholder like `{1}` in the WHERE clause
2. A hidden filter with matching `placeholder` field
3. A filter template using `{filter_name}` for value substitution

```json
{
  "procedure": "twxUpsertRecord",
  "type": "customrecord_pri_qt_query",
  "fields": {
    "name": "Customer Orders Details",
    "custrecord_pri_qt_q_query": "SELECT * FROM transaction WHERE {1} AND type = 'SalesOrd'"
  }
}
```

#### Step 2: Create the Hidden Filter on Target Query

```json
{
  "procedure": "twxUpsertRecord",
  "type": "customrecord_pri_qt_query_filter",
  "fields": {
    "name": "customer_id",
    "custrecord_pri_qt_qf_parent": 150,
    "custrecord_pri_qt_qf_placeholder": "{1}",
    "custrecord_pri_qt_qf_filter": "entity = {customer_id}",
    "custrecord_pri_qt_qf_type": "2",
    "custrecord_pri_qt_qf_hidden": "T"
  }
}
```

**Critical fields:**
- `name` = "customer_id" - This is the filter name that will be passed via link_params
- `placeholder` = "{1}" - Matches the `{1}` in the query SQL
- `filter` = "entity = {customer_id}" - Uses `{customer_id}` (the filter name) as value placeholder

#### Step 3: Create the Link Column on Source Query

```json
{
  "procedure": "twxUpsertRecord",
  "type": "customrecord_pri_qt_query_column",
  "fields": {
    "name": "customer_name",
    "custrecord_pri_qt_qc_parent": 202,
    "custrecord_pri_qt_qc_heading": "Customer",
    "custrecord_pri_qt_qc_data_type": "text",
    "custrecord_pri_qt_qc_link_type": "linked_query",
    "custrecord_pri_qt_qc_linked_query": 150,
    "custrecord_pri_qt_qc_parms": "customer_id={customer_id_column}"
  }
}
```

**Link Parameters Format:** `filter_name={source_column_name}`
- `filter_name` = name of the filter in the TARGET query (e.g., "customer_id")
- `source_column_name` = column from the SOURCE query's results (e.g., "customer_id_column")

**Link Types:**
- `linked_query` - Opens another PRI Query with parameters
- `record_detail` - Opens a NetSuite record view
- `none` - No link (default)

**For linked_query:**
- `custrecord_pri_qt_qc_linked_query` - ID of the target query
- `custrecord_pri_qt_qc_parms` - Parameters to pass (format: `filter_name={column}`)

**For record_detail:**
- `custrecord_pri_qt_qc_recordtype` - NetSuite record type (e.g., "customer", "salesorder")
- `custrecord_pri_qt_qc_parms` - Use format `id={id_column}` to specify which column has the record ID

### 5. Listing Existing Queries

Query the catalog to find existing queries:

```json
{
  "procedure": "queryRun",
  "query": "SELECT id, name, custrecord_pri_qt_q_description, custrecord_twx_qt_q_category FROM customrecord_pri_qt_query ORDER BY name"
}
```

**Finding columns for a query:**
```json
{
  "procedure": "queryRun",
  "query": "SELECT id, name, custrecord_pri_qt_qc_heading, custrecord_pri_qt_qc_data_type FROM customrecord_pri_qt_query_column WHERE custrecord_pri_qt_qc_parent = 202"
}
```

**Finding filters for a query:**
```json
{
  "procedure": "queryRun",
  "query": "SELECT id, name, custrecord_pri_qt_qf_label, custrecord_pri_qt_qf_type FROM customrecord_pri_qt_query_filter WHERE custrecord_pri_qt_qf_parent = 202"
}
```

## Complete Query Setup Workflow

**Step 1: Create the Query Record**
```bash
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query",
    "fields": {
      "name": "Customer Orders Report",
      "custrecord_pri_qt_q_query": "SELECT so.id, so.tranid, c.entityid AS customer_name, c.id AS customer_id, so.total FROM transaction so JOIN customer c ON so.entity = c.id WHERE so.type = '\''SalesOrd'\'' AND {customer_filter}",
      "custrecord_pri_qt_q_description": "Lists all sales orders with customer filtering",
      "custrecord_twx_qt_q_category": "Sales",
      "custrecord_pri_qt_q_paged": true
    }
  }'
```

**Step 2: Add Columns**
```bash
# ID column (hidden for linking)
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query_column",
    "fields": {
      "name": "id",
      "custrecord_pri_qt_qc_parent": 203,
      "custrecord_pri_qt_qc_heading": "ID",
      "custrecord_pri_qt_qc_data_type": "number",
      "custrecord_pri_qt_qc_reference": "T"
    }
  }'

# Transaction number with record link
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query_column",
    "fields": {
      "name": "tranid",
      "custrecord_pri_qt_qc_parent": 203,
      "custrecord_pri_qt_qc_heading": "Order #",
      "custrecord_pri_qt_qc_data_type": "text",
      "custrecord_pri_qt_qc_link_type": "record_detail",
      "custrecord_pri_qt_qc_recordtype": "salesorder"
    }
  }'

# Customer name with drill-down
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query_column",
    "fields": {
      "name": "customer_name",
      "custrecord_pri_qt_qc_parent": 203,
      "custrecord_pri_qt_qc_heading": "Customer",
      "custrecord_pri_qt_qc_data_type": "text"
    }
  }'

# Total with currency formatting
curl -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{
    "procedure": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_pri_qt_query_column",
    "fields": {
      "name": "total",
      "custrecord_pri_qt_qc_parent": 203,
      "custrecord_pri_qt_qc_heading": "Total",
      "custrecord_pri_qt_qc_data_type": "currency",
      "custrecord_pri_qt_qc_totals_row": "T"
    }
  }'
```

**Step 3: Add Filters**
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
      "custrecord_pri_qt_qf_parent": 203,
      "custrecord_pri_qt_qf_placeholder": "customer_filter",
      "custrecord_pri_qt_qf_label": "Customer",
      "custrecord_pri_qt_qf_type": "5",
      "custrecord_pri_qt_qf_select_recordtype": "customer",
      "custrecord_pri_qt_qf_filter": "c.id = {customer_filter}",
      "custrecord_pri_qt_qf_default_value": "",
      "custrecord_pri_qt_qf_help": "Select a customer to filter results"
    }
  }'
```

## ⚠️ CRITICAL: Two-Level Placeholder System

**This is the #1 source of bugs when setting up drill-down queries.** There are TWO different placeholder systems:

### Level 1: Query Placeholders (in the SuiteQL)
- Format: `{1}`, `{2}`, etc. (single character/number only!)
- NetSuite validates these - `{fulfillment_id}` will cause "PLACEHOLDER must have format {x}" error
- These are replaced with the ENTIRE filter expression (e.g., `field = 123`)
- Location: In the query's `custrecord_pri_qt_q_query` field

### Level 2: Filter Template Value Placeholders (in the filter definition)
- Format: `{filter_name}` or `{value}`
- `{filter_name}` must match the filter's `name` field exactly
- These are replaced with just the VALUE (e.g., `123`)
- Location: In the filter's `custrecord_pri_qt_qf_filter` field

### Correct Setup Example

**Query SQL (Level 1):**
```sql
SELECT * FROM package WHERE {1} AND tracking IS NOT NULL
```

**Filter Record (Level 2):**
```json
{
  "name": "fulfillment_id",
  "custrecord_pri_qt_qf_placeholder": "{1}",
  "custrecord_pri_qt_qf_filter": "parent_transaction = {fulfillment_id}"
}
```

**How it works:**
1. User clicks drill-down, link_params passes `fulfillment_id=12345`
2. Filter template `parent_transaction = {fulfillment_id}` becomes `parent_transaction = 12345`
3. Query placeholder `{1}` is replaced with `(parent_transaction = 12345)`
4. Final query: `SELECT * FROM package WHERE (parent_transaction = 12345) AND tracking IS NOT NULL`

### ❌ WRONG: Using query placeholder in filter template
```json
{
  "custrecord_pri_qt_qf_placeholder": "{1}",
  "custrecord_pri_qt_qf_filter": "parent_transaction = {1}"  // WRONG! {1} won't be replaced!
}
```
This fails because the frontend code looks for `{filter_name}` or `{value}`, NOT `{1}`.

### ❌ WRONG: Using named placeholder in query SQL
```sql
SELECT * FROM package WHERE {fulfillment_id}  -- NetSuite validation error!
```
NetSuite requires `{x}` format where x is single char/number.

---

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Column not displaying | Column `name` doesn't match SELECT alias | Ensure column name matches query alias exactly (case-sensitive) |
| Filter not working | Placeholder mismatch | Verify `custrecord_pri_qt_qf_placeholder` matches `{placeholder}` in query |
| Link not clickable | Missing link type | Set `custrecord_pri_qt_qc_link_type` to `linked_query` or `record_detail` |
| No results | Query syntax error | Test query in SuiteQL Workbench first |
| Wrong formatting | Incorrect data type | Use appropriate `custrecord_pri_qt_qc_data_type` value |
| **Drill-down returns "1 = 1"** | Filter template has wrong placeholder | Use `{filter_name}` not `{1}` in `custrecord_pri_qt_qf_filter` |
| **"PLACEHOLDER must have format {x}"** | Named placeholder in query SQL | Use `{1}`, `{2}` etc. in query, not `{filter_name}` |
| **400 error on drill-down** | Filter template is null/empty | Set `custrecord_pri_qt_qf_filter` field |
| **Drill-down shows wrong data** | Link params don't match filter name | Ensure `link_params` uses `filter_name={column}` format |
| **Changes not reflected** | RTK Query caching | Hard refresh may not help; restart API gateway or clear Redux store |

## Debugging Drill-Down Issues

When a drill-down link fails with a 400 error or returns wrong data, follow these steps:

### Step 1: Check Browser Console
Look for these log messages:
- `Filter "xxx" has no filter template` → Filter's `custrecord_pri_qt_qf_filter` is null
- `Replacing {1} with: 1 = 1` → Filter expression wasn't built correctly

### Step 2: Verify Filter Configuration Directly
```bash
curl -s -X POST http://localhost:3001/api/suiteapi \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3030" \
  -d '{"procedure":"queryRun","query":"SELECT id, name, custrecord_pri_qt_qf_placeholder AS placeholder, custrecord_pri_qt_qf_filter AS filter FROM customrecord_pri_qt_query_filter WHERE custrecord_pri_qt_qf_parent = [TARGET_QUERY_ID]"}'
```

### Step 3: Verify the Fix Checklist
- [ ] Query SQL uses `{1}`, `{2}` format (NOT `{filter_name}`)
- [ ] Filter `placeholder` field matches query placeholder (e.g., `{1}`)
- [ ] Filter `filter` field uses `{filter_name}` for value (NOT `{1}`)
- [ ] Filter `name` field matches what's passed in link_params
- [ ] Column `link_params` format is `filter_name={column_name}`

### Step 4: Clear Cache After Updates
RTK Query caches aggressively. After database updates:
1. Try hard refresh (Ctrl+Shift+R)
2. If that doesn't work, restart the API gateway
3. Or navigate away and back to the query

## Best Practices

1. **Always create columns for all SELECT fields** - Each field in the SELECT must have a corresponding column record
2. **Use reference columns for link IDs** - Set `custrecord_pri_qt_qc_reference` to "T" for ID columns used in links but not displayed
3. **Test queries in SuiteQL Workbench first** - Validate syntax before creating the query record
4. **Use numbered placeholders in queries** - Always use `{1}`, `{2}` format, never named placeholders
5. **Use filter names in filter templates** - The `filter` field should use `{filter_name}`, not `{1}`
6. **Hidden filters for drill-down** - Set `custrecord_pri_qt_qf_hidden` to "T" for filters only used by drill-down links
7. **Verify the complete data flow** - Check: link_params → filter name → placeholder match → filter template → value substitution
8. **Set default filter values** - Provides better user experience
9. **Add help text to filters** - Guides users on expected input

## Resources

### Reference Documentation (`references/`)
- **record-fields.md** - Complete field reference for all 3 record types
- **api-examples.md** - Working API examples for common operations
- **patterns.md** - Common configuration patterns and templates

---

**Skill Version:** 1.1
**Last Updated:** 2026-01-07
**Change Log:**
- v1.1 (2026-01-07): Added critical "Two-Level Placeholder System" section, expanded drill-down documentation, added debugging guide, fixed common issues table
