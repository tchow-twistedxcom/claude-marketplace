# SuiteQL Supported and Unsupported Functions

Complete reference for SQL functions available in NetSuite's SuiteQL query language.

**Important:** This list is based on NetSuite's official documentation but is not exhaustive. Always test functions in a sandbox environment before using in production queries.

## Mathematical Functions

| Function | Description | Example |
|----------|-------------|---------|
| ABS | Absolute value | `SELECT ABS(-15)` → 15 |
| ACOS | Arc cosine | `SELECT ACOS(0.5)` |
| ASIN | Arc sine | `SELECT ASIN(0.5)` |
| ATAN | Arc tangent | `SELECT ATAN(1)` |
| ATAN2 | Arc tangent of two values | `SELECT ATAN2(y, x)` |
| CEIL | Smallest integer ≥ value | `SELECT CEIL(15.7)` → 16 |
| COS | Cosine | `SELECT COS(angle)` |
| COSH | Hyperbolic cosine | `SELECT COSH(value)` |
| EXP | e raised to the power | `SELECT EXP(2)` |
| FLOOR | Largest integer ≤ value | `SELECT FLOOR(15.7)` → 15 |
| LN | Natural logarithm | `SELECT LN(value)` |
| LOG | Logarithm (base 10) | `SELECT LOG(10, value)` |
| MOD | Modulo (remainder) | `SELECT MOD(11, 4)` → 3 |
| POWER | Raise to power | `SELECT POWER(2, 10)` → 1024 |
| REMAINDER | IEEE 754 remainder | `SELECT REMAINDER(11, 4)` |
| ROUND | Round to n decimals | `SELECT ROUND(15.193, 1)` → 15.2 |
| SIGN | Sign of number (-1, 0, 1) | `SELECT SIGN(-15)` → -1 |
| SIN | Sine | `SELECT SIN(angle)` |
| SINH | Hyperbolic sine | `SELECT SINH(value)` |
| SQRT | Square root | `SELECT SQRT(16)` → 4 |
| TAN | Tangent | `SELECT TAN(angle)` |
| TANH | Hyperbolic tangent | `SELECT TANH(value)` |

## String/Character Functions

| Function | Description | Example |
|----------|-------------|---------|
| ASCII | ASCII code of first char | `SELECT ASCII('A')` → 65 |
| ASCIISTR | ASCII string representation | `SELECT ASCIISTR(string)` |
| CHR | Character from ASCII code | `SELECT CHR(65)` → 'A' |
| COALESCE | First non-null value | `SELECT COALESCE(col1, col2, 'default')` |
| COMPOSE | Unicode normalization | `SELECT COMPOSE(string)` |
| CONCAT | Concatenate strings | `SELECT CONCAT('Hello', ' World')` |
| DECOMPOSE | Unicode decomposition | `SELECT DECOMPOSE(string)` |
| INITCAP | Capitalize first letter | `SELECT INITCAP('hello world')` → 'Hello World' |
| INSTR | Position of substring | `SELECT INSTR('hello', 'l')` → 3 |
| LENGTH | Length of string | `SELECT LENGTH('hello')` → 5 |
| LENGTH2 | Length (UCS2 codepoints) | `SELECT LENGTH2(string)` |
| LENGTH4 | Length (UCS4 codepoints) | `SELECT LENGTH4(string)` |
| LENGTHB | Length in bytes | `SELECT LENGTHB(string)` |
| LENGTHC | Length in Unicode chars | `SELECT LENGTHC(string)` |
| LOWER | Convert to lowercase | `SELECT LOWER('HELLO')` → 'hello' |
| LPAD | Left pad string | `SELECT LPAD('abc', 5, '*')` → '**abc' |
| LTRIM | Trim left whitespace | `SELECT LTRIM('  hello')` → 'hello' |
| NLS_INITCAP | Language-specific initcap | `SELECT NLS_INITCAP(string)` |
| NLS_LOWER | Language-specific lowercase | `SELECT NLS_LOWER(string)` |
| NLS_UPPER | Language-specific uppercase | `SELECT NLS_UPPER(string)` |
| REPLACE | Replace substring | `SELECT REPLACE('hello', 'l', 'r')` → 'herro' |
| RPAD | Right pad string | `SELECT RPAD('abc', 5, '*')` → 'abc**' |
| RTRIM | Trim right whitespace | `SELECT RTRIM('hello  ')` → 'hello' |
| SOUNDEX | Phonetic representation | `SELECT SOUNDEX('Smith')` |
| SUBSTR | Extract substring | `SELECT SUBSTR('hello', 2, 3)` → 'ell' |
| TRANSLATE | Character-by-char replace | `SELECT TRANSLATE(string, from, to)` |
| UPPER | Convert to uppercase | `SELECT UPPER('hello')` → 'HELLO' |
| UNISTR | Unicode string literal | `SELECT UNISTR('\\00C4')` |

