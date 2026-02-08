---
name: netsuite-execution-logs
description: Query NetSuite script execution logs to debug SuiteScript issues without accessing NetSuite UI. Use this skill when you need to check script logs, debug script errors, find DEBUG entries, or investigate script execution history. Triggers include "script logs", "execution logs", "debug script", "check script errors", "what did the script log", "show me the logs".
---

# NetSuite Script Execution Log Query Skill

## Overview

Query script execution logs from NetSuite via the SuiteAPI gateway. This skill enables debugging SuiteScripts without manually copying logs from the NetSuite UI.

**Authentication is handled automatically** by the NetSuite API Gateway.

**Use this skill when:**
- Debugging SuiteScript issues by checking execution logs
- Finding DEBUG, AUDIT, ERROR, or EMERGENCY log entries
- Filtering logs by script ID, log level, or time range
- Searching for specific log messages by title pattern

## Prerequisites

**NetSuite API Gateway** must be running:
```bash
cd ~/NetSuiteApiGateway
docker compose up -d
```

Verify gateway is running:
```bash
curl http://localhost:3001/health
```

## Quick Start

```bash
# Get DEBUG logs for a specific script from the last hour
python3 scripts/query_execution_logs.py --script customscript_pri_qt_sl_render_query --level DEBUG --hours 1 --account dm --env prod

# Get all ERROR logs from the last 24 hours
python3 scripts/query_execution_logs.py --level ERROR --hours 24 --account dm

# Search for specific log titles
python3 scripts/query_execution_logs.py --title "DEBUG-USER" --hours 1 --account dm --format detailed

# Get logs as JSON for processing
python3 scripts/query_execution_logs.py --hours 1 --account dm --format json
```

## Command Line Options

### Filter Options

| Option | Description | Example |
|--------|-------------|---------|
| `--script <id>` | Filter by script ID | `--script customscript_pri_qt_sl_render_query` |
| `--level <level>` | Filter by log level | `--level DEBUG` |
| `--hours <n>` | Logs from last N hours (default: 24) | `--hours 1` |
| `--title <pattern>` | Filter logs containing pattern | `--title "DEBUG-"` |
| `--limit <n>` | Max results (default: 200) | `--limit 50` |

### Connection Options

| Option | Description | Default |
|--------|-------------|---------|
| `--account <a>` | NetSuite account (dm/dutyman, twx/twistedx) | dutyman |
| `--env <e>` | Environment (prod, sb1, sb2) | production |

### Output Options

| Option | Description |
|--------|-------------|
| `--format table` | ASCII table output (default) |
| `--format json` | JSON output for scripting |
| `--format detailed` | Full log details with detail field |

## Log Levels

| Level | Description |
|-------|-------------|
| DEBUG | Detailed debugging information |
| AUDIT | Audit trail entries |
| ERROR | Error conditions |
| EMERGENCY | Critical errors |

## Common Use Cases

### Debug a Script Issue

```bash
# 1. Get recent DEBUG logs for the script
python3 scripts/query_execution_logs.py \
  --script customscript_pri_qt_sl_render_query \
  --level DEBUG \
  --hours 1 \
  --account dm \
  --format detailed
```

### Find All Errors

```bash
# Get all ERROR and EMERGENCY logs
python3 scripts/query_execution_logs.py --level ERROR --hours 24 --account dm
python3 scripts/query_execution_logs.py --level EMERGENCY --hours 24 --account dm
```

### Search Log Messages

```bash
# Find logs with specific title pattern
python3 scripts/query_execution_logs.py --title "runQueryAsJSON" --hours 2 --account dm
```

### Export Logs for Analysis

```bash
# Export to JSON file
python3 scripts/query_execution_logs.py --hours 24 --account dm --format json > logs.json
```

## Output Examples

### Table Format (default)
```
Date       | Time         | Level      | Script                                   | Title
-----------+--------------+------------+------------------------------------------+--------------------------------------------------
1/14/2026  | 5:30:15 PM   | DEBUG      | PRI Query Renderer - Render Query        | DEBUG-USER
1/14/2026  | 5:30:15 PM   | DEBUG      | PRI Query Renderer - Render Query        | DEBUG-QUERY
```

