# Brainstorm: Celigo Aggregated Health Digest

**Date:** 2026-02-19
**Status:** Design approved, pending implementation
**Flow:** AI Test (`698b4a31ae386aee54914746`)

## What We're Building

Transform the Celigo "AI Test" flow from producing 1,000+ per-record AI assessments into a single **executive health digest** — one consolidated summary of all Celigo job errors/successes, suitable for posting to Slack.

### Current State
- Export fetches ~1,000 job records from `/v1/jobs` across multiple pages
- AI Agent (gpt-4.1-nano) processes each record individually → 1,000 API calls
- CSV writes 1,000+ rows with per-record "summaries" (most are just timestamps due to weak model)
- Expensive, noisy, not actionable

### Target State
- Export fetches same job records
- `preSavePage` hook accumulates stats across all pages via State API
- On the final page, produces ONE summary record with aggregated stats
- AI Agent (gpt-4.1-mini) receives ONE record → executive health digest
- CSV writes ONE row (later: Slack webhook)

## Why Approach 3: preSavePage + State API

### Approaches Considered

| # | Approach | Pros | Cons |
|---|----------|------|------|
| 1 | Two-flow chain (`_runNextFlowIds`) | Clean separation, Flow 1 accumulates → Flow 2 summarizes | Extra flow to manage, more API calls, cursor coordination |
| 2 | `postAggregate` hook on FTP import | Fires after all records processed | Only receives aggregated file metadata (`success`, `_json`), cannot produce new records, fires too late in pipeline |
| 3 | **`preSavePage` + State API** | Single flow, accumulate in-place, produce summary record on last page | Must detect last page heuristically (no `lastPage` flag in hook) |

**Chosen: Approach 3** — simplest architecture, fewest moving parts, stays within single flow.

### Critical Finding: No `lastPage` Flag

The `preSavePage` hook does **not** receive an `options.lastPage` property. Available detection mechanisms:

1. **`data.length < pageSize`** — if a page has fewer records than the configured page size, it's likely the last page
2. **`abort: true` return** — stop pagination explicitly after processing enough data
3. **Empty data array** — some exports send a final empty page

**Chosen strategy:** Use `data.length < pageSize` heuristic, with a fallback `abort: true` after a configurable max page count. The State API accumulation means even if detection is off by one page, the summary still captures all data.

### Final-page summary production

When last page detected:
1. Read accumulated state via `bearerToken` + Celigo API (`GET /state/{key}`)
2. Build single summary record from accumulated stats
3. Clear state (`DELETE /state/{key}`)
4. Return `data: [summaryRecord]` — this ONE record flows to AI Agent → CSV/Slack

Non-last pages:
1. Accumulate stats from `options.data` into state (`PUT /state/{key}`)
2. Return `data: []` — empty array skips downstream processing for this page

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| AI Model | gpt-4.1-mini | Better instruction-following than nano, reasonable cost for 1 call |
| Summary format | Executive summary (2-3 paragraphs) | Actionable for Slack consumption |
| Script language | JavaScript (Celigo hooks) | Native to platform, no external dependencies |
| State key | `flow_{flowId}_job_digest` | Namespaced to avoid collisions |
| Page size detection | Check `data.length < pageSize` | Simplest heuristic; pageSize stored in flow settings |
| Max pages safety | `abort: true` after 200 pages | Prevents runaway accumulation |

## Hook Options Available in `preSavePage`

From official Celigo docs:
- `options.data` — array of records (current page)
- `options.errors` — array of errors
- `options.pageIndex` — 0-based page counter
- `options.bearerToken` — one-time token for Celigo API calls
- `options._exportId`, `options._flowId`, `options._connectionId`
- `options.settings` — integration-level settings
- `options.testMode` — boolean

Return object:
- `data` — modified records array
- `errors` — modified errors
- `abort` — boolean, stop pagination
- `newErrorsAndRetryData` — new errors

## State API Usage Pattern

```javascript
// Within preSavePage, use bearerToken to call State API
const BASE = 'https://api.integrator.io/v1';
const headers = { Authorization: `Bearer ${options.bearerToken}` };

// Read state
const state = JSON.parse(
  options.request('GET', `${BASE}/state/flow_${options._flowId}_digest`, { headers })
);

// Write state
options.request('PUT', `${BASE}/state/flow_${options._flowId}_digest`, {
  headers,
  body: JSON.stringify({ value: accumulatedStats })
});

// Delete state (cleanup after final page)
options.request('DELETE', `${BASE}/state/flow_${options._flowId}_digest`, { headers });
```

## Summary Record Schema (passed to AI Agent)

```json
{
  "totalJobs": 1003,
  "totalErrors": 47,
  "totalSuccesses": 956,
  "errorsByFlow": {
    "Order Sync": { "errors": 23, "successes": 500 },
    "Inventory Update": { "errors": 24, "successes": 456 }
  },
  "timeRange": { "earliest": "2026-02-18T00:00:00Z", "latest": "2026-02-19T12:00:00Z" },
  "topErrorMessages": ["Connection timeout (15)", "Rate limit exceeded (12)", "Invalid SKU (10)"]
}
```

## AI Agent Prompt (gpt-4.1-mini)

```
You are a Celigo integration health monitor. You receive a JSON summary of recent job execution data.

Write a concise executive health digest (2-3 paragraphs) covering:
1. Overall health status (healthy/warning/critical based on error rate)
2. Key issues requiring attention (top errors, affected flows)
3. Recommended actions

Format for Slack readability. Use plain text, no markdown headers.
Start with a status emoji: green_circle for <5% errors, yellow_circle for 5-15%, red_circle for >15%.
```

## Open Questions

1. **`options.request` signature for POST/PUT with body** — our docs show `options.request('GET', url)` but not how to pass a body for PUT. May need to use `bearerToken` with a raw HTTP call instead.
2. **State API via bearerToken** — confirmed available per official docs, but need to verify exact request format from within hooks.
3. **Script deployment** — need to create script via `POST /scripts`, then attach to export via `PUT /exports/{id}` with `hooks.preSavePage._scriptId`.
4. **pageSize value** — need to check current export's page size setting to use in last-page detection.

## Implementation Sequence

1. Create Celigo script (`POST /scripts`) with `preSavePage` hook code
2. Attach script to export (`698b4a2e1abec9665997a07b`) via hooks
3. Update AI Agent import (`698b4eb6adf72c4591f9685f`): model → gpt-4.1-mini, new prompt, updated mappings
4. Simplify FTP CSV import (`699605c7783ea4efe70cc4ff`): single `aiSummary` column
5. Test with small page size first (pageSize=5) to verify accumulation + last-page detection
6. Run full flow, download CSV, verify single-row executive summary
7. (Future) Replace CSV step with Slack webhook import
