---
module: Celigo Integration
date: 2026-02-24
problem_type: integration_issue
component: tooling
symptoms:
  - "Standalone flows missing Resolve/Retry buttons in Slack Health Digest messages"
  - "preMap hook output data not available at subsequent Page Processors"
  - "Module-level variables not shared between preMap and postResponseMap hooks in the same script"
root_cause: config_error
resolution_type: code_fix
severity: high
tags: [celigo, pipeline, persistence, premap, presavepage, flowmap, buttons, health-digest]
---

# Troubleshooting: Celigo Pipeline Field Persistence — preMap Output vs Export-Stage Fields

## Problem

Data set by a Page Processor's preMap hook does NOT persist on the pipeline record for subsequent PPs. Only the current PP's import consumes the preMap output. This caused standalone flows to have no Resolve/Retry buttons in the Health Digest Slack message because the button metadata (flowId → flowName mapping) was set in the AI Agent's preMap hook (PP3) but was unavailable at the Slack import's preMap hook (PP4).

## Environment

- Module: Celigo Integration (Health Digest)
- Platform: Celigo iPaaS (integrator.io API v1)
- Affected Component: Flow A — PP3 (AI Agent import) preMap hook, PP4 (Slack import) preMap hook
- Date: 2026-02-24

## Symptoms

