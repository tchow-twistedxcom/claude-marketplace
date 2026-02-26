/*
 * Record Type Filter — Celigo preMap hooks for PP0, PP1, PP2
 *
 * The health digest flow emits three record types through shared PPs:
 *   - Integration records (isIntegration = true, _id = integrationId)
 *   - Standalone records (isStandaloneFlow = true, _id = flowId)
 *   - Trigger record (isTrigger = true, no _id)
 *
 * Without filtering, wrong record types hit wrong PPs causing:
 *   - handlebars_template_parse_error: trigger record has no _id for URL template
 *   - 404: standalone _id used as integrationId (or vice versa)
 *
 * Returning {} from preMap skips the record for that import only —
 * the record continues through subsequent PPs unaffected.
 *
 * Functions:
 *   filterIntegrationOnly — PP0 (integration errors) and PP2 (integration names)
 *   filterStandaloneOnly  — PP1 (flow errors)
 *
 * Deployed via: celigo_api.py scripts update <SCRIPT_ID> --code-file record_type_filter.js
 */

function filterIntegrationOnly(options) {
  var result = [];
  for (var i = 0; i < options.data.length; i++) {
    if (options.data[i].isIntegration) {
      result.push({ data: options.data[i] });
    } else {
      result.push({});
    }
  }
  return result;
}

function filterStandaloneOnly(options) {
  var result = [];
  for (var i = 0; i < options.data.length; i++) {
    if (options.data[i].isStandaloneFlow) {
      result.push({ data: options.data[i] });
    } else {
      result.push({});
    }
  }
  return result;
}
