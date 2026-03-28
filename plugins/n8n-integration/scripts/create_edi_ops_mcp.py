#!/usr/bin/env python3
"""
Create EDI Ops MCP workflow in n8n.

Builds a separate n8n workflow for non-technical ops/business users to answer
EDI business process questions like "did all Academy 850 POs become NetSuite
orders?" — cross-referencing Celigo flow execution data with NetSuite EDI
Transaction History records.

This is a NEW workflow separate from celigo-tools (which serves IT/dev users).

Tools:
  list_edi_partners         - List all EDI trading partners and their doc types
  check_order_processing    - 850 POs: did inbound POs flow to NetSuite?
  check_asn_compliance      - 856 ASNs: were ASNs sent on time?
  check_invoice_transmission- 810 invoices: did invoices transmit?
  check_inventory_updates   - 846 inventory: what styles were sent?
  get_partner_status        - Full status for one partner (all doc types)
  get_edi_daily_summary     - All partners summary for a date range

NetSuite field names (from customrecord_twx_edi_history):
  Record: customrecord_twx_edi_history
  Date:   h.created
  Type:   h.custrecord_twx_edi_type (850=3, 856=5, 810=1, 846=2)
  Partner link: h.custrecord_twx_eth_edi_tp → customrecord_twx_edi_tp.id
  Partner name: tp.name

Usage:
    python3 create_edi_ops_mcp.py              # Create Wave 1 (all 7 tools)
    python3 create_edi_ops_mcp.py --dry-run    # Print workflow JSON only
    python3 create_edi_ops_mcp.py --wave 0     # Wave 0 (2 tools: list + 850)
"""

import json
import os
import sys
import uuid
import urllib.request
import urllib.error
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from n8n_config import get_api_credentials

# Celigo config
CELIGO_API_KEY = "252f7167e58f4d369fffb658662bff43"
CELIGO_BASE = "https://api.integrator.io/v1"

# NetSuite gateway (no auth required — internal network)
NS_GATEWAY_URL = "https://nsapi.twistedx.tech/api/suiteapi"
NS_ACCOUNT = "twistedx"
NS_ENVIRONMENT = "production"

# Workflow config
WORKFLOW_NAME = "EDI Ops MCP: Wave 1 (7 tools)"
MCP_PATH = "edi-ops"


def uid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# n8n API helpers
# ---------------------------------------------------------------------------

