---
title: "feat: Build edi-ops n8n MCP Workflow for EDI Business Process Visibility"
type: feat
status: active
date: 2026-03-08
brainstorm: docs/brainstorms/2026-03-08-edi-ops-mcp-tools-brainstorm.md
---

# ✨ feat: Build edi-ops n8n MCP Workflow for EDI Business Process Visibility

## Overview

Build a new n8n MCP workflow (`edi-ops`) exposing 7 business-process tools for non-technical ops users to answer EDI questions like "did all Academy 850 POs become NetSuite orders last week?" — using natural language partner names, cross-referencing Celigo flow execution data with NetSuite EDI Transaction History records.

This is a **new, separate workflow** alongside the existing `celigo-tools` (which remains unchanged for IT/dev users).

## Problem Statement

The existing 37-tool `celigo-tools` MCP is optimal for integration developers who know Celigo internals. Ops/business users need to answer business-process questions across EDI transaction types (850 POs, 856 ASNs, 810 invoices, 846 inventory updates) and confirm records were created in NetSuite — but today this requires IT involvement or manually digging through Celigo dashboards.

## Proposed Solution

A `create_edi_ops_mcp.py` script (modeled after `create_celigo_mcp.py`) that generates and deploys an n8n workflow with 7 toolCode nodes connected to an MCP Server Trigger. Each tool accepts business-vocabulary parameters (`partner_name`, `start_date`, `end_date`) and returns exception-first summaries combining Celigo job execution data + NetSuite SuiteQL EDI Transaction History counts.

## Technical Approach

### Architecture

```
User / Claude
    │
    ▼
edi-ops MCP (n8n workflow, separate from celigo-tools)
    │
    ├─ list_edi_partners      ─── Partner lookup cache (Celigo lookup cache)
    ├─ check_order_processing ─── Celigo jobs (850 IB flows) + NS EDI TH (doctype=850)
    ├─ check_asn_compliance   ─── Celigo jobs (856 OB flows) + NS EDI TH (doctype=856)
    ├─ check_invoice_transmission ─── Celigo jobs (810 OB flows) + NS EDI TH (doctype=810)
    ├─ check_inventory_updates ─── Celigo jobs (846 OB flows) + NS EDI TH (doctype=846)
    ├─ get_partner_status     ─── Composite of all 4 doc types for one partner
    └─ get_edi_daily_summary  ─── All partners, all doc types summary
         │                              │
         ▼                              ▼
   Celigo API                    NetSuite Gateway
   https://api.integrator.io/v1  https://nsapi.twistedx.tech/api/suiteapi
```

### Key Technical Constraints (from institutional knowledge)

- **All tools expose `{input: string}` schema** — DynamicTool calling convention. Args wrapped as JSON string.
- **`this.helpers.httpRequest()` only** — NOT `fetch()`. n8n NodeVM sandbox restriction.
- **Parameter extraction**: `const params = JSON.parse(query || '{}');` in all toolCode.
- **NetSuite gateway**: POST to `https://nsapi.twistedx.tech/api/suiteapi` with `X-API-Key` header. Cloud-accessible from n8n.
- **Celigo jobs API date filter**: Only `createdAt_gte` supported (Unix epoch ms). Filter by execution time client-side after fetch.
- **Staging flows**: Always exclude flows matching `/\(\d{1,2}\/\d{1,2}\/\d{4}\)$/` (staging suffix).
- **`GET /v1/exports` and `/v1/imports` are unusable** — return ~67MB, hit 25MB limit. Do not call these.
- **Celigo errors API is current-state only** — not historical. Use job records for date-range queries.

### Tool Inventory

