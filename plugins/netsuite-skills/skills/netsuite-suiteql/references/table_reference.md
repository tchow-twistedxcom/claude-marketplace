# NetSuite Table Reference

Common NetSuite tables and their key fields for SuiteQL queries.

## Transaction Tables

### Transaction (Base Transaction Table)
**Table Name:** `Transaction`

**Common Fields:**
| Field | Type | Description |
|-------|------|-------------|
| ID | INT | Internal transaction ID |
| TranID | STRING | Transaction number (e.g., SO12345) |
| TranDate | DATE | Transaction date |
| Type | STRING | Transaction type (SalesOrd, TrnfrOrd, ItemShip, ItemRcpt, etc.) |
| Entity | INT | Customer/Vendor ID |
| Status | INT | Transaction status ID (use BUILTIN.DF for text) |
| Location | INT | Location ID |
| TransferLocation | INT | Transfer destination location (for Transfer Orders) |
| Total | CURRENCY | Transaction total amount |
| Memo | STRING | Transaction memo |
| Created | DATETIME | Record creation timestamp |
| LastModified | DATETIME | Last modification timestamp |

**Transaction Types:**
- `'SalesOrd'` - Sales Order
- `'TrnfrOrd'` - Transfer Order
- `'ItemShip'` - Item Fulfillment
- `'ItemRcpt'` - Item Receipt
- `'VendBill'` - Vendor Bill
- `'CustInvc'` - Invoice
- `'CustPymt'` - Customer Payment

### TransactionLine (Transaction Line Items)
**Table Name:** `TransactionLine`

**Common Fields:**
| Field | Type | Description |
|-------|------|-------------|
| ID | INT | Line ID |
| Transaction | INT | Parent transaction ID |
| Line | INT | Line number (sequencing) |
| Item | INT | Item ID |
| Quantity | FLOAT | Line quantity |
| Amount | CURRENCY | Line amount |
| Rate | CURRENCY | Unit price |
| Location | INT | Line location |

### NextTransactionLineLink (Transaction Relationships)
**Table Name:** `NextTransactionLineLink`

Links transactions in a chain (e.g., Transfer Order → Item Fulfillment → Item Receipt)

**Common Fields:**
| Field | Type | Description |
|-------|------|-------------|
| PreviousDoc | INT | Source transaction ID |
| NextDoc | INT | Linked transaction ID |
| PreviousLine | INT | Source line number |
| NextLine | INT | Linked line number |

**Usage Pattern:**
```sql
-- Find Item Fulfillment from Transfer Order
SELECT IF_TXN.*
FROM Transaction AS IF_TXN
INNER JOIN NextTransactionLineLink AS NTLL
    ON IF_TXN.ID = NTLL.NextDoc
WHERE NTLL.PreviousDoc = ? -- Transfer Order ID
    AND IF_TXN.Type = 'ItemShip'
```

## Customer & Entity Tables

### Customer
**Table Name:** `Customer`

**Common Fields:**
| Field | Type | Description |
|-------|------|-------------|
| ID | INT | Customer internal ID |
| EntityID | STRING | Customer number |
| CompanyName | STRING | Company name |
| Email | STRING | Primary email |
| Phone | STRING | Primary phone |
| Parent | INT | Parent customer ID |
| IsInactive | CHAR | 'T' or 'F' |
| DateCreated | DATE | Customer creation date |

### Vendor
**Table Name:** `Vendor`

Similar structure to Customer table.

## Item Tables

### Item
**Table Name:** `Item`

**Common Fields:**
| Field | Type | Description |
|-------|------|-------------|
| ID | INT | Item internal ID |
| ItemID | STRING | Item number/SKU |
| DisplayName | STRING | Item display name |
| ItemType | STRING | InvtPart, Assembly, Kit, Service, etc. |
| IsInactive | CHAR | 'T' or 'F' |
| Class | INT | Item class ID |
| Department | INT | Item department ID |
| UPCCode | STRING | UPC barcode |

**Item Types:**
- `'InvtPart'` - Inventory Item
- `'Assembly'` - Assembly/Bill of Materials
- `'Kit'` - Kit/Package
- `'Service'` - Service Item
- `'NonInvtPart'` - Non-Inventory Item

## Location Tables

### Location
**Table Name:** `Location`

**Common Fields:**
| Field | Type | Description |
|-------|------|-------------|
| ID | INT | Location internal ID |
| Name | STRING | Location name |
| IsInactive | CHAR | 'T' or 'F' |
| Country | INT | Country ID |
| State | INT | State/Province ID |

## Custom Record Tables

### PRI Freight Container
**Table Name:** `customrecord_pri_frgt_cnt`

