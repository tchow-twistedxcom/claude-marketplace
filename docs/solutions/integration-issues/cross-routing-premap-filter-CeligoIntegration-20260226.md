---
module: Celigo Integration
date: 2026-02-26
problem_type: integration_issue
component: tooling
symptoms:
  - "handlebars_template_parse_error: _id not defined in the model (trigger record has no _id)"
  - "404 errors when standalone record _id used as integrationId in URL template"
  - "152+ proceedOnFailure errors per flow run from wrong record types hitting wrong PPs"
  - "PUT /resolved returns 204 but parse errors with retryDataKey persist in error list"
root_cause: config_error
resolution_type: code_fix
severity: high
tags: [celigo, premap, cross-routing, handlebars, record-filter, health-digest, retry-vs-resolve]
---

# Troubleshooting: Celigo Cross-Routing Errors — preMap Record Type Filters

## Problem

The Health Digest flow emits three record types (integration, standalone, trigger) through shared Page Processors, but each PP expects only one type. Without filtering, wrong record types hit wrong PPs — trigger records (no `_id`) cause handlebars URL template parse errors, and standalone `_id` values used as `integrationId` cause 404s. Additionally, once these errors accumulated, the standard `PUT /resolved` API couldn't clear them.

## Environment

- Module: Celigo Integration (Health Digest)
- Platform: Celigo iPaaS (integrator.io API v1)
- Affected Component: Flow `698b4a31ae386aee54914746` — PP0 (integration errors), PP1 (flow errors), PP2 (integration names)
- Date: 2026-02-26

## Symptoms

- `handlebars_template_parse_error`: "Failed to generate request url from template: https://api{{{connection.settings.region}}}integrator.io/v1/integrations/{{{_id}}}/errors. Details: '_id' not defined in the model."
- 404 responses when standalone flow `_id` used in integration API URL templates
- ~152 errors per flow run logged under `proceedOnFailure` across PP0/PP1/PP2
- Stale errors persisted even after `PUT /flows/{flowId}/{expOrImpId}/resolved` returned HTTP 204
- The health digest flow monitored itself and reported its own errors, inflating the error count

## What Didn't Work

**Attempted Solution 1:** Exclude the health digest flow from monitoring itself (`SELF_FLOW_ID` constant in `flow_data_processor.js`)
- **Why it failed:** This was treating the symptom, not the root cause. The errors existed because wrong record types were hitting wrong PPs — excluding the flow from self-monitoring just hid the problem. Monitoring itself is intentionally valuable.

**Attempted Solution 2:** Resolve stale errors via `PUT /flows/{flowId}/{expOrImpId}/resolved` with `{"errorIds": [...]}`
- **Why it failed:** The API returned HTTP 204 (success) but the errors remained in the error list. Parse errors with `retryDataKey` fields are not clearable via the resolve endpoint — the retry data keeps them in an active state.

**Attempted Solution 3:** Blanket resolve via `PUT /flows/{flowId}/{expOrImpId}/resolved` with empty body `{}`
- **Why it failed:** Same result — 204 response but errors persisted. The resolve endpoint simply doesn't work for errors in retry state.

**Attempted Solution 4:** Set preMap hooks on the flow's `pageProcessors[].hooks` via `PUT /v1/flows/{flowId}`
- **Why it failed:** Celigo silently dropped the preMap hooks from the flow-level PUT. The API accepted the payload and returned 200, but the hooks were not attached. preMap hooks must be set on the import resource directly.

## Solution

### Part 1: preMap Record Type Filters (Root Cause Fix)

Created `record_type_filter.js` with two filter functions and attached them as preMap hooks on each import resource:

```javascript
// record_type_filter.js — preMap hooks for PP0, PP1, PP2
// Returning {} from preMap skips the record for that import only —
// the record continues through subsequent PPs unaffected.

function filterIntegrationOnly(options) {
  var result = [];
  for (var i = 0; i < options.data.length; i++) {
    if (options.data[i].isIntegration) {
      result.push({ data: options.data[i] });
    } else {
      result.push({});
    }
  }
  return result;
}

function filterStandaloneOnly(options) {
  var result = [];
  for (var i = 0; i < options.data.length; i++) {
    if (options.data[i].isStandaloneFlow) {
      result.push({ data: options.data[i] });
    } else {
      result.push({});
    }
  }
  return result;
}
```

