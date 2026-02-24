/*
 * PP Response Capture — Celigo postResponseMap hook
 *
 * Celigo's response mapping cannot handle array responses or complex values
 * (extract: "$" drops arrays/objects, lists mapping only captures first element).
 * This hook fires AFTER the response mapping and injects the full raw API
 * response as a JSON string field on the record.
 *
 * Three functions for three PPs:
 *   - captureIntegrationErrors: PP0 (GET /v1/integrations/{id}/errors)
 *     Response: [{_flowId, numError, lastErrorAt}]
 *     Injects: integrationErrors (JSON string of the full array)
 *
 *   - captureFlowErrors: PP1 (GET /v1/flows/{id}/errors)
 *     Response: {flowErrors: [{_expOrImpId, numError, lastErrorAt}]}
 *     Injects: flowErrors (JSON string of the flowErrors inner array)
 *
 *   - captureSlackResponse: PP4 (Slack chat.postMessage)
 *     Validates Slack API response body for ok=false errors.
 *     Celigo HTTPImport counts HTTP 200 as success even when Slack returns
 *     {"ok": false, "error": "..."}. This hook throws on API errors.
 *     Skipped records have {ignored: true} in responseData — those are safe.
 *
 * Deployed via: celigo_api.py scripts update <SCRIPT_ID> --code-file pp_response_capture.js
 * Attached to: Flow A pageProcessors[0].hooks.postResponseMap (PP0)
 *              Flow A pageProcessors[1].hooks.postResponseMap (PP1)
 *              Flow A pageProcessors[4].hooks.postResponseMap (PP4)
 */

function captureIntegrationErrors(options) {
  var data = options.data || options.postResponseMapData || [];
  var result = [];

  for (var i = 0; i < data.length; i++) {
    var original = data[i];
    var newRec = {};

    // Copy all existing properties from the original record
    if (typeof original === 'object' && original !== null) {
      var source = original.data || original;
      var sourceKeys = Object.keys(source);
      for (var k = 0; k < sourceKeys.length; k++) {
        newRec[sourceKeys[k]] = source[sourceKeys[k]];
      }
    }

    // Inject the full API response as a JSON string
    if (options.responseData && options.responseData[i]) {
      var resp = options.responseData[i];
      var body = resp.data || resp.body || resp._json || resp;
      if (typeof body === 'object') {
        newRec.integrationErrors = JSON.stringify(body);
      } else if (typeof body === 'string') {
        newRec.integrationErrors = body;
      }
    }

    // Preserve original wrapper format
    if (original && typeof original === 'object' && original.data !== undefined) {
      result.push({ data: newRec });
    } else {
      result.push(newRec);
    }
  }

  return result;
}

function captureSlackResponse(options) {
  var data = options.data || options.postResponseMapData || [];
  var respData = options.responseData || [];
  var result = [];

  for (var i = 0; i < data.length; i++) {
    var original = data[i];
    var newRec = {};

    if (typeof original === 'object' && original !== null) {
      var source = original.data || original;
      var sourceKeys = Object.keys(source);
      for (var k = 0; k < sourceKeys.length; k++) {
        newRec[sourceKeys[k]] = source[sourceKeys[k]];
      }
    }

    // Check Slack response for non-ignored records
    if (respData[i] && !respData[i].ignored) {
      var resp = respData[i];
      var body = resp._json || resp.data || resp;
      if (body && body.ok === false) {
        throw new Error('Slack API error: ' + JSON.stringify(body).substring(0, 500));
      }
    }

    if (original && typeof original === 'object' && original.data !== undefined) {
      result.push({ data: newRec });
    } else {
      result.push(newRec);
    }
  }

  return result;
}

function captureFlowErrors(options) {
  var data = options.data || options.postResponseMapData || [];
  var result = [];

  for (var i = 0; i < data.length; i++) {
    var original = data[i];
    var newRec = {};

    if (typeof original === 'object' && original !== null) {
      var source = original.data || original;
      var sourceKeys = Object.keys(source);
      for (var k = 0; k < sourceKeys.length; k++) {
        newRec[sourceKeys[k]] = source[sourceKeys[k]];
      }
    }

    // Extract the flowErrors inner array from the response
    if (options.responseData && options.responseData[i]) {
      var resp = options.responseData[i];
      var body = resp.data || resp.body || resp._json || resp;
      if (typeof body === 'object' && body.flowErrors) {
        newRec.flowErrors = JSON.stringify(body.flowErrors);
      } else if (typeof body === 'object') {
        newRec.flowErrors = JSON.stringify(body);
      } else if (typeof body === 'string') {
        newRec.flowErrors = body;
      }
    }

    if (original && typeof original === 'object' && original.data !== undefined) {
      result.push({ data: newRec });
    } else {
      result.push(newRec);
    }
  }

  return result;
}