## Date/Time Functions

| Function | Description | Example |
|----------|-------------|---------|
| ADD_MONTHS | Add months to date | `SELECT ADD_MONTHS(date, 3)` |
| CURRENT_DATE | Current date | `SELECT CURRENT_DATE` |
| CURRENT_TIMESTAMP | Current timestamp | `SELECT CURRENT_TIMESTAMP` |
| FROM_TZ | Convert to timestamp with TZ | `SELECT FROM_TZ(timestamp, timezone)` |
| LAST_DAY | Last day of month | `SELECT LAST_DAY(date)` |
| LOCALTIMESTAMP | Local timestamp | `SELECT LOCALTIMESTAMP` |
| MONTHS_BETWEEN | Months between dates | `SELECT MONTHS_BETWEEN(date1, date2)` |
| NEW_TIME | Convert timezone | `SELECT NEW_TIME(date, tz1, tz2)` |
| NEXT_DAY | Next occurrence of day | `SELECT NEXT_DAY(date, 'MONDAY')` |
| SYS_EXTRACT_UTC | Extract UTC from timestamp | `SELECT SYS_EXTRACT_UTC(timestamp)` |
| TO_DATE | Convert string to date | `SELECT TO_DATE('2025-01-01', 'YYYY-MM-DD')` |
| TO_TIMESTAMP | Convert to timestamp | `SELECT TO_TIMESTAMP(string, format)` |
| TO_TIMESTAMP_TZ | Convert to timestamp with TZ | `SELECT TO_TIMESTAMP_TZ(string, format)` |
| TZ_OFFSET | Timezone offset | `SELECT TZ_OFFSET('US/Pacific')` |

## Aggregate Functions

| Function | Description | Example |
|----------|-------------|---------|
| AVG | Average value | `SELECT AVG(amount) FROM Transaction` |
| COUNT | Count rows | `SELECT COUNT(*) FROM Customer` |
| DENSE_RANK | Dense rank (no gaps) | `SELECT DENSE_RANK() OVER (ORDER BY score)` |
| MAX | Maximum value | `SELECT MAX(total) FROM Transaction` |
| MEDIAN | Median value | `SELECT MEDIAN(amount) FROM Transaction` |
| MIN | Minimum value | `SELECT MIN(total) FROM Transaction` |
| RANK | Rank with gaps | `SELECT RANK() OVER (ORDER BY score)` |
| ROW_NUMBER | Sequential row number | `SELECT ROW_NUMBER() OVER (ORDER BY date)` |
| SUM | Sum of values | `SELECT SUM(amount) FROM Transaction` |
| CORR | Correlation coefficient | `SELECT CORR(col1, col2)` |
| CORR_K | Kendall correlation | `SELECT CORR_K(col1, col2)` |
| CORR_S | Spearman correlation | `SELECT CORR_S(col1, col2)` |
| COVAR_POP | Population covariance | `SELECT COVAR_POP(col1, col2)` |
| COVAR_SAMP | Sample covariance | `SELECT COVAR_SAMP(col1, col2)` |

## Data Type Conversion Functions

