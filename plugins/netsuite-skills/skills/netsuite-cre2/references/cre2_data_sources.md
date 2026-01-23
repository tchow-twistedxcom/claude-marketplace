# CRE 2.0 Data Sources Reference

Guide to configuring data sources for CRE 2.0 profiles.

## Data Source Types

| Type | Description | Best For |
|------|-------------|----------|
| **Saved Search** | Existing NetSuite saved search | Standard reports, simple data |
| **SuiteQL** | Direct SQL-like queries | Complex joins, calculations |
| **Record Fields** | Direct record access | Header information |

## Saved Search Data Sources

### Configuration

1. Create a Saved Search in NetSuite
2. Note the Search ID (e.g., `customsearch_cre_cust_stmt_ar_line`)
3. Add to CRE2 Profile as data source
4. Name the data source (this becomes the variable name in templates)

### Accessing in Templates

```freemarker
<!-- Single row data source -->
${datasource.fieldname}

<!-- Multi-row data source -->
<#list datasource.rows as row>
    ${row.fieldname}
</#list>

<!-- First row of multi-row -->
${datasource.rows[0].fieldname}
```

### Common Saved Searches

| Search Name | Purpose | Variable |
|-------------|---------|----------|
| `customsearch_cre_cust_stmt_head` | Customer header | `customer` |
| `customsearch_cre_cust_stmt_ar_line` | AR transactions | `tran` |
| `customsearch_cre_cust_stmt_aging` | Aging buckets | `aging` |

## SuiteQL Data Sources

### Configuration

1. Open CRE2 Profile
2. Add new Data Source
3. Select Type: **SuiteQL**
4. Name the data source
5. Enter SQL query with `{record.id}` placeholder

### Variable Substitution

| Placeholder | Description |
|-------------|-------------|
| `{record.id}` | Current record internal ID |
| `{record.entityid}` | Entity ID field |
| `{record.subsidiary}` | Subsidiary ID |

### Example Queries

#### Customer Transactions
```sql
SELECT
    T.ID,
    T.TranID AS DocNo,
    T.TranDate,
    T.DueDate,
    BUILTIN.DF(T.Type) AS TransType,
    T.ForeignTotal AS Amount,
    T.ForeignAmountUnpaid AS OpenBalance
FROM Transaction T
WHERE T.Entity = {record.id}
  AND T.Type IN ('CustInvc', 'CustCred', 'CustPymt')
  AND T.ForeignAmountUnpaid != 0
ORDER BY T.TranDate
```

#### Invoice with Discount Info
```sql
SELECT
    T.ID,
    T.TranID AS DocNo,
    T.TranDate AS InvoiceDate,
    T.DueDate,
    (SELECT SUM(TAL.Debit)
     FROM TransactionAccountingLine TAL
     WHERE TAL.Transaction = T.ID) AS OriginalAmount,
    BUILTIN.DF(T.Terms) AS Terms,
    Trm.DiscountPercent,
    T.TranDate + Trm.DaysUntilExpiry AS DiscountDate,
    TRUNC(T.TranDate + Trm.DaysUntilExpiry) - TRUNC(SYSDATE) AS DaysToDiscount,
    CASE
        WHEN Trm.DiscountPercent IS NOT NULL
        THEN ROUND(
            (SELECT SUM(TAL.Debit)
             FROM TransactionAccountingLine TAL
             WHERE TAL.Transaction = T.ID) * Trm.DiscountPercent / 100, 2)
        ELSE NULL
    END AS DiscountAmount
FROM Transaction T
LEFT JOIN Term Trm ON T.Terms = Trm.ID
WHERE T.Type = 'CustInvc'
  AND T.Entity = {record.id}
ORDER BY T.TranDate DESC
```

