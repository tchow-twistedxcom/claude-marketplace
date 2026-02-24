/*
 * Digest Aggregator — Celigo preMap hook for AI Agent import
 *
 * Single-export architecture: all records come from one export (GET /v1/flows),
 * processed through shared PPs, and arrive at this preMap in batch order.
 *
 * Record types (from flow_data_processor.js preSavePage):
 *   - Integration records: _id = integrationId, isIntegration = true
 *     Enriched by PPs: integrationErrors (JSON string from postResponseMap hook),
 *                       integrationName (from response mapping)
 *     flowNameMap provided by preSavePage (JSON string of {flowId: name})
 *   - Standalone records: _id = flowId, isStandaloneFlow = true
 *     Enriched by PPs: flowErrors (JSON string from postResponseMap hook)
 *   - Trigger record: isTrigger = true (ALWAYS LAST)
 *     Merges accumulated _liveErrors and sends to AI
 *
 * Module-level _liveErrors accumulates across all records in the same job.
 * Only the trigger record gets sent to the AI Agent.
 *
 * Deployed via: celigo_api.py scripts update <SCRIPT_ID> --code-file digest_aggregator.js
 * Attached to: AI Agent import preMap hook
 */

// Module-level accumulator — persists across record processing within one job
var _liveErrors = [];

// Response data arrives as JSON strings (from postResponseMap hooks) or native arrays.
function toArray(val) {
  if (!val) return [];
  if (Array.isArray(val)) return val;
  if (typeof val === 'object') return [val];
  if (typeof val === 'string') {
    try { var p = JSON.parse(val); return Array.isArray(p) ? p : (p ? [p] : []); } catch (e) { return []; }
  }
  return [];
}

function toObject(val) {
  if (!val) return {};
  if (typeof val === 'object' && !Array.isArray(val)) return val;
  if (typeof val === 'string') {
    try { return JSON.parse(val); } catch (e) { return {}; }
  }
  return {};
}

function preMap(options) {
  var result = [];

  for (var i = 0; i < options.data.length; i++) {
    var rec = options.data[i];

    if (rec.isTrigger) {
      // ── Trigger record (LAST in batch) ──
      // Merge accumulated errors and send to AI
      var triggerRec = {};
      triggerRec.liveErrors = JSON.stringify(_liveErrors);
      triggerRec.liveErrorsTotal = _liveErrors.reduce(function(sum, e) {
        return sum + e.numError;
      }, 0);
      // Count unique flows (standalone may have multiple step-level entries per flow)
      var uniqueFlows = {};
      for (var uf = 0; uf < _liveErrors.length; uf++) {
        uniqueFlows[_liveErrors[uf].flowId] = true;
      }
      triggerRec.liveErrorsFlowCount = Object.keys(uniqueFlows).length;

      // Count unique integrations
      var intNames = {};
      for (var li = 0; li < _liveErrors.length; li++) {
        intNames[_liveErrors[li].integrationName] = true;
      }
      triggerRec.liveErrorsIntegrationCount = Object.keys(intNames).length;

      // Summary stats from trigger record (set by preSavePage)
      triggerRec.expectedIntegrations = rec.expectedIntegrations || 0;
      triggerRec.expectedStandalones = rec.expectedStandalones || 0;

      _liveErrors = []; // reset for next run
      result.push({ data: triggerRec });

    } else if (rec.isStandaloneFlow) {
      // ── Standalone flow record ──
      // flowErrors from PP1 postResponseMap hook (GET /v1/flows/{id}/errors)
      // JSON string of [{_expOrImpId, numError, lastErrorAt}]
      // Preserve per-step data for step-level buttons at PP4
      var standaloneErrors = toArray(rec.flowErrors);

      for (var se = 0; se < standaloneErrors.length; se++) {
        if ((standaloneErrors[se].numError || 0) > 0) {
          _liveErrors.push({
            integrationName: 'Standalone',
            flowId: rec._id || '',
            flowName: rec.name || '',
            expOrImpId: standaloneErrors[se]._expOrImpId || '',
            numError: standaloneErrors[se].numError,
            lastErrorAt: standaloneErrors[se].lastErrorAt || ''
          });
        }
      }
      result.push({}); // skip AI processing

    } else if (rec.isIntegration) {
      // ── Integration record ──
      // integrationErrors from PP0 postResponseMap hook (GET /v1/integrations/{id}/errors)
      // JSON string of [{_flowId, numError, lastErrorAt}]
      // integrationName from PP2 response mapping (GET /v1/integrations/{id})
      // flowNameMap from preSavePage: JSON string of {flowId: flowName}
      var errors = toArray(rec.integrationErrors);
      var flowNameMap = toObject(rec.flowNameMap);
      var integrationName = rec.integrationName || rec._id || 'Unknown';

      for (var ie = 0; ie < errors.length; ie++) {
        if (errors[ie].numError > 0) {
          _liveErrors.push({
            integrationName: integrationName,
            flowId: errors[ie]._flowId,
            flowName: flowNameMap[errors[ie]._flowId] || errors[ie]._flowId,
            expOrImpId: '',  // Flow-level only for integration flows
            numError: errors[ie].numError,
            lastErrorAt: errors[ie].lastErrorAt || ''
          });
        }
      }
      result.push({}); // skip AI processing

    } else {
      // Unknown record type — skip
      result.push({});
    }
  }

  return result;
}
