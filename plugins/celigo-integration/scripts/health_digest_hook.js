/*
 * Health Digest Accumulator — Celigo preSavePage hook
 *
 * Accumulates job stats across all export pages using the State API,
 * then emits a single summary record on the final page for the AI Agent
 * to turn into an executive health digest.
 *
 * Deployed via: celigo_api.py scripts create --name "Health Digest Accumulator" \
 *               --function preSavePage --code-file health_digest_hook.js
 *
 * Attached via: celigo_api.py exports update <EXPORT_ID> \
 *               --data '{"hooks":{"preSavePage":{"_scriptId":"<SCRIPT_ID>"}}}'
 */
function preSavePage(options) {
  var PAGE_SIZE = 20; // match export config — adjust if export pageSize changes
  var STATE_KEY = 'health_digest_' + options._flowId;
  var MAX_PAGES = 200;
  var STALE_THRESHOLD_MS = 3600000; // 1 hour

  // Helper: call State API via global request() + bearerToken
  function getState() {
    try {
      var resp = request({
        method: 'GET',
        relativeURI: 'v1/state/' + STATE_KEY,
        headers: { Authorization: 'Bearer ' + options.bearerToken }
      });
      if (resp.statusCode === 200) {
        return JSON.parse(resp.body);
      }
    } catch (e) { /* no state yet */ }
    return null;
  }

  function putState(value) {
    request({
      method: 'PUT',
      relativeURI: 'v1/state/' + STATE_KEY,
      headers: {
        Authorization: 'Bearer ' + options.bearerToken,
        'Content-Type': 'application/json'
      },
      body: value
    });
  }

  function deleteState() {
    try {
      request({
        method: 'DELETE',
        relativeURI: 'v1/state/' + STATE_KEY,
        headers: { Authorization: 'Bearer ' + options.bearerToken }
      });
    } catch (e) { /* ok if missing */ }
  }

  // Accumulate stats from this page
  function accumulatePage(data, existing) {
    var stats = existing || {
      totalJobs: 0, totalErrors: 0, totalSuccesses: 0,
      errorsByFlow: {}, topErrors: {},
      earliest: null, latest: null,
      startedAt: new Date().toISOString(),
      pagesProcessed: 0
    };

    for (var i = 0; i < data.length; i++) {
      var job = data[i];
      stats.totalJobs++;
      stats.totalErrors += (job.numError || 0);
      stats.totalSuccesses += (job.numSuccess || 0);

      // Track by flow
      var fid = job._flowId || 'unknown';
      if (!stats.errorsByFlow[fid]) {
        stats.errorsByFlow[fid] = { errors: 0, successes: 0 };
      }
      stats.errorsByFlow[fid].errors += (job.numError || 0);
      stats.errorsByFlow[fid].successes += (job.numSuccess || 0);

      // Time range
      if (job.endedAt) {
        if (!stats.earliest || job.endedAt < stats.earliest) stats.earliest = job.endedAt;
        if (!stats.latest || job.endedAt > stats.latest) stats.latest = job.endedAt;
      }
    }
    stats.pagesProcessed++;
    return stats;
  }

  // Build summary record for AI Agent
  function buildSummary(stats) {
    var errorRate = stats.totalJobs > 0
      ? ((stats.totalErrors / (stats.totalErrors + stats.totalSuccesses)) * 100).toFixed(1)
      : 0;
    return {
      totalJobs: stats.totalJobs,
      totalErrors: stats.totalErrors,
      totalSuccesses: stats.totalSuccesses,
      errorRate: errorRate + '%',
      errorsByFlow: JSON.stringify(stats.errorsByFlow),
      timeRange: (stats.earliest || 'N/A') + ' to ' + (stats.latest || 'N/A'),
      pagesProcessed: stats.pagesProcessed,
      generatedAt: new Date().toISOString()
    };
  }

  try {
    var isLastPage = options.data.length < PAGE_SIZE;
    var isMaxPages = options.pageIndex >= MAX_PAGES;

    // Get existing accumulated state
    var existing = getState();

    // Stale state guard: discard if older than threshold
    if (existing && existing.startedAt) {
      var age = Date.now() - new Date(existing.startedAt).getTime();
      if (age > STALE_THRESHOLD_MS) {
        existing = null;
      }
    }

    // Accumulate this page
    var stats = accumulatePage(options.data, existing);

    if (isLastPage || isMaxPages) {
      // Final page: build summary, clean up state, emit record
      var summary = buildSummary(stats);
      deleteState();
      return {
        data: [summary],
        errors: options.errors,
        abort: isMaxPages
      };
    } else {
      // Non-last page: save state, skip downstream
      putState(stats);
      return {
        data: [],
        errors: options.errors,
        abort: false
      };
    }
  } catch (e) {
    // Graceful degradation: pass raw data through
    return {
      data: options.data,
      errors: [{ code: 'HOOK_ERROR', message: e.message || String(e) }],
      abort: false
    };
  }
}
