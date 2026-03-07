# Brainstorm: Celigo MCP via n8n Orchestration Layer

**Date**: 2026-03-07
**Status**: Decided — proceeding with n8n
**Topic**: What capabilities should the Celigo MCP expose, and where should it be hosted?

---

## What We're Building

A unified **read-only MCP server** giving org members natural language access to Celigo integration monitoring and analytics via Claude Desktop. Three user personas:

- **Ops/Support**: "Are there integration errors?", "What flows ran last night?"
- **Integration Builders**: "Show me the flow definition for X", "What connections does this flow use?"
- **Business Analysts**: "Which trading partners have the most failures?", "How many records processed this week?"

---

## Why We're Building It

The org currently has:
- On-prem Docker gateway (single point of failure, reliability concern)
- Multiple disconnected platforms: Celigo, DXT extensions, n8n plugin, health digest
- No unified MCP layer — org members can't ask Claude about integration health

We want scalable AI infrastructure that grows with the org.

---

## Key Decisions

### 1. Hosting: n8n over Celigo Tool Builder

**Decision**: Host the MCP in n8n, not Celigo's native Tool Builder.

**Why n8n wins**:
- Full code execution (JS + Python) — Celigo's Tool Builder is sandboxed (no HTTP, no regex)
- Cross-system by nature — wraps any API (Celigo, NetSuite, Slack, dashboards in one MCP server)
- Free self-hosted, unlimited executions vs Tool Builder's cloud-only managed service
- Native MCP Server Trigger node — expose any workflow as an MCP tool
- Visual debugging with per-node input/output and full execution history
- EDI analytics: full regex parsing (port Python logic directly) vs naming conventions only
- n8n already hosted on Portainer — zero new infrastructure

**Trade-off accepted**: Hosting burden (we manage Docker) is acceptable given we're moving gateway to cloud anyway.

### 2. Access: Read-only

**Decision**: All 37 tools are read-only. No writes (no retry, run, resolve, delete, create, update).

**Why**: Safe for broad org access. No risk of accidentally running flows or modifying configs.

**Write access preserved**: Celigo DXT extension (18 tools, 2 writable) stays for admin/power users.

### 3. Scope: Comprehensive 37 tools in 8 groups

**Decision**: Start with all 37 Celigo read tools, extend to cross-system (NetSuite, Slack, dashboard) in Wave 3.

**Groups**:
1. Integration Discovery (4)
2. Flow Inspection (6)
3. Error Investigation (5)
4. Job History & Analytics (5)
5. Resource Inspection (7)
6. Reference Data & State (5)
7. Account & Access (2)
8. EDI Analytics (3)

### 4. EDI Tools: Full Regex Parsing

**Decision**: Port Python `_parse_edi_integration()` and `_extract_doc_type()` to n8n Code nodes.

**Why**: n8n Code nodes run full JavaScript. Regex staging detection (`\(\d{1,2}/\d{1,2}/\d{4}\)$`) and doc type extraction (`\b(8[0-9]{2}|9[0-9]{2}|7[0-9]{2})\b`) work natively — no compromises on accuracy.

### 5. Rollout: Prototype First

**Decision**: Validate n8n MCP capabilities with 3 prototype workflows before committing to all 37.

**Prototype tools**:
- `list_step_errors` — simple single API call (baseline validation)
- `get_integration_summary` — composite 4 API calls (chaining validation)
- `get_edi_health_dashboard` — 27+ API calls with EDI regex (stress test)

**Escalation path**: If Tool Builder composites fail → simplify to single-API-call tools. If n8n MCP is too slow → move EDI dashboard to API gateway endpoint.

### 6. Coexistence (No Deprecation)

- **Celigo DXT** (18 tools, 2 writable): Admin/power users for writes
- **n8n MCP** (37+ tools, read-only): Org-wide read access
- **NetSuite SuiteQL DXT**: Unchanged (calls cloud gateway)
- **NetSuite AI Connector**: Unchanged (native SuiteApp)

---

## Infrastructure Decisions

### Gateway Cloud Migration (parallel workstream)

**Decision**: Migrate NetSuite API Gateway from on-prem Docker to Railway (or Fly.io).

**Why**: On-prem is a single point of failure. NetSuite is already on Oracle Cloud — gateway should be cloud-side too for lower latency, auto-restart, and health checks.

**Effort**: Low — gateway is already Docker-ready. Deploy same Dockerfile to Railway, update DNS.

**Redis**: Managed add-on (Railway Redis or Upstash).

**Sequencing**: Parallel with n8n MCP buildout.

### n8n Hosting

n8n already runs on Portainer (same Tailscale network as dev server). No new infrastructure needed. Claude Desktop connects via n8n-mcp npm package (SSE → stdio proxy) already in the n8n plugin.

---

## Open Questions (to resolve during prototype)

1. **MCP Server Trigger node format**: Exact parameter structure for tool name/description/schema may need adjustment based on the installed n8n version.
2. **Response size**: Can we apply field stripping (whitelist pattern from `extensions/celigo/src/server.py:_slim()`) in a Code node between the HTTP Request and workflow response?
3. **EDI dashboard concurrency**: Does n8n handle 25 sequential error API calls within acceptable latency? (SplitInBatches + loop pattern may be needed.)

---

## Reference Files

| File | Purpose |
|------|---------|
| `extensions/celigo/src/server.py:519-545` | `_parse_edi_integration()` + `_extract_doc_type()` to port to JS |
| `extensions/celigo/src/server.py:105-125` | `_LIST_KEEP` whitelist + `_slim()` to port to JS |
| `plugins/celigo-integration/skills/celigo-integrator/references/errors.md` | Unified error path (no `/exports/` prefix) |
| `plugins/celigo-integration/skills/celigo-integrator/references/flows.md` | Flow endpoints: `/descendants`, `/jobs/latest`, `/audit` |
| `plugins/n8n-integration/skills/n8n-workflow-builder/references/node-patterns.md` | HTTP Request, Code, IF, Merge node JSON formats |
| `~/NetSuiteApiGateway/` | Gateway to migrate to cloud |