def n8n_api(method, path, n8n_url, n8n_key, data=None):
    """Make a request to the n8n API. Returns parsed JSON."""
    full_url = f"{n8n_url.rstrip('/')}/{path.lstrip('/')}"
    headers = {
        "X-N8N-API-KEY": n8n_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(full_url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Tool node builders
# ---------------------------------------------------------------------------

def tool_code(name, description, js_code):
    """Build a toolCode node (JavaScript, full logic, arbitrary HTTP calls)."""
    return {
        "id": uid(),
        "name": name,
        "type": "@n8n/n8n-nodes-langchain.toolCode",
        "typeVersion": 1,
        "position": [0, 0],
        "parameters": {
            "name": name,
            "description": description,
            "language": "javaScript",
            "jsCode": js_code,
        },
    }


def mcp_trigger(path):
    """Build an MCP Server Trigger node."""
    return {
        "id": uid(),
        "name": "MCP Server Trigger",
        "type": "@n8n/n8n-nodes-langchain.mcpTrigger",
        "typeVersion": 1,
        "position": [0, 0],
        "webhookId": uid(),
        "parameters": {
            "authentication": "none",
            "path": path,
        },
    }


# ---------------------------------------------------------------------------
# Shared JS helpers injected into every toolCode snippet
# ---------------------------------------------------------------------------

# These constants are substituted into every JS snippet via Python f-strings
_CHDRS = f"{{Authorization: 'Bearer {CELIGO_API_KEY}'}}"
_CBASE = CELIGO_BASE
_NS_GW = NS_GATEWAY_URL
_NS_ACCT = NS_ACCOUNT
_NS_ENV = NS_ENVIRONMENT

# JS header for common constants (injected at top of each snippet)
_JS_COMMONS = f"""
const EDI_RE = /^(.+?)\\s*-\\s*EDI\\s+(\\d{{3}})\\s+(IB|OB|INB)\\b/i;
const STAGING_RE = /\\(\\d{{1,2}}\\/\\d{{1,2}}\\/\\d{{4}}\\)$/;
const CHDRS = {{Authorization: 'Bearer {CELIGO_API_KEY}'}};
const CBASE = '{CELIGO_BASE}';
const NS_GW = '{NS_GATEWAY_URL}';
// DOCTYPE_MAP: EDI doc code → NetSuite custrecord_twx_edi_type internal ID
const DOCTYPE_NS = {{'850': 3, '856': 5, '810': 1, '846': 2}};
// NS SuiteQL helper: returns parsed response object
async function nsQuery(sql) {{
  return await this.helpers.httpRequest({{
    method: 'POST', url: NS_GW,
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{action: 'queryRun', procedure: 'queryRun', query: sql,
      params: [], returnAllRows: false,
      netsuiteAccount: '{NS_ACCOUNT}', netsuiteEnvironment: '{NS_ENVIRONMENT}'}})
  }});
}}
""".strip()

# Note: nsQuery uses `this.helpers.httpRequest` which means `this` context matters.
# In toolCode, `this` is bound at the top level. nsQuery is defined as an arrow-function
# alternative or we use it inline. Actually, regular function declarations in JS
# do NOT capture `this` from the outer scope, so we inline NS queries instead.


# ---------------------------------------------------------------------------
# JavaScript snippets
# ---------------------------------------------------------------------------

# --- Tool 1: list_edi_partners ---

JS_LIST_EDI_PARTNERS = f"""
// Lists all active EDI trading partners from Celigo flow names.
// No input required — pass empty object {{}}.
const EDI_RE = /^(.+?)\\s*-\\s*EDI\\s+(\\d{{3}})\\s+(IB|OB|INB)\\b/i;
const STAGING_RE = /\\(\\d{{1,2}}\\/\\d{{1,2}}\\/\\d{{4}}\\)$/;
const CHDRS = {{Authorization: 'Bearer {CELIGO_API_KEY}'}};
try {{
  const flows = await this.helpers.httpRequest({{method: 'GET', url: '{CELIGO_BASE}/flows', headers: CHDRS}});
  const partners = {{}};
  (Array.isArray(flows) ? flows : []).forEach(f => {{
    const m = f.name.match(EDI_RE);
    if (!m || STAGING_RE.test(f.name)) return;
    const p = m[1].trim();
    const dt = m[2];
    const dir = m[3].toUpperCase();
    if (!partners[p]) partners[p] = {{name: p, doc_types: [], flow_count: 0, disabled_count: 0}};
    const label = dt + '_' + (dir === 'INB' ? 'IB' : dir);
    if (!partners[p].doc_types.includes(label)) partners[p].doc_types.push(label);
    partners[p].flow_count++;
    if (f.disabled) partners[p].disabled_count++;
  }});
  const list = Object.values(partners)
    .map(p => ({{...p, doc_types: p.doc_types.sort()}}))
    .sort((a, b) => a.name.localeCompare(b.name));
  return JSON.stringify({{
    partner_count: list.length,
    partners: list,
    tip: 'Use the name field exactly in check_order_processing, check_asn_compliance, etc.',
  }});
}} catch(e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()


# --- Shared validation + partner-flow-lookup helper (inlined per tool) ---

def _js_validate_and_find_flows(doc_code, directions):
    """
    Returns JS code fragment that:
    1. Validates partner_name, start_date, end_date params
    2. Fetches flows and finds matching flows for this partner/doc/direction
    3. Returns early with error if partner not found
    Sets: partnerName, startDate, endDate, startMs, endMs, matchingFlows
    """
    dir_check = " || ".join([f"m[3].toUpperCase() === '{d}'" for d in directions])
    return f"""
const params = JSON.parse(query || '{{}}');
const partnerName = params.partner_name;
const startDate = params.start_date;
const endDate = params.end_date;
if (!partnerName || !startDate || !endDate) {{
  return JSON.stringify({{error: 'Required: {{"partner_name": "Academy", "start_date": "2026-03-01", "end_date": "2026-03-07"}}'}});
}}
const startMs = Date.parse(startDate + 'T00:00:00Z');
const endMs = Date.parse(endDate + 'T23:59:59Z');
if (isNaN(startMs) || isNaN(endMs)) return JSON.stringify({{error: 'Invalid date. Use YYYY-MM-DD'}});
if (startMs > endMs) return JSON.stringify({{error: 'start_date must be before or equal to end_date'}});
if ((endMs - startMs) > 90 * 86400000) return JSON.stringify({{error: 'Date range exceeds 90-day maximum'}});
const EDI_RE = /^(.+?)\\s*-\\s*EDI\\s+(\\d{{3}})\\s+(IB|OB|INB)\\b/i;
const STAGING_RE = /\\(\\d{{1,2}}\\/\\d{{1,2}}\\/\\d{{4}}\\)$/;
const CHDRS = {{Authorization: 'Bearer {CELIGO_API_KEY}'}};
const pLower = partnerName.toLowerCase().trim();
const allFlows = await this.helpers.httpRequest({{method: 'GET', url: '{CELIGO_BASE}/flows', headers: CHDRS}});
const allFlowList = Array.isArray(allFlows) ? allFlows : [];
const matchingFlows = allFlowList.filter(f => {{
  const m = f.name.match(EDI_RE);
  if (!m || STAGING_RE.test(f.name)) return false;
  return m[1].trim().toLowerCase() === pLower && m[2] === '{doc_code}' && ({dir_check});
}});
if (matchingFlows.length === 0) {{
  const allPartners = [...new Set(allFlowList
    .filter(f => f.name.match(EDI_RE) && !STAGING_RE.test(f.name))
    .map(f => f.name.match(EDI_RE)[1].trim()))].sort();
  return JSON.stringify({{
    error: `No {doc_code} flows found for partner "${{partnerName}}"`,
    suggestion: 'Call list_edi_partners to see available partners',
    sample_partners: allPartners.slice(0, 10),
  }});
}}
""".strip()


def _js_aggregate_celigo_jobs(doc_code):
    """Returns JS fragment to aggregate Celigo job counts across matchingFlows.
    Uses _flowId (not flow_id) and ISO date comparison (not epoch ms)."""
    return f"""
let totalJobs = 0, totalSuccess = 0, totalError = 0, flowsDisabled = 0;
const flowsChecked = matchingFlows.length;
matchingFlows.forEach(f => {{ if (f.disabled) flowsDisabled++; }});
// Fetch all flow jobs in parallel (_flowId is the correct param; flow_id is ignored by Celigo)
const allJobResults = await Promise.all(matchingFlows.map(async flow => {{
  try {{
    return await this.helpers.httpRequest({{
      method: 'GET',
      url: `{CELIGO_BASE}/jobs?_flowId=${{flow._id}}&type=flow&createdAt_gte=${{startDate}}&limit=200`,
      headers: CHDRS,
    }});
  }} catch(e) {{ return []; }}
}}));
allJobResults.forEach(jobs => {{
  (Array.isArray(jobs) ? jobs : []).filter(j => {{
    // Timestamps are ISO strings (e.g. "2026-03-02T14:00:00Z") — compare by date prefix
    const d = (j.startedAt || j.createdAt || '').slice(0, 10);
    return d >= startDate && d <= endDate;
  }}).forEach(j => {{
    totalJobs++;
    totalSuccess += (j.numSuccess || 0);
    totalError += (j.numError || 0);
  }});
}});
""".strip()


def _js_query_ns(doc_code, ns_type_id, return_count_only=True):
    """Returns JS fragment to query NetSuite EDI TH. Sets nsCount/nsError."""
    count_select = "COUNT(*) AS cnt" if return_count_only else "h.id, h.created, tp.name AS partner"
    return f"""
let nsCount = null, nsError = null;
const safePName = partnerName.replace(/'/g, "''").toUpperCase();
const nsSql = `SELECT {count_select} FROM customrecord_twx_edi_history h LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id WHERE h.custrecord_twx_edi_type = {ns_type_id} AND UPPER(tp.name) LIKE '%${{safePName}}%' AND h.created >= TO_DATE('${{startDate}}', 'YYYY-MM-DD') AND h.created < TO_DATE('${{endDate}}', 'YYYY-MM-DD') + 1`;
try {{
  const nsResp = await this.helpers.httpRequest({{
    method: 'POST', url: '{NS_GATEWAY_URL}',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{action: 'queryRun', procedure: 'queryRun', query: nsSql,
      params: [], returnAllRows: false,
      netsuiteAccount: '{NS_ACCOUNT}', netsuiteEnvironment: '{NS_ENVIRONMENT}'}})
  }});
  if (nsResp && nsResp.success) {{
    const recs = (nsResp.data || {{}}).records || [];
    {"nsCount = recs.length > 0 ? parseInt(recs[0].cnt || recs[0].CNT || 0, 10) : 0;" if return_count_only else "nsCount = recs.length;"}
  }} else {{
    nsError = nsResp && nsResp.error ? JSON.stringify(nsResp.error) : 'NS query failed';
  }}
}} catch(e) {{ nsError = e.message; }}
""".strip()


def _js_query_ns_850():
    """NS query for 850 POs: validates every received PO has a linked Sales Order.
    Uses status=2 (success) to distinguish NS processing failures from SO-creation gaps.
    externalid format: HIST_{PO_number}_{PARTNER}_00 — PO number extractable from it."""
    return f"""
let ns850 = null, nsError = null;
const safePName = partnerName.replace(/'/g, "''").toUpperCase();
// Count query: break down by status and SO presence
const ns850Sql = `SELECT COUNT(*) AS total_received, SUM(CASE WHEN custrecord_twx_edi_history_status = 2 THEN 1 ELSE 0 END) AS ns_success, SUM(CASE WHEN custrecord_twx_edi_history_status != 2 THEN 1 ELSE 0 END) AS ns_failed, SUM(CASE WHEN custrecord_twx_edi_history_transaction IS NOT NULL THEN 1 ELSE 0 END) AS orders_created, SUM(CASE WHEN custrecord_twx_edi_history_status = 2 AND custrecord_twx_edi_history_transaction IS NULL THEN 1 ELSE 0 END) AS pos_without_order FROM customrecord_twx_edi_history h LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id WHERE h.custrecord_twx_edi_type = 3 AND UPPER(tp.name) LIKE '%${{safePName}}%' AND h.created >= TO_DATE('${{startDate}}', 'YYYY-MM-DD') AND h.created < TO_DATE('${{endDate}}', 'YYYY-MM-DD') + 1`;
try {{
  const nsResp = await this.helpers.httpRequest({{
    method: 'POST', url: '{NS_GATEWAY_URL}',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{action: 'queryRun', procedure: 'queryRun', query: ns850Sql,
      params: [], returnAllRows: false,
      netsuiteAccount: '{NS_ACCOUNT}', netsuiteEnvironment: '{NS_ENVIRONMENT}'}})
  }});
  if (nsResp && nsResp.success) {{
    const r = ((nsResp.data || {{}}).records || [])[0] || {{}};
    ns850 = {{
      pos_received: parseInt(r.total_received || r.TOTAL_RECEIVED || 0, 10),
      ns_processing_ok: parseInt(r.ns_success || r.NS_SUCCESS || 0, 10),
      ns_processing_failed: parseInt(r.ns_failed || r.NS_FAILED || 0, 10),
      orders_created: parseInt(r.orders_created || r.ORDERS_CREATED || 0, 10),
      pos_without_order: parseInt(r.pos_without_order || r.POS_WITHOUT_ORDER || 0, 10),
    }};
    // If any failures exist, fetch the specific PO numbers (up to 20)
    if (ns850.ns_processing_failed > 0 || ns850.pos_without_order > 0) {{
      const detailSql = `SELECT h.externalid, h.created, h.custrecord_twx_edi_history_status FROM customrecord_twx_edi_history h LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id WHERE h.custrecord_twx_edi_type = 3 AND UPPER(tp.name) LIKE '%${{safePName}}%' AND h.created >= TO_DATE('${{startDate}}', 'YYYY-MM-DD') AND h.created < TO_DATE('${{endDate}}', 'YYYY-MM-DD') + 1 AND (h.custrecord_twx_edi_history_status != 2 OR h.custrecord_twx_edi_history_transaction IS NULL) ORDER BY h.created DESC FETCH FIRST 20 ROWS ONLY`;
      try {{
        const detailResp = await this.helpers.httpRequest({{
          method: 'POST', url: '{NS_GATEWAY_URL}',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{action: 'queryRun', procedure: 'queryRun', query: detailSql,
            params: [], returnAllRows: false,
            netsuiteAccount: '{NS_ACCOUNT}', netsuiteEnvironment: '{NS_ENVIRONMENT}'}})
        }});
        if (detailResp && detailResp.success) {{
          // externalid = HIST_{{PO_number}}_{{PARTNER}}_00 — extract the PO number
          ns850.failed_pos = ((detailResp.data || {{}}).records || []).map(r => {{
            const eid = r.externalid || r.EXTERNALID || '';
            const poNum = eid.replace(/^HIST_/, '').split('_')[0];
            const status = parseInt(r.custrecord_twx_edi_history_status || r.CUSTRECORD_TWX_EDI_HISTORY_STATUS || 0);
            return {{ po_number: poNum, date: r.created || r.CREATED, reason: status === 2 ? 'no_sales_order_created' : `ns_processing_failed_status_${{status}}` }};
          }});
        }}
      }} catch(e) {{ /* detail query failed, continue without it */ }}
    }}
  }} else {{
    nsError = nsResp && nsResp.error ? JSON.stringify(nsResp.error) : 'NS query failed';
  }}
}} catch(e) {{ nsError = e.message; }}
""".strip()


def _js_build_result(doc_type_label, show_discrepancy=True):
    """Returns JS fragment that assembles the final result object and returns it."""
    discrepancy_block = """
  if (nsCount !== null) {
    const gap = totalSuccess - nsCount;
    result.discrepancy = {
      detected: gap !== 0,
      celigo_success: totalSuccess, netsuite_count: nsCount, gap,
      note: gap === 0 ? 'Counts match' : `Gap of ${Math.abs(gap)}: Celigo processed ${totalSuccess}, NetSuite shows ${nsCount} transactions`,
    };
  }