| Tool | Params | Celigo Call | NetSuite Call |
|------|--------|-------------|---------------|
| `list_edi_partners` | none | `GET /integrations` → regex parse | none |
| `check_order_processing` | partner_name, start_date, end_date | 850 IB flow jobs | EDI TH doctype=850 |
| `check_asn_compliance` | partner_name, start_date, end_date | 856 OB flow jobs | EDI TH doctype=856 |
| `check_invoice_transmission` | partner_name, start_date, end_date | 810 OB flow jobs | EDI TH doctype=810 |
| `check_inventory_updates` | partner_name, start_date, end_date | 846 OB flow jobs | EDI TH doctype=846 |
| `get_partner_status` | partner_name, start_date, end_date | all 4 doc types | all 4 doc types |
| `get_edi_daily_summary` | start_date, end_date | all partners × all types | all partners × all types |

### Data Sources

**Celigo:**
- `GET /v1/integrations` — list all integrations, filter by EDI regex for partner flows
- `GET /v1/jobs?_flowId={id}&type=flow&limit=100` — job history for a flow
- Filter jobs client-side by `startedAt` range converted from ISO date string to epoch ms

**NetSuite EDI Transaction History (SuiteQL):**
```sql
SELECT id, custrecord_edi_doctype, custrecord_edi_partner, custrecord_edi_trandate
FROM customrecord_edi_transaction_history
WHERE custrecord_edi_doctype = {DOCTYPE_ID}
  AND custrecord_edi_partner = (
    SELECT id FROM customrecord_edi_trading_partner WHERE name = '{partner_name}'
  )
  AND custrecord_edi_trandate >= '{start_date}'
  AND custrecord_edi_trandate <= '{end_date}'
```

> ⚠️ **Discovery required during implementation**: Exact NetSuite custom record internal names (`customrecord_*` and `custrecord_*`) must be confirmed via SuiteQL schema inspection before building queries. DOCTYPE_MAP from `netsuite-edi/server.py`: 850→3, 856→5, 810→1, 846→2.

**Partner Lookup Table:**
```json
{
  "Academy": {
    "celigo_integration_id": "<id>",
    "asn_sla_hours": 24
  },
  ...
}
```
Stored as a **Celigo lookup cache** (accessible via `get_lookup_cache` from existing tools; no external config files needed).

### Output Format (Exception-First)

```json
{
  "partner": "Academy",
  "doc_type": "850 - Purchase Order",
  "period": "2026-03-01 to 2026-03-07",
  "celigo": {
    "flows_checked": 2,
    "jobs_ran": 15,
    "records_succeeded": 47,
    "records_errored": 3,
    "flows_disabled": 0
  },
  "netsuite": {
    "transactions_found": 44
  },
  "discrepancy": {
    "detected": true,
    "gap": 3,
    "note": "Celigo reports 47 successes; NetSuite shows 44 EDI transactions. 3 records may not have been created in NetSuite."
  },
  "errors_current": 3
}
```

## Implementation Phases

### Phase 1: Infrastructure & Discovery (prerequisite)

**Tasks:**

- [ ] Verify NetSuite gateway reachability from n8n toolCode: `this.helpers.httpRequest({method:'POST', url:'https://nsapi.twistedx.tech/api/suiteapi', ...})`
- [ ] Discover NetSuite custom record internal names via SuiteQL: query `SELECT scriptId, name FROM customrecordtype WHERE name LIKE '%EDI%'` and `SELECT id, scriptId, label FROM customrecordfield WHERE rectype = {edi_th_type_id}`
- [ ] Confirm NETSUITE_API_KEY value available in n8n credentials (or hardcode in toolCode if already in memory)
- [ ] Create partner lookup cache in Celigo with all 19 EDI partners + asn_sla_hours per partner
- [ ] Create `plugins/n8n-integration/scripts/create_edi_ops_mcp.py` skeleton based on `create_celigo_mcp.py`

**Critical files:**
- `plugins/n8n-integration/scripts/create_celigo_mcp.py` — template to follow
- `extensions/netsuite-suiteql/src/server.py:158-199` — NetSuite gateway call pattern
- `extensions/netsuite-edi/src/server.py:49-67` — DOCTYPE_MAP reference

