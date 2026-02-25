/*
 * Dashboard Payload Builder — Celigo preMap hook for Dashboard HTTP Import (PP4)
 *
 * Replaces block_kit_builder.js. Instead of Slack Block Kit, builds a structured
 * JSON payload for POST /api/health/ingest on B2bDashboard.
 *
 * Record processing order at PP4:
 *   integration records → accumulate errors with flow names
 *   standalone records  → accumulate errors with step-level detail
 *   trigger record      → build multi-system health snapshot
 *
 * Output: Single record with flat fields for Celigo HTTP import mapping:
 *   - timestamp (ISO string)
 *   - source ("celigo-orchestrator")
 *   - ai_summary (AI-generated text)
 *   - systems (JSON string of systems object)
 *
 * Systems object structure:
 *   {
 *     celigo: {
 *       status: "healthy"|"warning"|"error",
 *       total_errors: N,
 *       error_flows: N,       // flows with >5 errors
 *       warning_flows: N,     // flows with 1-5 errors
 *       healthy_flows: N,     // flows with 0 errors
 *       errors: [{ integration_name, flow_id, flow_name, exp_or_imp_id,
 *                  step_label, num_error, last_error_at }]
 *     }
 *   }
 *
 * Status determination:
 *   - "error"   if any flow has >5 errors
 *   - "warning" if any flow has 1-5 errors (none above 5)
 *   - "healthy" otherwise
 *
 * Deployed via: celigo_api.py scripts update <SCRIPT_ID> --code-file dashboard_payload_builder.js
 * Attached to: Dashboard HTTP import preMap hook
 */

// Module-level accumulators — persist across records within one job
var _stepNames = {};   // { stepId: stepName } — from future name-resolution enrichment
var _flowErrors = {};  // { flowId: [{ expOrImpId, numError, lastErrorAt }] }
var _intNames = {};    // { flowId: integrationName } — from integration records
var _flowNames = {};   // { flowId: flowName } — from integration and standalone records

// Parse JSON strings from pipeline fields
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

// Generate ordinal step label from flowStepIds for a given step ID.
// Returns "Export", "Import 1", "Import 2", etc. based on position and count.
// Falls back to _stepNames map or truncated ID.
function resolveStepLabel(stepId, flowSteps) {
  if (!stepId) return 'Unknown';

  // Prefer named resolution if available (future enrichment)
  if (_stepNames[stepId]) return _stepNames[stepId];

  if (!flowSteps || flowSteps.length === 0) {
    return stepId.substring(0, 8) + '..';
  }

  // Count exports and imports in this flow
  var exportCount = 0, importCount = 0;
  for (var c = 0; c < flowSteps.length; c++) {
    if (flowSteps[c].type === 'export') exportCount++;
    else importCount++;
  }

  // Find the position of stepId and generate ordinal label
  var expIdx = 0, impIdx = 0;
  for (var s = 0; s < flowSteps.length; s++) {
    if (flowSteps[s].type === 'export') expIdx++;
    else impIdx++;

    if (flowSteps[s].id === stepId) {
      if (flowSteps[s].type === 'export') {
        return exportCount > 1 ? 'Export ' + expIdx : 'Export';
      } else {
        return importCount > 1 ? 'Import ' + impIdx : 'Import';
      }
    }
  }

  // stepId not found in flowSteps — truncated ID fallback
  return stepId.substring(0, 8) + '..';
}