| Function | Description | Example |
|----------|-------------|---------|
| TO_BINARY_DOUBLE | Convert to binary double | `SELECT TO_BINARY_DOUBLE(value)` |
| TO_BINARY_FLOAT | Convert to binary float | `SELECT TO_BINARY_FLOAT(value)` |
| TO_CHAR | Convert to string | `SELECT TO_CHAR(12345)` → '12345' |
| TO_CLOB | Convert to CLOB | `SELECT TO_CLOB(string)` |
| TO_MULTI_BYTE | Convert to multi-byte | `SELECT TO_MULTI_BYTE(string)` |
| TO_NCHAR | Convert to NCHAR | `SELECT TO_NCHAR(value)` |
| TO_NCLOB | Convert to NCLOB | `SELECT TO_NCLOB(string)` |
| TO_NUMBER | Convert to number | `SELECT TO_NUMBER('12345')` → 12345 |
| TO_SINGLE_BYTE | Convert to single-byte | `SELECT TO_SINGLE_BYTE(string)` |

## Other Supported Functions

| Function | Description | Example |
|----------|-------------|---------|
| APPROX_COUNT_DISTINCT | Approximate distinct count | `SELECT APPROX_COUNT_DISTINCT(column)` |
| BFILENAME | Binary file name | `SELECT BFILENAME(dir, filename)` |
| BITAND | Bitwise AND | `SELECT BITAND(5, 3)` → 1 |
| CHARTOROWID | Convert char to ROWID | `SELECT CHARTOROWID(string)` |
| DECODE | Conditional logic | `SELECT DECODE(col, 'A', 1, 'B', 2, 0)` |
| EMPTY_BLOB | Empty BLOB | `SELECT EMPTY_BLOB()` |
| EMPTY_CLOB | Empty CLOB | `SELECT EMPTY_CLOB()` |
| GREATEST | Greatest value | `SELECT GREATEST(10, 20, 5)` → 20 |
| LEAST | Least value | `SELECT LEAST(10, 20, 5)` → 5 |
| NANVL | NaN value substitution | `SELECT NANVL(col, 0)` |
| NLSSORT | Language-specific sort | `SELECT NLSSORT(string)` |
| NULLIF | Return NULL if equal | `SELECT NULLIF(col1, col2)` |
| NVL | NULL value substitution | `SELECT NVL(col, 'default')` |
| NVL2 | Conditional NULL handling | `SELECT NVL2(col, 'not null', 'null')` |
| ORA_HASH | Hash value | `SELECT ORA_HASH(value)` |
| REGEXP_INSTR | Regex position | `SELECT REGEXP_INSTR(string, pattern)` |
| REGEXP_REPLACE | Regex replace | `SELECT REGEXP_REPLACE(string, pattern, replace)` |
| REGEXP_SUBSTR | Regex substring | `SELECT REGEXP_SUBSTR(string, pattern)` |
| VSIZE | Storage size | `SELECT VSIZE(column)` |
| WIDTH_BUCKET | Histogram bucket | `SELECT WIDTH_BUCKET(value, min, max, buckets)` |

## Unsupported Functions

These standard SQL functions are **NOT supported** in SuiteQL. Use the suggested alternatives where available.

| Unsupported Function | Supported Alternative | Notes |
|---------------------|----------------------|-------|
| CEILING | CEIL | Use CEIL instead |
| CHARINDEX | INSTR | Returns position of substring |
| CHAR_LENGTH | LENGTH | String length |
| CHARACTER_LENGTH | LENGTH | String length |
| LCASE | LOWER | Lowercase conversion |
| LEFT | SUBSTR | `LEFT(str, n)` → `SUBSTR(str, 1, n)` |
| RIGHT | SUBSTR | `RIGHT(str, n)` → `SUBSTR(str, LENGTH(str) - n + 1)` |
| LOCATE | INSTR | Find substring position |
| POSITION | INSTR | Find substring position |
| SUBSTRING | SUBSTR | Extract substring |
| UCASE | UPPER | Uppercase conversion |
| BIT_LENGTH | *(no alternative)* | Not supported |
| BIT_XOR_AGG | *(no alternative)* | Not supported |
| CHAR | *(no alternative)* | Use CHR for ASCII |
| CONVERT | TO_CHAR, TO_NUMBER, etc. | Use explicit conversion functions |
| COT | *(no alternative)* | Can calculate as 1/TAN |
| DATEDIFF | MONTHS_BETWEEN, date arithmetic | Use date subtraction or MONTHS_BETWEEN |
| LISTAGG | *(no alternative)* | String aggregation not supported |
| REPEAT | *(no alternative)* | Not supported |

## NetSuite-Specific Functions

