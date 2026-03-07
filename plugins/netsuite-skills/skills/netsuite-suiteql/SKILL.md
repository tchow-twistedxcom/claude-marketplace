---
name: netsuite-suiteql
description: Execute ad hoc SuiteQL queries and perform CRUD operations on NetSuite records using the NetSuite API Gateway. Use this skill when you need to test queries, update records, verify data, or explore NetSuite records during Record Display development or container lifecycle testing. Triggers include "run query", "update record", "create record", "test SuiteQL", "check container data", "query NetSuite", "fix NetSuite record", or any data validation needs.
---

# NetSuite SuiteQL Query Execution Skill

## Overview

Execute SuiteQL queries directly against NetSuite environments (Production, Sandbox 1, or Sandbox 2) using the NetSuite API Gateway. This skill enables rapid ad hoc query testing during development of NetSuite Record Display features, particularly for validating container lifecycle data, transaction chains, and custom record queries.

**Authentication is handled automatically** by the NetSuite API Gateway using OAuth 1.0a - no session cookies or manual authentication required.

**Use this skill when:**
- Testing container flowchart queries before/after deployment
- Verifying custom record data structures
- Exploring transaction relationships (Transfer Order → Item Fulfillment → Item Receipt)
- Debugging data issues during Record Display development
- Validating SuiteQL syntax and performance
- Building query patterns for new features

## Prerequisites

**NetSuite API Gateway** must be running:
```bash
cd ~/NetSuiteApiGateway
docker compose up -d
```

Verify gateway is running:
```bash
curl http://localhost:3001/health
# Expected: {"status":"healthy","timestamp":"...","version":"1.0.0"}
```

The gateway handles OAuth authentication automatically - no manual authentication needed!

## Quick Start

Execute a simple query:
```bash
python3 scripts/query_netsuite.py 'SELECT id, name FROM customer WHERE ROWNUM <= 5' --env sb2 --format table
```

Execute a parameterized query:
```bash
python3 scripts/query_netsuite.py 'SELECT * FROM customrecord_pri_frgt_cnt WHERE id = ?' --params 12345 --env sb2
```

## Account Reference

| Account | Alias | Account ID | Auth Type | Environments |
|---------|-------|------------|-----------|--------------|
| TwistedX | twx | 4829859 | OAuth 1.0a | prod, sb1, sb2 |
| Dutyman | dm | 8055418 | OAuth 2.0 M2M | **prod, sb1 only** |

**Note:** Dutyman does NOT support sandbox2 (sb2). Use `--env prod` or `--env sb1`.

```bash
# TwistedX example (supports all environments)
python3 scripts/query_netsuite.py 'SELECT id, name FROM customer WHERE ROWNUM <= 5' --account twx --env sb2

# Dutyman example (prod or sb1 only)
python3 scripts/query_netsuite.py 'SELECT id, name FROM customer WHERE ROWNUM <= 5' --account dm --env prod
```

## Core Workflow

### 1. **Identify Query Need**
Determine what data you need to test or verify:
- Container lifecycle status
- Transaction relationships
- Custom record validation
- Performance testing

### 2. **Look Up Schema (Required Before Writing Queries)**

Before writing any SuiteQL query for an unfamiliar table, verify exact table and column names. **Never guess column names** — they differ from UI field names and many fields are not exposed in SuiteQL.

**Find the right table:**
```bash
python3 scripts/schema_lookup.py tables "Transaction*" --env sb2
python3 scripts/schema_lookup.py tables "custom*" --env sb2
python3 scripts/schema_lookup.py search "shipping" --env sb2
```

**Get exact column names for your target table:**
```bash
python3 scripts/schema_lookup.py describe Transaction --env sb2
python3 scripts/schema_lookup.py describe customrecord_pri_frgt_cnt --env sb2
python3 scripts/query_netsuite.py --describe TransactionLine --env sb2
```

**Find which table has a specific column:**
```bash
python3 scripts/schema_lookup.py search "shippingrate" --env sb2
python3 scripts/schema_lookup.py search "custrecord_pri" --env sb2
```

**Check FK relationships before writing JOINs:**
```bash
python3 scripts/schema_lookup.py relationships Transaction --env sb2
```

The `describe` command shows **all columns** including custom fields (`custbody_*`, `custrecord_*`) with their human-readable labels. Common pitfalls this prevents:
- `Transaction.shippingcost` doesn't exist → use `TransactionShipment.shippingrate`
- `Transaction.total` doesn't exist → use `SUM(TransactionLine.netamount)`
- Custom field names like `custbody_pri_bpa_ff_inv_link` — must be exact, no guessing

