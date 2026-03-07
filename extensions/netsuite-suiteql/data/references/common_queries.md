# Common NetSuite SuiteQL Queries

Library of frequently used query patterns for NetSuite development and testing.

## Container Lifecycle Queries

### Get Container by ID
```sql
SELECT
    CNT.ID,
    CNT.Name,
    BUILTIN.DF(CNT.custrecord_pri_frgt_cnt_log_status) AS status_text,
    CNT.custrecord_pri_frgt_cnt_log_status AS status_value,
    CNT.custrecord_pri_frgt_cnt_to AS transfer_order_id,
    CNT.custrecord_pri_frgt_cnt_vsl AS vessel_id,
    CNT.custrecord_pri_frgt_cnt_date_sail AS date_sail,
    CNT.custrecord_pri_frgt_cnt_date_land_act AS date_land_act,
    BUILTIN.DF(CNT.custrecord_pri_frgt_cnt_location_origin) AS origin_location,
    BUILTIN.DF(CNT.custrecord_pri_frgt_cnt_location_dest) AS dest_location
FROM customrecord_pri_frgt_cnt AS CNT
WHERE CNT.ID = ?
```

### List Active Containers
```sql
SELECT * FROM (
    SELECT
        ID,
        Name,
        BUILTIN.DF(custrecord_pri_frgt_cnt_log_status) AS status,
        custrecord_pri_frgt_cnt_date_sail AS sail_date,
        BUILTIN.DF(custrecord_pri_frgt_cnt_location_dest) AS destination
    FROM customrecord_pri_frgt_cnt
    WHERE custrecord_pri_frgt_cnt_log_status IS NOT NULL
    ORDER BY lastmodified DESC
) WHERE ROWNUM <= 20
```

### Container with Vessel Information
```sql
SELECT
    CNT.ID AS container_id,
    CNT.Name AS container_name,
    VSL.ID AS vessel_id,
    VSL.Name AS vessel_name,
    CNT.custrecord_pri_frgt_cnt_date_sail AS sail_date
FROM customrecord_pri_frgt_cnt AS CNT
LEFT JOIN customrecord_pri_frgt_cnt_vsl AS VSL
    ON CNT.custrecord_pri_frgt_cnt_vsl = VSL.ID
WHERE CNT.ID = ?
```

## Transaction Queries

### Get Transfer Order by ID
```sql
SELECT
    TO_TXN.ID,
    TO_TXN.TranID AS tran_number,
    TO_TXN.TranDate AS tran_date,
    BUILTIN.DF(TO_TXN.Status) AS status,
    BUILTIN.DF(TO_TXN.Location) AS from_location,
    BUILTIN.DF(TO_TXN.TransferLocation) AS to_location
FROM Transaction AS TO_TXN
WHERE TO_TXN.ID = ?
    AND TO_TXN.Type = 'TrnfrOrd'
```

### Get Item Fulfillment for Transfer Order
```sql
SELECT
    IF_TXN.ID,
    IF_TXN.TranID AS tran_number,
    IF_TXN.TranDate AS tran_date,
    BUILTIN.DF(IF_TXN.Status) AS status,
    (
        SELECT ABS(SUM(TL.Quantity))
        FROM TransactionLine AS TL
        INNER JOIN Item AS I ON TL.Item = I.ID
        WHERE TL.Transaction = IF_TXN.ID
        AND I.ItemType IN ('InvtPart', 'Assembly', 'Kit')
    ) AS total_quantity
FROM Transaction AS IF_TXN
INNER JOIN NextTransactionLineLink AS NTLL
    ON IF_TXN.ID = NTLL.NextDoc
WHERE IF_TXN.Type = 'ItemShip'
    AND NTLL.PreviousDoc = ?
ORDER BY IF_TXN.TranDate DESC
```