### BUILTIN.DF (Display Format)
Converts internal IDs to display text. **Very expensive** - use sparingly.

```sql
-- Returns internal ID (e.g., 3)
SELECT Status FROM Transaction

-- Returns display text (e.g., "Pending Fulfillment")
SELECT BUILTIN.DF(Status) AS status_text FROM Transaction
```

**Performance Impact:**
- Avoid in large result sets
- Don't use in WHERE clauses
- Get IDs first, format only displayed rows

**Example - Good Practice:**
```sql
-- Fast: Get IDs first
SELECT ID, Status, Location
FROM Transaction
WHERE Type = 'SalesOrd'

-- Then format only the displayed rows (e.g., first 10)
-- in application code or second query
```

**Example - Bad Practice:**
```sql
-- Slow: Format everything
SELECT
    ID,
    BUILTIN.DF(Status),
    BUILTIN.DF(Location),
    BUILTIN.DF(Entity)
FROM Transaction
WHERE Type = 'SalesOrd'
```

## Common Workarounds

### String Aggregation (No LISTAGG)
Since LISTAGG is not supported, handle string aggregation in application code:

```sql
-- Instead of: SELECT LISTAGG(name, ', ') FROM table
-- Use: SELECT name FROM table
-- Then join in application code
```

### DATEDIFF Equivalent
Use date arithmetic or MONTHS_BETWEEN:

```sql
-- Days between dates
SELECT date1 - date2 AS days_diff

-- Months between dates
SELECT MONTHS_BETWEEN(date1, date2) AS months_diff

-- Year difference
SELECT FLOOR(MONTHS_BETWEEN(date1, date2) / 12) AS years_diff
```

### LEFT/RIGHT String Functions
Use SUBSTR with LENGTH:

```sql
-- LEFT(string, 5)
SELECT SUBSTR(string, 1, 5)

-- RIGHT(string, 5)
SELECT SUBSTR(string, LENGTH(string) - 4)
```

### CONVERT Alternative
Use specific conversion functions:

```sql
-- Instead of: CONVERT(VARCHAR, number)
SELECT TO_CHAR(number)

-- Instead of: CONVERT(INT, string)
SELECT TO_NUMBER(string)
```

## Best Practices

1. **Test Functions in Sandbox**: Not all Oracle SQL-92 functions are supported - always test
2. **Check Performance**: Some functions (especially BUILTIN.DF) are expensive
3. **Use Native Types**: Prefer TO_DATE, TO_NUMBER over generic conversion
4. **Avoid BUILTIN.DF in Loops**: Get IDs first, format only what's displayed
5. **Handle Aggregation Client-Side**: SuiteQL lacks some aggregation functions
6. **Use ROWNUM for Limits**: Not LIMIT (see table_reference.md)
7. **Prefer Standard SQL**: Stick to documented functions, avoid database-specific extensions

## Additional Resources

- **Official Documentation**: [SuiteQL Supported Built-in Functions](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_158513731864.html)
- **Function Categories**: Mathematical, String, Date/Time, Aggregate, Conversion
- **Important Note**: NetSuite's documentation notes that unsupported function lists are "not exhaustive"

## Testing New Functions

When using a function not explicitly listed here:

1. Test in Sandbox environment first
2. Start with simple example queries
3. Check for performance impact with EXPLAIN PLAN if available
4. Document successful usage for team reference
5. Report unsupported functions to avoid future issues

## Common Mistakes

❌ **Using LIMIT instead of ROWNUM**
```sql
SELECT * FROM customer LIMIT 10  -- WRONG
```

✅ **Correct syntax:**
```sql
SELECT * FROM customer WHERE ROWNUM <= 10  -- CORRECT
```

❌ **Using unsupported functions without alternatives**
```sql
SELECT LISTAGG(name, ', ') FROM items  -- WRONG (not supported)
```

✅ **Handle in application code:**
```sql
SELECT name FROM items  -- CORRECT (aggregate client-side)
```

❌ **Overusing BUILTIN.DF**
```sql
SELECT BUILTIN.DF(every_column) FROM large_table  -- WRONG (slow)
```

✅ **Format only what's needed:**
```sql
SELECT column_ids FROM large_table WHERE ROWNUM <= 10  -- CORRECT
-- Then format those 10 rows
```