### 3. **Build Query**
Use the verified column names from schema lookup plus the reference documentation:
- `references/common_queries.md` - Pre-built query patterns
- `references/suiteql_functions.md` - Supported/unsupported SQL functions

### 4. **Execute Query**
Run the query using the Python script:
```bash
python3 scripts/query_netsuite.py '<query>' [options]
```

**Options:**
- `--params <param1>,<param2>` - Parameterized query values
- `--env sb2|prod` - Target environment (default: sb2)
- `--all-rows` - Enable pagination for large result sets
- `--format json|table|csv` - Output format (default: table)
- `--describe <TABLE>` - Schema lookup shortcut (no query needed)
- `--tables [PATTERN]` - List tables (no query needed)
- `--search-columns <PAT>` - Column search (no query needed)

### 5. **Analyze Results**
Review the output to validate data or debug issues:
- Table format for quick visual inspection
- JSON format for programmatic processing
- CSV format for spreadsheet analysis

## Common Tasks

### Test Container Lifecycle Queries

**Get container by ID:**
```bash
python3 scripts/query_netsuite.py 'SELECT CNT.ID, CNT.Name, BUILTIN.DF(CNT.custrecord_pri_frgt_cnt_log_status) AS status FROM customrecord_pri_frgt_cnt AS CNT WHERE CNT.ID = ?' --params 12345
```

**List active containers:**
```bash
python3 scripts/query_netsuite.py 'SELECT * FROM (SELECT ID, Name, BUILTIN.DF(custrecord_pri_frgt_cnt_log_status) AS status FROM customrecord_pri_frgt_cnt WHERE custrecord_pri_frgt_cnt_log_status IS NOT NULL ORDER BY lastmodified DESC) WHERE ROWNUM <= 20'
```

### Test Transaction Chain Queries

**Get Item Fulfillment for Transfer Order:**
```bash
python3 scripts/query_netsuite.py 'SELECT IF_TXN.ID, IF_TXN.TranID FROM Transaction AS IF_TXN INNER JOIN NextTransactionLineLink AS NTLL ON IF_TXN.ID = NTLL.NextDoc WHERE IF_TXN.Type = '\''ItemShip'\'' AND NTLL.PreviousDoc = ?' --params 54321
```

**Note:** Single quotes in queries must be escaped as `'\''` in bash.

### Explore Custom Record Structure

**List custom record types:**
```bash
python3 scripts/query_netsuite.py 'SELECT ID, ScriptID, Name FROM CustomRecordType WHERE IsInactive = '\''F'\'' ORDER BY Name'
```

**List custom fields for a record:**
```bash
python3 scripts/query_netsuite.py 'SELECT ID, ScriptID, FieldLabel, FieldType FROM CustomField WHERE AppliesToRecord = ? ORDER BY FieldLabel' --params customrecord_pri_frgt_cnt
```

### Performance Testing

**Test with pagination:**
```bash
python3 scripts/query_netsuite.py 'SELECT * FROM Transaction WHERE Type = '\''SalesOrd'\'' AND TranDate >= CURRENT_DATE - 30' --all-rows
```

The `--all-rows` flag enables automatic pagination and returns performance analysis.

## Query Building Tips

### Use Parameterized Queries
Always use `?` placeholders for dynamic values:
```sql
-- GOOD: Parameterized (safe, cached)
SELECT * FROM Customer WHERE ID = ?

-- BAD: Direct concatenation (unsafe, no caching)
SELECT * FROM Customer WHERE ID = 12345
```

### Optimize with Filters
Apply WHERE conditions before JOINs:
```sql
-- GOOD: Filter first
SELECT T.ID, C.CompanyName
FROM (
    SELECT * FROM Transaction
    WHERE Type = 'SalesOrd' AND TranDate >= TO_DATE('2025-01-01', 'YYYY-MM-DD')
) AS T
INNER JOIN Customer AS C ON T.Entity = C.ID

-- AVOID: Join then filter
SELECT T.ID, C.CompanyName
FROM Transaction AS T
INNER JOIN Customer AS C ON T.Entity = C.ID
WHERE T.Type = 'SalesOrd' AND T.TranDate >= TO_DATE('2025-01-01', 'YYYY-MM-DD')
```

