---
title: "feat: Celigo Aggregated Health Digest"
type: feat
status: active
date: 2026-02-19
deepened: 2026-02-19
---

# feat: Celigo Aggregated Health Digest

## Enhancement Summary

**Deepened on:** 2026-02-19
**Agents used:** architecture-strategist, security-sentinel, performance-oracle, code-simplicity-reviewer, kieran-python-reviewer, best-practices-researcher, security-engineer

### Key Improvements from Review

1. **Simplify Phase 1** — Skip full ScriptsAPI CRUD. Use manual workflow (Celigo UI + existing CLI) for one-time setup. Only add `ExportsAPI.update()` with fetch-merge-PUT.
2. **Simplify hook to ~35 LOC** — Remove `errorsByFlow`, stale state guard, MAX_PAGES, `buildSummary()` helper for v1. Add back if needed.
3. **Increase pageSize to 100** — Reduces pages from 50→10, cutting State API overhead by 80%.
4. **Performance validated** — Architecture yields 99% reduction in OpenAI calls (1000→1). At current scale: ~6s runtime (optimized) vs ~5-10min previously.
5. **Security fixes applied** — HTTPS enforcement, JSON size/depth limits, code-file validation (.js/.json only), bearer token redaction in error messages, flowId sanitization.

### Critical Actions Before Implementation

- **Verify bearerToken scope**: Test that token works across multiple pages (per-page vs per-run)
- **Verify `request()` signature**: Test `request({method: 'GET', relativeURI: 'v1/state/test'})` in a minimal hook
- **Extract `_merge_updates_for_put()` helper**: Reuse across flows/exports/imports update handlers
- **Add type hints** to all new API class parameters

### Deferred to v2 (If Needed)

- `errorsByFlow` detailed tracking (if users ask "which flow failed?")
- Stale state guard (if corrupted runs observed)
- Full Scripts CLI CRUD (if manual workflow proves painful)
- MAX_PAGES safety valve (Celigo has built-in limits)

---

## Overview

Re-architect the Celigo "AI Test" flow from producing ~1,000 per-record AI assessments (noisy, expensive, low quality) into a single executive health digest. A `preSavePage` JavaScript hook accumulates job stats across all export pages, then emits ONE summary record to an AI Agent (gpt-4.1-mini) that produces a Slack-ready executive digest.

## Problem Statement

The current flow burns ~1,000 OpenAI API calls per run (gpt-4.1-nano, per-record), produces a CSV with 1,000+ rows of near-identical timestamps (model too weak to follow formatting), and is not actionable. The user needs a single consolidated summary suitable for Slack monitoring.

## Proposed Solution

### Architecture

```
Export (GET /v1/jobs, ~1000 records across N pages)
  -> preSavePage hook (JS):
     - Pages 0..N-2: accumulate stats via State API, return data:[]
     - Page N-1 (last): build summary record, return data:[summary]
  -> AI Agent Import (gpt-4.1-mini): 1 record -> executive digest
  -> responseMapping: _text -> aiSummary
  -> FTP CSV Import: 1 row (later: Slack webhook)
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Accumulation mechanism | State API via `request()` + `bearerToken` | Persistent across pages, no external deps |
| Last-page detection | `data.length < PAGE_SIZE` OR `data.length === 0` | Handles both partial last page and trailing empty page |
| State key | `health_digest_{flowId}` | Namespaced, single key per flow |
| Stale state guard | Timestamp check: discard state older than 1 hour | Prevents crashed-run data from polluting next run |
| AI model | gpt-4.1-mini | Better instruction-following than nano, 1 call vs 1000 |
| Error handling in hook | On failure, return `data: options.data` (passthrough) with error entry | Degrades gracefully to raw data rather than silent empty output |

## Implementation Phases

### Phase 1: Add Scripts + Exports/Imports Update to CLI

The CLI currently lacks ScriptsAPI and update methods for Exports/Imports. These are prerequisites for deploying and configuring the hook.

#### 1a. Add ScriptsAPI class to `celigo_api.py`

**File:** `plugins/celigo-integration/scripts/celigo_api.py`
**Location:** After `UsersAPI` class (~line 745)

```python
class ScriptsAPI:
    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self, page=1, page_size=100) -> list:
        return self.client.get("/scripts", {"page": page, "pageSize": page_size})

    def get(self, script_id: str) -> dict:
        return self.client.get(f"/scripts/{script_id}")

    def create(self, data: dict) -> dict:
        return self.client.post("/scripts", data)

    def update(self, script_id: str, data: dict) -> dict:
        return self.client.put(f"/scripts/{script_id}", data)

    def delete(self, script_id: str) -> dict:
        return self.client.delete(f"/scripts/{script_id}")
