---
title: "feat: Multi-System Health Orchestrator Consumer Wiring + Phases 2-4"
type: feat
status: active
date: 2026-02-26
supersedes: 2026-02-19-feat-celigo-aggregated-health-digest-plan.md
brainstorm: /home/tchow/.claude/plans/rippling-questing-charm.md
deepened: 2026-02-26
---

# Multi-System Health Orchestrator — Consumer Wiring + Phases 2-4

## Enhancement Summary

**Deepened on:** 2026-02-26
**Research agents used:** spec-flow-analyzer, architecture-strategist, security-sentinel, performance-oracle, code-simplicity-reviewer, best-practices-researcher

### Key Improvements
1. **Fallback path redesigned** — Replaced infeasible "re-enable Slack PP" approach with PP5 pipeline-field-gated Slack fallback + external dead man's switch
2. **Security hardening** — Added Socket.IO auth, GET endpoint auth, timing-safe API key comparison, EDI endpoint auth
3. **Performance optimizations** — Direct RTK cache update (not tag invalidation), room-based slim broadcasts, raw_payload removal, history projections
4. **YAGNI simplifications** — Removed alert config UI, trend charts, 60s polling fallback; merged Phase 3+4; simplified self-health to 4 lines
5. **22 gaps addressed** from spec-flow analysis — out-of-order snapshots, duplicate notifications, record type filter strategy, Resolve/Retry migration

### Critical Decisions Made
- **Fallback:** PP5 always-present Slack import with `_dashboardDelivered` pipeline field gate (architecturally viable within Celigo sandbox)
- **Simplification:** 4 phases → 3 phases (merged EDI + self-health + retirement)
- **Security:** All GET endpoints require session auth; Socket.IO requires auth middleware
- **Performance:** `updateCachedData` for Socket.IO → RTK (no double-fetch); drop `raw_payload` in production

---

## Overview

Complete the Multi-System Health Orchestrator by wiring up consumers (Slack App Home + web dashboard) to the new `health_snapshots` collection, then incrementally add NetSuite, EDI, and dashboard self-health monitoring. The Celigo flow orchestrates data collection; B2bDashboard handles persistence, display, and notifications.

**Current state:** Phase 1 producer is complete — Celigo flow POSTs structured JSON to `/api/health/ingest`, data lands in `health_snapshots` MongoDB collection, Socket.IO broadcasts `health:snapshot`. But no UI reads from it yet.

**What remains:**
- Phase 1b: Consumer wiring (Slack App Home, web dashboard, notification path)
- Phase 2: NetSuite monitoring via gateway SuiteQL proxy
- Phase 3: EDI + Dashboard self-health + CeligoHealthWorker retirement

## Problem Statement

Health monitoring is currently fragmented:
- **Celigo errors**: Visible via CeligoHealthWorker (60s polling) in Slack App Home + web dashboard
- **NetSuite scripts**: No monitoring — failures discovered manually
- **EDI pipeline**: Status visible in web dashboard but not in health digest
- **Dashboard health**: Basic `/api/health` endpoint, no proactive monitoring

The orchestrator flow already collects Celigo data and pushes it to the dashboard, but the dashboard doesn't display it. Meanwhile, CeligoHealthWorker duplicates the Celigo polling. The consumer side needs to be wired up, and additional systems need to be added.

## Technical Approach

### Architecture

```
Celigo Flow (every 15 min)
├── ExportA: GET /v1/flows → flow_data_processor.js
│   └── Records: integration, standalone, trigger
│
├── PP0: GET /v1/integrations/{id}/errors   [preMap: filterIntegrationOnly]
├── PP1: GET /v1/flows/{id}/errors          [preMap: filterStandaloneOnly]
├── PP2: GET /v1/integrations/{id}          [preMap: filterIntegrationOnly]
├── PP3: AI Agent (digest_aggregator.js preMap → AI → aiSummary responseMapping)
├── PP4: POST /api/health/ingest (dashboard_payload_builder.js preMap)
│   └── postResponseMap: set _dashboardDelivered on pipeline record
├── PP5: POST Slack webhook (FALLBACK — preMap: skip if _dashboardDelivered)
│
B2bDashboard (consumer + display)
├── POST /api/health/ingest → health_snapshots (MongoDB)
│   └── Reject out-of-order snapshots (timestamp comparison)
├── Socket.IO 'health:snapshot' room broadcast (slim status payload)
├── Slack App Home (reads health_snapshots, renders Block Kit)
├── Web dashboard (RTK Query + Socket.IO streaming update)
├── Slack channel notifications (on status transitions, feature-flagged)
└── External dead man's switch (healthchecks.io ping)
```