- Integration flows (Bass Pro, Nordstrom, Elliott's, etc.) had Resolve/Retry buttons via static configuration, but standalone flows (Health Digest Monitor, Button Handler) had NO buttons
- Debug instrumentation on PP4 record showed: `recKeys=isTrigger,expectedIntegrations,expectedStandalones,integrationErrors,flowErrors,aiSummary` — no `liveErrors` field despite being set in PP3's preMap
- Module-level variables (`_savedLiveErrors`) set in preMap were empty string in postResponseMap, even when both functions were in the same script file
- For AI Agent imports specifically, `options.data` is `null` in postResponseMap — data is in `options.postResponseMapData` instead

## What Didn't Work

**Attempted Solution 1:** Set `liveErrors` on the trigger record in digest_aggregator's preMap (PP3) and read it in block_kit_builder's preMap (PP4)
- **Why it failed:** preMap transforms the record for the CURRENT import only. The output is consumed by the AI Agent import and does NOT persist on the pipeline record. PP4 never sees `liveErrors`.

**Attempted Solution 2:** Use `postResponseMap` on PP3 to inject data after the AI Agent processes it
- **Why it failed:** Two cascading issues: (1) For AI Agent imports, `options.data` is `null` — the data is in `options.postResponseMapData` instead. (2) Even after fixing the data source, module-level variables set in preMap are NOT shared with postResponseMap. Each hook function gets its own module scope, even when defined in the same script file.

**Attempted Solution 3:** Have the AI Agent echo back button metadata (BUTTONS line) in its response text
- **Why it failed:** The AI reliably echoed the `BUTTONS:` prefix, but the `buttonMetadata` field was empty. The `expOrImpIds` collection in the digest_aggregator wasn't working because `flowErrors` data on standalone records at preMap time needed different parsing. Additionally, relying on the AI to echo structured data is inherently fragile.

**Attempted Solution 4:** Static `FLOW_CONFIG` in block_kit_builder with hardcoded flowId → name/expOrImpIds mappings
- **Why it failed:** Worked technically, but user explicitly rejected this approach — it requires manual updates whenever integrations are added/restructured and is not dynamic.

## Solution

Set the flowId → flowName mapping (`flowMap`) on the trigger record at the **export stage** (preSavePage hook in `flow_data_processor.js`), not at a PP's preMap stage. Fields set by the export's preSavePage persist on the pipeline record through ALL Page Processors.

**Code change 1 — `flow_data_processor.js` (export preSavePage):**
```javascript
// Build flowMap for dynamic button generation at PP4
// Maps flowId → flowName for ALL flows (integration + standalone).
// Persists on the pipeline record through all PPs.
var flowMap = {};
for (var fi = 0; fi < integrationIds.length; fi++) {
  var intFlows = _integrations[integrationIds[fi]].flowNames;
  for (var fid in intFlows) {
    if (intFlows.hasOwnProperty(fid)) {
      flowMap[fid] = intFlows[fid];
    }
  }
}
for (var sfi = 0; sfi < _standalones.length; sfi++) {
  flowMap[_standalones[sfi]._id] = _standalones[sfi].name;
}

// Trigger record — flowMap persists through PP0→PP1→PP2→PP3→PP4
records.push({
  isTrigger: true,
  expectedIntegrations: integrationIds.length,
  expectedStandalones: _standalones.length,
  flowMap: JSON.stringify(flowMap)
});
```

**Code change 2 — `block_kit_builder.js` (Slack import preMap):**
```javascript
// Parse flowMap from pipeline record — set by flow_data_processor, persists through all PPs
var flowMap = {};
if (rec.flowMap) {
  try { flowMap = JSON.parse(rec.flowMap); } catch (e) {}
}

// Build entries sorted by name length descending (avoid substring conflicts)
var flowEntries = [];
for (var fid in flowMap) {
  if (flowMap.hasOwnProperty(fid)) {
    flowEntries.push({ flowId: fid, flowName: flowMap[fid] });
  }
}
flowEntries.sort(function(a, b) { return b.flowName.length - a.flowName.length; });

// Match flow names in AI text → generate dynamic Resolve/Retry buttons
// Button value: flowId|actionType (handler discovers expOrImpIds dynamically)
if (para.indexOf(entry.flowName) !== -1) {
  paraButtons.push({
    type: 'button',
    text: { type: 'plain_text', text: ':white_check_mark: Resolve ' + displayName + countLabel, emoji: true },
    action_id: 'resolve_errors_' + btnIndex,
    value: entry.flowId + '|resolve',
    style: 'primary'
  });
}
```

## Why This Works

1. **Root cause:** Celigo's pipeline has three distinct persistence layers:
   - **Export-stage fields** (preSavePage output): Persist on the pipeline record through ALL subsequent Page Processors. This is the foundational record.
   - **postResponseMap/responseMapping additions**: ADD fields to the pipeline record after each PP processes. These also persist downstream.
   - **preMap output**: Consumed ONLY by the current PP's import. Does NOT persist. The preMap transforms the record specifically for that import's processing.

2. **Why the solution works:** By setting `flowMap` at the export stage (flow_data_processor's preSavePage), the field becomes part of the foundational pipeline record. It persists through PP0 (integration errors), PP1 (flow errors), PP2 (integration names), PP3 (AI Agent), and arrives intact at PP4 (Slack) where block_kit_builder reads it.

3. **Additional discovery — module scope isolation:** Even within the same script file, preMap and postResponseMap functions do NOT share module-level variables. Each hook function gets its own isolated execution context. This means you cannot accumulate data in preMap and read it in postResponseMap.

4. **AI Agent import specifics:** For AI Agent imports (unlike HTTP imports), `options.data` is `null` in postResponseMap. The data is in `options.postResponseMapData` instead. The count for `options.postResponseMapData` matches `options.responseData`.

## Prevention

- **Set pipeline-wide data at the export stage** (preSavePage), never in a PP's preMap hook. Export-stage fields are the only ones guaranteed to persist through ALL PPs.
- **Use postResponseMap or responseMapping to ADD fields** to the pipeline record at individual PPs. These additions persist downstream.
- **Never rely on preMap output persisting** to subsequent PPs. PreMap is a transformation layer for the current import only.
- **Never share data between preMap and postResponseMap** via module-level variables. They have separate execution scopes.
- **For AI Agent imports:** Always check for `options.postResponseMapData` instead of `options.data` in postResponseMap hooks.

### Pipeline Persistence Reference

```
┌─────────────────────────────────────────────────────────┐
│ Export preSavePage                                       │
│   Sets: isTrigger, flowMap, expectedIntegrations, etc.  │
│   PERSISTS through all PPs ✓                            │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│ PP0 postResponseMap → adds integrationErrors            │
│   PERSISTS downstream ✓                                 │
│ PP0 preMap output → consumed by PP0 import ONLY ✗       │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│ PP3 preMap (digest_aggregator) → consumed by AI Agent   │
│   liveErrors, liveErrorsTotal → NOT on pipeline ✗       │
│ PP3 responseMapping → adds aiSummary                    │
│   PERSISTS downstream ✓                                 │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│ PP4 preMap (block_kit_builder) → reads flowMap ✓        │
│   Has: isTrigger, flowMap, integrationErrors,           │
│        flowErrors, integrationName, aiSummary           │
└─────────────────────────────────────────────────────────┘
```

## Related Issues

- See also: [response-mapping-array-drop-CeligoIntegration-20260223.md](./response-mapping-array-drop-CeligoIntegration-20260223.md) — Response mapping limitations that led to the postResponseMap approach for capturing array data. The postResponseMap additions DO persist on the pipeline, unlike preMap output.
- See also: [ai-agent-response-mapping-CeligoIntegration-20260219.md](./ai-agent-response-mapping-CeligoIntegration-20260219.md) — AI Agent `_text` response mapping to `aiSummary` field, which is an example of responseMapping additions that persist downstream.
- See also: [cross-routing-premap-filter-CeligoIntegration-20260226.md](./cross-routing-premap-filter-CeligoIntegration-20260226.md) — preMap `{}` skip for record-type routing. Also documents that preMap hooks must be set on import resources, not flow-level PUT.
