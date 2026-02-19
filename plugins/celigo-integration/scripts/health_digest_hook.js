/*
 * Health Digest Accumulator — Celigo preSavePage hook (v2)
 *
 * Accumulates job stats across all export pages using a module-level
 * variable (persists across page invocations within the same job),
 * then emits a single summary record on the final page for the AI Agent.
 *
 * NOTE: JS hooks run in a sandboxed environment WITHOUT request() or
 * bearerToken. State API is NOT available. This hook uses in-memory
 * accumulation instead.
 *
 * Deployed via: celigo_api.py scripts update <SCRIPT_ID> --code-file health_digest_hook.js
 * Attached via: celigo_api.py exports update <EXPORT_ID> \
 *               --data '{"hooks":{"preSavePage":{"_scriptId":"<SCRIPT_ID>","function":"preSavePage"}}}'
 */

// Module-level accumulator — persists across page invocations within one job
var _accumulated = null;

function preSavePage(options) {
  // Validate flowId before use
  function sanitizeFlowId(flowId) {
    if (!flowId || typeof flowId !== 'string') return 'unknown';
    var sanitized = flowId.replace(/[^a-zA-Z0-9_-]/g, '');
    return sanitized || 'unknown';
  }

  var PAGE_SIZE = 20; // actual page size (assistant formType ignores URL pageSize param)

  // Initialize accumulator on first page
  if (!_accumulated) {
    _accumulated = {
      totalJobs: 0,
      totalErrors: 0,
      totalSuccesses: 0,
      errorsByFlow: {},
      earliest: null,
      latest: null,
      pagesProcessed: 0,
      flowId: sanitizeFlowId(options._flowId)
    };
  }

  // Accumulate this page's data
  for (var i = 0; i < options.data.length; i++) {
    var job = options.data[i];
    _accumulated.totalJobs++;
    _accumulated.totalErrors += (job.numError || 0);
    _accumulated.totalSuccesses += (job.numSuccess || 0);

    // Track by flow
    var fid = job._flowId || 'unknown';
    if (!_accumulated.errorsByFlow[fid]) {
      _accumulated.errorsByFlow[fid] = { errors: 0, successes: 0 };
    }
    _accumulated.errorsByFlow[fid].errors += (job.numError || 0);
    _accumulated.errorsByFlow[fid].successes += (job.numSuccess || 0);

    // Time range
    if (job.endedAt) {
      if (!_accumulated.earliest || job.endedAt < _accumulated.earliest) _accumulated.earliest = job.endedAt;
      if (!_accumulated.latest || job.endedAt > _accumulated.latest) _accumulated.latest = job.endedAt;
    }
  }
  _accumulated.pagesProcessed++;

  var isLastPage = options.data.length < PAGE_SIZE || options.data.length === 0;

  if (isLastPage) {
    // Final page: build summary, reset accumulator, emit one record
    var stats = _accumulated;
    _accumulated = null; // reset for next job run

    var total = stats.totalErrors + stats.totalSuccesses;
    var errorRate = total > 0
      ? ((stats.totalErrors / total) * 100).toFixed(1)
      : '0.0';

    return {
      data: [{
        totalJobs: stats.totalJobs,
        totalErrors: stats.totalErrors,
        totalSuccesses: stats.totalSuccesses,
        errorRate: errorRate + '%',
        errorsByFlow: JSON.stringify(stats.errorsByFlow),
        timeRange: (stats.earliest || 'N/A') + ' to ' + (stats.latest || 'N/A'),
        pagesProcessed: stats.pagesProcessed,
        generatedAt: new Date().toISOString()
      }],
      errors: options.errors,
      abort: false
    };
  } else {
    // Non-last page: drop records from downstream, keep accumulating
    return {
      data: [],
      errors: options.errors,
      abort: false
    };
  }
}
