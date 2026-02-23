/*
 * Block Kit Builder — Celigo preMap hook for Slack import
 *
 * Transforms the AI Agent's mrkdwn summary into Slack Block Kit format
 * with interactive Resolve/Retry buttons placed inline after each error group.
 *
 * APPROACH: Parses error counts directly from the AI Agent's mrkdwn text
 * (e.g., "AI Test: 51 errors") rather than relying on pipeline metadata.
 * This ensures button counts always match what the user sees in the message.
 *
 * STATIC (stable): flowId → display name, text match pattern, and expOrImpIds.
 * These IDs don't change when flows run — only update when integrations are
 * added/restructured in Celigo.
 *
 * Button value format: flowId|expOrImpId|actionType
 *
 * Deployed via: celigo_api.py scripts update <SCRIPT_ID> --code-file block_kit_builder.js
 * Attached to: Slack import preMap hook
 */

function preMap(options) {
  var data = options.data;

  // Stable config: flowId → { name, match, expOrImpIds }
  // match: text pattern to find this flow in the AI summary
  // Only update when integrations are added/restructured in Celigo.
  var FLOW_CONFIG = {
    '698b4a31ae386aee54914746': {
      name: 'AI Test',
      match: 'AI Test',
      expOrImpIds: ['698b4a2e1abec9665997a07b', '699c7192dbb446adf74f7216']
    },
    '620d4059f1262f4959e19e0d': {
      name: 'Bass Pro Shops',
      match: 'Bass Pro',
      expOrImpIds: ['620d41200e97bd3b3b5c94f6']
    },
    '6704473fa2db28ae220b4c28': {
      name: 'Nordstrom',
      match: 'Nordstrom',
      expOrImpIds: ['6704479b1e4a6fe1cca7f78d']
    },
    '66fb1f2c8220d745b1934bbe': {
      name: "Elliott's",
      match: 'Elliott',
      expOrImpIds: ['66fb1f2b8220d745b1934bad']
    },
    '678e6af3e6d4f60a942a2602': {
      name: 'Twisted X',
      match: 'Twisted X',
      expOrImpIds: ['678e6af2c5f9882439c8d504']
    },
    '69850b01ae386aee54527f3a': {
      name: 'Buckle EDI',
      match: 'Buckle',
      expOrImpIds: ['69851f55c0cf4ff918d373e6', '6985230e23e43b3119d0f7e2']
    },
    '5fdab69b86aafd4d0920d584': {
      name: 'Bank File BAI2',
      match: 'Bank File',
      expOrImpIds: ['5fdab6952644264e21a1faf7']
    }
  };

  // Extract error count from text near a match pattern
  // Looks for patterns like "51 errors" or "1 error" near the match string
  function extractErrorCount(text, matchStr) {
    var idx = text.indexOf(matchStr);
    if (idx === -1) return 0;
    // Search in a window around the match for "N error(s)"
    var window = text.substring(idx, Math.min(idx + 200, text.length));
    var match = window.match(/(\d+)\s+(?:open\s+)?error/);
    return match ? parseInt(match[1], 10) : 0;
  }

  var btnIndex = 0;

  function makeButtons(flowId, config, errorCount) {
    var countLabel = errorCount > 0 ? ' (' + errorCount + ')' : '';
    var elements = [];
    for (var e = 0; e < config.expOrImpIds.length; e++) {
      var expOrImpId = config.expOrImpIds[e];
      var suffix = config.expOrImpIds.length > 1 ? ' [' + (e + 1) + '/' + config.expOrImpIds.length + ']' : '';
      elements.push({
        type: 'button',
        text: { type: 'plain_text', text: ':white_check_mark: Resolve ' + config.name + countLabel + suffix, emoji: true },
        action_id: 'resolve_errors_' + btnIndex,
        value: flowId + '|' + expOrImpId + '|resolve',
        style: 'primary'
      });
      elements.push({
        type: 'button',
        text: { type: 'plain_text', text: ':arrows_counterclockwise: Retry ' + config.name + countLabel + suffix, emoji: true },
        action_id: 'retry_errors_' + btnIndex,
        value: flowId + '|' + expOrImpId + '|retry'
      });
      btnIndex++;
    }
    return { type: 'actions', elements: elements };
  }

  var result = [];
  for (var i = 0; i < data.length; i++) {
    var rec = data[i];
    var text = rec.aiSummary || '';
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

      // Check which configured flows are mentioned in this paragraph
      for (var flowId in FLOW_CONFIG) {
        if (!FLOW_CONFIG.hasOwnProperty(flowId)) continue;
        if (usedFlows[flowId]) continue;

        var config = FLOW_CONFIG[flowId];
        if (para.indexOf(config.match) !== -1) {
          var errorCount = extractErrorCount(para, config.match);
          blocks.push(makeButtons(flowId, config, errorCount));
          usedFlows[flowId] = true;
        }
      }
    }

    rec.blocks = JSON.stringify(blocks);
    result.push({ data: rec });
  }

  return result;
}