### Get Item Receipt for Transfer Order
```sql
SELECT
    IR_TXN.ID,
    IR_TXN.TranID AS tran_number,
    IR_TXN.TranDate AS tran_date,
    BUILTIN.DF(IR_TXN.Status) AS status,
    BUILTIN.DF(IR_TXN.Location) AS location,
    (
        SELECT ABS(SUM(TL.Quantity))
        FROM TransactionLine AS TL
        INNER JOIN Item AS I ON TL.Item = I.ID
        WHERE TL.Transaction = IR_TXN.ID
        AND I.ItemType IN ('InvtPart', 'Assembly', 'Kit')
    ) AS total_quantity
FROM Transaction AS IR_TXN
INNER JOIN NextTransactionLineLink AS NTLL
    ON IR_TXN.ID = NTLL.NextDoc
WHERE IR_TXN.Type = 'ItemRcpt'
    AND NTLL.PreviousDoc = ?
ORDER BY IR_TXN.TranDate DESC
```

### Transaction Chain (TO → IF → IR)
```sql
SELECT
    BASE.ID AS to_id,
    BASE.TranID AS to_number,
    IF_TXN.ID AS if_id,
    IF_TXN.TranID AS if_number,
    IR_TXN.ID AS ir_id,
    IR_TXN.TranID AS ir_number
FROM Transaction AS BASE
LEFT JOIN NextTransactionLineLink AS IF_LINK
    ON BASE.ID = IF_LINK.PreviousDoc
LEFT JOIN Transaction AS IF_TXN
    ON IF_LINK.NextDoc = IF_TXN.ID
    AND IF_TXN.Type = 'ItemShip'
LEFT JOIN NextTransactionLineLink AS IR_LINK
    ON BASE.ID = IR_LINK.PreviousDoc
LEFT JOIN Transaction AS IR_TXN
    ON IR_LINK.NextDoc = IR_TXN.ID
    AND IR_TXN.Type = 'ItemRcpt'
WHERE BASE.ID = ?
    AND BASE.Type = 'TrnfrOrd'
```

## Customer & Sales Order Queries

### Get Customer by ID
```sql
SELECT
    ID,
    EntityID AS customer_number,
    CompanyName AS company_name,
    Email,
    Phone,
    BUILTIN.DF(Parent) AS parent_customer
FROM Customer
WHERE ID = ?
```

### Get Sales Order with Customer
```sql
SELECT
    SO.ID,
    SO.TranID AS order_number,
    SO.TranDate AS order_date,
    BUILTIN.DF(SO.Status) AS status,
    C.CompanyName AS customer_name,
    SO.Total AS order_total
FROM Transaction AS SO
INNER JOIN Customer AS C ON SO.Entity = C.ID
WHERE SO.ID = ?
    AND SO.Type = 'SalesOrd'
```

### Recent Sales Orders
```sql
SELECT * FROM (
    SELECT
        SO.ID,
        SO.TranID AS order_number,
        SO.TranDate AS order_date,
        BUILTIN.DF(SO.Status) AS status,
        C.CompanyName AS customer_name,
        SO.Total AS order_total
    FROM Transaction AS SO
    INNER JOIN Customer AS C ON SO.Entity = C.ID
    WHERE SO.Type = 'SalesOrd'
    ORDER BY SO.TranDate DESC
) WHERE ROWNUM <= 50
```

## Item & Inventory Queries

### Get Item by ID
```sql
SELECT
    I.ID,
    I.ItemID AS item_number,
    I.DisplayName AS item_name,
    I.ItemType,
    I.IsInactive,
    BUILTIN.DF(I.Class) AS item_class
FROM Item AS I
WHERE I.ID = ?
```

### Items on Transfer Order
```sql
SELECT
    I.ID AS item_id,
    I.ItemID AS item_number,
    I.DisplayName AS item_name,
    TL.Quantity,
    TL.Amount,
    TL.Line AS line_number
FROM TransactionLine AS TL
INNER JOIN Item AS I ON TL.Item = I.ID
WHERE TL.Transaction = ?
    AND I.ItemType IN ('InvtPart', 'Assembly', 'Kit')
ORDER BY TL.Line
```

## Custom Record Queries

### Query Any Custom Record
```sql
SELECT
    ID,
    Name,
    Created,
    LastModified
FROM customrecord_your_record_type
WHERE ID = ?
```

### Count Records by Status
```sql
SELECT
    BUILTIN.DF(your_status_field) AS status,
    COUNT(*) AS record_count
FROM customrecord_your_record_type
GROUP BY your_status_field
ORDER BY record_count DESC
```

## Metadata & Schema Queries

