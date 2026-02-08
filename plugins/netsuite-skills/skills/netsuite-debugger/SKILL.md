---
name: netsuite-debugger
description: Systematic diagnosis of NetSuite API Gateway connectivity, environment routing, and deployment issues
triggers:
  - "INVALID_RCRD_TYPE"
  - "UNEXPECTED_ERROR"
  - "INSUFFICIENT_PERMISSION"
  - "netsuite error"
  - "netsuite gateway"
  - "environment routing"
  - "multi-tenant"
---

# NetSuite API Gateway Debugger

Systematic troubleshooting for NetSuite multi-tenant API Gateway issues with emphasis on environment routing verification.

## Core Principle

**"Environment routing is infrastructure, not deployment"**

When dealing with multi-tenant gateways:
- ALWAYS verify environment connectivity FIRST
- NEVER assume header routing works without testing
- TRUST user observations about record existence
- TEST environment before investigating deployment

## Multi-Tenant Gateway Architecture

### Overview

The NetSuite API Gateway (`netsuite-api-gateway`) is a **multi-tenant proxy** that routes requests to different NetSuite environments based on HTTP headers.

### Environment Routing

**Header-Based Routing** (CRITICAL):
- **Production**: No header OR `X-NetSuite-Environment: production`
- **Sandbox 2 (SB2)**: `X-NetSuite-Environment: sandbox2`
- **Sandbox 1 (SB1)**: `X-NetSuite-Environment: sandbox1`

⚠️ **WARNING**: Without the proper header, ALL requests default to **PRODUCTION**!

### Gateway Endpoints

```
Gateway URL: http://localhost:3001/api/suiteapi

Required Headers:
- Content-Type: application/json
- Origin: http://localhost:5173 (for CORS)
- X-NetSuite-Environment: sandbox2 (for SB2 routing)
```

## Systematic Debugging Workflow

### Phase 1: Environment Connectivity Test (ALWAYS FIRST)

Before investigating anything else, verify which environment is responding:

```bash
# Test Production (no environment header)
curl -s -X POST "http://localhost:3001/api/suiteapi" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:5173" \
  -d '{"procedure": "queryRun", "query": "SELECT ACCOUNT_ID FROM DUAL"}' \
  | jq -r '.data.records[0].ACCOUNT_ID'

# Test SB2 (with environment header)
curl -s -X POST "http://localhost:3001/api/suiteapi" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:5173" \
  -H "X-NetSuite-Environment: sandbox2" \
  -d '{"procedure": "queryRun", "query": "SELECT ACCOUNT_ID FROM DUAL"}' \
  | jq -r '.data.records[0].ACCOUNT_ID'
```

**Expected Results**:
- Production: `4138030`
- SB2: `4138030-sb2` or `4138030_SB2`

If account IDs are the same, environment routing is NOT working.

### Phase 2: Record Existence Verification

Query NetSuite to check if the record type exists in the target environment:

```bash
curl -s -X POST "http://localhost:3001/api/suiteapi" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:5173" \
  -H "X-NetSuite-Environment: sandbox2" \
  -d '{
    "procedure": "queryRun",
    "query": "SELECT ID, ScriptID, Name FROM CustomRecordType WHERE ScriptID = '\''customrecord_twx_notification_channel'\''"
  }' | jq .
```

**Interpretation**:
- Records found → Deployment is fine, routing may be issue
- No records found → Either deployment issue OR wrong environment

### Phase 3: Header Routing Validation

Test the actual API call that's failing WITH and WITHOUT the environment header:

```bash
# Test record creation WITHOUT header (hits production)
curl -s -X POST "http://localhost:3001/api/suiteapi" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:5173" \
  -d '{
    "procedure": "twxUpsertRecord",
    "action": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_twx_notification_channel",
    "fields": {"name": "Test"}
  }' | jq .

# Test record creation WITH header (hits SB2)
curl -s -X POST "http://localhost:3001/api/suiteapi" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:5173" \
  -H "X-NetSuite-Environment: sandbox2" \
  -d '{
    "procedure": "twxUpsertRecord",
    "action": "twxUpsertRecord",
    "id": null,
    "type": "customrecord_twx_notification_channel",
    "fields": {"name": "Test"}
  }' | jq .
```

### Phase 4: Root Cause Determination

Based on test results, categorize the issue:

1. **Environment Routing Issue**
   - Environment test shows same account ID
   - Record exists in target environment
   - API call fails without header, succeeds with header
   - **Fix**: Add `X-NetSuite-Environment` header

2. **Deployment Issue**
   - Environment test shows correct account ID
   - Record NOT found in target environment
   - API call fails even with correct header
   - **Fix**: Deploy record type to target environment