### Record Type Routing (Phase 2/3 safe)

> **Note:** `record_type_filter.js` uses positive checks (`isIntegration`, `isStandaloneFlow`). New record types (`isNetSuiteHealth`, `isEdiHealth`) are implicitly skipped by both `filterIntegrationOnly` and `filterStandaloneOnly` — they return `{}` for unrecognized types. This is intentional. New records flow through PP0-PP2 as skipped records and are only consumed at PP3 (AI Agent) and PP4 (dashboard payload builder). Add a code comment documenting this when deploying Phase 2.

### Implementation Phases

#### Phase 1b: Consumer Wiring (B2bDashboard)

Wire the Slack App Home and web dashboard to read from `health_snapshots` instead of `celigo_health_snapshots`. Keep CeligoHealthWorker running in parallel for the per-flow Resolve/Retry action data.

**Key decision: Dual-source strategy.**
- `health_snapshots` = canonical health summary (from orchestrator, every 15 min)
- `celigo_health_snapshots` = per-flow action data for Resolve/Retry buttons (from CeligoHealthWorker, every 60s)
- Slack App Home reads summary from `health_snapshots`, buttons use CeligoHealthWorker data
- Web dashboard reads from `health_snapshots` for the multi-system view, existing Celigo detail page stays on CeligoHealthWorker
- CeligoHealthWorker retirement deferred to Phase 3 (when all action data migrated)
- **Hard deadline:** Dual-source period ends with Phase 3 delivery. No indefinite coexistence.

**Tasks:**

1. **Security hardening (prerequisite for all consumer work)**
   - File: `server/routes/health-ingest.ts`
   - Add timing-safe API key comparison: `timingSafeEqual(Buffer.from(a), Buffer.from(b))`
   - Add session auth middleware to `GET /latest` and `GET /history` endpoints
   - Add `limit` upper bound (max 1000) to history query
   - File: `server/unified-edi-server.ts`
   - Add Socket.IO auth middleware: validate session cookie/token before allowing connection
   - Add `X-API-Key` to CORS `allowedHeaders`

2. **Socket.IO room + subscription protocol**
   - File: `server/routes/health-ingest.ts`
   - Room-based emission: `io.to('health').emit('health:snapshot', slimPayload)` (status-only, not full snapshot)
   - Slim payload: `{ _id, timestamp, source, systemStatuses: { celigo: { status } } }` (~200 bytes vs ~18KB)
   - Subscription handler: on `health:subscribe`, join `health` room + emit latest snapshot immediately
   - **On ingest: compare incoming timestamp against latest stored snapshot; reject if older (409 Conflict)**
   - Pattern: follows existing `celigo:health:subscribe` / `celigo:health:data` convention
   - Enable Socket.IO connection state recovery: `maxDisconnectionDuration: 2 * 60 * 1000`

   ### Research Insight: Out-of-Order Snapshot Handling
   ```typescript
   // In POST /ingest handler, before insert:
   const previous = await repo.getLatestSnapshot();
   if (previous && new Date(timestamp) <= previous.timestamp) {
     logger.warn('Out-of-order snapshot rejected', { incoming: timestamp, existing: previous.timestamp });
     return res.status(409).json({ success: false, error: 'Stale snapshot' });
   }
   ```

3. **RTK Query API slice for health snapshots**
   - New file: `src/features/health-orchestrator/api/healthSnapshotApi.ts`
   - Base URL: `/api/health`
   - Endpoints:
     - `getLatestSnapshot()` → `GET /latest` → tag: `HealthSnapshot`
     - `getSnapshotHistory({ from?, to?, limit? })` → `GET /history` → tag: `HealthSnapshotHistory`
   - **Socket.IO: use `updateCachedData` (not tag invalidation) to inject WebSocket payload directly into Redux store**
   - On Socket.IO `reconnect` event: re-emit `health:subscribe` to rejoin room
   - No polling fallback needed — data changes every 15 min; Socket.IO push + fetch-on-mount is sufficient

   ### Research Insight: RTK Query Streaming Update Pattern
   ```typescript
   getLatestSnapshot: builder.query<HealthSnapshot, void>({
     query: () => '/latest',
     providesTags: ['HealthSnapshot'],
     async onCacheEntryAdded(_arg, { updateCachedData, cacheDataLoaded, cacheEntryRemoved }) {
       const socket = io({ autoConnect: false });
       try {
         await cacheDataLoaded;
         socket.connect();
         socket.emit('health:subscribe');
         socket.on('health:snapshot', (snapshot) => {
           updateCachedData(() => snapshot); // Direct cache update, no HTTP round-trip
         });
         socket.on('connect', () => {
           if (!socket.recovered) socket.emit('health:subscribe');
         });
       } catch { /* component unmounted before data loaded */ }
       await cacheEntryRemoved;
       socket.emit('health:unsubscribe');
       socket.disconnect();
     },
   }),
   ```

