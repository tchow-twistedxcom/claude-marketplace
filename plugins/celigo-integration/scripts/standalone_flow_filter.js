/*
 * Standalone Flow Filter — Celigo preSavePage hook for Export 3
 *
 * Export 3 fetches GET /v1/flows?pageSize=1000 which returns ALL flows (~691).
 * This hook filters to only standalone flows (no _integrationId) and marks
 * each with isStandaloneFlow: true for downstream PP routing.
 *
 * Standalone flows don't belong to any integration and aren't covered by
 * GET /v1/integrations/{id}/errors. They need separate error checking
 * via GET /v1/flows/{id}/errors (PP0.5).
 *
 * Deployed via: celigo_api.py scripts update <SCRIPT_ID> --code-file standalone_flow_filter.js
 * Attached to: Export 3 preSavePage hook
 */

function preSavePage(options) {
  var standalone = [];

  for (var i = 0; i < options.data.length; i++) {
    var flow = options.data[i];

    // Only keep flows without an integration (standalone)
    if (!flow._integrationId) {
      standalone.push({
        _id: flow._id,
        name: flow.name || '',
        isStandaloneFlow: true
      });
    }
  }

  return {
    data: standalone,
    errors: options.errors,
    abort: false
  };
}