### Use BUILTIN.DF Sparingly
Display formatting is expensive:
```sql
-- GOOD: Get IDs first, format only displayed rows
SELECT ID, Status, Location FROM Transaction WHERE Type = 'SalesOrd'

-- SLOW: Format everything
SELECT ID, BUILTIN.DF(Status), BUILTIN.DF(Location) FROM Transaction WHERE Type = 'SalesOrd'
```

### Limit Exploratory Queries
Always use ROWNUM for initial testing:
```sql
-- Safe exploration
SELECT * FROM customrecord_pri_frgt_cnt WHERE ROWNUM <= 10
```

## Error Handling

### Gateway Connection Errors
If you receive gateway connection errors, ensure the NetSuite API Gateway is running:

```bash
# Check gateway status
curl http://localhost:3001/health

# Start gateway if not running
cd ~/NetSuiteApiGateway
docker compose up -d

# View gateway logs
docker compose logs -f gateway
```

### Authentication Errors
The gateway handles OAuth 1.0a authentication automatically. If you receive authentication errors:
- Check gateway logs: `docker compose logs gateway`
- Verify OAuth configuration in `~/NetSuiteApiGateway/config/oauth.json`
- Ensure credentials are properly configured for the target environment

### Query Syntax Errors
If the query fails with "Field not found" or similar errors, verify the exact column names before guessing:
```bash
python3 scripts/schema_lookup.py describe Transaction --env sb2
# or: search for a column pattern
python3 scripts/schema_lookup.py search "shippingcost" --env sb2
```

Also check:
- Table names (case-insensitive in SuiteQL but check OA_TABLES for exact names)
- Parameter count matches `?` placeholders
- Single quotes properly escaped in bash

### Timeout Errors
For long-running queries:
- Add more specific WHERE conditions
- Use ROWNUM to test with smaller datasets first
- Consider breaking into multiple smaller queries

## Integration with Record Display Development

This skill is specifically designed to support the container lifecycle Record Display feature:

**Before Deployment:**
```bash
# Verify container structure
python3 scripts/query_netsuite.py 'SELECT * FROM customrecord_pri_frgt_cnt WHERE ID = ?' --params <container_id>

# Test flowchart query
python3 scripts/query_netsuite.py '<flowchart_query_from_code>' --params <container_id>
```

**After Deployment:**
```bash
# Validate deployed feature loads correct data
python3 scripts/query_netsuite.py '<same_query>' --params <container_id>

# Compare results to ensure consistency
```

**Development Workflow:**
1. Write SuiteQL in Record Display code
2. Test query using this skill
3. Iterate until query returns expected data structure
4. Deploy Record Display feature
5. Verify deployed feature using same query

## Record Operations (Create, Update, Delete)

While this skill focuses primarily on SuiteQL queries, record CRUD operations use the `twxUpsertRecord` procedure through the same API Gateway. For record modifications, use the `update_record.py` script.

### Quick Start - Record Operations

**Update an existing record:**
```bash
python3 scripts/update_record.py customrecord_twx_notification_rule 2 \
  --field custrecord_twx_rule_conditions='{"status":"Processing Error"}' \
  --field custrecord_twx_rule_template=1 \
  --env sb2
```

**Create a new record:**
```bash
python3 scripts/update_record.py customrecord_twx_notification_template --create \
  --field name="New Template" \
  --field custrecord_twx_template_subject="Subject Line" \
  --field custrecord_twx_template_body="Email body" \
  --env sb2
```

### Record Operation Workflow

#### 1. **Identify Record Type and ID**
Determine what you need to modify:
- Record type (e.g., `customrecord_twx_notification_rule`)
- Record ID (query to find it first if needed)
- Fields to update

#### 2. **Query First (Recommended)**
Before updating, query the record to see current values:
```bash
python3 scripts/query_netsuite.py 'SELECT * FROM customrecord_twx_notification_rule WHERE id = ?' --params 2 --env sb2
```

#### 3. **Update Record**
Use `update_record.py` to modify fields:
```bash
python3 scripts/update_record.py <record_type> <record_id> \
  --field <fieldname>=<value> \
  [--env sb2] [--account twx]
```

#### 4. **Verify Update**
Query again to confirm changes:
```bash
python3 scripts/query_netsuite.py 'SELECT * FROM customrecord_twx_notification_rule WHERE id = ?' --params 2 --env sb2
```

### Common Record Operations