4. **Slack App Home update — summary from health_snapshots**
   - File: `src/services/slack/SlackAppHomeService.ts`
   - Add method: `buildMultiSystemSummaryBlocks(snapshot: HealthSnapshot)` — renders AI summary + per-system status blocks
   - File: `src/services/slack/SlackSocketModeHandler.ts`
   - `app_home_opened` handler: fetch latest from `health_snapshots` for summary section, keep `celigo_health_snapshots` for action buttons
   - **Parallelize independent reads:** `Promise.all([registerUser, isAdmin, celigoSnapshot, activity, healthSnapshot])`
   - Block budget: stay under 100 blocks total; truncate error list if needed
   - If no `health_snapshots` data yet (first run), fall back to CeligoHealthWorker-only view
   - Use overflow menus instead of separate action blocks to save blocks (section accessory vs actions block)

   ### Research Insight: Overflow Menu Pattern (saves ~10 blocks)
   ```typescript
   // Instead of separate Resolve/Retry buttons taking a full actions block:
   accessory: {
     type: 'overflow',
     action_id: `flow_actions_${flow.flow_id}`,
     options: [
       { text: { type: 'plain_text', text: 'Resolve All Errors' }, value: `${flowId}|${expOrImpId}|resolve` },
       { text: { type: 'plain_text', text: 'Retry Failed Records' }, value: `${flowId}|${expOrImpId}|retry` },
       { text: { type: 'plain_text', text: 'View in Celigo' }, value: `${flowId}||open_celigo` },
     ]
   }
   ```

5. **Slack channel notification on health status change**
   - File: `server/routes/health-ingest.ts`
   - After successful ingest: compare new snapshot's system statuses with previous snapshot
   - **Feature flag:** `HEALTH_ORCHESTRATOR_NOTIFICATIONS_ENABLED=false` during parallel period
   - Notify on meaningful transitions only:
     - Any system transitions to `error` → post alert
     - Any system recovers from `error` → post per-system recovery message
     - All systems healthy → post "all clear" summary
   - Debounce: only notify on actual transitions, not repeated same-status snapshots
   - **Channel alert content:** High-level status only (system name, old→new status, link to `/health`). No flow-level detail, no AI summary. Reserve detail for Slack App Home and web dashboard.
   - **Duplicate prevention:** Feature flag stays off until CeligoHealthWorker notification capability is confirmed disabled

6. **Web dashboard multi-system health page**
   - New file: `src/features/health-orchestrator/routes/HealthOrchestratorRoute.tsx`
   - Route: `/health` (new top-level route, separate from existing `/celigo-health`)
   - Layout: system status cards (Celigo, NetSuite, EDI, Dashboard) + AI summary panel + error list + last-updated timestamp + Socket.IO connection indicator (green/red dot)
   - Phase 1b: only Celigo card populated, others show "Coming soon" placeholder
   - "Coming soon" vs populated: driven by snapshot data — if `systems.netsuite` exists in latest snapshot, render card; otherwise show placeholder
   - Uses RTK Query `useGetLatestSnapshotQuery` with streaming Socket.IO update
   - Stale data indicator: >20 min = yellow "stale" label, >60 min = red pulsing label

7. **Navigation update**
   - File: `src/App.tsx` or sidebar navigation component
   - Add "System Health" link to `/health` route
   - Keep existing "Celigo Health" link to `/celigo-health` (detail view with Resolve/Retry)

8. **Performance: Remove raw_payload from production ingests**
   - File: `server/routes/health-ingest.ts`
   - Remove `raw_payload: req.body` from snapshot document (halves storage: ~300MB → ~150MB over 90 days)
   - Optional: `raw_payload: process.env.HEALTH_INGEST_DEBUG === 'true' ? req.body : undefined`

9. **Performance: Add projection to history queries**
   - File: `src/services/mongodb/repositories/healthSnapshotRepository.ts`
   - Always exclude `raw_payload` from history queries
   - Add `summaryOnly` mode: exclude `systems.celigo.errors` for trend queries