**Common Fields:**
| Field | Type | Description |
|-------|------|-------------|
| ID | INT | Container internal ID |
| Name | STRING | Container name/number |
| custrecord_pri_frgt_cnt_to | INT | Transfer Order ID |
| custrecord_pri_frgt_cnt_vsl | INT | Vessel ID |
| custrecord_pri_frgt_cnt_log_status | INT | Logistics status ID |
| custrecord_pri_frgt_cnt_date_sail | DATE | Sailing date |
| custrecord_pri_frgt_cnt_date_land_est | DATE | Estimated landing date |
| custrecord_pri_frgt_cnt_date_land_act | DATE | Actual landing date |
| custrecord_pri_frgt_cnt_date_fwd_est | DATE | Estimated forwarding date |
| custrecord_pri_frgt_cnt_date_fwd_act | DATE | Actual forwarding date |
| custrecord_pri_frgt_cnt_date_arr_est | DATE | Estimated arrival date |
| custrecord_pri_frgt_cnt_date_arr_act | DATE | Actual arrival date |
| custrecord_pri_frgt_cnt_date_dest_est | DATE | Estimated destination date |
| custrecord_pri_frgt_cnt_date_dest_act | DATE | Actual destination date |
| custrecord_pri_frgt_cnt_location_origin | INT | Origin location ID |
| custrecord_pri_frgt_cnt_location_dest | INT | Destination location ID |

### PRI Freight Container Vessel
**Table Name:** `customrecord_pri_frgt_cnt_vsl`

**Common Fields:**
| Field | Type | Description |
|-------|------|-------------|
| ID | INT | Vessel internal ID |
| Name | STRING | Vessel name/number |
| custrecord_pri_frgt_cnt_vsl_carrier | INT | Carrier ID |
| custrecord_pri_frgt_cnt_vsl_log_status | INT | Logistics status ID |
| custrecord_pri_frgt_cnt_vsl_date_sail | DATE | Sailing date |

## Metadata Tables

### CustomRecordType
**Table Name:** `CustomRecordType`

Lists all custom record types in the account.

**Common Fields:**
| Field | Type | Description |
|-------|------|-------------|
| ID | INT | Custom record type internal ID |
| ScriptID | STRING | Script ID (e.g., customrecord_pri_frgt_cnt) |
| Name | STRING | Display name |
| IsInactive | CHAR | 'T' or 'F' |

### CustomField
**Table Name:** `CustomField`

Lists all custom fields.

**Common Fields:**
| Field | Type | Description |
|-------|------|-------------|
| ID | INT | Custom field internal ID |
| ScriptID | STRING | Script ID (e.g., custrecord_pri_frgt_cnt_to) |
| FieldLabel | STRING | Display label |
| FieldType | STRING | Field data type |
| AppliesToRecord | STRING | Record type this field belongs to |

## Built-in Functions

### BUILTIN.DF (Display Format)
Converts internal IDs to display text.

**Usage:**
```sql
SELECT
    ID,
    Status, -- Returns internal ID (e.g., 3)
    BUILTIN.DF(Status) AS status_text -- Returns display text (e.g., "Pending Fulfillment")
FROM Transaction
```

**Performance Note:** BUILTIN.DF is expensive. Only use when display text is needed.

### Date Functions

**TO_DATE:** Convert string to date
```sql
SELECT * FROM Transaction
WHERE TranDate >= TO_DATE('2025-01-01', 'YYYY-MM-DD')
```

**CURRENT_DATE:** Get current date
```sql
SELECT * FROM Transaction
WHERE TranDate = CURRENT_DATE
```

**Date Arithmetic:**
```sql
-- Last 30 days
WHERE TranDate >= CURRENT_DATE - 30
```

### Aggregate Functions

**Standard Aggregates:**
- `COUNT(*)` - Count rows
- `SUM(column)` - Sum values
- `AVG(column)` - Average
- `MIN(column)` - Minimum
- `MAX(column)` - Maximum

**Example:**
```sql
SELECT
    Status,
    COUNT(*) AS order_count,
    SUM(Total) AS total_amount
FROM Transaction
WHERE Type = 'SalesOrd'
GROUP BY Status
```

### String Functions

**UPPER/LOWER:** Case conversion
```sql
SELECT UPPER(CompanyName) AS company_upper
FROM Customer
```

**CONCAT:** String concatenation
```sql
SELECT CONCAT(FirstName, ' ', LastName) AS full_name
FROM Employee
```

**LIKE:** Pattern matching
```sql
SELECT * FROM Customer
WHERE CompanyName LIKE '%Twisted%'
```

## SuiteQL Limitations & Notes

### Known Limitations
1. **No DELETE/UPDATE:** SuiteQL is read-only for SELECT queries
2. **No Subqueries in WHERE:** Limited subquery support
3. **No WITH/CTE:** Common Table Expressions not supported
4. **Limited Window Functions:** No OVER() clause
5. **BUILTIN.DF Performance:** Very expensive, use sparingly

### Best Practices
1. **Filter Early:** Apply WHERE conditions before JOINs
2. **Limit Results:** Always use ROWNUM for exploratory queries
3. **Index Awareness:** Filter on ID fields for best performance
4. **Avoid BUILTIN.DF in Loops:** Get IDs first, format only what's displayed
5. **Use Parameterization:** Always use ? for dynamic values

### Pagination Pattern
```sql
-- Page 1 (rows 1-1000)
SELECT * FROM (
    SELECT ROWNUM AS rn, t.*
    FROM Transaction t
    WHERE Type = 'SalesOrd'
) WHERE rn BETWEEN 1 AND 1000

-- Page 2 (rows 1001-2000)
SELECT * FROM (
    SELECT ROWNUM AS rn, t.*
    FROM Transaction t
    WHERE Type = 'SalesOrd'
) WHERE rn BETWEEN 1001 AND 2000
```

### Field Name Discovery
To find custom field names, query the metadata tables or use NetSuite's UI to inspect field Script IDs.
