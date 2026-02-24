---
module: Celigo Integration
date: 2026-02-23
problem_type: integration_issue
component: tooling
symptoms:
  - "Health Digest Slack message always shows 'Open Errors (0 across 0 flows)' despite 215+ live errors"
  - "PP response mapping extract: '$' silently drops array and object values from records"
  - "PP response mapping 'lists' only captures first array element, not the full array"
root_cause: wrong_api
resolution_type: code_fix
severity: critical
tags: [celigo, response-mapping, postresponsemap, array, health-digest, page-processor]
---

# Troubleshooting: Celigo PP Response Mapping Silently Drops Arrays/Objects

## Problem

Celigo Page Processor (PP) response mappings cannot pass array or complex object values from HTTP API responses into downstream record fields. Using `extract: "$"` in the `fields` section silently drops the data, and using the `lists` section only captures the first element. This caused the Health Digest to always report "0 across 0 flows" despite 215+ live errors existing in the Celigo APIs.

## Environment

- Module: Celigo Integration (Health Digest)
- Platform: Celigo iPaaS (integrator.io API v1)
- Affected Component: Flow A Page Processors (PP0, PP1) response mappings
- Date: 2026-02-23

## Symptoms

- Health Digest Slack messages consistently showed "Open Errors (0 across 0 flows)" across 10+ runs
- Direct API calls confirmed 215+ live errors (44 integration + 171 standalone)
- PP0 (`GET /v1/integrations/{id}/errors`) returned 87 successes but `integrationErrors` field was absent from records
- PP1 (`GET /v1/flows/{id}/errors`) returned 31 successes but `flowErrors` field was absent from records
- PP2 (`GET /v1/integrations/{id}` — scalar `name` extraction) worked correctly, proving PPs were functional
- Debug instrumentation showed `intTotalErrEntries: 0, saTotalErrEntries: 0` in the preMap hook

## What Didn't Work

**Attempted Solution 1:** Response mapping `fields` with `extract: "$"` → `generate: "integrationErrors"`
- **Why it failed:** Celigo's `fields` response mapping silently drops complex values (arrays, objects). Only scalar field extraction works (e.g., `extract: "name"` for a string value). When `extract: "$"` points to an array `[{_flowId, numError}]` or object `{flowErrors: [...]}`, the value is never injected into the record. No error is thrown — the field simply doesn't appear.

**Attempted Solution 2:** Response mapping `lists` with field-level extraction
```json
{
  "lists": [{
    "generate": "integrationErrors",
    "fields": [
      {"extract": "_flowId", "generate": "_flowId"},
      {"extract": "numError", "generate": "numError"},
      {"extract": "lastErrorAt", "generate": "lastErrorAt"}
    ]
  }]
}
```
- **Why it failed:** The `lists` response mapping only captures the **first element** of the array, creating a single-element array regardless of the actual response size. Debug counters showed `intTotalErrEntries: 87` (exactly 1 per integration record) when the API responses contained 2-20+ elements each. Additionally, the first element often had `numError: 0`, hiding all actual errors.

**Attempted Solution 3:** `postResponseMap` hook returning `{data: result}` or `{postResponseMapData: result}`
- **Why it failed:** Error: `invalid_extension_response: Extension result doesn't contain the same number of elements as the request object. Expected 119, got .` Celigo's `postResponseMap` hook expects a **flat array** return, not a wrapped object. Returning `{data: [...]}` causes Celigo to not find the array and report 0 elements.

**Attempted Solution 4:** `postResponseMap` hook modifying existing record objects in-place
- **Why it failed:** The record objects in `options.data` appear to be frozen/sealed. Adding new properties to existing objects silently fails. The modifications don't appear in downstream hooks even though no error is thrown.

## Solution

Created a `postResponseMap` flow hook (`pp_response_capture.js`) that:
1. Creates **entirely new record objects** (avoids frozen object issue)
2. Copies all existing properties from the original records
3. Accesses raw API response via `options.responseData[i]`
4. JSON-stringifies the full response body and injects it as a string field
5. Returns a **flat array** of records (matching input length)