10. **Fallback notification path (PP5 Slack fallback)**
    - **Celigo flow modification:** Add PP5 (Slack import) after PP4 (dashboard import)
    - PP4 `postResponseMap`: set `_dashboardDelivered: true` on pipeline record when dashboard POST succeeds
    - PP5 `preMap`: check `_dashboardDelivered` field — if true, return `{}` (skip); if false/missing, build minimal Slack alert
    - PP5 uses preserved Slack import `699c7192dbb446adf74f7216`
    - This works because postResponseMap output persists downstream (documented in pipeline-field-persistence solution doc)
    - **No flow reconfiguration needed — PP5 is always present, usually no-ops via preMap skip**

    ### Research Insight: Why This Works
    ```
    PP4: POST /api/health/ingest (dashboard)
      postResponseMap: set _dashboardDelivered=true on pipeline record
    PP5: POST Slack webhook (fallback)
      preMap: if record._dashboardDelivered, return {}; else build minimal Slack blocks
    ```
    JS hooks cannot make HTTP requests (sandboxed). But pipeline field persistence (postResponseMap → downstream preMap) is fully supported. This is the only viable in-Celigo fallback mechanism.

11. **External dead man's switch**
    - After successful ingest in `health-ingest.ts`: ping healthchecks.io URL (best-effort `fetch`)
    - Configure 20-minute expected period (15-min cadence + 5-min grace)
    - If ping stops → external service alerts via email/Slack
    - Catches total failure (both Celigo flow AND dashboard down simultaneously)

12. **Slack `publishToAllUsers` optimization**
    - File: `src/services/slack/SlackAppHomeService.ts`
    - Replace sequential publish with batched concurrency (5 parallel):
    ```typescript
    const BATCH_SIZE = 5;
    for (let i = 0; i < userIds.length; i += BATCH_SIZE) {
      const batch = userIds.slice(i, i + BATCH_SIZE);
      await Promise.allSettled(batch.map(userId => this.publishHomeView(userId, ...)));
      if (i + BATCH_SIZE < userIds.length) await delay(PUBLISH_DELAY_MS);
    }
    ```
    - For 10 users: ~3s → ~0.8s. Stays within Slack Tier 2 rate limit (~50/min).

#### Phase 2: NetSuite Monitoring

Add NetSuite scheduled script and map/reduce health to the orchestrator.

**Tasks:**

1. **NetSuite SuiteQL health query**
   - File: `~/NetSuiteApiGateway/routes/netsuite-health.js` (NEW)
   - Mount at `/api/health/netsuite`
   - SuiteQL queries via existing `suiteapi-queryrun` action → RESTlet 2655:
     - Scheduled script status: `SELECT scriptid, status, datecreated, percentcomplete FROM scheduledscriptinstance WHERE status IN ('Processing', 'Failed', 'Pending') AND datecreated > SYSDATE - 1`
     - Map/Reduce jobs: `SELECT scriptid, stage, status FROM mapreducescriptinstance WHERE status IN ('Processing', 'Failed') AND datecreated > SYSDATE - 1`
     - Governance: `SELECT concurrencyLimit, concurrencyUsage FROM account` (or equivalent)
   - Response: `{ scheduled_scripts: {...}, map_reduce_jobs: {...}, concurrency: {...}, stale_records: {...} }`
   - Auth: same `authManager.createAuthMiddleware()` pattern as EDI monitor routes
   - **Response caching:** 5-minute TTL at gateway level to prevent SuiteQL governance exhaustion on retries

   ### Research Insight: Gateway Caching
   ```javascript
   const CACHE_TTL_MS = 5 * 60 * 1000;
   let cachedResult = null, cacheTimestamp = 0;
   router.get('/api/health/netsuite', auth, async (req, res) => {
     if (cachedResult && Date.now() - cacheTimestamp < CACHE_TTL_MS) return res.json(cachedResult);
     // ... execute SuiteQL queries
     cachedResult = result; cacheTimestamp = Date.now();
     res.json(result);
   });
   ```

2. **Celigo ExportB — NetSuite health**
   - New HTTP export in Celigo flow calling `GET http://gateway:3001/api/health/netsuite`
   - preSavePage hook: `netsuite_health_collector.js` (NEW) — formats response into pipeline record with `isNetSuiteHealth: true` flag
   - Add as second page generator (run sequentially after ExportA)
   - **Gateway must be robust:** If NetSuite SuiteQL fails, gateway returns `{ status: 'unknown', error: '...' }` with HTTP 200 (not 4xx/5xx). This prevents ExportB failure from halting the entire flow.

   ### Research Insight: Page Generator Failure Isolation
   With `runPageGeneratorsInParallel: false`, a failed page generator likely stops the flow. The gateway endpoint MUST return HTTP 200 with degraded data rather than error codes. The `netsuite_health_collector.js` preSavePage maps `status: 'unknown'` appropriately.

