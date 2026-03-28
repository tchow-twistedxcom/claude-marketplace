---
date: 2026-03-08
topic: edi-ops-mcp-tools
---

# EDI Ops MCP Tools — Business Process Visibility

## What We're Building

A new set of MCP tools purpose-built for **non-technical ops/business users** who need to answer EDI business process questions like "did all customer POs become orders in NetSuite?" rather than "are there errors in flow X?"

The existing 37-tool Celigo MCP (`celigo-tools`) is technically correct but aimed at integration developers. This new tool set (working title: `edi-ops`) will be **business-process oriented**, cross-system (Celigo + NetSuite), and answer questions in business terms — not API terms.

## Current State Assessment

The existing `celigo-tools` n8n MCP workflow:
- **37 tools** across 8 groups: integration discovery, flow inspection, error investigation, resources, job history, scripts, users, EDI analytics
- All correctly wired with `ai_tool` connections and `{input: string}` calling convention
- Well-documented with clear descriptions — suitable for IT/dev users
- **Gap**: No cross-system NetSuite correlation; tool names are API-level, not business-level

**Verdict**: The existing tools are optimal for their intended audience (integration developers). The problem isn't the tools themselves — it's that ops users have different needs. Solution: a separate, dedicated tool set for ops.

## Why This Approach (Separate MCP Workflow)

Three options were considered:

**Option A: Add business tools to existing celigo-tools workflow**
- Pro: one endpoint, less setup
- Con: mixes technical + business tools; ops users would see 37+ confusing technical tools

**Option B: Separate `edi-ops` n8n MCP workflow** ← Recommended
- Pro: purpose-built for ops users; clean separation of concerns; can evolve independently
- Con: one more workflow to maintain

**Option C: One "mega tool" that returns everything**
- Pro: simplest interface
- Con: huge responses; harder to drill down; less composable for Claude

**Recommendation: Option B** — separate workflow. Ops users get a focused, business-vocabulary tool set. IT users keep their technical tools. Two audiences, two tool sets.

## Proposed Tool Inventory (6 tools)

Tools named in **business terms**, not API terms. Each tool calls both Celigo (did the flow run successfully?) and NetSuite (was the record actually created?) to provide cross-system answers.

| Tool | Business Question | Data Sources |
|------|------------------|--------------|
| `check_order_processing` | Did all inbound 850 POs become NetSuite orders? | Celigo 850 flow results + NS EDI Transaction History (doc_type=850) |
| `check_asn_compliance` | Were ASNs sent on time after shipment? | Celigo 856 flow results + NS EDI Transaction History (doc_type=856) |
| `check_invoice_transmission` | Did all invoices transmit successfully? | Celigo 810 flow results + NS EDI Transaction History (doc_type=810) |
| `check_inventory_updates` | What styles/inventory were sent to a partner (846)? | Celigo 846 flow results + NS EDI Transaction History (doc_type=846) |
| `get_partner_status` | What is the current EDI health for a specific partner? | All above, scoped to one partner |
| `get_edi_daily_summary` | What happened today across all partners? | All above, summarized |

**Priority**: Build `check_order_processing` first (850 → NS Sales Order) — highest business impact, revenue entry point.

## Key Decisions

- **Separate workflow**: `edi-ops` MCP lives alongside `celigo-tools`, not replacing it
- **Business vocabulary**: Tool names use business terms (orders, invoices, ASNs), not technical terms (exports, imports, pageProcessors)
- **Cross-system by default**: Every tool joins Celigo execution data with NetSuite record confirmation
- **Natural parameters**: Tools accept `partner_name` (human readable) and explicit `date` (no default — user must always specify), not `flow_id` or `_integrationId`
- **Exception-first output**: Lead with failures, not successes. "3 POs failed to process" before "47 processed successfully"
- **Partner config schema**: The partner lookup table stores `partner_name → celigo_integration_id` plus `asn_sla_hours` for per-partner ASN compliance thresholds

## Open Questions

None — all resolved.

## Resolved Questions

1. **Partner-to-flow mapping**: Maintain an explicit lookup table (partner name → Celigo integration ID) in n8n as a config or workflow variable. More reliable than regex parsing; requires manual upkeep when partners change.

2. **NetSuite EDI record**: There is a custom **EDI Transaction History** record in NetSuite with:
   - A `document_type` field (850, 856, 810, 846)
   - A link to the **EDI Trading Partner** record
   - This is the primary source for cross-system confirmation queries (SuiteQL against this record type).

3. **Date range**: No default. User must always specify the date range explicitly (e.g., "today", "2026-03-07"). Eliminates ambiguity.

4. **ASN timeliness threshold**: Per-partner SLA. Each trading partner has their own chargeback window. The partner lookup table (see #1) should include an `asn_sla_hours` field per partner.

5. **NetSuite API gateway**: Use the existing NS extension server (`netsuite-skills` plugin, SuiteQL endpoint). Auth via the same credentials used by existing netsuite tools. Confirm endpoint in plan phase.

## Next Steps
→ `/workflows:plan` for implementation details (start with `check_order_processing`)
