/*
 * Block Kit Builder — Celigo preMap hook for Slack import
 *
 * Transforms the AI Agent's mrkdwn summary into Slack Block Kit format
 * with interactive Resolve/Retry buttons placed inline after each error group.
 *
 * DYNAMIC: Uses flowMap (flowId → flowName) from the pipeline record to match
 * flow names in the AI text and generate buttons. No static configuration needed.
 * flowMap is set by flow_data_processor.js (export preSavePage) and persists
 * through all PPs on the pipeline record.
 *
 * Button value format: flowId|actionType
 * The button handler discovers expOrImpIds dynamically via GET /flows/{flowId}/errors.
 *
 * Deployed via: celigo_api.py scripts update <SCRIPT_ID> --code-file block_kit_builder.js
 * Attached to: Slack import preMap hook
 */

function preMap(options) {
  var data = options.data;

  // Extract error count from text near a match pattern
  // Looks for patterns like "51 errors" or "1 error" near the match string
  function extractErrorCount(text, matchStr) {
    var idx = text.indexOf(matchStr);
    if (idx === -1) return 0;
    var window = text.substring(idx, Math.min(idx + 200, text.length));
    var match = window.match(/(\d+)\s+(?:open\s+)?error/);
    return match ? parseInt(match[1], 10) : 0;
  }

  var btnIndex = 0;

  var result = [];
  for (var i = 0; i < data.length; i++) {
    var rec = data[i];
    var text = rec.aiSummary || '';

    if (!text) {
      result.push({ data: rec });
      continue;
    }

    // Parse flowMap: {flowId: flowName} — set by flow_data_processor, persists on pipeline
    var flowMap = {};
    if (rec.flowMap) {
      try { flowMap = JSON.parse(rec.flowMap); } catch (e) {}
    }

    // Build entries sorted by name length descending (match longer names first to avoid
    // substring conflicts, e.g., "Bass Pro Shops - Export" before "Bass Pro Shops")
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

        if (para.indexOf(entry.flowName) !== -1) {
          var errorCount = extractErrorCount(para, entry.flowName);
          var countLabel = errorCount > 0 ? ' (' + errorCount + ')' : '';

          // Truncate flow name for button text (Slack limit: 75 chars total)
          var displayName = entry.flowName.length > 30
            ? entry.flowName.substring(0, 27) + '...'
            : entry.flowName;

          paraButtons.push({
            type: 'button',
            text: { type: 'plain_text', text: ':white_check_mark: Resolve ' + displayName + countLabel, emoji: true },
            action_id: 'resolve_errors_' + btnIndex,
            value: entry.flowId + '|resolve',
            style: 'primary'
          });
          paraButtons.push({
            type: 'button',
            text: { type: 'plain_text', text: ':arrows_counterclockwise: Retry ' + displayName + countLabel, emoji: true },
            action_id: 'retry_errors_' + btnIndex,
            value: entry.flowId + '|retry'
          });
          btnIndex++;
          usedFlows[entry.flowId] = true;
        }
      }

      // Add action blocks (max 25 elements per actions block)
      for (var bi = 0; bi < paraButtons.length; bi += 24) {
        blocks.push({ type: 'actions', elements: paraButtons.slice(bi, bi + 24) });
      }
    }

    rec.blocks = JSON.stringify(blocks);
    result.push({ data: rec });
  }

  return result;
}