3. **Update dashboard_payload_builder.js**
   - Accumulate NetSuite health record alongside Celigo data
   - On trigger record: include `systems.netsuite` in the payload
   - Status thresholds: any failed scripts/jobs = `error`, pending > 5 = `warning`, else `healthy`

4. **Update AI Agent prompt**
   - File: Celigo AI Agent import (`698b4eb6adf72c4591f9685f`) → `aiAgent.openai.instructions`
   - Add NetSuite context: "You also receive NetSuite scheduled script and map/reduce job status..."
   - Instruct AI to include NetSuite health in its narrative summary

5. **Web dashboard NetSuite card**
   - File: `src/features/health-orchestrator/routes/HealthOrchestratorRoute.tsx`
   - Replace "Coming soon" placeholder with real NetSuite data from snapshot

6. **Update record_type_filter.js documentation**
   - Add code comment: "New record types (isNetSuiteHealth) are implicitly skipped by both filters — this is intentional."

#### Phase 3: EDI + Dashboard Self-Health + CeligoHealthWorker Retirement

> **Merged from original Phase 3 + Phase 4.** EDI monitoring, dashboard self-health, and CeligoHealthWorker retirement are combined because self-health is ~4 lines of code and retirement depends on completing the action data migration.

**Tasks:**

1. **EDI status aggregation endpoint**
   - File: `~/B2bDashboard/server/routes/edi-status.ts` (NEW)
   - Mount at `/api/edi/status`
   - **Auth: Apply `requireApiKey` pattern (NOT "no auth required")** — Celigo ExportC includes API key in headers
   - MongoDB aggregation on `edi_transactions`:
     - Documents today: group by `document_type`, count where `created_at` > start of day (UTC)
     - Stuck: count where `status` = `RECEIVED` or `PARSED` and `updated_at` > 1 hour ago
     - Parser errors: count where `status` = `ERROR` and `created_at` > last 24 hours
     - Queue depth: count where `status` IN (`RECEIVED`, `PARSED`, `VALIDATED`) — not yet `PROCESSED`
   - Response: `{ documents_today: {...}, stuck: N, parser_errors: N, queue_depth: N }`
   - **Pre-create indexes before deployment:**
     ```
     { created_at: -1, document_type: 1, status: 1 }
     { status: 1, updated_at: 1 }
     ```

   ### Research Insight: Weekend False Positives
   "Stuck" detection using `updated_at > 1 hour ago` will flag Friday evening documents on Saturday morning. Consider adding a `business_hours_only` flag or only alerting on stuck during weekdays. Alternatively, increase the stuck threshold on weekends to 4 hours.

2. **Celigo ExportC — EDI health**
   - New HTTP export in Celigo flow calling `GET http://dashboard:3002/api/edi/status`
   - preSavePage hook: `edi_health_collector.js` (NEW) — formats into pipeline record with `isEdiHealth: true`
   - Add as third page generator
   - **Same HTTP 200 resilience pattern as ExportB** — endpoint returns degraded data, not HTTP errors

3. **Update dashboard_payload_builder.js**
   - Accumulate EDI health record
   - On trigger record: include `systems.edi` in payload
   - Status thresholds: stuck > 0 or parser_errors > 5 = `error`, parser_errors 1-5 = `warning`, else `healthy`

4. **Dashboard self-health enrichment (simplified)**
   - File: `server/routes/health-ingest.ts`
   - On ingest: auto-inject `systems.dashboard` with minimal health check:
   ```typescript
   snapshot.systems.dashboard = {
     status: mongoose.connection.readyState === 1 ? 'healthy' : 'error',
     uptime_hours: Math.floor(process.uptime() / 3600),
   };
   ```
   - If the server processes the ingest POST successfully, it is healthy. Do not over-instrument.

5. **Web dashboard EDI + Dashboard cards**
   - Replace "Coming soon" placeholders with real data from snapshot
   - Click EDI card → navigate to existing EDI dashboard
   - Click Celigo card → navigate to `/celigo-health` (existing detail page)

6. **Resolve/Retry action migration**
   - **Critical path for CeligoHealthWorker retirement**
   - Refactor Slack button handler to call Celigo API directly using `flowId` + `expOrImpId` from `health_snapshots.systems.celigo.errors` array
   - The `health_snapshots` errors array already contains `flow_id`, `exp_or_imp_id`, `num_error` — sufficient for button actions
   - The existing Celigo webhook flow (`slack_webhook_parser.js`) continues to handle button dispatch
   - **The change:** Slack App Home reads error data for button rendering from `health_snapshots` instead of `celigo_health_snapshots`