#### Update Notification Rule
**Problem:** Rule has invalid status or template
**Solution:**
```bash
# Fix status from "error" to "Processing Error"
python3 scripts/update_record.py customrecord_twx_notification_rule 2 \
  --field custrecord_twx_rule_conditions='{"status":"Processing Error"}' \
  --env sb2

# Assign valid template
python3 scripts/update_record.py customrecord_twx_notification_rule 2 \
  --field custrecord_twx_rule_template=1 \
  --env sb2

# Update multiple fields at once
python3 scripts/update_record.py customrecord_twx_notification_rule 2 \
  --field custrecord_twx_rule_conditions='{"status":"Processing Error"}' \
  --field custrecord_twx_rule_template=1 \
  --env sb2
```

#### Create Notification Template
```bash
python3 scripts/update_record.py customrecord_twx_notification_template --create \
  --field name="TMPL-0005: EDI Processing Alert" \
  --field custrecord_twx_template_subject="EDI Alert: {transaction_type} {status}" \
  --field custrecord_twx_template_body="<html><body>Transaction {tranId} status: {status}</body></html>" \
  --env sb2
```

#### Disable/Enable Records
```bash
# Disable a rule
python3 scripts/update_record.py customrecord_twx_notification_rule 5 \
  --field custrecord_twx_rule_active=false \
  --env sb2

# Enable a rule
python3 scripts/update_record.py customrecord_twx_notification_rule 5 \
  --field custrecord_twx_rule_active=true \
  --env sb2
```

### Field Value Types

The script automatically handles different data types:

**String values:**
```bash
--field name="My Template"
--field description="Some text"
```

**Numeric values:**
```bash
--field custrecord_twx_rule_template=1
--field priority=5
```

**JSON/Object values (use single quotes):**
```bash
--field custrecord_twx_rule_conditions='{"status":"Processing Error"}'
--field custrecord_twx_rule_recipients='["email1@example.com","email2@example.com"]'
```

**Boolean values:**
```bash
--field custrecord_twx_rule_active=true
--field custrecord_twx_rule_active=false
```

### Combining Query + Update Workflow

**Typical development pattern:**

```bash
# 1. Find the record you need to update
python3 scripts/query_netsuite.py \
  'SELECT id, name, custrecord_twx_rule_conditions FROM customrecord_twx_notification_rule WHERE name LIKE ?' \
  --params 'RULE-%' --env sb2

# 2. Examine current values to determine what to change
# (Review query output)

# 3. Update the record
python3 scripts/update_record.py customrecord_twx_notification_rule 2 \
  --field custrecord_twx_rule_conditions='{"status":"Processing Error"}' \
  --env sb2

# 4. Verify the update
python3 scripts/query_netsuite.py \
  'SELECT id, name, custrecord_twx_rule_conditions FROM customrecord_twx_notification_rule WHERE id = ?' \
  --params 2 --env sb2
```

### Error Handling

**Field doesn't exist:**
```
ERROR: HTTP 400: Invalid field name 'custrecord_invalid_field'
```
→ Check field scriptid in NetSuite or query CustomField table

**Record not found:**
```
ERROR: HTTP 404: Record not found
```
→ Query to verify record ID exists

**Invalid field value:**
```
ERROR: HTTP 400: Invalid value for field
```
→ Check field type (text, list, checkbox) and provide appropriate value

**Gateway not running:**
```
ERROR: Gateway connection error: Connection refused
```
→ Start the NetSuite API Gateway: `cd ~/NetSuiteApiGateway && docker compose up -d`

### Record Operations Best Practices

1. **Query First:** Always query before updating to see current state
2. **Test in Sandbox:** Use `--env sb2` for testing, only update prod when verified
3. **One Field at a Time:** For complex updates, change one field and verify before next
4. **JSON Format:** Use `--json` flag for scripted operations that need structured output
5. **Document Updates:** Keep track of what you changed and why
6. **Verify After:** Always query after update to confirm changes took effect

## Resources

### scripts/query_netsuite.py
Main executable Python script for query execution. Handles:
- RESTlet communication with SuiteAPI
- Multiple output formats (json, table, csv)
- Parameter handling and environment selection
- Error handling and timeout management

### scripts/schema_lookup.py
Schema discovery tool for exploring table definitions, columns, and relationships.
Reads from cached JSON files at `~/.cache/netsuite-schema/`. Stdlib-only.
Subcommands: `describe`, `tables`, `search`, `relationships`, `refresh-custom`, `status`.
The `refresh-custom` subcommand queries CustomRecordType + CustomField via the API gateway
to get custom record types and custom field labels (no ODBC required).