### List Custom Record Types
```sql
SELECT
    ID,
    ScriptID AS record_type,
    Name AS record_name
FROM CustomRecordType
WHERE IsInactive = 'F'
ORDER BY Name
```

### List Custom Fields for a Record Type
```sql
SELECT
    ID,
    ScriptID AS field_id,
    FieldLabel AS field_label,
    FieldType AS field_type
FROM CustomField
WHERE AppliesToRecord = ?
ORDER BY FieldLabel
```

## Performance Optimization Patterns

### Use BUILTIN.DF Only When Needed
```sql
-- SLOW: Display formatting for all records
SELECT
    ID,
    BUILTIN.DF(Status) AS status_text,
    BUILTIN.DF(Location) AS location_text
FROM Transaction
WHERE Type = 'SalesOrd'

-- FAST: Get IDs first, then format only what's displayed
SELECT
    ID,
    Status,
    Location
FROM Transaction
WHERE Type = 'SalesOrd'
```

### Filter Before Joining
```sql
-- BETTER: Filter base table first
SELECT
    T.ID,
    T.TranID,
    C.CompanyName
FROM (
    SELECT * FROM Transaction
    WHERE Type = 'SalesOrd'
        AND TranDate >= TO_DATE('2025-01-01', 'YYYY-MM-DD')
) AS T
INNER JOIN Customer AS C ON T.Entity = C.ID

-- AVOID: Join then filter
SELECT T.ID, T.TranID, C.CompanyName
FROM Transaction AS T
INNER JOIN Customer AS C ON T.Entity = C.ID
WHERE T.Type = 'SalesOrd'
    AND T.TranDate >= TO_DATE('2025-01-01', 'YYYY-MM-DD')
```

### Use Subqueries for Aggregations
```sql
-- Aggregate in subquery to avoid GROUP BY
SELECT
    T.ID,
    T.TranID,
    (
        SELECT SUM(TL.Amount)
        FROM TransactionLine AS TL
        WHERE TL.Transaction = T.ID
    ) AS line_total
FROM Transaction AS T
WHERE T.Type = 'SalesOrd'
```

## Invoice & Cost Calculation Patterns

**⚠️ Note:** Standard Transaction fields like `subtotal`, `total`, `shippingcost`, `handlingcost` are **NOT exposed in SuiteQL**. Use TransactionLine aggregations and TransactionShipment instead.

### TransactionLine Item Types
Understanding `itemtype` values is critical for accurate totals:

| itemtype | Description | Include in Subtotal? |
|----------|-------------|---------------------|
| `InvtPart` | Inventory items (product lines) | ✅ Yes |
| `NonInvtPart` | Non-inventory items | ✅ Yes |
| `Service` | Service items | ✅ Yes |
| `ShipItem` | Shipping charges | ❌ No (separate) |
| `OthCharge` | Other charges (handling, fees) | ❌ No (separate) |
| `Discount` | Discount lines | ⚠️ Usually no |
| `Payment` | Payment application lines | ❌ No |
| `Markup` | Markup lines | ⚠️ Depends |

### Invoice Subtotal (Product Lines Only)
```sql
-- Get product line subtotal excluding shipping/handling
SELECT SUM(ABS(TL.netamount)) AS subtotal
FROM TransactionLine TL
WHERE TL.transaction = {invoice_id}
  AND TL.mainline = 'F'
  AND TL.taxline = 'F'
  AND TL.itemtype = 'InvtPart'
```

### Shipping & Handling from Fulfillment
```sql
-- Get shipping/handling from linked Item Fulfillment
SELECT
    TS.shippingrate AS shipping_cost,
    TS.handlingrate AS handling_cost
FROM TransactionShipment TS
INNER JOIN Transaction T ON T.ID = TS.doc
WHERE T.custbody_pri_bpa_ff_inv_link = {invoice_id}
-- Note: custbody_pri_bpa_ff_inv_link is the custom field linking fulfillment to invoice
```

### Invoice Total (All Line Items)
```sql
-- Get full invoice total from transaction lines
SELECT SUM(ABS(TL.netamount)) AS invoice_total
FROM TransactionLine TL
WHERE TL.transaction = {invoice_id}
  AND TL.mainline = 'F'
  AND TL.taxline = 'F'
```

