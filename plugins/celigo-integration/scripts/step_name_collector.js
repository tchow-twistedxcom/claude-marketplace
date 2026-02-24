/*
 * Step Name Collector — Celigo preSavePage hook for exports/imports page generators
 *
 * Attached to two HTTP exports that fetch GET /v1/exports and GET /v1/imports.
 * Accumulates {_id: name} across all pages, then emits a single stepNameBatch
 * record on the last page for downstream accumulation by block_kit_builder.
 *
 * These records pass through PP0-PP2 (404 with proceedOnFailure: true),
 * skip at PP3 (digest_aggregator returns {}), and accumulate at PP4.
 *
 * Deployed via: celigo_api.py scripts create --name "step_name_collector" --code-file step_name_collector.js
 * Attached to: Export B (GET /v1/exports) and Export C (GET /v1/imports) preSavePage hooks
 */

// Module-level accumulator — persists across pages within one job
var _stepNames = {};

function preSavePage(options) {
  var PAGE_SIZE = 1000;

  for (var i = 0; i < options.data.length; i++) {
    var item = options.data[i];
    if (item._id && item.name) {
      _stepNames[item._id] = item.name;
    }
  }

  var isLastPage = options.data.length < PAGE_SIZE || options.data.length === 0;

  if (!isLastPage) {
    return { data: [], errors: options.errors, abort: false };
  }

  // Emit a single batch record with all collected names
  var record = {
    isStepNameBatch: true,
    stepNameMap: JSON.stringify(_stepNames)
  };

  _stepNames = {}; // Reset for next run

  return {
    data: [record],
    errors: options.errors,
    abort: false
  };
}