function preMap(options) {
  var data = options.data;
  var result = [];

  for (var i = 0; i < data.length; i++) {
    var rec = data[i];

    // ── stepNameBatch records (from future name-resolution enrichment) ──
    if (rec.isStepNameBatch) {
      var nameMap = toObject(rec.stepNameMap);
      for (var sid in nameMap) {
        if (nameMap.hasOwnProperty(sid)) {
          _stepNames[sid] = nameMap[sid];
        }
      }
      result.push({});
      continue;
    }

    // ── Integration records — accumulate flow-level errors ──
    if (rec.isIntegration) {
      var intErrors = toArray(rec.integrationErrors);
      var flowNameMap = toObject(rec.flowNameMap);
      var integrationName = rec.integrationName || rec._id || 'Unknown';

      // Store flow names and integration names for later resolution
      for (var fnk in flowNameMap) {
        if (flowNameMap.hasOwnProperty(fnk)) {
          _flowNames[fnk] = flowNameMap[fnk];
          _intNames[fnk] = integrationName;
        }
      }

      for (var ie = 0; ie < intErrors.length; ie++) {
        if ((intErrors[ie].numError || 0) > 0) {
          var intFlowId = intErrors[ie]._flowId;
          if (!_flowErrors[intFlowId]) _flowErrors[intFlowId] = [];
          _flowErrors[intFlowId].push({
            expOrImpId: '',
            numError: intErrors[ie].numError,
            lastErrorAt: intErrors[ie].lastErrorAt || ''
          });
        }
      }
      result.push({});
      continue;
    }

    // ── Standalone flow records — accumulate step-level errors ──
    if (rec.isStandaloneFlow) {
      var flowErrs = toArray(rec.flowErrors);
      var sfid = rec._id || '';

      // Store flow name for later resolution
      if (sfid && rec.name) {
        _flowNames[sfid] = rec.name;
        _intNames[sfid] = 'Standalone';
      }

      for (var se = 0; se < flowErrs.length; se++) {
        if ((flowErrs[se].numError || 0) > 0) {
          if (!_flowErrors[sfid]) _flowErrors[sfid] = [];
          _flowErrors[sfid].push({
            expOrImpId: flowErrs[se]._expOrImpId || '',
            numError: flowErrs[se].numError,
            lastErrorAt: flowErrs[se].lastErrorAt || ''
          });
        }
      }
      result.push({});
      continue;
    }

    // ── Trigger record — build the dashboard payload ──
    if (rec.isTrigger || rec.aiSummary) {
      var flowMap = toObject(rec.flowMap);
      var flowStepIds = toObject(rec.flowStepIds);

      // Build per-step error entries with resolved labels
      var celigoErrors = [];
      // Track per-flow total errors for status determination
      var flowTotalErrors = {};  // { flowId: totalNumError }
      var totalErrors = 0;

      var errorFlowIds = Object.keys(_flowErrors);
      for (var ef = 0; ef < errorFlowIds.length; ef++) {
        var fid = errorFlowIds[ef];
        var entries = _flowErrors[fid];
        var steps = flowStepIds[fid] || [];
        var flowName = _flowNames[fid] || flowMap[fid] || fid;
        var intName = _intNames[fid] || 'Unknown';

        // Check if we have per-step data (standalone flows have expOrImpId set)
        var hasStepData = false;
        for (var ed = 0; ed < entries.length; ed++) {
          if (entries[ed].expOrImpId) { hasStepData = true; break; }
        }

        // Calculate flow total for status determination
        var flowSum = 0;
        for (var fs = 0; fs < entries.length; fs++) {
          flowSum += entries[fs].numError || 0;
        }
        flowTotalErrors[fid] = flowSum;
        totalErrors += flowSum;

        if (hasStepData) {
          // ── Standalone: per-step entries with error counts ──
          for (var sd = 0; sd < entries.length; sd++) {
            if (!entries[sd].expOrImpId) continue;
            var stepLabel = resolveStepLabel(entries[sd].expOrImpId, steps);

            celigoErrors.push({
              integration_name: intName,
              flow_id: fid,
              flow_name: flowName,
              exp_or_imp_id: entries[sd].expOrImpId,
              step_label: stepLabel,
              num_error: entries[sd].numError,
              last_error_at: entries[sd].lastErrorAt || ''
            });
          }

        } else {
          // ── Integration / Fallback: flow-level entry ──
          // Integration errors are flow-level (no per-step breakdown from API).
          // Emit a single flow-level entry with the full error count.
          // Step IDs may be available but error attribution is unknown.
          celigoErrors.push({
            integration_name: intName,
            flow_id: fid,
            flow_name: flowName,
            exp_or_imp_id: '',
            step_label: '',
            num_error: flowSum,
            last_error_at: entries[0] ? entries[0].lastErrorAt || '' : ''
          });
        }
      }

      // ── Status determination ──
      // Count flows by severity: >5 errors = "error" flow, 1-5 = "warning" flow
      var errorFlowCount = 0;    // flows with >5 errors
      var warningFlowCount = 0;  // flows with 1-5 errors
      var allFlowIds = Object.keys(flowTotalErrors);

      for (var sc = 0; sc < allFlowIds.length; sc++) {
        var errCount = flowTotalErrors[allFlowIds[sc]];
        if (errCount > 5) {
          errorFlowCount++;
        } else if (errCount > 0) {
          warningFlowCount++;
        }
      }

      var celigoStatus = 'healthy';
      if (errorFlowCount > 0) {
        celigoStatus = 'error';
      } else if (warningFlowCount > 0) {
        celigoStatus = 'warning';
      }

      // Total flows from the canonical flowMap on the trigger record
      var totalFlows = Object.keys(flowMap).length;
      var healthyFlows = Math.max(0, totalFlows - errorFlowCount - warningFlowCount);

      var systems = {
        celigo: {
          status: celigoStatus,
          total_errors: totalErrors,
          error_flows: errorFlowCount,
          warning_flows: warningFlowCount,
          healthy_flows: healthyFlows,
          errors: celigoErrors
        }
      };

      var output = {};
      output.timestamp = new Date().toISOString();
      output.source = 'celigo-orchestrator';
      output.ai_summary = rec.aiSummary || '';
      output.systems = JSON.stringify(systems);

      // Reset accumulators
      _stepNames = {};
      _flowErrors = {};
      _intNames = {};
      _flowNames = {};

      result.push({ data: output });
      continue;
    }

    // Unknown record type — skip
    result.push({});
  }

  return result;
}
