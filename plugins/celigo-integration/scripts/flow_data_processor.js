/*
 * Flow Data Processor — Celigo preSavePage hook for the single-export architecture
 *
 * Export fetches GET /v1/flows?pageSize=1000 (all ~691 flows).
 * This hook groups flows by integration and emits three types of records:
 *   1. Integration records: one per unique _integrationId (for PP error/name enrichment)
 *   2. Standalone records: one per flow without _integrationId (for PP flow-error enrichment)
 *   3. Trigger record: last record, triggers AI processing after all data is accumulated
 *
 * The trigger record is ALWAYS emitted LAST to ensure the preMap accumulator
 * has all integration + standalone error data before sending to AI.
 *
 * Deployed via: celigo_api.py scripts update <SCRIPT_ID> --code-file flow_data_processor.js
 * Attached to: Export preSavePage hook
 */

// Module-level accumulators — persist across pages
var _integrations = {}; // { integrationId: { flowNames: { flowId: name } } }
var _standalones = [];  // [ { _id: flowId, name: flowName } ]

function preSavePage(options) {
  var PAGE_SIZE = 1000;

  // Accumulate this page's data
  for (var i = 0; i < options.data.length; i++) {
    var flow = options.data[i];

    if (flow._integrationId) {
      // Integration-linked flow
      if (!_integrations[flow._integrationId]) {
        _integrations[flow._integrationId] = { flowNames: {} };
      }
      _integrations[flow._integrationId].flowNames[flow._id] = flow.name || '';
    } else {
      // Standalone flow (no integration)
      _standalones.push({
        _id: flow._id,
        name: flow.name || ''
      });
    }
  }

  // Check if this is the last page
  var isLastPage = options.data.length < PAGE_SIZE || options.data.length === 0;

  if (!isLastPage) {
    // Non-last page: accumulate only, emit nothing downstream
    return { data: [], errors: options.errors, abort: false };
  }

  // ── Last page: emit all records ──
  var records = [];

  // 1. Integration records (one per unique integration)
  var integrationIds = Object.keys(_integrations);
  for (var ii = 0; ii < integrationIds.length; ii++) {
    records.push({
      _id: integrationIds[ii],
      flowNameMap: JSON.stringify(_integrations[integrationIds[ii]].flowNames),
      isIntegration: true
    });
  }

  // 2. Standalone flow records
  for (var si = 0; si < _standalones.length; si++) {
    records.push({
      _id: _standalones[si]._id,
      name: _standalones[si].name,
      isStandaloneFlow: true
    });
  }

  // 3. Build flowMap for dynamic button generation at PP4
  //    Maps flowId → flowName for ALL flows (integration + standalone).
  //    Persists on the pipeline record through all PPs.
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

  // 4. Trigger record — MUST be last
  records.push({
    isTrigger: true,
    expectedIntegrations: integrationIds.length,
    expectedStandalones: _standalones.length,
    flowMap: JSON.stringify(flowMap)
  });

  // Reset accumulators
  _integrations = {};
  _standalones = [];

  return {
    data: records,
    errors: options.errors,
    abort: false
  };
}