**Hook code (pp_response_capture.js):**
```javascript
function captureIntegrationErrors(options) {
  var data = options.data || options.postResponseMapData || [];
  var result = [];

  for (var i = 0; i < data.length; i++) {
    var original = data[i];
    var newRec = {};

    // Copy all existing properties — MUST create new objects (originals may be frozen)
    if (typeof original === 'object' && original !== null) {
      var source = original.data || original;
      var sourceKeys = Object.keys(source);
      for (var k = 0; k < sourceKeys.length; k++) {
        newRec[sourceKeys[k]] = source[sourceKeys[k]];
      }
    }

    // Inject the full API response as a JSON string
    if (options.responseData && options.responseData[i]) {
      var resp = options.responseData[i];
      var body = resp.data || resp.body || resp._json || resp;
      if (typeof body === 'object') {
        newRec.integrationErrors = JSON.stringify(body);
      } else if (typeof body === 'string') {
        newRec.integrationErrors = body;
      }
    }

    // Preserve original wrapper format
    if (original && typeof original === 'object' && original.data !== undefined) {
      result.push({ data: newRec });
    } else {
      result.push(newRec);
    }
  }

  return result;  // MUST return flat array, NOT {data: [...]}
}
```

**Flow configuration changes:**
```json
// PP0 pageProcessor config:
{
  "responseMapping": {"fields": [], "lists": []},  // Cleared — hook handles injection
  "hooks": {
    "postResponseMap": {
      "_scriptId": "699cdce672bd43b9d78ec568",
      "function": "captureIntegrationErrors"
    }
  }
}
```

**Downstream hook (digest_aggregator.js) — handles JSON string input:**
```javascript
function toArray(val) {
  if (!val) return [];
  if (Array.isArray(val)) return val;
  if (typeof val === 'object') return [val];
  if (typeof val === 'string') {
    try { var p = JSON.parse(val); return Array.isArray(p) ? p : (p ? [p] : []); } catch (e) { return []; }
  }
  return [];
}

// Usage: var errors = toArray(rec.integrationErrors);  // parses JSON string → array
```

## Why This Works

1. **Root cause:** Celigo's response mapping engine is designed for scalar value extraction. When `extract: "$"` encounters an array or object, it silently drops the value (no error, no injection). The `lists` mapping iterates but only keeps one element per record.

2. **Why the hook works:** The `postResponseMap` hook fires AFTER the response mapping step. It has access to `options.responseData` which contains the **raw parsed API response** for each record. By JSON-stringifying the array/object and injecting it as a string field, we bypass the response mapping limitation entirely.

3. **Key implementation details:**
   - Must create NEW record objects (originals are frozen/sealed)
   - Must return a flat array (not `{data: [...]}`), with length matching input
   - `options.responseData[i].data` contains the parsed response body
   - JSON-stringify converts the array to a string that `toArray()` can parse downstream

## Prevention

- **Never use `extract: "$"` for non-scalar responses** in Celigo PP response mappings. It will silently fail.
- **Never rely on `lists` response mapping** for capturing full arrays — it only gets the first element.
- **Always use `postResponseMap` hooks** when you need to pass array/object data from PP API responses to downstream processing.
- **Always create new objects** in `postResponseMap` hooks — don't modify originals in-place.
- **Always return a flat array** from `postResponseMap` hooks matching the input count.
- **Test with debug instrumentation** — Celigo provides no error when response mappings silently fail. Add temporary debug fields to verify data flow.

## Related Issues

- See also: [ai-agent-response-mapping-CeligoIntegration-20260219.md](./ai-agent-response-mapping-CeligoIntegration-20260219.md) — Another response mapping issue where the AI Agent's `_text` field wasn't auto-injected into the pipeline
- See also: [celigo-put-full-replace-CeligoIntegration-20260219.md](./celigo-put-full-replace-CeligoIntegration-20260219.md) — PUT API full-replace behavior that affects flow configuration updates
- See also: [pipeline-field-persistence-premap-vs-export-CeligoIntegration-20260224.md](./pipeline-field-persistence-premap-vs-export-CeligoIntegration-20260224.md) — Pipeline field persistence rules: export-stage fields persist through all PPs, preMap output does not
