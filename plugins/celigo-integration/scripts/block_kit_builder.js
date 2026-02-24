/*
 * Block Kit Builder — Celigo preMap hook for Slack import (PP4)
 *
 * Transforms the AI Agent's mrkdwn summary into Slack Block Kit format
 * with interactive Resolve/Retry buttons placed inline after each error group.
 *
 * DYNAMIC: Uses module-level accumulators to collect error details from
 * pipeline records arriving before the trigger record.
 *
 * Record processing order at PP4:
 *   integration records → accumulate _flowErrors (flow-level)
 *   standalone records → accumulate _flowErrors (step-level with expOrImpId)
 *   trigger record → generate per-step buttons using accumulated data
 *
 * Step name resolution: Uses ordinal labels derived from flowStepIds
 * (e.g., "Export", "Import 1", "Import 2"). Falls back to _stepNames map
 * if populated by future name-resolution enrichment.
 *
 * Button value format: flowId|expOrImpId|actionType (3-part)
 *   - expOrImpId may be empty for flow-level fallback: flowId||actionType
 *
 * Button text format (uses › not > to avoid Celigo HTML-encoding corruption):
 *   - Standalone (step-level): ":white_check_mark: Resolve FlowName › Import 2 (N)"
 *   - Integration (step-level, no count): ":white_check_mark: Resolve FlowName › Export"
 *   - Fallback (no step data): ":white_check_mark: Resolve FlowName (N)"
 *
 * Deployed via: celigo_api.py scripts update <SCRIPT_ID> --code-file block_kit_builder.js
 * Attached to: Slack import preMap hook
 */

// Module-level accumulators — persist across records within one job
var _stepNames = {};   // { stepId: stepName } — from future name-resolution enrichment
var _flowErrors = {};  // { flowId: [{ expOrImpId, numError }] } — from pipeline records

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