### Phase 2: Core Tools — list_edi_partners + check_order_processing

**Tasks:**

- [ ] Implement `list_edi_partners` toolCode:
  - `GET /v1/integrations` from Celigo
  - Apply EDI regex `/^(.+?)\s*-\s*EDI\s+(\d{3})\s+(IB|OB|INB)\b/i`
  - Exclude staging integrations (date suffix regex)
  - Return deduplicated partner names + doc types available per partner
  - Hint in description: "Call this first if you don't know the exact partner name"

- [ ] Implement `check_order_processing` toolCode:
  - Validate `partner_name`, `start_date`, `end_date` (ISO 8601 → epoch ms)
  - Guard: max 90-day range; `start_date < end_date`
  - Exclude staging flows by default
  - Celigo: get integration ID from lookup table → find 850 IB flows → fetch jobs → filter by date → aggregate counts + flag disabled flows
  - NetSuite: SuiteQL EDI Transaction History for doctype=850, partner, date range
  - Return exception-first output with discrepancy detection

- [ ] Generate workflow JSON via `create_edi_ops_mcp.py --wave 0` (2 tools)
- [ ] Upload to n8n, verify MCP tools appear at new `edi-ops` SSE endpoint
- [ ] Test via MCP: call `list_edi_partners`, then `check_order_processing` for one known partner

**New file:** `plugins/n8n-integration/scripts/create_edi_ops_mcp.py`

### Phase 3: Remaining 5 Tools

**Tasks:**

- [ ] Implement `check_asn_compliance` toolCode:
  - Same pattern as `check_order_processing` but doctype=856 OB flows
  - Read `asn_sla_hours` from partner lookup table
  - Add `sla_compliance` section to output: jobs within SLA vs exceeded (using `startedAt` field)
  - Note: SLA clock starts at Celigo job start (earliest available proxy for receipt time)

- [ ] Implement `check_invoice_transmission` toolCode:
  - Doctype=810 OB flows
  - Celigo job counts + NS EDI TH for doctype=810

- [ ] Implement `check_inventory_updates` toolCode:
  - Doctype=846 OB flows
  - List inventory records from NS EDI TH for doctype=846 (item-level detail if available)

- [ ] Implement `get_partner_status` toolCode:
  - Calls all 4 doc-type checks sequentially for one partner
  - Returns consolidated status object with health indicator per doc type

- [ ] Implement `get_edi_daily_summary` toolCode:
  - Iterates all partners from lookup table
  - Runs `get_partner_status`-equivalent per partner
  - Returns ranked summary (most errors first)
  - Include timeout guard: skip partner if API calls exceed 5 seconds each

- [ ] Update `create_edi_ops_mcp.py` to include all 7 tools, redeploy workflow

### Phase 4: Deploy & Register

**Tasks:**

- [ ] Add `edi-ops` bridge entry to `celigo_mcp_bridge.py` (or create `edi_ops_mcp_bridge.py`)
- [ ] Register new MCP in `plugins/n8n-integration/plugin.json` as a second `mcpServers` entry:
  ```json
  "edi-ops": {
    "command": "python3",
    "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/edi_ops_mcp_bridge.py"]
  }
  ```
- [ ] Add to `marketplace.json` or plugin config for easy install
- [ ] Document usage examples in `plugins/n8n-integration/skills/n8n-workflow-builder/SKILL.md` or new `edi-ops-guide.md`

## Acceptance Criteria

### Functional

- [ ] `list_edi_partners` returns all 19 active EDI partners with their available doc types (no staging entries)
- [ ] `check_order_processing("Academy", "2026-03-01", "2026-03-07")` returns Celigo job counts + NS EDI TH counts for 850 POs in that window, with discrepancy flag if counts differ
- [ ] All tools fail gracefully when partner_name not found — return candidate list from `list_edi_partners`, not an error
- [ ] All tools exclude staging flows by default (flows with date suffix)
- [ ] Tools correctly distinguish "zero records processed" from "no flows ran at all"
- [ ] `check_asn_compliance` includes per-partner SLA assessment using `asn_sla_hours` from lookup table
- [ ] `get_edi_daily_summary` completes within n8n toolCode execution timeout (no single partner blocks the call)

