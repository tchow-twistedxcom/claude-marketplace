/*
 * Digest Aggregator — Celigo preMap hook for AI Agent import
 *
 * Accumulates live error data from integration and standalone flow records
 * (enriched by upstream page processors), then merges everything into the
 * summary record for AI processing.
 *
 * Record types (identified by marker fields):
 *   - Integration records (Export 1): have integrationErrors + integrationFlows
 *   - Standalone flow records (Export 3): have isStandaloneFlow + flowErrors
 *   - Summary record (Export 2): has isSummary — triggers merge + AI processing
 *
 * Module-level _liveErrors accumulates across all records in the same job.
 * Only the summary record (last) gets sent to the AI Agent.
 *
 * Deployed via: celigo_api.py scripts update <SCRIPT_ID> --code-file digest_aggregator.js
 * Attached to: AI Agent import preMap hook
 */

// Module-level accumulator — persists across record processing within one job
var _liveErrors = [];

function preMap(options) {
  var result = [];

  for (var i = 0; i < options.data.length; i++) {
    var rec = options.data[i];

    if (rec.isSummary) {
      // ── Summary record from Export 2 (jobs) ──
      // This is the LAST record. Merge accumulated errors and send to AI.
      rec.liveErrors = JSON.stringify(_liveErrors);
      rec.liveErrorsTotal = _liveErrors.reduce(function(sum, e) {
        return sum + e.numError;
      }, 0);
      rec.liveErrorsFlowCount = _liveErrors.length;

      // Count unique integrations
      var intNames = {};
      for (var li = 0; li < _liveErrors.length; li++) {
        intNames[_liveErrors[li].integrationName] = true;
      }
      rec.liveErrorsIntegrationCount = Object.keys(intNames).length;

      _liveErrors = []; // reset for next run
      result.push({ data: rec });

    } else if (rec.isStandaloneFlow) {
      // ── Standalone flow record from Export 3 ──
      // flowErrors comes from PP0.5 response mapping (GET /v1/flows/{id}/errors)
      var standaloneErrors = [];
      try {
        var parsed = JSON.parse(rec.flowErrors || '{}');
        standaloneErrors = parsed.flowErrors || parsed || [];
      } catch (e) {
        standaloneErrors = [];
      }

      var total = 0;
      var lastError = '';
      for (var se = 0; se < standaloneErrors.length; se++) {
        total += (standaloneErrors[se].numError || 0);
        if (standaloneErrors[se].lastErrorAt && standaloneErrors[se].lastErrorAt > lastError) {
          lastError = standaloneErrors[se].lastErrorAt;
        }
      }

      if (total > 0) {
        _liveErrors.push({
          integrationName: 'Standalone',
          flowId: rec._id || rec.flowId || '',
          flowName: rec.name || rec.flowName || '',
          numError: total,
          lastErrorAt: lastError
        });
      }
      result.push({}); // skip AI processing

    } else {
      // ── Integration record from Export 1 ──
      // integrationErrors comes from PP0 response mapping
      // integrationFlows comes from PP1 response mapping
      var errors = [];
      try { errors = JSON.parse(rec.integrationErrors || '[]'); } catch (e) {}
      var flows = [];
      try { flows = JSON.parse(rec.integrationFlows || '[]'); } catch (e) {}

      // Build flowId → name lookup from integration flows
      var nameMap = {};
      for (var f = 0; f < flows.length; f++) {
        if (flows[f]._id) {
          nameMap[flows[f]._id] = flows[f].name;
        }
      }

      // Add flows with errors to accumulator
      var integrationName = rec.name || 'Unknown';
      for (var ie = 0; ie < errors.length; ie++) {
        if (errors[ie].numError > 0) {
          _liveErrors.push({
            integrationName: integrationName,
            flowId: errors[ie]._flowId,
            flowName: nameMap[errors[ie]._flowId] || errors[ie]._flowId,
            numError: errors[ie].numError,
            lastErrorAt: errors[ie].lastErrorAt || ''
          });
        }
      }
      result.push({}); // skip AI processing
    }
  }

  return result;
}