// Truncate "FlowName › StepLabel (N)" to fit Slack's 75-char button text limit
// Longest prefix: ":arrows_counterclockwise: Retry " = 32 chars → 43 chars remaining
// NOTE: Uses › (U+203A) not > to avoid Celigo HTTP connector HTML-encoding
// the > character inside the blocks JSON string, which corrupts the payload.
function truncateButtonText(flowName, stepLabel, errorCount) {
  var countSuffix = errorCount > 0 ? ' (' + errorCount + ')' : '';
  var separator = ' \u203A ';
  var MAX = 43; // 75 - 32 (longest prefix)

  var full = flowName + separator + stepLabel + countSuffix;
  if (full.length <= MAX) return full;

  // Step labels are short (e.g., "Import 2"), so prioritize truncating flowName
  var fixedLen = separator.length + countSuffix.length + stepLabel.length;
  var flowMax = MAX - fixedLen;

  if (flowMax < 6) {
    // Both names need truncation
    var nameSpace = MAX - separator.length - countSuffix.length;
    var half = Math.floor(nameSpace / 2);
    var f = flowName.length > half ? flowName.substring(0, half - 2) + '..' : flowName;
    var s = stepLabel.length > (nameSpace - f.length)
      ? stepLabel.substring(0, nameSpace - f.length - 2) + '..'
      : stepLabel;
    return f + separator + s + countSuffix;
  }

  var truncFlow = flowName.length > flowMax
    ? flowName.substring(0, flowMax - 2) + '..'
    : flowName;

  return truncFlow + separator + stepLabel + countSuffix;
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
      result.push({}); // Skip Slack processing
      continue;
    }

    // ── Integration records — accumulate flow-level errors ──
    if (rec.isIntegration) {
      var intErrors = toArray(rec.integrationErrors);
      for (var ie = 0; ie < intErrors.length; ie++) {
        if ((intErrors[ie].numError || 0) > 0) {
          var intFlowId = intErrors[ie]._flowId;
          if (!_flowErrors[intFlowId]) _flowErrors[intFlowId] = [];
          _flowErrors[intFlowId].push({
            expOrImpId: '',
            numError: intErrors[ie].numError
          });
        }
      }
      result.push({}); // Skip Slack processing
      continue;
    }

    // ── Standalone flow records — accumulate step-level errors ──
    if (rec.isStandaloneFlow) {
      var flowErrs = toArray(rec.flowErrors);
      var sfid = rec._id || '';
      for (var se = 0; se < flowErrs.length; se++) {
        if ((flowErrs[se].numError || 0) > 0) {
          if (!_flowErrors[sfid]) _flowErrors[sfid] = [];
          _flowErrors[sfid].push({
            expOrImpId: flowErrs[se]._expOrImpId || '',
            numError: flowErrs[se].numError
          });
        }
      }
      result.push({}); // Skip Slack processing
      continue;
    }

    // ── Trigger record (with AI summary) ──
    var text = rec.aiSummary || '';
    if (!text) {
      result.push({ data: rec });
      continue;
    }

    // Parse maps from trigger record
    var flowMap = toObject(rec.flowMap);
    var flowStepIds = toObject(rec.flowStepIds);

    // Build flow entries sorted by name length descending (match longer names first
    // to avoid substring conflicts, e.g., "Bass Pro Shops - Export" before "Bass Pro Shops")
    var flowEntries = [];
    for (var fid in flowMap) {
      if (flowMap.hasOwnProperty(fid)) {
        flowEntries.push({ flowId: fid, flowName: flowMap[fid] });
      }
    }
    flowEntries.sort(function(a, b) { return b.flowName.length - a.flowName.length; });

    var blocks = [];
    var paragraphs = text.split('\n\n');
    var usedFlows = {};
    var btnIndex = 0;

    for (var p = 0; p < paragraphs.length; p++) {
      var para = paragraphs[p];
      if (!para.trim()) continue;

      // Add section block (respect 3000 char Block Kit limit)
      if (para.length <= 3000) {
        blocks.push({ type: 'section', text: { type: 'mrkdwn', text: para } });
      } else {
        var lines = para.split('\n');
        var chunk = '';
        for (var l = 0; l < lines.length; l++) {
          if ((chunk + '\n' + lines[l]).length > 2900 && chunk.length > 0) {
            blocks.push({ type: 'section', text: { type: 'mrkdwn', text: chunk } });
            chunk = lines[l];
          } else {
            chunk = chunk ? chunk + '\n' + lines[l] : lines[l];
          }
        }
        if (chunk) {
          blocks.push({ type: 'section', text: { type: 'mrkdwn', text: chunk } });
        }
      }

      // Find flows mentioned in this paragraph and generate buttons
      var paraButtons = [];
      for (var fe = 0; fe < flowEntries.length; fe++) {
        var entry = flowEntries[fe];
        if (usedFlows[entry.flowId]) continue;
        if (para.indexOf(entry.flowName) === -1) continue;

        usedFlows[entry.flowId] = true;
        var entries = _flowErrors[entry.flowId] || [];
        var steps = flowStepIds[entry.flowId] || [];

        if (entries.length === 0) continue; // No errors → no buttons

        // Check if we have per-step data (standalone flows have expOrImpId set)
        var hasStepData = false;
        for (var ed = 0; ed < entries.length; ed++) {
          if (entries[ed].expOrImpId) { hasStepData = true; break; }
        }

        if (hasStepData) {
          // ── Standalone: per-step buttons with error counts ──
          for (var sd = 0; sd < entries.length; sd++) {
            if (!entries[sd].expOrImpId) continue;
            var stepLabel = resolveStepLabel(entries[sd].expOrImpId, steps);
            var btnText = truncateButtonText(entry.flowName, stepLabel, entries[sd].numError);

            paraButtons.push({
              type: 'button',
              text: { type: 'plain_text', text: ':white_check_mark: Resolve ' + btnText, emoji: true },
              action_id: 'resolve_errors_' + btnIndex,
              value: entry.flowId + '|' + entries[sd].expOrImpId + '|resolve',
              style: 'primary'
            });
            paraButtons.push({
              type: 'button',
              text: { type: 'plain_text', text: ':arrows_counterclockwise: Retry ' + btnText, emoji: true },
              action_id: 'retry_errors_' + btnIndex,
              value: entry.flowId + '|' + entries[sd].expOrImpId + '|retry'
            });
            btnIndex++;
          }

        } else if (steps.length > 0) {
          // ── Integration: per-step buttons without error counts ──
          for (var st = 0; st < steps.length; st++) {
            var sLabel = resolveStepLabel(steps[st].id, steps);
            var sBtnText = truncateButtonText(entry.flowName, sLabel, 0);

            paraButtons.push({
              type: 'button',
              text: { type: 'plain_text', text: ':white_check_mark: Resolve ' + sBtnText, emoji: true },
              action_id: 'resolve_errors_' + btnIndex,
              value: entry.flowId + '|' + steps[st].id + '|resolve',
              style: 'primary'
            });
            paraButtons.push({
              type: 'button',
              text: { type: 'plain_text', text: ':arrows_counterclockwise: Retry ' + sBtnText, emoji: true },
              action_id: 'retry_errors_' + btnIndex,
              value: entry.flowId + '|' + steps[st].id + '|retry'
            });
            btnIndex++;
          }

        } else {
          // ── Fallback: flow-level buttons (no step data available) ──
          var totalErrors = 0;
          for (var te = 0; te < entries.length; te++) {
            totalErrors += entries[te].numError;
          }
          var countLabel = totalErrors > 0 ? ' (' + totalErrors + ')' : '';
          var displayName = entry.flowName.length > 30
            ? entry.flowName.substring(0, 27) + '...'
            : entry.flowName;

          paraButtons.push({
            type: 'button',
            text: { type: 'plain_text', text: ':white_check_mark: Resolve ' + displayName + countLabel, emoji: true },
            action_id: 'resolve_errors_' + btnIndex,
            value: entry.flowId + '||resolve',
            style: 'primary'
          });
          paraButtons.push({
            type: 'button',
            text: { type: 'plain_text', text: ':arrows_counterclockwise: Retry ' + displayName + countLabel, emoji: true },
            action_id: 'retry_errors_' + btnIndex,
            value: entry.flowId + '||retry'
          });
          btnIndex++;
        }
      }

      // Add action blocks (max 25 elements per actions block)
      for (var bi = 0; bi < paraButtons.length; bi += 24) {
        blocks.push({ type: 'actions', elements: paraButtons.slice(bi, bi + 24) });
      }
    }

    rec.blocks = JSON.stringify(blocks);
    // text field serves as notification fallback (Slack renders blocks, not text)
    rec.aiSummary = text;

    // Reset accumulators
    _stepNames = {};
    _flowErrors = {};

    result.push({ data: rec });
  }

  return result;
}