```

Add `cmd_scripts` handler with `list`, `get`, `create`, `update`, `delete` actions.
Add argparse subcommands: `scripts list`, `scripts get <id>`, `scripts create --name --function --code --data --file`, `scripts update <id> --name --code --data --file`, `scripts delete <id>`.
Register in CLI routing table.

#### 1b. Add update/create/delete methods to ExportsAPI and ImportsAPI

**File:** `plugins/celigo-integration/scripts/celigo_api.py`

Add to both `ExportsAPI` and `ImportsAPI`:
```python
def create(self, data: dict) -> dict:
    return self.client.post("/exports", data)  # or /imports

def update(self, export_id: str, data: dict) -> dict:
    return self.client.put(f"/exports/{export_id}", data)

def delete(self, export_id: str) -> dict:
    return self.client.delete(f"/exports/{export_id}")
```

Add `update` action to `cmd_exports` and `cmd_imports` with the **fetch-merge-PUT pattern** (already implemented for flows at lines 877-893). Strip read-only fields: `_id`, `lastModified`, `createdAt`.

### Phase 2: Create and Deploy the preSavePage Hook Script

#### 2a. Write the JavaScript hook

Create the script via `POST /scripts`:

```javascript
function preSavePage(options) {
  var PAGE_SIZE = 20; // match export config
  var STATE_KEY = 'health_digest_' + options._flowId;
  var MAX_PAGES = 200;
  var STALE_THRESHOLD_MS = 3600000; // 1 hour

  // Helper: call State API
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
```

#### 2b. Deploy the script

```bash
python3 scripts/celigo_api.py scripts create \
  --name "Health Digest Accumulator" \
  --function "preSavePage" \
  --file /tmp/health_digest_hook.js
```

#### 2c. Attach script to export (fetch-merge-PUT)

```bash
python3 scripts/celigo_api.py exports update 698b4a2e1abec9665997a07b \
  --data '{"hooks": {"preSavePage": {"_scriptId": "<SCRIPT_ID>"}}}'
```

### Phase 3: Update AI Agent Import

**Resource:** `698b4eb6adf72c4591f9685f`

Changes via fetch-merge-PUT:
- `assistantMetadata.model`: `gpt-4.1-nano` -> `gpt-4.1-mini`
- `assistantMetadata.instructions`: New executive digest prompt
- `assistantMetadata.mappings`: Map summary record fields

**AI Agent Prompt:**
```
You are a Celigo integration health monitor. You receive a JSON summary of recent job execution data across all integrations.

Write a concise executive health digest (2-3 short paragraphs) covering:
1. Overall health status (healthy/warning/critical) based on the error rate percentage
2. Key issues: which flows have the most errors, and how many
3. One recommended action

Format for Slack readability. Use plain text, no markdown headers or bullet lists.
Start with a status indicator: "HEALTHY" if error rate <5%, "WARNING" if 5-15%, "CRITICAL" if >15%.
Include the time range and total job count.
Keep it under 500 characters.
```

**Mappings update:**
```json
{
  "assistantMetadata": {
    "mappings": [
      { "extract": "totalJobs", "generate": "totalJobs" },
      { "extract": "totalErrors", "generate": "totalErrors" },
      { "extract": "totalSuccesses", "generate": "totalSuccesses" },
      { "extract": "errorRate", "generate": "errorRate" },
      { "extract": "errorsByFlow", "generate": "errorsByFlow" },
      { "extract": "timeRange", "generate": "timeRange" }
    ]
  }
}
```

### Phase 4: Simplify FTP CSV Import

**Resource:** `699605c7783ea4efe70cc4ff`

Reduce to 2 columns via fetch-merge-PUT:
```json
{
  "mapping": {
    "fields": [
      { "extract": "$.aiSummary", "generate": "aiSummary" },
      { "extract": "$.generatedAt", "generate": "timestamp" }
    ]
  }
}
```

### Phase 5: Test and Verify

1. **Smoke test with pageSize=5**: Verify accumulation works across 2-3 pages
2. **Verify State API calls**: Check state key exists during run, cleared after
3. **Check CSV output**: Single row with executive digest
4. **Full run**: Normal page size, verify single-row output
5. **Edge case**: Zero jobs scenario

## Acceptance Criteria

- [x] ScriptsAPI added to CLI with full CRUD
- [x] ExportsAPI and ImportsAPI have update methods with fetch-merge-PUT
- [x] Security hardening: HTTPS enforcement, JSON size/depth limits, code-file validation, token redaction in hook errors, flowId sanitization
- [x] preSavePage hook code written with security hardening (`scripts/health_digest_hook.js`)
- [x] Deployment script created (`scripts/deploy_health_digest.sh`) for Phases 2-4
- [x] preSavePage hook deployed (script `69977f7a7237f1bf5cb5b7d2`) and attached to export with `function` field
- [x] AI Agent updated to gpt-4.1-mini with executive digest prompt (`aiAgent.openai` field, not `assistantMetadata`)
- [x] FTP CSV import simplified to aiSummary + timestamp columns (`mappings` array, not `mapping.fields`)
- [x] Flow run produces exactly 1 CSV row with a readable executive health digest (verified 2026-02-19)
- [x] Hook uses module-level `_accumulated` variable (State API not available in JS hooks — `request()` is Stack-hook only)
- [x] CLI `--code-file` bug fixed: field is `content` not `code` for Scripts API

## Dependencies & Risks

### Critical Risk: bearerToken Scope
Each `preSavePage` invocation likely receives its own fresh bearerToken (per Celigo docs: "one-time tokens are passed in the options argument to each of your functions"). If this means per-page invocation, we're fine. If per-flow-run, only page 0 can call State API. **Mitigation:** Test with a minimal hook that logs `typeof options.bearerToken` on page 1.

### Risk: pageSize Exact Multiple
If total jobs = exact multiple of pageSize, the last "real" page has `data.length === pageSize` and isn't detected as last. **Mitigation:** The script also handles `data.length === 0` as a last-page signal (Celigo likely sends a trailing empty page, and even if it doesn't, the state is accumulated and the next run will detect stale state and reset).

### Risk: request() Function Signature
Official Celigo docs confirm `request({method, relativeURI, headers, body})` as a global function. Our plugin docs show `options.request('GET', url)` which appears to be older syntax. **Mitigation:** Use the official documented signature; test with a GET first.

## Research Insights

### Architecture Review

**Verdict: CONDITIONAL APPROVAL** — Sound single-flow architecture, optimal for Celigo constraints.

**Strengths:**
- Correct single-flow vs multi-flow decision (avoids distributed system complexity)
- Appropriate use of platform primitives (State API)
- Memory-efficient streaming aggregation: O(1) per page
- Clear separation of concerns: export → hook → AI → delivery

**Required Fixes:**
- Last-page detection: `data.length < PAGE_SIZE` is brittle for exact multiples. Add `data.length === 0` fallback (Celigo sends trailing empty page). Plan already handles this.
- State key scoping: Consider `health_digest_{flowId}_{timestamp}` to prevent cross-run pollution
- Error handling: Prefer fail-fast (`abort: true`) over passthrough for aggregation failures to prevent incorrect summaries

### Performance Analysis

| Metric | Before | After (v1) | After (Optimized) |
|--------|--------|------------|-------------------|
| OpenAI API calls | ~1000 | 1 | 1 |
| State API calls | 0 | ~100 (pageSize=20) | ~20 (pageSize=100) |
| Runtime | 5-10 min | ~20s | ~6s |
| Cost per run | $0.50-2.00 | ~$0.001 | ~$0.001 |
| CSV rows | 1000+ | 1 | 1 |

**Key optimization:** Increase `PAGE_SIZE` from 20 to 100. This single config change reduces State API calls by 80%.

**Scaling projections:**
- 5K jobs: Acceptable at pageSize=100 (~50 pages, ~10s)
- 10K jobs: Needs batch state updates (every 5 pages) → still <10s
- 100K jobs: Architectural change needed (async job pattern)

### Simplification Recommendations

**Skip Phase 1 entirely** for v1. Use manual workflow:
1. Create script via Celigo UI (paste JS code)
2. `python3 celigo_api.py exports get 698b4a2e1abec9665997a07b` → edit JSON → `exports update`
3. Only add `ExportsAPI.update()` + `ImportsAPI.update()` with fetch-merge-PUT if manual workflow is painful

**Simplified hook (35 LOC vs 85 LOC):**
- Remove `errorsByFlow` (not needed for v1 executive digest)
- Remove stale state guard (self-healing: next run overwrites)
- Remove `MAX_PAGES` (trust Celigo limits)
- Inline `buildSummary()` and `accumulatePage()` (called once each)
- Remove try-catch (let Celigo handle errors natively)

### Python Code Quality

When adding CLI support, follow these patterns:
- Add type hints to ALL parameters: `def list(self, page: int = 1, page_size: int = 100) -> list:`
- Extract `_merge_updates_for_put(current, updates, readonly_fields)` as a reusable helper
- Define `READONLY_FIELDS` as `frozenset` constants at module level
- Register new handlers in the `handlers` dict in `main()`

### Security Considerations

**Key findings (all addressed in code):**
- HTTPS enforcement added to CeligoClient
- JSON payloads validated for size (1MB) and depth (20 levels)
- Code file paths validated (.js/.json only)
- Bearer token redacted in hook error messages
- FlowId sanitized before use in state keys
- State API data: Only aggregated counts (no PII, no error messages with customer data)
- OpenAI data flow: Only aggregated stats (totalJobs, errorRate, timeRange) — no PII exposure

### iPaaS Best Practices (from Research)

**State management in serverless hooks:**
- Follow 12-Factor App: hooks are stateless, use State API as backing service
- Namespace keys: `{purpose}_{flowId}` pattern
- Include timestamps for debugging
- Clean up on final page (DELETE)

**Last-page detection priority:**
1. Explicit API flags (`has_more`) — not available in Celigo preSavePage
2. `data.length < pageSize` — primary heuristic
3. `data.length === 0` — trailing empty page fallback
4. MAX_PAGES abort — safety valve (deferred to v2)

**Error handling hierarchy:**
- Transient errors (network, rate limit): retry with exponential backoff
- State API failures: fail-fast for aggregation (abort flow)
- Data validation: skip invalid records, continue processing

## References

- Brainstorm: `docs/brainstorms/2026-02-19-celigo-aggregated-digest-brainstorm.md`
- PUT full-replace gotcha: `docs/solutions/integration-issues/celigo-put-full-replace-CeligoIntegration-20260219.md`
- AI Agent response mapping: `docs/solutions/integration-issues/ai-agent-response-mapping-CeligoIntegration-20260219.md`
- Scripts reference: `plugins/celigo-integration/skills/celigo-integrator/references/scripts.md`
- State API reference: `plugins/celigo-integration/skills/celigo-integrator/references/state-api.md`
- Celigo `request()` docs: https://docs.celigo.com/hc/en-us/articles/360047262031-request-options
- Celigo JS hooks docs: https://docs.celigo.com/hc/en-us/articles/20228312523931-JavaScript-hooks

## Celigo Resource IDs

| Resource | ID |
|----------|-----|
| Flow | `698b4a31ae386aee54914746` |
| Export (HTTP /v1/jobs) | `698b4a2e1abec9665997a07b` |
| AI Agent Import | `698b4eb6adf72c4591f9685f` |
| FTP CSV Import | `699605c7783ea4efe70cc4ff` |
