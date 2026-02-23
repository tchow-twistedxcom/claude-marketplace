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
 * Button value format: flowId|actionType
 *   - flowId: Celigo flow ID
 *   - actionType: "resolve" or "retry"
 *
 * The button handler flow discovers expOrImpIds dynamically via:
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

    // Parse pipe-delimited value: flowId|actionType
    var parts = (action.value || '').split('|');
    if (parts.length < 2) continue;

    var responseUrl = payload.response_url || '';
    // Strip base URL — Slack hooks connection has base URI https://hooks.slack.com
    var responseUrlPath = responseUrl.replace('https://hooks.slack.com', '');

    result.push({
      flowId: parts[0],
      actionType: parts[1],     // "resolve" or "retry"
      responseUrlPath: responseUrlPath,
      userName: (payload.user && payload.user.name) || 'unknown',
      actionId: action.action_id || ''
    });
  }

  return {
    data: result,
    errors: options.errors,
    abort: false
  };
}