### Non-Functional

- [ ] Date parameters: ISO 8601 format (`YYYY-MM-DD`), max 90-day range enforced
- [ ] All toolCode uses `this.helpers.httpRequest()` not `fetch()`
- [ ] All tools expose `{input: string}` schema (DynamicTool calling convention)
- [ ] Staging flows excluded by default, not by user flag
- [ ] Output is exception-first: failures and discrepancies shown before success counts
- [ ] NetSuite queries gracefully return `{netsuite: {unavailable: true, reason: "..."}}` if gateway call fails

## Dependencies & Prerequisites

- Celigo lookup cache created with all 19 partner entries + ASN SLA hours
- NetSuite API Gateway accessible at `https://nsapi.twistedx.tech` from n8n (verify before coding)
- NetSuite custom record internal names for EDI Transaction History discovered via SuiteQL
- Existing `create_celigo_mcp.py` patterns understood (toolCode JS, `build_workflow()`, `tool_http()`, `tool_code()`)
- n8n API key for workflow upload

## Risk Analysis

| Risk | Impact | Mitigation |
|------|--------|------------|
| NS custom record names differ from expected | Blocking for Phase 2 | Run discovery SuiteQL in Phase 1 before writing tool code |
| NetSuite gateway not reachable from n8n | Blocking for all NS queries | Test HTTP call from toolCode sandbox in Phase 1 as first step |
| Celigo jobs API `limit` insufficient for large date ranges | Missing records in aggregate | Paginate with `skip` parameter in toolCode (FIXME: confirm Celigo jobs API supports pagination) |
| `get_edi_daily_summary` times out across 19 partners | Tool unusable | Add per-partner timeout guard; return partial results with `{timed_out: true}` for slow partners |
| Aggregate-only comparison (no PO-level matching) | Gap between Celigo count and NS count unexplainable | Document clearly in tool output: "aggregate counts only; individual PO tracing not available" |

## Files to Create / Modify

**New files:**
- `plugins/n8n-integration/scripts/create_edi_ops_mcp.py` — main tool generator
- `plugins/n8n-integration/scripts/edi_ops_mcp_bridge.py` — SSE/stdio bridge for edi-ops endpoint
- `plugins/n8n-integration/workflows/edi-ops/edi-ops-wave1.json` — generated workflow (output of script)

**Modified files:**
- `plugins/n8n-integration/plugin.json` — add `edi-ops` to `mcpServers`

## References

### Internal
- `plugins/n8n-integration/scripts/create_celigo_mcp.py:74-110` — `tool_http()` / `tool_code()` builder functions
- `plugins/n8n-integration/scripts/create_celigo_mcp.py:593-665` — EDI regex and parse_edi_flows pattern
- `plugins/n8n-integration/scripts/celigo_mcp_bridge.py:31-110` — SSE bridge pattern to replicate
- `extensions/netsuite-suiteql/src/server.py:158-199` — NetSuite gateway POST pattern
- `extensions/netsuite-edi/src/server.py:49-67` — DOCTYPE_MAP (850→3, 856→5, 810→1, 846→2)
- `docs/solutions/integration-issues/mcp-tool-calling-convention-n8n-MCP-20260308.md` — calling convention constraints

### Key Gotchas to Avoid
- Do NOT call `GET /v1/exports` or `GET /v1/imports` — 67MB response, hits 25MB limit
- Do NOT use `fetch()` in toolCode — use `this.helpers.httpRequest()`
- Do NOT use `main` connection type — must use `ai_tool` for MCP tools
- Do NOT default date ranges — require explicit start/date from user
- Do NOT include staging flows (date-suffix regex must always be applied)