""" if show_discrepancy else ""

    return f"""
const result = {{
  partner: partnerName,
  doc_type: '{doc_type_label}',
  period: `${{startDate}} to ${{endDate}}`,
}};
if (flowsDisabled > 0) result.WARNING_flows_disabled = `${{flowsDisabled}}/${{flowsChecked}} flows are disabled`;
if (totalError > 0) result.ALERT_celigo_errors = `${{totalError}} job errors in Celigo for this period (check celigo-tools for details)`;
// Note: celigo records_succeeded counts line items/records processed, not document count.
// NS transactions_found is the source of truth for document-level counts.
result.celigo = {{flows_checked: flowsChecked, flows_disabled: flowsDisabled, jobs_ran: totalJobs, job_errors: totalError,
  note: 'records_succeeded counts line items processed, not document count'}};
result.netsuite = nsCount !== null ? {{transactions_found: nsCount}} : {{unavailable: true, reason: nsError}};
{discrepancy_block}
return JSON.stringify(result);
""".strip()


# --- Tool 2: check_order_processing (850 IB) ---
# 850 validation: Celigo SUM(numSuccess) = POs processed; NS check = POs received + SOs created.
# custrecord_twx_edi_history_transaction IS NULL means PO received but no Sales Order created.

_JS_BUILD_RESULT_850 = f"""
const result = {{
  partner: partnerName,
  doc_type: '850 - Purchase Order',
  period: `${{startDate}} to ${{endDate}}`,
}};
// Stage 1: Celigo job activity — job_errors may indicate POs that never reached NetSuite
if (flowsDisabled > 0) result.ALERT_flows_disabled = `${{flowsDisabled}}/${{flowsChecked}} Celigo flows are disabled`;
if (totalError > 0) result.ALERT_celigo_job_errors = `${{totalError}} Celigo job error(s) — some 850 batches may not have reached NetSuite`;
// Note: line_items_processed = Celigo numSuccess (EDI line items, not PO document count)
result.celigo = {{flows_checked: flowsChecked, flows_disabled: flowsDisabled, jobs_ran: totalJobs, line_items_processed: totalSuccess, job_errors: totalError}};
if (ns850 !== null) {{
  // Stage 2: NS processing failures — NS received the PO but failed to process it
  if (ns850.ns_processing_failed > 0) {{
    result.ALERT_ns_processing_failed = `${{ns850.ns_processing_failed}} PO(s) received by NetSuite but NS processing failed (status≠2)`;
  }}
  // Stage 3: SO creation gap — NS processed OK but no Sales Order was created
  if (ns850.pos_without_order > 0) {{
    result.ALERT_pos_without_so = `${{ns850.pos_without_order}} PO(s) received and processed by NetSuite but no Sales Order was created`;
  }}
  result.netsuite = {{
    pos_received: ns850.pos_received,
    ns_processing_ok: ns850.ns_processing_ok,
    ns_processing_failed: ns850.ns_processing_failed,
    orders_created: ns850.orders_created,
    pos_without_order: ns850.pos_without_order,
  }};
  if (ns850.failed_pos && ns850.failed_pos.length > 0) {{
    result.failed_po_details = ns850.failed_pos;
  }}
  const anyAlert = totalError > 0 || ns850.ns_processing_failed > 0 || ns850.pos_without_order > 0;
  result.validation = {{
    passed: !anyAlert,
    celigo_job_errors: totalError,
    ns_processing_failed: ns850.ns_processing_failed,
    ns_pos_without_order: ns850.pos_without_order,
    note: !anyAlert
      ? `All ${{ns850.pos_received}} PO(s) received in NetSuite were processed and have linked Sales Orders`
      : `Issues detected — see ALERT fields above. ${{ns850.orders_created}}/${{ns850.pos_received}} received POs have Sales Orders.`,
  }};
}} else {{
  result.netsuite = {{unavailable: true, reason: nsError}};
}}
return JSON.stringify(result);
""".strip()

_js_850_body = f"""
{_js_validate_and_find_flows('850', ['IB', 'INB'])}
{_js_aggregate_celigo_jobs('850')}
{_js_query_ns_850()}
{_JS_BUILD_RESULT_850}
""".strip()

JS_CHECK_ORDER_PROCESSING = f"""
try {{
{chr(10).join('  ' + line for line in _js_850_body.splitlines())}
}} catch(e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()


# --- Tool 3: check_asn_compliance (856 OB) ---

_JS_ASN_SLA_BLOCK = f"""
const asnSlaHours = params.asn_sla_hours || 24;
const slaMs = asnSlaHours * 3600000;
let jobsWithinSla = 0, jobsExceededSla = 0;
// SLA check: compare job duration (startedAt→endedAt) against slaMs per job run
const slaJobResults = await Promise.all(matchingFlows.map(async flow => {{
  try {{
    return await this.helpers.httpRequest({{
      method: 'GET',
      url: `{CELIGO_BASE}/jobs?_flowId=${{flow._id}}&type=flow&createdAt_gte=${{startDate}}&limit=200`,
      headers: CHDRS,
    }});
  }} catch(e) {{ return []; }}
}}));
slaJobResults.forEach(jobs => {{
  (Array.isArray(jobs) ? jobs : []).filter(j => {{
    const d = (j.startedAt || j.createdAt || '').slice(0, 10);
    return d >= startDate && d <= endDate;
  }}).forEach(j => {{
    if (j.startedAt && j.endedAt) {{
      const duration = new Date(j.endedAt) - new Date(j.startedAt);
      if (duration <= slaMs) jobsWithinSla++; else jobsExceededSla++;
    }}
  }});
}});
""".strip()

_JS_ASN_RESULT = f"""
const result = {{
  partner: partnerName,
  doc_type: '856 - Advance Ship Notice',
  period: `${{startDate}} to ${{endDate}}`,
  asn_sla_hours: asnSlaHours,
}};
if (flowsDisabled > 0) result.WARNING_flows_disabled = `${{flowsDisabled}}/${{flowsChecked}} flows are disabled`;
if (totalError > 0) result.ALERT_celigo_errors = `${{totalError}} job errors in Celigo (check celigo-tools for details)`;
// celigo.jobs_ran = number of Celigo job executions; job_errors = failed jobs.
// NS transactions_found is the document-level count of ASNs actually sent.
result.celigo = {{flows_checked: flowsChecked, flows_disabled: flowsDisabled, jobs_ran: totalJobs, job_errors: totalError}};
if (jobsWithinSla + jobsExceededSla > 0) {{
  const pct = Math.round(jobsWithinSla / (jobsWithinSla + jobsExceededSla) * 100);
  result.sla_compliance = {{within_sla: jobsWithinSla, exceeded_sla: jobsExceededSla, compliance_pct: pct, sla_hours: asnSlaHours}};
  if (jobsExceededSla > 0) result.ALERT_sla = `${{jobsExceededSla}} job(s) exceeded ${{asnSlaHours}}-hour SLA`;
}}
result.netsuite = nsCount !== null ? {{asns_sent: nsCount}} : {{unavailable: true, reason: nsError}};
return JSON.stringify(result);
""".strip()

JS_CHECK_ASN_COMPLIANCE = f"""
try {{
  {chr(10).join('  ' + line for line in (_js_validate_and_find_flows('856', ['OB', 'OUT']) + chr(10) + _js_aggregate_celigo_jobs('856') + chr(10) + _JS_ASN_SLA_BLOCK + chr(10) + _js_query_ns('856', 5, return_count_only=True) + chr(10) + _JS_ASN_RESULT).splitlines())}
}} catch(e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()


# --- Tool 4: check_invoice_transmission (810 OB) ---

JS_CHECK_INVOICE_TRANSMISSION = f"""
try {{
{chr(10).join('  ' + line for line in (_js_validate_and_find_flows('810', ['OB', 'OUT']) + chr(10) + _js_aggregate_celigo_jobs('810') + chr(10) + _js_query_ns('810', 1, return_count_only=True) + chr(10) + _js_build_result('810 - Invoice', show_discrepancy=False)).splitlines())}
}} catch(e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()


# --- Tool 5: check_inventory_updates (846 OB) ---
# Returns list of individual NS records (item-level detail if available)

_JS_NS_846_RECORDS = f"""
let nsCount = null, nsError = null, nsRecords = [];
const safePName = partnerName.replace(/'/g, "''").toUpperCase();
const nsSql = `SELECT h.id, h.created, tp.name AS partner FROM customrecord_twx_edi_history h LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id WHERE h.custrecord_twx_edi_type = 2 AND UPPER(tp.name) LIKE '%${{safePName}}%' AND h.created >= TO_DATE('${{startDate}}', 'YYYY-MM-DD') AND h.created < TO_DATE('${{endDate}}', 'YYYY-MM-DD') + 1 ORDER BY h.created DESC`;
try {{
  const nsResp = await this.helpers.httpRequest({{
    method: 'POST', url: '{NS_GATEWAY_URL}',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{action: 'queryRun', procedure: 'queryRun', query: nsSql,
      params: [], returnAllRows: false,
      netsuiteAccount: '{NS_ACCOUNT}', netsuiteEnvironment: '{NS_ENVIRONMENT}'}})
  }});
  if (nsResp && nsResp.success) {{
    nsRecords = (nsResp.data || {{}}).records || [];
    nsCount = nsRecords.length;
  }} else {{
    nsError = nsResp && nsResp.error ? JSON.stringify(nsResp.error) : 'NS query failed';
  }}
}} catch(e) {{ nsError = e.message; }}
""".strip()

_JS_846_RESULT = f"""
const result = {{
  partner: partnerName,
  doc_type: '846 - Inventory Advice',
  period: `${{startDate}} to ${{endDate}}`,
}};
if (flowsDisabled > 0) result.WARNING_flows_disabled = `${{flowsDisabled}}/${{flowsChecked}} flows are disabled`;
if (totalError > 0) result.ALERT_celigo_errors = `${{totalError}} records errored in Celigo for this period`;
result.celigo = {{flows_checked: flowsChecked, flows_disabled: flowsDisabled, jobs_ran: totalJobs, records_succeeded: totalSuccess, records_errored: totalError}};
result.netsuite = nsCount !== null ? {{transactions_found: nsCount, records: nsRecords.slice(0, 50)}} : {{unavailable: true, reason: nsError}};
return JSON.stringify(result);
""".strip()

JS_CHECK_INVENTORY_UPDATES = f"""
try {{
{chr(10).join('  ' + line for line in (_js_validate_and_find_flows('846', ['OB', 'OUT']) + chr(10) + _js_aggregate_celigo_jobs('846') + chr(10) + _JS_NS_846_RECORDS + chr(10) + _JS_846_RESULT).splitlines())}
}} catch(e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()


# --- Tool 6: get_partner_status (all 4 doc types) ---

JS_GET_PARTNER_STATUS = f"""
const params = JSON.parse(query || '{{}}');
const partnerName = params.partner_name;
const startDate = params.start_date;
const endDate = params.end_date;
if (!partnerName || !startDate || !endDate) {{
  return JSON.stringify({{error: 'Required: {{"partner_name": "Academy", "start_date": "2026-03-01", "end_date": "2026-03-07"}}'}});
}}
const startMs = Date.parse(startDate + 'T00:00:00Z');
const endMs = Date.parse(endDate + 'T23:59:59Z');
if (isNaN(startMs) || isNaN(endMs)) return JSON.stringify({{error: 'Invalid date. Use YYYY-MM-DD'}});
if (startMs > endMs) return JSON.stringify({{error: 'start_date must be before end_date'}});
if ((endMs - startMs) > 90 * 86400000) return JSON.stringify({{error: 'Date range exceeds 90-day maximum'}});
const EDI_RE = /^(.+?)\\s*-\\s*EDI\\s+(\\d{{3}})\\s+(IB|OB|INB)\\b/i;
const STAGING_RE = /\\(\\d{{1,2}}\\/\\d{{1,2}}\\/\\d{{4}}\\)$/;
const CHDRS = {{Authorization: 'Bearer {CELIGO_API_KEY}'}};
const pLower = partnerName.toLowerCase().trim();
// DOCTYPE_MAP: [docCode, nsTypeId, label, directions[]]
const DOC_TYPES = [
  ['850', 3, '850 - Purchase Order', ['IB', 'INB']],
  ['856', 5, '856 - ASN', ['OB', 'OUT']],
  ['810', 1, '810 - Invoice', ['OB', 'OUT']],
  ['846', 2, '846 - Inventory Advice', ['OB', 'OUT']],
];
const safe = partnerName.replace(/'/g, "''").toUpperCase();
async function checkDocType([docCode, nsTypeId, label, dirs], allFlowList) {{
  const flows = allFlowList.filter(f => {{
    const m = f.name.match(EDI_RE);
    if (!m || STAGING_RE.test(f.name)) return false;
    return m[1].trim().toLowerCase() === pLower && m[2] === docCode && dirs.includes(m[3].toUpperCase());
  }});
  if (flows.length === 0) return [docCode, {{label, status: 'no_flows'}}];
  // Fetch all flow jobs in parallel (_flowId is correct; flow_id is silently ignored)
  let jobs = 0, success = 0, errors = 0, disabled = 0;
  flows.forEach(f => {{ if (f.disabled) disabled++; }});
  const jobResults = await Promise.all(flows.map(async flow => {{
    try {{
      return await this.helpers.httpRequest({{
        method: 'GET',
        url: `{CELIGO_BASE}/jobs?_flowId=${{flow._id}}&type=flow&createdAt_gte=${{startDate}}&limit=200`,
        headers: CHDRS,
      }});
    }} catch(e) {{ return []; }}
  }}));
  jobResults.forEach(js => {{
    (Array.isArray(js) ? js : []).filter(j => {{
      const d = (j.startedAt || j.createdAt || '').slice(0, 10);
      return d >= startDate && d <= endDate;
    }}).forEach(j => {{ jobs++; success += (j.numSuccess||0); errors += (j.numError||0); }});
  }});
  // NS count
  let nsCount = null;
  try {{
    const nr = await this.helpers.httpRequest({{
      method: 'POST', url: '{NS_GATEWAY_URL}',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{action: 'queryRun', procedure: 'queryRun',
        query: `SELECT COUNT(*) AS cnt FROM customrecord_twx_edi_history h LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id WHERE h.custrecord_twx_edi_type = ${{nsTypeId}} AND UPPER(tp.name) LIKE '%${{safe}}%' AND h.created >= TO_DATE('${{startDate}}', 'YYYY-MM-DD') AND h.created < TO_DATE('${{endDate}}', 'YYYY-MM-DD') + 1`,
        params: [], returnAllRows: false,
        netsuiteAccount: '{NS_ACCOUNT}', netsuiteEnvironment: '{NS_ENVIRONMENT}'}})
    }});
    if (nr && nr.success) {{ const recs = (nr.data||{{}}).records||[]; nsCount = recs.length>0 ? parseInt(recs[0].cnt||recs[0].CNT||0) : 0; }}
  }} catch(e) {{ /* ns error */ }}
  const health = errors > 0 ? 'errors' : (disabled > 0 && flows.length === disabled ? 'all_disabled' : (success > 0 ? 'ok' : 'no_activity'));
  return [docCode, {{label, health, flows_count: flows.length, disabled, jobs_ran: jobs, records_succeeded: success, records_errored: errors, netsuite_count: nsCount}}];
}}
try {{
  const allFlows = await this.helpers.httpRequest({{method: 'GET', url: '{CELIGO_BASE}/flows', headers: CHDRS}});
  const allFlowList = Array.isArray(allFlows) ? allFlows : [];
  // Run all 4 doc-type checks in parallel
  const entries = await Promise.all(DOC_TYPES.map(dt => checkDocType.call(this, dt, allFlowList)));
  const statusByDoc = Object.fromEntries(entries);
  const hasErrors = Object.values(statusByDoc).some(d => d.records_errored > 0);
  const hasDisabled = Object.values(statusByDoc).some(d => d.disabled > 0);
  return JSON.stringify({{
    partner: partnerName,
    period: `${{startDate}} to ${{endDate}}`,
    overall_health: hasErrors ? 'errors_present' : (hasDisabled ? 'some_flows_disabled' : 'ok'),
    by_doc_type: statusByDoc,
  }});
}} catch(e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()


# --- Tool 7: get_edi_daily_summary (all partners) ---

JS_GET_EDI_DAILY_SUMMARY = f"""
const params = JSON.parse(query || '{{}}');
const startDate = params.start_date;
const endDate = params.end_date;
if (!startDate || !endDate) {{
  return JSON.stringify({{error: 'Required: {{"start_date": "2026-03-01", "end_date": "2026-03-07"}}'}});
}}
const startMs = Date.parse(startDate + 'T00:00:00Z');
const endMs = Date.parse(endDate + 'T23:59:59Z');
if (isNaN(startMs) || isNaN(endMs)) return JSON.stringify({{error: 'Invalid date. Use YYYY-MM-DD'}});
if (startMs > endMs) return JSON.stringify({{error: 'start_date must be before end_date'}});
if ((endMs - startMs) > 31 * 86400000) return JSON.stringify({{error: 'Date range exceeds 31-day maximum for summary (use shorter range or get_partner_status for one partner)'}});
const EDI_RE = /^(.+?)\\s*-\\s*EDI\\s+(\\d{{3}})\\s+(IB|OB|INB)\\b/i;
const STAGING_RE = /\\(\\d{{1,2}}\\/\\d{{1,2}}\\/\\d{{4}}\\)$/;
const CHDRS = {{Authorization: 'Bearer {CELIGO_API_KEY}'}};
const PARTNER_TIMEOUT = 8000; // ms per partner before skip
try {{
  // Get all flows and extract unique partners
  const allFlows = await this.helpers.httpRequest({{method: 'GET', url: '{CELIGO_BASE}/flows', headers: CHDRS}});
  const flowList = Array.isArray(allFlows) ? allFlows : [];
  const partners = [...new Set(flowList
    .filter(f => f.name.match(EDI_RE) && !STAGING_RE.test(f.name))
    .map(f => f.name.match(EDI_RE)[1].trim()))].sort();
  // Get NS error totals per partner for the period (one query, efficient)
  const safe = startDate.replace(/'/g, "''");
  const safeEnd = endDate.replace(/'/g, "''");
  let nsPartnerCounts = {{}};
  try {{
    const nsResp = await this.helpers.httpRequest({{
      method: 'POST', url: '{NS_GATEWAY_URL}',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{action: 'queryRun', procedure: 'queryRun',
        query: `SELECT tp.name AS partner, COUNT(*) AS cnt FROM customrecord_twx_edi_history h LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id WHERE h.created >= TO_DATE('${{safe}}', 'YYYY-MM-DD') AND h.created < TO_DATE('${{safeEnd}}', 'YYYY-MM-DD') + 1 GROUP BY tp.name ORDER BY cnt DESC`,
        params: [], returnAllRows: false,
        netsuiteAccount: '{NS_ACCOUNT}', netsuiteEnvironment: '{NS_ENVIRONMENT}'}})
    }});
    if (nsResp && nsResp.success) {{
      ((nsResp.data||{{}}).records||[]).forEach(r => {{ nsPartnerCounts[r.partner || r.PARTNER] = parseInt(r.cnt || r.CNT || 0); }});
    }}
  }} catch(e) {{ /* ns summary failed, continue */ }}
  // Get Celigo job counts per partner (aggregate from flow jobs)
  const summary = [];
  for (const partnerName of partners) {{
    const pLower = partnerName.toLowerCase();
    const pFlows = flowList.filter(f => {{
      const m = f.name.match(EDI_RE);
      return m && !STAGING_RE.test(f.name) && m[1].trim().toLowerCase() === pLower;
    }});
    let totalSuccess = 0, totalError = 0, disabledCount = 0;
    const tStart = Date.now();
    let timedOut = false;
    for (const flow of pFlows) {{
      if (flow.disabled) disabledCount++;
      if (Date.now() - tStart > PARTNER_TIMEOUT) {{ timedOut = true; break; }}
      try {{
        const jobs = await this.helpers.httpRequest({{
          method: 'GET',
          url: `{CELIGO_BASE}/jobs?_flowId=${{flow._id}}&type=flow&createdAt_gte=${{startDate}}&limit=100`,
          headers: CHDRS,
        }});
        (Array.isArray(jobs) ? jobs : []).filter(j => {{
          const d = (j.startedAt || j.createdAt || '').slice(0, 10);
          return d >= startDate && d <= endDate;
        }}).forEach(j => {{ totalSuccess += (j.numSuccess||0); totalError += (j.numError||0); }});
      }} catch(e) {{ /* skip */ }}
    }}
    // NS count (fuzzy match from pre-fetched summary)
    const nsCount = Object.entries(nsPartnerCounts).find(([k]) => k && k.toUpperCase().includes(partnerName.toUpperCase()));
    const partnerEntry = {{
      partner: partnerName,
      flow_count: pFlows.length, disabled_count: disabledCount,
      celigo_success: totalSuccess, celigo_errors: totalError,
      netsuite_count: nsCount ? nsCount[1] : null,
      status: totalError > 0 ? 'errors' : (disabledCount === pFlows.length && pFlows.length > 0 ? 'all_disabled' : 'ok'),
    }};
    if (timedOut) partnerEntry.warning = 'timed_out_partial_results';
    summary.push(partnerEntry);
  }}
  // Sort: errors first, then by partner name
  summary.sort((a, b) => (b.celigo_errors - a.celigo_errors) || a.partner.localeCompare(b.partner));
  const totalErrors = summary.reduce((s, p) => s + p.celigo_errors, 0);
  const partnersWithErrors = summary.filter(p => p.celigo_errors > 0).length;
  return JSON.stringify({{
    period: `${{startDate}} to ${{endDate}}`,
    summary: {{total_partners: partners.length, partners_with_errors: partnersWithErrors, total_celigo_errors: totalErrors}},
    partners: summary,
  }});
}} catch(e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()


# ---------------------------------------------------------------------------
# Wave builders
# ---------------------------------------------------------------------------

def build_wave0():
    """Wave 0: 2 tools — list_edi_partners + check_order_processing."""
    return [
        tool_code(
            "list_edi_partners",
            (
                "List all active EDI trading partners from Celigo flow names, with available "
                "document types (850_IB, 856_OB, 810_OB, 846_OB) and flow counts. "
                "No input required — pass empty object {}. "
                "CALL THIS FIRST if you don't know the exact partner name to use in other tools. "
                "Returns {partner_count, partners: [{name, doc_types, flow_count, disabled_count}]}."
            ),
            JS_LIST_EDI_PARTNERS,
        ),
        tool_code(
            "check_order_processing",
            (
                "Check if inbound 850 Purchase Orders from a trading partner were processed by Celigo "
                "and confirm count in NetSuite EDI Transaction History. "
                'Input JSON: {"partner_name": "Academy", "start_date": "2026-03-01", "end_date": "2026-03-07"}. '
                "Date format: YYYY-MM-DD. Max 90-day range. No default dates — always specify both. "
                "Returns Celigo job counts (records_succeeded, records_errored), NetSuite transaction count, "
                "and a discrepancy flag if counts differ. Exception-first: alerts appear before success counts. "
                "Call list_edi_partners first if partner name is unknown."
            ),
            JS_CHECK_ORDER_PROCESSING,
        ),
    ]


def build_wave1():
    """Wave 1: All 7 business-process tools."""
    return [
        tool_code(
            "list_edi_partners",
            (
                "List all active EDI trading partners from Celigo flow names, with available "
                "document types (850_IB, 856_OB, 810_OB, 846_OB) and flow counts. "
                "No input required — pass empty object {}. "
                "CALL THIS FIRST if you don't know the exact partner name to use in other tools. "
                "Returns {partner_count, partners: [{name, doc_types, flow_count, disabled_count}]}."
            ),
            JS_LIST_EDI_PARTNERS,
        ),
        tool_code(
            "check_order_processing",
            (
                "Check if inbound 850 Purchase Orders from a trading partner were processed by Celigo "
                "and confirm count in NetSuite EDI Transaction History. "
                'Input JSON: {"partner_name": "Academy", "start_date": "2026-03-01", "end_date": "2026-03-07"}. '
                "Date format: YYYY-MM-DD. Max 90-day range. No default dates — always specify both. "
                "Returns Celigo job counts (records_succeeded, records_errored), NetSuite transaction count, "
                "and a discrepancy flag if counts differ. Exception-first output."
            ),
            JS_CHECK_ORDER_PROCESSING,
        ),
        tool_code(
            "check_asn_compliance",
            (
                "Check if outbound 856 Advance Ship Notices were sent for a trading partner and assess SLA compliance. "
                'Input JSON: {"partner_name": "Academy", "start_date": "2026-03-01", "end_date": "2026-03-07", "asn_sla_hours": 24}. '
                "asn_sla_hours is optional (default 24). No default dates. "
                "Returns Celigo job counts, SLA compliance stats (within_sla vs exceeded_sla), and NetSuite ASN count. "
                "SLA clock measured from job start time (proxy for inbound PO receipt)."
            ),
            JS_CHECK_ASN_COMPLIANCE,
        ),
        tool_code(
            "check_invoice_transmission",
            (
                "Check if outbound 810 Invoices were transmitted to a trading partner. "
                'Input JSON: {"partner_name": "Academy", "start_date": "2026-03-01", "end_date": "2026-03-07"}. '
                "Date format: YYYY-MM-DD. Max 90-day range. No default dates. "
                "Returns Celigo job counts (succeeded, errored), NetSuite invoice transaction count, "
                "and discrepancy flag if Celigo and NetSuite counts differ."
            ),
            JS_CHECK_INVOICE_TRANSMISSION,
        ),
        tool_code(
            "check_inventory_updates",
            (
                "Check outbound 846 Inventory Advice transmissions to a trading partner. "
                'Input JSON: {"partner_name": "Academy", "start_date": "2026-03-01", "end_date": "2026-03-07"}. '
                "Date format: YYYY-MM-DD. Max 90-day range. No default dates. "
                "Returns Celigo job counts and a list of NetSuite EDI Transaction History records "
                "for 846 transmissions (up to 50 records with dates)."
            ),
            JS_CHECK_INVENTORY_UPDATES,
        ),
        tool_code(
            "get_partner_status",
            (
                "Get full EDI health status for a single trading partner across all document types "
                "(850 POs, 856 ASNs, 810 Invoices, 846 Inventory). "
                'Input JSON: {"partner_name": "Academy", "start_date": "2026-03-01", "end_date": "2026-03-07"}. '
                "Date format: YYYY-MM-DD. Max 90-day range. No default dates. "
                "Returns overall_health and per-doc-type breakdown with Celigo job counts and NetSuite counts. "
                "Useful for a complete partner health check in one call."
            ),
            JS_GET_PARTNER_STATUS,
        ),
        tool_code(
            "get_edi_daily_summary",
            (
                "Get a summary of EDI activity across ALL trading partners for a date range, "
                "ranked by errors (most errors first). "
                'Input JSON: {"start_date": "2026-03-01", "end_date": "2026-03-07"}. '
                "Date format: YYYY-MM-DD. Max 31-day range (use get_partner_status for longer ranges). "
                "No default dates — always specify both. "
                "Returns summary stats and per-partner breakdown with Celigo success/error counts and NetSuite counts."
            ),
            JS_GET_EDI_DAILY_SUMMARY,
        ),
    ]


# ---------------------------------------------------------------------------
# Workflow assembly (same pattern as create_celigo_mcp.py)
# ---------------------------------------------------------------------------

def assign_positions(tool_nodes):
    """Lay out tool nodes horizontally, trigger at the end."""
    spacing = 220
    for i, node in enumerate(tool_nodes):
        node["position"] = [-(len(tool_nodes) - i) * spacing, 0]


def build_workflow(tool_nodes, workflow_name, mcp_path):
    """Assemble full workflow JSON from tool nodes."""
    assign_positions(tool_nodes)
    trigger = mcp_trigger(mcp_path)
    trigger["position"] = [0, 0]

    connections = {}
    for node in tool_nodes:
        connections[node["name"]] = {
            "ai_tool": [[{"node": "MCP Server Trigger", "type": "ai_tool", "index": 0}]]
        }

    return {
        "name": workflow_name,
        "settings": {
            "executionOrder": "v1",
            "availableInMCP": True,
        },
        "nodes": tool_nodes + [trigger],
        "connections": connections,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Create EDI Ops MCP workflow in n8n")
    parser.add_argument("--dry-run", action="store_true", help="Print workflow JSON without creating")
    parser.add_argument("--wave", type=int, default=1, choices=[0, 1], help="0=2 tools, 1=all 7 tools (default)")
    parser.add_argument("--path", default=MCP_PATH, help=f"MCP path (default: {MCP_PATH})")
    parser.add_argument("--name", default=WORKFLOW_NAME, help="Workflow name")
    args = parser.parse_args()

    if args.wave == 0:
        tool_nodes = build_wave0()
        wf_name = "EDI Ops MCP: Wave 0 (2 tools)"
    else:
        tool_nodes = build_wave1()
        wf_name = args.name

    workflow = build_workflow(tool_nodes, wf_name, args.path)

    if args.dry_run:
        print(json.dumps(workflow, indent=2))
        return

    n8n_url, n8n_key = get_api_credentials()

    print(f"n8n:      {n8n_url}")
    print(f"Workflow: {wf_name}")
    print(f"Tools:    {len(tool_nodes)}")
    print(f"MCP path: /mcp/{args.path}/sse")
    print()

    print("Creating workflow...", end="", flush=True)
    try:
        result = n8n_api("POST", "workflows", n8n_url, n8n_key, data=workflow)
        wf_id = result["id"]
        print(f" {wf_id}")
    except urllib.error.HTTPError as e:
        print()
        print(f"ERROR: HTTP {e.code}", file=sys.stderr)
        print(e.read().decode("utf-8"), file=sys.stderr)
        sys.exit(1)

    print("Activating...", end="", flush=True)
    try:
        n8n_api("POST", f"workflows/{wf_id}/activate", n8n_url, n8n_key)
        print(" active")
    except urllib.error.HTTPError as e:
        print(f" WARNING: activation failed: HTTP {e.code}")

    base_url = n8n_url.rstrip("/")
    if base_url.endswith("/api/v1"):
        base_url = base_url[: -len("/api/v1")]

    print()
    print("=== EDI Ops workflow created ===")
    print(f"ID:   {wf_id}")
    print(f"SSE:  {base_url}/mcp/{args.path}/sse")
    print()
    print("Test:")
    print(f"  curl -N -H 'X-N8N-API-KEY: {n8n_key[:8]}...' '{base_url}/mcp/{args.path}/sse'")
    print()
    print("Bridge config (Claude Desktop):")
    print(f'  "edi-ops": {{"command": "python3", "args": ["/path/to/edi_ops_mcp_bridge.py"]}}')


if __name__ == "__main__":
    main()
