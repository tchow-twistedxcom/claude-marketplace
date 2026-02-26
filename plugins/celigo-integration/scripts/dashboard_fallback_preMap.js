/**
 * dashboard_fallback_preMap.js
 *
 * PP5 preMap hook — Slack fallback when dashboard is unreachable.
 *
 * Pipeline field gating:
 *   - PP4 (dashboard import) postResponseMap sets _dashboardDelivered = true
 *   - This preMap checks that field: if true, skip (return {}); if false, build minimal Slack alert
 *
 * This works because postResponseMap output persists to downstream PPs
 * (documented in pipeline-field-persistence solution doc).
 *
 * JS hooks are sandboxed — they cannot make HTTP requests or call the Celigo API.
 * This pipeline-field approach is the only viable in-Celigo fallback mechanism.
 *
 * Attached to: PP5 (Slack webhook import, preserved ID 699c7192dbb446adf74f7216)
 * Function: dashboardFallbackPreMap
 */

/*
 * @param options {{
 *   data: Array,
 *   errors: Object,
 *   _exportId: string,
 *   _connectionId: string,
 *   _flowId: string,
 *   _integrationId: string,
 *   settings: Object
 * }}
 */
function dashboardFallbackPreMap(options) {
  var data = options.data;
  var result = [];

  for (var i = 0; i < data.length; i++) {
    var rec = data[i];

    // If dashboard delivery succeeded, skip this record for Slack
    if (rec._dashboardDelivered === true || rec._dashboardDelivered === 'true') {
      result.push({});
      continue;
    }

    // Dashboard was unreachable — build a minimal Slack fallback message
    // This fires only when PP4's postResponseMap did NOT set _dashboardDelivered
    var timestamp = rec.timestamp || new Date().toISOString();
    var aiSummary = rec.aiSummary || rec.ai_summary || '';
    var totalErrors = 0;

    // Try to extract error count from the record
    if (rec._celigoErrorCount !== undefined) {
      totalErrors = parseInt(rec._celigoErrorCount) || 0;
    }

    // Build minimal Slack text (not Block Kit — keep it simple for fallback)
    var text = ':warning: *Health Digest Fallback*\n'
      + '_Dashboard unreachable — sending via direct Slack._\n\n'
      + '*Timestamp:* ' + timestamp + '\n';

    if (totalErrors > 0) {
      text += '*Total Celigo Errors:* ' + totalErrors + '\n';
    }

    if (aiSummary) {
      // Truncate AI summary to 500 chars for fallback
      var summary = aiSummary.length > 500 ? aiSummary.substring(0, 497) + '...' : aiSummary;
      text += '\n*AI Summary:*\n' + summary + '\n';
    }

    text += '\n_Check dashboard status at the server._';

    result.push({
      data: {
        text: text
      }
    });
  }

  return result;
}
