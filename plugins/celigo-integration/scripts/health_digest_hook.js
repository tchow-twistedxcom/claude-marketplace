/*
 * Health Digest Accumulator — Celigo preSavePage hook (v4)
 *
 * Accumulates job stats across all export pages using a module-level
 * variable (persists across page invocations within the same job),
 * then emits a single summary record on the final page for the AI Agent.
 *
 * v4: Filter to flow-type jobs only to avoid double-counting errors
 *     (export/import child jobs duplicate the parent flow's error counts).
 *     All flow-type jobs have _flowId, eliminating "unknown" bucket.
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
  var PAGE_SIZE = 2000; // export pageSize=2000; API returns max 1001, so always single-page
  var now = new Date();

  // Initialize accumulator on first page
  if (!_accumulated) {
    _accumulated = {
      totalFlowRuns: 0,
      totalErrors: 0,
      totalSuccesses: 0,
      totalOpenErrors: 0,
      totalResolved: 0,
      errorsByFlow: {},
      openErrorsByFlow: {},
      agingBuckets: { under24h: 0, days1to3: 0, days3to7: 0, days7to14: 0, over14d: 0 },
      earliest: null,
      latest: null,
      pagesProcessed: 0
    };
  }

  // Accumulate this page's data — only flow-type jobs to avoid double-counting
  for (var i = 0; i < options.data.length; i++) {
    var job = options.data[i];

    // Skip export/import child jobs — their errors duplicate the parent flow job's counts
    if (job.type !== 'flow') continue;

    _accumulated.totalFlowRuns++;
    _accumulated.totalErrors += (job.numError || 0);
    _accumulated.totalSuccesses += (job.numSuccess || 0);
    _accumulated.totalOpenErrors += (job.numOpenError || 0);
    _accumulated.totalResolved += (job.numResolved || 0);

    // Flow-type jobs always have _flowId
    var fid = job._flowId || 'unknown';

    // Track errors by flow
    if (!_accumulated.errorsByFlow[fid]) {
      _accumulated.errorsByFlow[fid] = { errors: 0, successes: 0 };
    }
    _accumulated.errorsByFlow[fid].errors += (job.numError || 0);
    _accumulated.errorsByFlow[fid].successes += (job.numSuccess || 0);

    // Track open errors by flow with aging
    var openCount = job.numOpenError || 0;
    if (openCount > 0) {
      if (!_accumulated.openErrorsByFlow[fid]) {
        _accumulated.openErrorsByFlow[fid] = { open: 0, oldest: null, newest: null };
      }
      _accumulated.openErrorsByFlow[fid].open += openCount;

      // Use endedAt as the error timestamp for aging
      var jobTime = job.endedAt || job.startedAt;
      if (jobTime) {
        if (!_accumulated.openErrorsByFlow[fid].oldest || jobTime < _accumulated.openErrorsByFlow[fid].oldest) {
          _accumulated.openErrorsByFlow[fid].oldest = jobTime;
        }
        if (!_accumulated.openErrorsByFlow[fid].newest || jobTime > _accumulated.openErrorsByFlow[fid].newest) {
          _accumulated.openErrorsByFlow[fid].newest = jobTime;
        }

        // Calculate age bucket
        var ageMs = now.getTime() - new Date(jobTime).getTime();
        var ageHours = ageMs / (1000 * 60 * 60);
        if (ageHours < 24) {
          _accumulated.agingBuckets.under24h += openCount;
        } else if (ageHours < 72) {
          _accumulated.agingBuckets.days1to3 += openCount;
        } else if (ageHours < 168) {
          _accumulated.agingBuckets.days3to7 += openCount;
        } else if (ageHours < 336) {
          _accumulated.agingBuckets.days7to14 += openCount;
        } else {
          _accumulated.agingBuckets.over14d += openCount;
        }
      }
    }

    // Time range
    if (job.endedAt) {
      if (!_accumulated.earliest || job.endedAt < _accumulated.earliest) _accumulated.earliest = job.endedAt;
      if (!_accumulated.latest || job.endedAt > _accumulated.latest) _accumulated.latest = job.endedAt;
    }
  }
  _accumulated.pagesProcessed++;

  var isLastPage = options.data.length < PAGE_SIZE || options.data.length === 0;

  if (isLastPage) {
    var stats = _accumulated;
    _accumulated = null; // reset for next job run

    var total = stats.totalErrors + stats.totalSuccesses;
    var errorRate = total > 0
      ? ((stats.totalErrors / total) * 100).toFixed(1)
      : '0.0';
    var resolutionRate = stats.totalErrors > 0
      ? ((stats.totalResolved / stats.totalErrors) * 100).toFixed(1)
      : '100.0';

    return {
      data: [{
        isSummary: true,
        totalFlowRuns: stats.totalFlowRuns,
        totalErrors: stats.totalErrors,
        totalSuccesses: stats.totalSuccesses,
        totalOpenErrors: stats.totalOpenErrors,
        totalResolved: stats.totalResolved,
        errorRate: errorRate + '%',
        resolutionRate: resolutionRate + '%',
        errorsByFlow: JSON.stringify(stats.errorsByFlow),
        openErrorsByFlow: JSON.stringify(stats.openErrorsByFlow),
        agingBuckets: JSON.stringify(stats.agingBuckets),
        timeRange: (stats.earliest || 'N/A') + ' to ' + (stats.latest || 'N/A'),
        pagesProcessed: stats.pagesProcessed,
        generatedAt: new Date().toISOString()
      }],
      errors: options.errors,
      abort: false
    };
  } else {
    return {
      data: [],
      errors: options.errors,
      abort: false
    };
  }
}