### Detailed Format
```
================================================================================
Log Entry 1
================================================================================
Date:    1/14/2026
Time:    5:30:15 PM
Level:   DEBUG
Script:  PRI Query Renderer - Render Query
User:    Administrator
Title:   DEBUG-USER
Detail:
  runtime.getCurrentUser(): {"id":5,"role":3,"roleId":"administrator"}
```

## Error Handling

### Gateway Not Running
```
ERROR: Gateway connection error: Connection refused
```
Start the gateway: `cd ~/NetSuiteApiGateway && docker compose up -d`

### Invalid Account
```
ERROR: Invalid account: xyz
```
Use valid account: `dm`/`dutyman` or `twx`/`twistedx`

### No Logs Found
If no logs are returned, try:
- Increasing the `--hours` parameter
- Removing filters to see all logs
- Checking the script has `log.debug()` calls

## Implementation Details

### How Hour-Precision Filtering Works

The `--hours` filter uses a **formula filter** in the saved search, NOT date string operators:

```javascript
// CORRECT: Formula filter for hour-precision
filters.push(search.createFilter({
    name: 'formulanumeric',
    formula: '({today} - {date}) * 24',  // {today} includes current TIME
    operator: search.Operator.LESSTHAN,
    values: hours
}));
```

**Why this works:**
- `{today}` in NetSuite formulas includes the current time (acts like `{now}`)
- Subtracting `{date}` gives difference in days as a decimal
- Multiplying by 24 converts to hours
- `LESSTHAN hours` filters to only recent entries

### Filter Architecture

All filters use `search.createFilter()` objects (NOT array syntax):

```javascript
// Hours filter
filters.push(search.createFilter({
    name: 'formulanumeric',
    formula: '({today} - {date}) * 24',
    operator: search.Operator.LESSTHAN,
    values: hours
}));

// Level filter
filters.push(search.createFilter({
    name: 'type',
    operator: search.Operator.IS,
    values: 'DEBUG'
}));

// Script ID filter (uses join)
filters.push(search.createFilter({
    name: 'scriptid',
    join: 'script',
    operator: search.Operator.IS,
    values: 'CUSTOMSCRIPT_MY_SCRIPT'  // Uppercase!
}));
```

## Gotchas & Troubleshooting

### Critical: What Does NOT Work

| Approach | Why It Fails |
|----------|--------------|
| `time` field filter | **NOT filterable** - only retrievable for display |
| `AFTER`/`BEFORE` operators with datetime strings | Causes `UNEXPECTED_ERROR` on scriptexecutionlog |
| `ONORAFTER` with time component | Ignores time, only filters by date |
| Mixing `createFilter()` with array `'AND'` strings | Causes "Wrong parameter type: filters is expected as Array" |
| `format.Type.DATETIME` formatting | Produces incompatible format for search filters |

### Script ID is Uppercase

NetSuite stores script IDs in uppercase. The endpoint auto-converts to uppercase:
```bash
# Both work (case-insensitive)
--script customscript_suiteapi
--script CUSTOMSCRIPT_SUITEAPI
```

### Filter Objects are Implicitly AND'd

When using `search.createFilter()` objects in an array, they are automatically AND'd together. Do NOT add `'AND'` strings between them.

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `UNEXPECTED_ERROR` | Wrong date format or operator | Use formula filter instead |
| `Wrong parameter type: filters` | Mixed filter styles | Use only `createFilter()` objects |
| `SSS_INVALID_SRCH_COL` | Invalid column name | Check field exists on scriptexecutionlog |
| `time` filter fails | `time` not filterable | Use formula with `{today}` instead |

## Resources

### scripts/query_execution_logs.py
Main query script:
- Calls `executionLogsGet` procedure on SuiteAPI RESTlet
- Multiple output formats (table, json, detailed)
- Flexible filtering by script, level, time, title

### SuiteAPI RESTlet Endpoint
Located at: `NetSuiteBundlet/SDF/Shared Modules/.../suiteapi.restlet.js`
- Function: `executionLogsGet(request)`
- Uses dynamic saved search with formula filters
- Returns: Array of log entry objects

### NetSuite Search References
- [Formula Filters](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_N661053.html)
- [search.createFilter()](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_4345777107.html)
- [Script Execution Logs](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_4375937190.html)