3. **Permissions Issue**
   - Environment test shows correct account ID
   - Record exists in target environment
   - API call fails with `INSUFFICIENT_PERMISSION`
   - **Fix**: Update role permissions

## Common Error Patterns

### `INVALID_RCRD_TYPE`

**Error Message**: `The record type [CUSTOMRECORD_XXX] is invalid.`

**Likely Causes** (in priority order):
1. ⚠️ **Missing `X-NetSuite-Environment` header** (90% of cases)
2. Record type not deployed to target environment
3. Incorrect record type ScriptID
4. Permissions issue

**Diagnostic Steps**:
1. Verify environment header is set correctly
2. Test environment connectivity
3. Query CustomRecordType in target environment
4. Check deployment status (SDF logs)

**Example**:
```bash
# Quick diagnostic
echo "Testing environment routing..."
curl -s -X POST "http://localhost:3001/api/suiteapi" \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:5173" \
  -H "X-NetSuite-Environment: sandbox2" \
  -d '{"procedure": "queryRun", "query": "SELECT ACCOUNT_ID FROM DUAL"}' \
  | jq -r '.data.records[0].ACCOUNT_ID'
```

### User Says "Records ARE Deployed"

**Response Protocol** (CRITICAL):
1. ✅ Accept user statement as ground truth immediately
2. ❌ Do NOT verify deployment status
3. ✅ Investigate environment routing FIRST
4. ✅ Check API request headers
5. ✅ Test connectivity to target environment

**Why**: User has direct access to NetSuite UI. They can see records. Trust their observation.

**Example Response**:
```
User: "The records ARE in SB2. You're missing something."

✅ CORRECT: "You're absolutely right - if records exist in SB2, then
deployment isn't the issue. Let me investigate environment routing
and verify the API gateway is hitting SB2, not production."

❌ WRONG: "Let me verify the deployment status by checking the SDF files..."
```

## Debugging Checklist

**Before investigating deployment**:
- [ ] Verify `X-NetSuite-Environment` header in API request
- [ ] Test connectivity to target environment
- [ ] Confirm which environment is actually responding
- [ ] Query record existence in that environment

**Before launching parallel agents**:
- [ ] Test single hypothesis with simple query
- [ ] Verify results are unexpected/problematic
- [ ] Ensure hypothesis is specific and testable
- [ ] Only parallelize if hypothesis confirmed

**When user corrects you**:
- [ ] STOP current line of reasoning immediately
- [ ] Explicitly acknowledge their correction
- [ ] Pivot to alternative hypothesis
- [ ] Do NOT re-verify what user confirmed

## Request Format Reference

### Correct Request Format (B2B Dashboard Gateway)

```json
{
  "procedure": "twxUpsertRecord",
  "action": "twxUpsertRecord",
  "id": null,
  "type": "customrecord_twx_notification_channel",
  "fields": {
    "name": "Test Record",
    "custrecord_field1": "value1"
  }
}
```

**Required Headers**:
```bash
-H "Content-Type: application/json"
-H "Origin: http://localhost:5173"
-H "X-NetSuite-Environment: sandbox2"  # For SB2 routing
```

### Common Mistakes

❌ **Missing environment header**:
```bash
curl -X POST "http://localhost:3001/api/suiteapi" \
  -H "Content-Type: application/json" \
  -d '{...}'
# This hits PRODUCTION, not SB2!
```

✅ **Correct with environment header**:
```bash
curl -X POST "http://localhost:3001/api/suiteapi" \
  -H "Content-Type: application/json" \
  -H "X-NetSuite-Environment: sandbox2" \
  -d '{...}'
# This correctly routes to SB2
```

## Quick Diagnostic Script

Use the provided diagnostic script for quick environment verification:

```bash
~/B2bDashboard/scripts/diagnose-netsuite-environment.sh
```

This script:
- Tests production connectivity
- Tests SB2 connectivity
- Compares account IDs
- Reports routing status

## Integration with Other Skills

- Use `sc:troubleshoot` for broader systematic debugging
- Use `netsuite-suiteql` for query execution once environment is verified
- Use `sc:implement` for fixing identified issues

## Success Metrics

**Good Debugging Session**:
- Environment verified in <2 minutes
- Root cause identified in <5 minutes
- Fix applied and tested in <10 minutes total

**Bad Debugging Session** (to avoid):
- 30+ minutes investigating wrong hypothesis
- Ignoring user corrections
- Launching parallel agents without hypothesis testing
- Assuming environment without verification

## Remember

> "When you receive INVALID_RCRD_TYPE with user saying records exist:
> Check environment routing FIRST, not deployment status LAST."