7. **CeligoHealthWorker retirement**
   - Prerequisites (reduced from 4 to 2):
     - [ ] Resolve/Retry actions work via `health_snapshots` error data (task 6 above)
     - [ ] All UI reads exclusively from `health_snapshots` (summary + action buttons)
   - **Stability gate:** 1 week of stable parallel operation (not 2 weeks — discrepancies surface within days)
   - **Reconciliation:** Daily comparison script comparing `health_snapshots.systems.celigo` against `celigo_health_snapshots` error counts, logging discrepancies
   - Retirement steps:
     - Set `CELIGO_HEALTH_CHECK_INTERVAL_MS=0` to disable polling
     - Remove CeligoHealthWorker from `unified-edi-server.ts` initialization
     - Drop `celigo_health_snapshots` collection after 30-day retention
     - Remove `celigo_activity_log` collection
     - Remove `CeligoHealthWorker.ts`, `CeligoHealthRepository.ts` (old)
   - **Rollback:** Re-enable CeligoHealthWorker via env var if issues found

8. **Enable Slack notifications**
   - Flip `HEALTH_ORCHESTRATOR_NOTIFICATIONS_ENABLED=true`
   - CeligoHealthWorker notifications now disabled (worker retired)
   - No duplicate notification risk

9. **Performance: Filter disabled standalone flows**
   - File: `plugins/celigo-integration/scripts/flow_data_processor.js`
   - Skip disabled flows: `if (flow.disabled === true) continue;`
   - If 30% of standalone flows are disabled, eliminates ~30 HTTP calls, saving ~6 seconds per flow run

## Acceptance Criteria

### Functional Requirements

- [ ] Slack App Home shows AI summary from `health_snapshots` when available
- [ ] Slack App Home shows per-flow Resolve/Retry buttons (from CeligoHealthWorker during parallel period)
- [ ] Web dashboard `/health` route renders multi-system status cards
- [ ] Web dashboard updates in real-time via Socket.IO when new snapshot arrives
- [ ] Slack channel notification fires on health status transitions (feature-flagged)
- [ ] `/api/health/latest` returns the most recent snapshot (requires session auth)
- [ ] `/api/health/history` returns time-range filtered snapshots with pagination (requires session auth)
- [ ] Out-of-order snapshots rejected with 409 Conflict
- [ ] PP5 Slack fallback fires when dashboard is unreachable
- [ ] External dead man's switch alerts when no snapshot ingested for 20+ minutes
- [ ] NetSuite health data appears in snapshot (Phase 2)
- [ ] EDI pipeline health data appears in snapshot (Phase 3)
- [ ] Dashboard self-health auto-injected into every snapshot (Phase 3)
- [ ] CeligoHealthWorker retired after 1-week stability gate (Phase 3)

### Non-Functional Requirements

- [ ] Socket.IO connections require authentication
- [ ] GET endpoints require session auth
- [ ] API key comparison uses `timingSafeEqual`
- [ ] Socket.IO reconnection recovers state (latest snapshot sent on re-subscribe)
- [ ] Slack App Home stays within 100-block limit (truncate error list if needed)
- [ ] health_snapshots TTL: 90-day retention (already configured in schema)
- [ ] `raw_payload` removed from production ingests
- [ ] History queries exclude `raw_payload` via projection
- [ ] "Last updated" timestamp visible on web dashboard with stale indicators
- [ ] Socket.IO connection status indicator on web dashboard (green/red dot)
- [ ] EDI status endpoint requires API key auth

### Quality Gates

- [ ] All existing Celigo health Slack App Home functionality preserved during parallel period
- [ ] CeligoHealthWorker not retired until all prerequisites met
- [ ] No duplicate Slack notifications (feature flag prevents during parallel period)
- [ ] Zero data loss during migration (both collections populated during parallel period)
- [ ] Daily reconciliation script confirms data consistency during parallel period

## Dependencies & Prerequisites

| Dependency | Status | Blocking |
|---|---|---|
| `POST /api/health/ingest` endpoint | Complete | No |
| `health_snapshots` MongoDB schema + repository | Complete | No |
| `dashboard_payload_builder.js` deployed to Celigo | Complete | No |
| `record_type_filter.js` preMap hooks on PP0-PP2 | Complete | No |
| Celigo flow producing clean snapshots (0 errors) | Complete | No |
| Docker container running with `HEALTH_INGEST_API_KEY` | Complete | No |
| NetSuite RESTlet 2655 (SuiteQL proxy) | Exists | Phase 2 |
| `edi_transactions` MongoDB collection | Exists | Phase 3 |
| Socket.IO infrastructure in unified-edi-server.ts | Exists | No |

