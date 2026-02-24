/*
 * Slack Webhook Parser — Celigo preSavePage hook
 *
 * Parses Slack interactive button payloads received by a webhook export.
 * Slack sends button clicks as application/x-www-form-urlencoded with a
 * `payload` field containing JSON.
 *
 * Input: Raw webhook data with `payload` field
 * Output: Normalized record with flowId, actionType, responseUrlPath, userName
 *
 * Button value format (v2): flowId|expOrImpId|actionType (3-part)
 *   - flowId: Celigo flow ID
 *   - expOrImpId: Specific export/import step ID (may be empty for flow-level)
 *   - actionType: "resolve" or "retry"
 *
 * Legacy format (v1): flowId|actionType (2-part)
 *   - Backward compatible: handler discovers expOrImpIds dynamically when empty
 *
 * The button handler uses expOrImpId directly when present, or discovers via:
 *   GET /flows/{flowId}/errors → { flowErrors: [{ _expOrImpId, numError }] }
 *
 * Deployed via: celigo_api.py scripts update <SCRIPT_ID> --code-file slack_webhook_parser.js
 * Attached to: Webhook export preSavePage hook
 */

function preSavePage(options) {
  var data = options.data;
  var result = [];

  for (var i = 0; i < data.length; i++) {
    var record = data[i];

    // Slack sends the payload as a JSON string in the `payload` field
    var payloadStr = record.payload;
    if (!payloadStr) continue;

    var payload;
    try {
      payload = JSON.parse(payloadStr);
    } catch (e) {
      continue;
    }

    // Extract the first action (button click)
    var action = payload.actions && payload.actions[0];
    if (!action) continue;

    // Parse pipe-delimited value:
    //   v2 (3-part): flowId|expOrImpId|actionType
    //   v1 (2-part): flowId|actionType (legacy, backward compatible)
    var parts = (action.value || '').split('|');
    if (parts.length < 2) continue;

    var responseUrl = payload.response_url || '';
    // Strip base URL — Slack hooks connection has base URI https://hooks.slack.com
    var responseUrlPath = responseUrl.replace('https://hooks.slack.com', '');

    if (parts.length >= 3) {
      // v2: flowId|expOrImpId|actionType
      result.push({
        flowId: parts[0],
        expOrImpId: parts[1],    // Specific step ID (may be empty string for flow-level)
        actionType: parts[2],    // "resolve" or "retry"
        responseUrlPath: responseUrlPath,
        userName: (payload.user && payload.user.name) || 'unknown',
        actionId: action.action_id || ''
      });
    } else {
      // v1 legacy: flowId|actionType
      result.push({
        flowId: parts[0],
        expOrImpId: '',          // Empty — handler discovers dynamically
        actionType: parts[1],    // "resolve" or "retry"
        responseUrlPath: responseUrlPath,
        userName: (payload.user && payload.user.name) || 'unknown',
        actionId: action.action_id || ''
      });
    }
  }

  return {
    data: result,
    errors: options.errors,
    abort: false
  };
}