### scripts/schema_refresh.py
ODBC-based full schema dump tool. Connects to NetSuite SuiteAnalytics Connect and
writes OA_TABLES, OA_COLUMNS, OA_FKEYS to JSON cache files.
Requires pyodbc and the NetSuite ODBC driver. Run quarterly or after NetSuite releases.
Reads account list, environments, and ODBC connection details (serviceHost, port, roleId)
dynamically from the API gateway — no hardcoded account values.
Uses DSNs named `netsuite_{account}_{environment}` (configured by setup_odbc.py).

### scripts/setup_odbc.py
Portable one-time setup script for the NetSuite ODBC driver, unixODBC, pyodbc, and DSN
configuration. Reads all account and connection details from the API gateway automatically.
Run once per machine before using schema_refresh.py. Supports:
- `--check` to verify current setup status
- `--dsns-only` to regenerate DSNs without reinstalling the driver
- `--driver-zip` / `--cert-zip` for non-interactive use

### scripts/update_record.py
Executable Python script for record CRUD operations. Handles:
- Record creation (--create flag)
- Record updates (by ID)
- Field value type detection (string, number, JSON, boolean)
- Multiple field updates in single operation
- Same account/environment support as query_netsuite.py
- Error handling for field validation and record access

### references/common_queries.md
Library of pre-built query patterns including:
- Container lifecycle queries
- Transaction chain queries (TO → IF → IR)
- Customer and sales order queries
- Item and inventory queries
- Metadata and schema discovery queries
- Performance optimization patterns

### references/table_reference.md
Complete NetSuite schema reference including:
- Transaction tables (Transaction, TransactionLine, NextTransactionLineLink)
- Entity tables (Customer, Vendor)
- Item and Location tables
- Custom record tables (PRI Freight Container, Vessel)
- Metadata tables (CustomRecordType, CustomField)
- Built-in functions (BUILTIN.DF, date functions, aggregates)
- SuiteQL limitations and best practices

### references/suiteql_functions.md
Comprehensive SQL function reference including:
- 100+ supported functions (mathematical, string, date/time, aggregate)
- Unsupported functions with alternatives
- NetSuite-specific functions (BUILTIN.DF)
- Common workarounds for missing functions
- Performance best practices
- Testing guidelines for new functions

## Quick Reference Commands

```bash
# Basic query (sandbox)
python3 scripts/query_netsuite.py '<query>'

# Production query
python3 scripts/query_netsuite.py '<query>' --env prod

# Parameterized query
python3 scripts/query_netsuite.py '<query>' --params value1,value2

# Large result set with pagination
python3 scripts/query_netsuite.py '<query>' --all-rows

# JSON output for scripting
python3 scripts/query_netsuite.py '<query>' --format json

# CSV export
python3 scripts/query_netsuite.py '<query>' --format csv > results.csv
```

## Critical: `runSuiteQLPaged` Silent Failure Modes

**`runSuiteQLPaged` has multiple known silent failure modes where it returns 0 records with no error.** These affect SuiteScript code using `query.runSuiteQLPaged()`, not queries run via this skill's `query_netsuite.py` (which uses the RESTlet's `runSuiteQL`).

If you are writing or reviewing SuiteScript that uses `runSuiteQLPaged`, be aware of these:

| Failure Mode | Symptom | Workaround |
|-------------|---------|------------|
| **LEFT JOINs inside UNION ALL** | Returns 0 pages/records silently | Use scalar subqueries instead of LEFT JOINs |
| **GROUP BY + SUM queries** | Returns 0 pages/records even with INNER JOINs | Use `runSuiteQL` with manual pagination |
| **Transaction.status filter** | Silently drops WHERE clause, returns ALL rows | Use `TransactionLine.isclosed = 'F'` instead |
| **ROWNUM subquery wrappers** | Same as Transaction.status — filter silently dropped | Use item_id-based manual pagination |

**Recommended alternative:** Use `runSuiteQL` with item_id-based manual pagination:
```javascript
// ORDER BY item_id + FETCH FIRST 5000 + WHERE item_id > lastItemId
// OFFSET/FETCH pagination does NOT work (runSuiteQL applies 5000-row cap BEFORE OFFSET)
```

**Transaction.status quirk:**
- `SELECT` returns short codes: `'B'`, `'H'`, `'G'`
- `WHERE` filtering requires full format: `'PurchOrd:B'`, `'PurchOrd:H'`
- Single-letter codes (`= 'B'`) return 0 results for POs
- Even full format is unreliable in `runSuiteQLPaged` context