## Risk Analysis & Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| CeligoHealthWorker and orchestrator show conflicting data | User confusion | Keep both during parallel period; clearly label data source in UI |
| 15-min cadence too slow for critical errors | Delayed response | CeligoHealthWorker (60s) stays for fast polling during parallel; consider 5-min Celigo schedule post-retirement |
| Slack App Home exceeds 100-block limit | Render failure | Use overflow menus; truncate error list dynamically |
| Dashboard down → no health notifications | Silent failures | PP5 pipeline-field-gated Slack fallback + external dead man's switch |
| NetSuite SuiteQL governance limits | Query failures | 5-min cache at gateway; return HTTP 200 with degraded status |
| Concurrent Celigo flow runs (>15 min execution) | Out-of-order snapshots | Server-side timestamp comparison; reject stale snapshots (409) |
| Page generator failure halts entire flow | NetSuite/EDI outage blocks Celigo monitoring | Gateway endpoints return HTTP 200 with degraded data, never error codes |
| Socket.IO unauthenticated | Data exposure | Add auth middleware before Phase 1b deployment |
| Duplicate Slack notifications during parallel | Notification spam | Feature flag `HEALTH_ORCHESTRATOR_NOTIFICATIONS_ENABLED=false` until retirement |
| Weekend EDI "stuck" false positives | Unnecessary alerts | Increase stuck threshold on weekends or restrict to business hours |

## File Inventory

### Phase 1b — Consumer Wiring (B2bDashboard)

| Action | File | Description |
|--------|------|-------------|
| MODIFY | `server/routes/health-ingest.ts` | Security hardening, room-based Socket.IO, out-of-order rejection, Slack notification, dead man's switch ping, raw_payload removal |
| MODIFY | `server/unified-edi-server.ts` | Socket.IO auth middleware, CORS allowedHeaders |
| NEW | `src/features/health-orchestrator/api/healthSnapshotApi.ts` | RTK Query API slice with streaming Socket.IO update |
| NEW | `src/features/health-orchestrator/routes/HealthOrchestratorRoute.tsx` | Multi-system health dashboard page |
| MODIFY | `src/services/slack/SlackAppHomeService.ts` | Multi-system summary blocks, batched publish, overflow menus |
| MODIFY | `src/services/slack/SlackSocketModeHandler.ts` | Dual-source with parallelized reads |
| MODIFY | `src/services/mongodb/repositories/healthSnapshotRepository.ts` | History projection, summary mode |
| MODIFY | `src/App.tsx` (or navigation) | Add "System Health" route |
| MODIFY (Celigo) | Flow `698b4a31ae386aee54914746` | Add PP5 Slack fallback import |
| NEW (Celigo) | `plugins/celigo-integration/scripts/dashboard_fallback_preMap.js` | PP5 preMap: skip if _dashboardDelivered |

### Phase 2 — NetSuite Monitoring

| Action | File | Description |
|--------|------|-------------|
| NEW | `~/NetSuiteApiGateway/routes/netsuite-health.js` | SuiteQL health queries with 5-min cache |
| MODIFY | `~/NetSuiteApiGateway/server.js` | Mount netsuite-health route |
| NEW | `plugins/celigo-integration/scripts/netsuite_health_collector.js` | preSavePage for ExportB |
| MODIFY | `plugins/celigo-integration/scripts/dashboard_payload_builder.js` | Add systems.netsuite accumulation |
| MODIFY | `plugins/celigo-integration/scripts/record_type_filter.js` | Add documentation comment for Phase 2 safety |
| Celigo | ExportB (new) + flow update | HTTP export calling gateway |

### Phase 3 — EDI + Self-Health + Retirement

| Action | File | Description |
|--------|------|-------------|
| NEW | `~/B2bDashboard/server/routes/edi-status.ts` | EDI aggregation endpoint with API key auth |
| MODIFY | `~/B2bDashboard/server/unified-edi-server.ts` | Mount edi-status route |
| NEW | `plugins/celigo-integration/scripts/edi_health_collector.js` | preSavePage for ExportC |
| MODIFY | `plugins/celigo-integration/scripts/dashboard_payload_builder.js` | Add systems.edi accumulation |
| MODIFY | `~/B2bDashboard/server/routes/health-ingest.ts` | Auto-inject systems.dashboard (4 lines) |
| MODIFY | `~/B2bDashboard/src/features/health-orchestrator/routes/HealthOrchestratorRoute.tsx` | EDI + Dashboard cards, drill-downs |
| MODIFY | `~/B2bDashboard/src/services/slack/SlackAppHomeService.ts` | Migrate button data to health_snapshots |
| DELETE | `~/B2bDashboard/src/services/celigo/CeligoHealthWorker.ts` | Retire after prerequisites met |
| Celigo | ExportC (new) + flow update | HTTP export calling dashboard |

