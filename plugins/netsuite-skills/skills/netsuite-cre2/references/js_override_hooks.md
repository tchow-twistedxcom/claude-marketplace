# CRE2 JavaScript Override Hooks

## Overview

CRE2 JS Override hooks allow custom data transformation before template rendering. The hook script is linked to a CRE2 Profile via the `custrecord_pri_cre2_js_override` field.

## CRITICAL: Correct Pattern

The `beforeTranslate` hook is the most common pattern for adding custom data to templates.

### Working Pattern

```javascript
/**
 * @NApiVersion 2.1
 * @NModuleScope Public
 */
define(['N/log'], function(log) {
    'use strict';

    /**
     * beforeTranslate hook - called before FreeMarker template rendering
     *
     * @param {Object} cre2 - CRE2 Engine object
     * @returns {Object} Object available as ${OVERRIDE} in template
     */
    function beforeTranslate(cre2) {
        try {
            // Access data sources loaded by CRE2 queries
            // Pattern: cre2.dataSources.<dataSourceName>.data
            var rows = cre2.dataSources.myQuery.data;

            if (!rows || rows.length === 0) {
                return { myData: { error: 'No data found' } };
            }

            // Transform and return data
            // Returned object becomes ${OVERRIDE} in template
            return {
                myData: {
                    field1: rows[0].column1,
                    field2: rows[0].column2,
                    items: rows
                }
            };

        } catch (e) {
            log.error('beforeTranslate', e.message);
            return { myData: { error: e.message } };
        }
    }

    return {
        beforeTranslate: beforeTranslate
    };
});
```

### Template Access

The returned object is available as `${OVERRIDE}`:

```freemarker
<#if OVERRIDE?? && OVERRIDE.myData??>
    <p>Field 1: ${OVERRIDE.myData.field1!"-"}</p>
    <p>Field 2: ${OVERRIDE.myData.field2!"-"}</p>

    <#list OVERRIDE.myData.items as item>
        <tr><td>${item.column1}</td></tr>
    </#list>
<#else>
    <p>Error: Data not available</p>
</#if>
```

## Data Source Access Patterns

### Correct Pattern
```javascript
// Data sources are in cre2.dataSources
// Each has { data: [...], dataType: '...' }
var ediDataSource = cre2.dataSources.edi;
var rows = ediDataSource.data;  // Array of row objects
var firstRow = rows[0];
var value = firstRow.column_name;
```

### Column Name Variations
```javascript
// SuiteQL aliases may come through lowercase
var value = firstRow.edi_json || firstRow.EDI_JSON || firstRow.custrecord_twx_edi_json;
```

### Available Properties on cre2 Object
```javascript
cre2.recordId        // Target record internal ID
cre2.dataSources     // Object containing all data sources keyed by name
cre2.ROOT            // Root record data (if available)
```

## Common Pitfalls

### 1. Cyclic Reference Error

**WRONG** - Returns the entire cre2 object (causes cyclic reference):
```javascript
function beforeTranslate(cre2) {
    cre2.myData = { ... };
    return cre2;  // ERROR: Cyclic reference!
}
```

**CORRECT** - Return a new plain object:
```javascript
function beforeTranslate(cre2) {
    return {
        myData: { ... }  // Plain object, no cyclic refs
    };
}
```

### 2. Wrong Data Access Pattern

**WRONG** - Using context.data:
```javascript
function beforeTranslate(context) {
    var rows = context.data.myQuery;  // WRONG!
}
```

**CORRECT** - Using cre2.dataSources:
```javascript
function beforeTranslate(cre2) {
    var rows = cre2.dataSources.myQuery.data;  // CORRECT!
}
```

### 3. Null/Undefined Handling

**WRONG** - No null checks:
```javascript
var value = cre2.dataSources.edi.data[0].column;  // Crashes if null!
```

**CORRECT** - Defensive null checks:
```javascript
var ds = cre2.dataSources && cre2.dataSources.edi;
var rows = ds && ds.data;
if (!rows || rows.length === 0) {
    return { edi: createEmptyData() };
}
var value = rows[0].column || '';
```

### 4. Array Iteration with Nulls

**WRONG** - No null check in loop:
```javascript
rawData.items.forEach(function(item) {
    // item might be null!
    result.push(item.value);
});
```

**CORRECT** - Check for null entries:
```javascript
rawData.items.forEach(function(item) {
    if (!item) return;  // Skip null entries
    result.push(item.value || '');
});
```

## JSON Parsing Example

For records with JSON blob fields:

```javascript
function beforeTranslate(cre2) {
    var rows = cre2.dataSources.edi.data;
    if (!rows || rows.length === 0) {
        return { edi: { debugInfo: 'No rows' } };
    }

    // Get JSON string from column
    var jsonStr = rows[0].edi_json;
    if (!jsonStr) {
        return { edi: { debugInfo: 'No JSON data' } };
    }

    // Parse JSON
    var parsed;
    try {
        parsed = JSON.parse(jsonStr);
    } catch (e) {
        return { edi: { debugInfo: 'JSON parse error: ' + e.message } };
    }

    // Transform and return
    return {
        edi: {
            documentNumber: parsed['BIG02 - Document Number'] || '',
            documentDate: formatDate(parsed['BIG01 - Date']),
            lineItems: extractLineItems(parsed),
            debugInfo: ''
        }
    };
}
```

## Linking Hook to Profile

1. Upload JS file to NetSuite File Cabinet
2. Get the file's internal ID
3. Update CRE2 profile:

```bash
# Using netsuite-suiteql skill
python3 update_record.py customrecord_pri_cre2_profile <PROFILE_ID> \
    --field custrecord_pri_cre2_js_override=<FILE_ID> \
    --env sb2
```

## Debugging

### Log Available Data Sources
```javascript
function beforeTranslate(cre2) {
    var dsKeys = cre2.dataSources ? Object.keys(cre2.dataSources) : [];
    log.debug('dataSources', dsKeys.join(', '));

    // Log first row columns
    if (cre2.dataSources.edi && cre2.dataSources.edi.data[0]) {
        var cols = Object.keys(cre2.dataSources.edi.data[0]);
        log.debug('columns', cols.join(', '));
    }
    // ...
}
```

### Check Script Execution Logs
```sql
SELECT id, date, title, detail
FROM scriptexecutionlog
WHERE title LIKE '%beforeTranslate%'
ORDER BY date DESC
```

## Template Debug Block

Add to template for troubleshooting:

```freemarker
<#if OVERRIDE?? && OVERRIDE.edi?? && OVERRIDE.edi.debugInfo?has_content>
<div style="background:#FFF5F5; border:1px dashed red; padding:10px;">
    <strong>Debug:</strong> ${OVERRIDE.edi.debugInfo}
</div>
</#if>
```