#### Aging Summary
```sql
SELECT
    SUM(CASE WHEN TRUNC(SYSDATE) - T.DueDate <= 0 THEN T.ForeignAmountUnpaid ELSE 0 END) AS Current,
    SUM(CASE WHEN TRUNC(SYSDATE) - T.DueDate BETWEEN 1 AND 30 THEN T.ForeignAmountUnpaid ELSE 0 END) AS Due1_30,
    SUM(CASE WHEN TRUNC(SYSDATE) - T.DueDate BETWEEN 31 AND 60 THEN T.ForeignAmountUnpaid ELSE 0 END) AS Due31_60,
    SUM(CASE WHEN TRUNC(SYSDATE) - T.DueDate BETWEEN 61 AND 90 THEN T.ForeignAmountUnpaid ELSE 0 END) AS Due61_90,
    SUM(CASE WHEN TRUNC(SYSDATE) - T.DueDate > 90 THEN T.ForeignAmountUnpaid ELSE 0 END) AS Due91Plus,
    SUM(T.ForeignAmountUnpaid) AS TotalDue
FROM Transaction T
WHERE T.Entity = {record.id}
  AND T.Type = 'CustInvc'
  AND T.ForeignAmountUnpaid != 0
```

### SuiteQL Field Limitations

**Fields NOT available in SuiteQL:**

| Field | Workaround |
|-------|------------|
| `discountamount` | Calculate: `Amount * Term.DiscountPercent / 100` |
| `discountdate` | Calculate: `TranDate + Term.DaysUntilExpiry` |
| `foreignamountremaining` | Use `ForeignAmountUnpaid` |
| `total` | Sum from `TransactionAccountingLine` |

### Accessing SuiteQL Results

```freemarker
<!-- Check if data exists -->
<#if discount_lines?has_content>

    <!-- Iterate rows -->
    <#list discount_lines.rows as disc>
        ${disc.docno}
        ${disc.discountamount}
    </#list>

    <!-- First row only -->
    ${discount_lines.rows[0].totals}

</#if>
```

## Record Field Data Sources

### Direct Record Access

The base record is always available as `record`:

```freemarker
${record.id}                    <!-- Internal ID -->
${record.entityid}              <!-- Entity ID -->
${record.companyname}           <!-- Company name -->
${record.email}                 <!-- Email -->
${record.phone}                 <!-- Phone -->
${record.creditlimit}           <!-- Credit limit -->
${record.terms["name"]}         <!-- Terms name -->
${record.billaddressee}         <!-- Bill to name -->
${record.billaddr1}             <!-- Bill address line 1 -->
${record.billcity}              <!-- Bill city -->
${record.billstate}             <!-- Bill state -->
${record.billzip}               <!-- Bill zip -->
${record.billcountry}           <!-- Bill country -->
```

### Sublists

```freemarker
<!-- Access sublists -->
<#list record.item as line>
    ${line.item}
    ${line.quantity}
    ${line.rate}
    ${line.amount}
</#list>
```

## Best Practices

### 1. Choose the Right Type

| Scenario | Use |
|----------|-----|
| Simple data, existing search | Saved Search |
| Complex joins, calculations | SuiteQL |
| Header/record info | Record Fields |
| Need field not in search | SuiteQL |

### 2. Optimize Queries

```sql
-- Good: Filter early, limit results
SELECT ID, TranID, Amount
FROM Transaction
WHERE Entity = {record.id}
  AND Type = 'CustInvc'
  AND ForeignAmountUnpaid != 0

-- Bad: Select all, filter in template
SELECT *
FROM Transaction
WHERE Entity = {record.id}
```

### 3. Handle Nulls

Always check for content before using:

```freemarker
<#if discount_lines?has_content && discount_lines.rows?size > 0>
    <#list discount_lines.rows as disc>
        <#if disc.discountamount?has_content>
            ${disc.discountamount}
        </#if>
    </#list>
</#if>
```

### 4. Test Queries First

Use netsuite-suiteql skill to validate queries:

```bash
cd ~/.claude/plugins/.../netsuite-suiteql
python3 scripts/query_netsuite.py "<query>" --env sb1 --format table
```

## Troubleshooting

### Empty Results

1. Check query parameters match record
2. Verify {record.id} substitution
3. Test query with hardcoded ID first
4. Check for filter conditions excluding data

### Field Not Found

1. Verify field exists in SuiteQL
2. Use BUILTIN.DF() for display values
3. Check field is exposed in record type
4. Some fields need JOIN to related tables

### Performance Issues

1. Add WHERE clauses to limit data
2. Use FETCH FIRST N ROWS for testing
3. Avoid SELECT * - specify needed fields
4. Index filter columns in NetSuite