### Complete Invoice Breakdown Pattern
```sql
-- Full invoice breakdown with all costs
SELECT
    T.TranID AS invoice_number,
    (SELECT SUM(ABS(TL.netamount))
     FROM TransactionLine TL
     WHERE TL.transaction = T.ID
       AND TL.mainline = 'F' AND TL.taxline = 'F'
       AND TL.itemtype = 'InvtPart') AS subtotal,
    (SELECT TS.shippingrate
     FROM TransactionShipment TS
     INNER JOIN Transaction IF_TXN ON IF_TXN.ID = TS.doc
     WHERE IF_TXN.custbody_pri_bpa_ff_inv_link = T.ID) AS shipping,
    (SELECT TS.handlingrate
     FROM TransactionShipment TS
     INNER JOIN Transaction IF_TXN ON IF_TXN.ID = TS.doc
     WHERE IF_TXN.custbody_pri_bpa_ff_inv_link = T.ID) AS handling,
    (SELECT SUM(ABS(TL.netamount))
     FROM TransactionLine TL
     WHERE TL.transaction = T.ID
       AND TL.mainline = 'F' AND TL.taxline = 'F') AS total
FROM Transaction T
WHERE T.Type = 'CustInvc'
  AND T.ID = ?
```

### Item Fulfillment with Costs
```sql
-- Get fulfillment with all shipping data
SELECT
    T.ID,
    T.TranID AS fulfillment_number,
    T.TranDate AS ship_date,
    BUILTIN.DF(T.ShipMethod) AS ship_method,
    (SELECT TS.shippingrate FROM TransactionShipment TS WHERE TS.doc = T.ID) AS shipping,
    (SELECT TS.handlingrate FROM TransactionShipment TS WHERE TS.doc = T.ID) AS handling,
    (SELECT TS.weight FROM TransactionShipment TS WHERE TS.doc = T.ID) AS weight
FROM Transaction T
WHERE T.Type = 'ItemShip'
  AND T.ID = ?
```

## Parameterized Query Patterns

### Single Parameter
```sql
SELECT * FROM Customer WHERE ID = ?
-- Call with: params = [12345]
```

### Multiple Parameters
```sql
SELECT * FROM Transaction
WHERE Type = ?
    AND TranDate >= TO_DATE(?, 'YYYY-MM-DD')
    AND Status = ?
-- Call with: params = ['SalesOrd', '2025-01-01', 'Pending Fulfillment']
```

### IN Clause with Parameters
```sql
-- For dynamic IN clauses, build query string programmatically
SELECT * FROM Customer WHERE ID IN (?, ?, ?)
-- Call with: params = [123, 456, 789]
```

## Dutyman Account Examples

**Note:** Dutyman only supports `prod` and `sb1` environments (no sb2).

### Query Customers (Dutyman)
```bash
python3 scripts/query_netsuite.py 'SELECT id, companyname FROM customer WHERE ROWNUM <= 5' --account dm --env prod
```

### Query PRI Query Renderer Records (Dutyman)
```bash
python3 scripts/query_netsuite.py 'SELECT id, name FROM customrecord_pri_qt_query' --account dm --env prod
```

### Query Query Filters (Dutyman)
```bash
python3 scripts/query_netsuite.py 'SELECT id, name, custrecord_pri_qt_qf_placeholder, custrecord_pri_qt_qf_filter FROM customrecord_pri_qt_query_filter WHERE custrecord_pri_qt_qf_parent = ?' --params 1 --account dm --env prod
```

### Query Backorder Items (Dutyman)
```bash
python3 scripts/query_netsuite.py "SELECT t.tranid, BUILTIN.DF(t.entity) as customer, BUILTIN.DF(t.status) as status FROM transaction t WHERE t.type = 'SalesOrd' AND t.status IN ('SalesOrd:B', 'SalesOrd:D', 'SalesOrd:E') AND ROWNUM <= 10" --account dm --env prod
```

### Update Record (Dutyman)
```bash
python3 scripts/update_record.py customrecord_pri_qt_query 1 --fields '{"custrecord_pri_qt_q_do_not_run": false}' --account dm --env prod
```