**When testing queries via this skill:** If the query works fine via `query_netsuite.py` but returns 0 records when used with `runSuiteQLPaged` in SuiteScript, suspect one of the above failure modes.

## Schema Discovery

Explore NetSuite table schemas without writing queries. Uses the schema cache at `~/.cache/netsuite-schema/`.

### Quick Commands

```bash
# Describe a table (columns, types, FK relationships, custom field labels)
python3 scripts/schema_lookup.py describe Transaction --env sb2
python3 scripts/schema_lookup.py describe customrecord_pri_frgt_cnt --env sb2
python3 scripts/query_netsuite.py --describe TransactionShipment --env sb2

# List tables (with optional glob filter)
python3 scripts/schema_lookup.py tables --env sb2
python3 scripts/schema_lookup.py tables "custom*" --env sb2
python3 scripts/query_netsuite.py --tables "Transaction*" --env sb2

# Search across table names and column names
python3 scripts/schema_lookup.py search "shipping" --env sb2
python3 scripts/schema_lookup.py search "custrecord_pri" --env sb2
python3 scripts/query_netsuite.py --search-columns "entity" --env sb2

# FK graph for planning JOINs
python3 scripts/schema_lookup.py relationships Transaction --env sb2

# Check cache freshness
python3 scripts/schema_lookup.py status
```

### Schema Cache Setup

The schema cache has two sources — use either or both:

**Custom records only (no ODBC needed, run anytime):**
```bash
python3 scripts/schema_lookup.py refresh-custom --account twx --env sb2
```
Queries `CustomRecordType` and `CustomField` via the API gateway. Covers all custom record types and custom fields with human-readable labels.

**Full schema (requires ODBC setup, run quarterly):**
```bash
# One-time ODBC setup (reads all account/connection details from gateway automatically)
python3 scripts/setup_odbc.py \
  --driver-zip ~/Downloads/NetSuiteODBCDrivers_Linux64bit.zip \
  --cert-zip ~/Downloads/Certificates.zip

# Reload shell env
source ~/.bashrc

# Refresh all accounts/environments
export NETSUITE_ODBC_USER='your@email.com'
export NETSUITE_ODBC_PASSWORD='yourpassword'
python3 scripts/schema_refresh.py --all-accounts --all-environments
```
Queries `OA_TABLES`, `OA_COLUMNS`, `OA_FKEYS` via SuiteAnalytics Connect ODBC. Covers all standard tables, all custom tables, column types/lengths, and FK relationships.

Download the driver from: NetSuite > Setup > Company > SuiteAnalytics Connect > Set Up SuiteAnalytics Connect (Linux 64-bit ODBC driver + Certificate Authority Certificates).

**Check setup status on any machine:**
```bash
python3 scripts/setup_odbc.py --check
```

**Regenerate DSNs after adding a new account to the gateway:**
```bash
python3 scripts/setup_odbc.py --dsns-only
```

### Fallback Behavior

Schema commands work at whatever level is available:
- Full ODBC cache → all tables, types, lengths, FK relationships
- Custom cache only → custom record columns with labels (standard tables limited)
- No cache at all → real-time probe (`SELECT * WHERE ROWNUM=1`) discovers column names

## Best Practices

0. **Schema First:** Run `schema_lookup.py describe <table>` before writing queries for unfamiliar tables. Never guess column names — they differ from the UI and many fields are unexposed.
1. **Start Simple:** Test with ROWNUM <= 10 before running full queries
2. **Use References:** Check `references/table_reference.md` and schema cache for correct field names
3. **Parameterize:** Always use `?` placeholders for dynamic values
4. **Filter Early:** Apply WHERE conditions before JOINs for performance
5. **Avoid BUILTIN.DF in Loops:** Get IDs first, format only what's displayed
6. **Test in Sandbox:** Use `--env sb2` by default, only use prod when necessary
7. **Version Control Queries:** Save useful queries to `common_queries.md` for reuse
8. **Document Patterns:** Add new query patterns as you discover them

## Summary

The netsuite-suiteql skill provides rapid SuiteQL query testing during NetSuite Record Display development. It eliminates the need for deploying code just to test queries, enabling faster iteration and validation. Use it whenever you need to verify data structures, test query syntax, or explore NetSuite records during development of container lifecycle features and other Record Display applications.