## Removed from Scope (YAGNI)

These items were in the original plan but removed after simplicity review:

| Item | Reason | Alternative |
|------|--------|-------------|
| Alert configuration UI | One user, known preferences | Hard-code notification logic (~15 lines) |
| Trend charts per system | No demonstrated need for historical visualization | Query `health_snapshots` via mongosh if needed |
| 60s RTK Query polling fallback | Data changes every 15 min; Socket.IO push sufficient | Fetch on mount + streaming update |
| "Re-enable Slack PP" fallback | Infeasible — JS hooks are sandboxed, cannot make HTTP requests | PP5 pipeline-field-gated fallback |
| Dashboard self-health with memory/workers | If ingest responds, server is healthy | 4-line connection state check |
| `process.memoryUsage()` monitoring | Self-evident from server responsiveness | Omit |

**Estimated LOC prevention:** ~700-900 lines never written, tested, or maintained.

## References & Research

### Internal References

- Brainstorm: `/home/tchow/.claude/plans/rippling-questing-charm.md`
- Previous plan: `docs/plans/2026-02-19-feat-celigo-aggregated-health-digest-plan.md`
- Health ingest route: `~/B2bDashboard/server/routes/health-ingest.ts`
- Health snapshot schema: `~/B2bDashboard/src/services/mongodb/schemas/healthSnapshotSchema.ts`
- Slack App Home service: `~/B2bDashboard/src/services/slack/SlackAppHomeService.ts`
- Socket mode handler: `~/B2bDashboard/src/services/slack/SlackSocketModeHandler.ts`
- CeligoHealthWorker: `~/B2bDashboard/src/services/celigo/CeligoHealthWorker.ts`
- Web health route: `~/B2bDashboard/src/features/celigo-health/routes/CeligoHealthRoute.tsx`
- RTK Query API: `~/B2bDashboard/src/features/celigo-health/api/celigoHealthApi.ts`
- Gateway health: `~/NetSuiteApiGateway/server.js` (GET /health, /health/detailed)
- EDI monitor routes: `~/NetSuiteApiGateway/routes/edi-monitor.js`
- EDI schema: `~/B2bDashboard/src/services/mongodb/schemas/ediDocumentSchema.ts`

### Institutional Learnings (docs/solutions/)

- [Pipeline field persistence](../solutions/integration-issues/pipeline-field-persistence-premap-vs-export-CeligoIntegration-20260224.md) — Export-stage fields persist; preMap output doesn't. **Critical for PP5 fallback design.**
- [Cross-routing preMap filters](../solutions/integration-issues/cross-routing-premap-filter-CeligoIntegration-20260226.md) — preMap hooks on import resources, not flow. **Phase 2/3 records are implicitly safe.**
- [Response mapping array drop](../solutions/integration-issues/response-mapping-array-drop-CeligoIntegration-20260223.md) — Use postResponseMap for arrays
- [AI Agent response mapping](../solutions/integration-issues/ai-agent-response-mapping-CeligoIntegration-20260219.md) — Map _text explicitly
- [Celigo PUT full-replace](../solutions/integration-issues/celigo-put-full-replace-CeligoIntegration-20260219.md) — Always fetch-merge-PUT

### External Research Sources

- Socket.IO v4: Connection State Recovery, Room-Based Subscription
- MongoDB: TTL Indexes, Time Series vs Regular Collections (regular is correct at this scale)
- Slack Block Kit: Table block (Aug 2025), Overflow menus, 100-block App Home limit
- RTK Query: Streaming Updates with `onCacheEntryAdded` + `updateCachedData`
- Dead Man's Switch: healthchecks.io for external heartbeat monitoring
- Migration: Strangler Fig pattern, reconciliation during parallel period

### Key Celigo Resource IDs

- Flow: `698b4a31ae386aee54914746`
- ExportA: `699cc1e34b3ef6068b901796`
- PP0 (int errors): `699cc1f2dbb446adf7704298`
- PP1 (flow errors): `699cc1f7dbb446adf77044e3`
- PP2 (int names): `699cc1f95c5197579cbf5971`
- PP3 (AI Agent): `698b4eb6adf72c4591f9685f`
- PP4 (Dashboard): `699f5ff47237f1bf5c60e70a`
- PP4 (Slack, preserved for PP5): `699c7192dbb446adf74f7216`
- Dashboard connection: `699f5fe87237f1bf5c60e107`
- Record type filter script: `699fb7ae783ea4efe781991e`
- Dashboard payload builder script: `699f5fd9dbb446adf77cd8c2`