**Attachment — must be on import resource, NOT flow:**

```bash
# WRONG: Setting preMap on the flow (silently dropped)
# PUT /v1/flows/{flowId} with pageProcessors[0].hooks.preMap = {...}

# CORRECT: Setting preMap on each import resource directly
# PUT /v1/imports/699cc1f2dbb446adf7704298  (PP0 - integration errors)
#   hooks.preMap = { _scriptId: "699fb7ae783ea4efe781991e", function: "filterIntegrationOnly" }
# PUT /v1/imports/699cc1f7dbb446adf77044e3  (PP1 - flow errors)
#   hooks.preMap = { _scriptId: "699fb7ae783ea4efe781991e", function: "filterStandaloneOnly" }
# PUT /v1/imports/699cc1f95c5197579cbf5971  (PP2 - integration names)
#   hooks.preMap = { _scriptId: "699fb7ae783ea4efe781991e", function: "filterIntegrationOnly" }
```

### Part 2: Clearing Stale Errors via Retry (Not Resolve)

After deploying the preMap filters, 8 stale errors remained from previous runs. The resolve API couldn't clear them. The fix was to **retry** the errors — the retry reprocesses the original record through the (now-fixed) pipeline, where the preMap filter returns `{}` to skip it:

```bash
# Collect retryDataKeys from error objects
# POST /v1/flows/{flowId}/{expOrImpId}/retry
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "https://api.integrator.io/v1/flows/$FLOW_ID/$PP0_ID/retry" \
  -d '{"retryDataKeys": ["8c3376b1316945eab65d401eb01c7b79", "1cbb23c2585c4b94864af674c7f83400"]}'

# Result: type=retry, status=completed, numError=0, numIgnore=2
# The preMap filter skipped the records, clearing the errors
```

## Why This Works

1. **Root cause:** The `flow_data_processor.js` preSavePage hook emits three record types through a shared pipeline. Each PP's import has a URL template expecting a specific field (e.g., `{{{_id}}}` for integration/flow ID). The trigger record has no `_id` field, causing handlebars parse errors. Standalone records have flow IDs that are invalid as integration IDs, causing 404s.

2. **Why preMap filters work:** Celigo's preMap hook runs before the import processes each record. Returning `{}` for a record skips that import entirely for that record — the record is NOT consumed or modified, and continues through subsequent PPs unaffected. This is the intended Celigo mechanism for record-type routing in shared pipelines.

3. **Why resolve didn't work but retry did:** Errors with `retryDataKey` have associated retry data stored by Celigo. The resolve endpoint marks errors as resolved but doesn't clear the retry data, so the errors persist in the active error list. Retrying reprocesses the record through the pipeline — if the retry succeeds (or is ignored by preMap), both the error AND retry data are consumed and cleared.

4. **Why preMap hooks must be on import resources:** Celigo's flow-level `pageProcessors[].hooks` only supports `postResponseMap` hooks. `preMap` hooks are a property of the import resource itself (`PUT /v1/imports/{id}`), not the flow's page processor configuration. Setting them via flow PUT is silently ignored.

## Prevention

- **Always use preMap filters** when a pipeline has multiple record types flowing through shared PPs. Don't rely on `proceedOnFailure` alone — it allows errors to accumulate.
- **Set preMap hooks on the import resource** (`PUT /v1/imports/{id}`), never on the flow's `pageProcessors[].hooks`. Verify hooks stuck by reading the import back.
- **Use retry (not resolve) for parse errors** with `retryDataKey`. Check error objects for `retryDataKey` — if present, retry is the correct clearance mechanism.
- **Verify hook attachment after PUT** — Celigo silently drops invalid hook placements. Always `GET` the resource after a PUT to confirm.

## Related Issues

- See also: [pipeline-field-persistence-premap-vs-export-CeligoIntegration-20260224.md](./pipeline-field-persistence-premap-vs-export-CeligoIntegration-20260224.md) — Related preMap behavior: preMap output doesn't persist on pipeline records.
- See also: [celigo-put-full-replace-CeligoIntegration-20260219.md](./celigo-put-full-replace-CeligoIntegration-20260219.md) — Fetch-merge-PUT pattern required for import updates.
