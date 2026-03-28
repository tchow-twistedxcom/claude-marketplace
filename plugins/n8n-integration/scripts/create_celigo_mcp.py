#!/usr/bin/env python3
"""
Create Celigo MCP workflow in n8n.

Builds a single n8n workflow with toolHttpRequest / toolCode nodes connected
to an MCP Server Trigger, exposing Celigo API operations as MCP tools for
Claude Desktop and other MCP clients.

Wave 0 (3 tools — validates architecture):
  list_integrations       - toolHttpRequest, no params
  list_step_errors        - toolCode, params: flow_id + step_id
  get_integration_summary - toolCode, composite: 3 parallel Celigo API calls

Wave 1 (20 tools — Groups 1-4):
  Integration Discovery, Flow Inspection, Error Investigation, Resources & Connections

Wave 2 (37 tools — Groups 1-8, Wave 1 + Groups 5-8):
  Adds: Job History, Scripts & Reference Data, Account & Access, EDI Analytics

Usage:
    python3 create_celigo_mcp.py              # Create and activate Wave 1 (default)
    python3 create_celigo_mcp.py --dry-run    # Print workflow JSON without creating
    python3 create_celigo_mcp.py --wave 2     # Create Wave 2 (37 tools, all groups)
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

# Celigo config (read-only tools — no writes)
CELIGO_API_KEY = "252f7167e58f4d369fffb658662bff43"
CELIGO_BASE = "https://api.integrator.io/v1"

# Workflow config
WORKFLOW_NAME = "Celigo MCP: Wave 0 Prototype"
MCP_PATH = "celigo-tools"


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

def tool_http(name, description, url, method="GET", extra_params=None):
    """Build a toolHttpRequest node (single API call, no dynamic params)."""
    params = {
        "toolDescription": description,
        "method": method,
        "url": url,
        "sendHeaders": True,
        "specifyHeaders": "json",
        "jsonHeaders": json.dumps({"Authorization": f"Bearer {CELIGO_API_KEY}"}),
    }
    if extra_params:
        params.update(extra_params)
    return {
        "id": uid(),
        "name": name,
        "type": "@n8n/n8n-nodes-langchain.toolHttpRequest",
        "typeVersion": 1.1,
        "position": [0, 0],
        "parameters": params,
    }


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
# JavaScript snippets (Wave 0)
# ---------------------------------------------------------------------------

JS_LIST_STEP_ERRORS = f"""
const params = JSON.parse(query || '{{}}');
const flowId = params.flow_id;
const stepId = params.step_id;
if (!flowId || !stepId) {{
  return JSON.stringify({{error: 'Required: {{"flow_id": "<id>", "step_id": "<export-or-import-id>"}}'  }});
}}
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET',
    url: `{CELIGO_BASE}/flows/${{flowId}}/${{stepId}}/errors`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  return JSON.stringify(data);
}} catch (e) {{
  return JSON.stringify({{error: e.message}});
}}
""".strip()


JS_GET_INTEGRATION_SUMMARY = f"""
const params = JSON.parse(query || '{{}}');
const integrationId = params.integration_id;
if (!integrationId) {{
  return JSON.stringify({{error: 'Required: {{"integration_id": "<id>"}}'  }});
}}
const base = '{CELIGO_BASE}';
const hdrs = {{Authorization: 'Bearer {CELIGO_API_KEY}'}};
try {{
  const integration = await this.helpers.httpRequest({{method: 'GET', url: `${{base}}/integrations/${{integrationId}}`, headers: hdrs}});
  const flows = await this.helpers.httpRequest({{method: 'GET', url: `${{base}}/flows?_integrationId=${{integrationId}}`, headers: hdrs}});
  const errors = await this.helpers.httpRequest({{method: 'GET', url: `${{base}}/integrations/${{integrationId}}/errors`, headers: hdrs}});
  const flowList = Array.isArray(flows) ? flows : [];
  const errorList = Array.isArray(errors) ? errors : [];
  return JSON.stringify({{
    integration,
    flows: flowList.map(f => ({{_id: f._id, name: f.name, disabled: f.disabled, lastModified: f.lastModified}})),
    errors: errorList,
    summary: {{
      flowCount: flowList.length,
      activeFlows: flowList.filter(f => !f.disabled).length,
      totalErrors: errorList.reduce((sum, e) => sum + (e.numError || 0), 0),
    }}
  }});
}} catch (e) {{
  return JSON.stringify({{error: e.message}});
}}
""".strip()


# ---------------------------------------------------------------------------
# Wave 1 JavaScript snippets (Groups 1-4, 17 new tools)
# ---------------------------------------------------------------------------

# --- Group 1: Integration Discovery ---

JS_GET_INTEGRATION = f"""
const params = JSON.parse(query || '{{}}');
const id = params.integration_id;
if (!id) return JSON.stringify({{error: 'Required: {{"integration_id": "<id>"}}'  }});
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/integrations/${{id}}`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  return JSON.stringify(data);
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_LIST_INTEGRATION_FLOWS = f"""
const params = JSON.parse(query || '{{}}');
const id = params.integration_id;
if (!id) return JSON.stringify({{error: 'Required: {{"integration_id": "<id>"}}'  }});
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/flows?_integrationId=${{id}}`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  const flows = Array.isArray(data) ? data : [];
  return JSON.stringify(flows.map(f => ({{_id: f._id, name: f.name, disabled: f.disabled, schedule: f.schedule, lastModified: f.lastModified}})));
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_LIST_INTEGRATION_ERRORS = f"""
const params = JSON.parse(query || '{{}}');
const id = params.integration_id;
if (!id) return JSON.stringify({{error: 'Required: {{"integration_id": "<id>"}}'  }});
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/integrations/${{id}}/errors`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  // [{{_flowId, numError, lastErrorAt}}]
  const list = Array.isArray(data) ? data : [];
  const withErrors = list.filter(e => e.numError > 0);
  return JSON.stringify({{
    integration_id: id,
    total_error_flows: withErrors.length,
    total_errors: withErrors.reduce((s, e) => s + e.numError, 0),
    flows: list,
  }});
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

# --- Group 2: Flow Inspection ---

JS_GET_FLOW = f"""
const params = JSON.parse(query || '{{}}');
const id = params.flow_id;
if (!id) return JSON.stringify({{error: 'Required: {{"flow_id": "<id>"}}'  }});
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/flows/${{id}}`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  return JSON.stringify(data);
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_GET_FLOW_LAST_RUN = f"""
const params = JSON.parse(query || '{{}}');
const id = params.flow_id;
if (!id) return JSON.stringify({{error: 'Required: {{"flow_id": "<id>"}}'  }});
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/flows/${{id}}/jobs/latest`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  return JSON.stringify(data);
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_GET_FLOW_STEP_ERROR_COUNTS = f"""
const params = JSON.parse(query || '{{}}');
const id = params.flow_id;
if (!id) return JSON.stringify({{error: 'Required: {{"flow_id": "<id>"}}'  }});
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/flows/${{id}}/errors`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  // {{flowErrors: [{{_expOrImpId, numError, lastErrorAt}}]}}
  const steps = (data.flowErrors || []);
  return JSON.stringify({{
    flow_id: id,
    total_errors: steps.reduce((s, e) => s + (e.numError || 0), 0),
    steps_with_errors: steps.filter(e => e.numError > 0).length,
    steps,
  }});
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_GET_FLOW_AUDIT_LOG = f"""
const params = JSON.parse(query || '{{}}');
const id = params.flow_id;
const limit = params.limit || 20;
if (!id) return JSON.stringify({{error: 'Required: {{"flow_id": "<id>"}}. Optional: {{"limit": 20}}'  }});
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/flows/${{id}}/audit`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  const entries = Array.isArray(data) ? data.slice(0, limit) : data;
  return JSON.stringify(entries);
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

# --- Group 3: Error Investigation ---

JS_LIST_FLOWS_WITH_ERRORS = f"""
const params = JSON.parse(query || '{{}}');
const id = params.integration_id;
if (!id) return JSON.stringify({{error: 'Required: {{"integration_id": "<id>"}}'  }});
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/integrations/${{id}}/errors`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  const withErrors = (Array.isArray(data) ? data : []).filter(e => e.numError > 0);
  return JSON.stringify({{integration_id: id, flows_with_errors: withErrors, count: withErrors.length}});
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_LIST_ALL_ERRORED_FLOWS = f"""
// No params — sweeps ALL integrations for flows with errors
try {{
  const integrations = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/integrations`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  const intList = Array.isArray(integrations) ? integrations : [];
  const results = [];
  for (const integration of intList) {{
    try {{
      const errors = await this.helpers.httpRequest({{
        method: 'GET', url: `{CELIGO_BASE}/integrations/${{integration._id}}/errors`,
        headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
      }});
      const withErrors = (Array.isArray(errors) ? errors : []).filter(e => e.numError > 0);
      if (withErrors.length > 0) {{
        results.push({{
          integration: {{_id: integration._id, name: integration.name}},
          flows_with_errors: withErrors,
          total_errors: withErrors.reduce((s, e) => s + e.numError, 0),
        }});
      }}
    }} catch(e) {{ /* skip failed integrations */ }}
  }}
  const grandTotal = results.reduce((s, r) => s + r.total_errors, 0);
  return JSON.stringify({{errored_integrations: results, integration_count: intList.length, grand_total_errors: grandTotal}});
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_GET_FLOW_HEALTH = f"""
const params = JSON.parse(query || '{{}}');
const id = params.flow_id;
if (!id) return JSON.stringify({{error: 'Required: {{"flow_id": "<id>"}}'  }});
const hdrs = {{Authorization: 'Bearer {CELIGO_API_KEY}'}};
try {{
  const flow = await this.helpers.httpRequest({{method: 'GET', url: `{CELIGO_BASE}/flows/${{id}}`, headers: hdrs}});
  const errors = await this.helpers.httpRequest({{method: 'GET', url: `{CELIGO_BASE}/flows/${{id}}/errors`, headers: hdrs}});
  const lastRun = await this.helpers.httpRequest({{method: 'GET', url: `{CELIGO_BASE}/flows/${{id}}/jobs/latest`, headers: hdrs}});
  const steps = errors.flowErrors || [];
  const totalErrors = steps.reduce((s, e) => s + (e.numError || 0), 0);
  return JSON.stringify({{
    flow: {{_id: flow._id, name: flow.name, disabled: flow.disabled, _integrationId: flow._integrationId, schedule: flow.schedule}},
    health: {{status: flow.disabled ? 'disabled' : 'enabled', totalErrors, stepsWithErrors: steps.filter(e => e.numError > 0)}},
    lastRun: Array.isArray(lastRun) ? lastRun[0] : lastRun,
  }});
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_GET_ALL_STEP_ERRORS = f"""
const params = JSON.parse(query || '{{}}');
const flowId = params.flow_id;
if (!flowId) return JSON.stringify({{error: 'Required: {{"flow_id": "<id>"}}'  }});
const hdrs = {{Authorization: 'Bearer {CELIGO_API_KEY}'}};
try {{
  const summary = await this.helpers.httpRequest({{method: 'GET', url: `{CELIGO_BASE}/flows/${{flowId}}/errors`, headers: hdrs}});
  const stepsWithErrors = (summary.flowErrors || []).filter(e => e.numError > 0);
  const results = [];
  for (const step of stepsWithErrors) {{
    try {{
      const stepErrors = await this.helpers.httpRequest({{
        method: 'GET', url: `{CELIGO_BASE}/flows/${{flowId}}/${{step._expOrImpId}}/errors`,
        headers: hdrs,
      }});
      results.push({{step_id: step._expOrImpId, numError: step.numError, errors: stepErrors.errors || stepErrors}});
    }} catch(e) {{ results.push({{step_id: step._expOrImpId, error: e.message}}); }}
  }}
  return JSON.stringify({{flow_id: flowId, total_steps_with_errors: stepsWithErrors.length, steps: results}});
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

# --- Group 4: Resources & Connections ---

JS_GET_CONNECTION = f"""
const params = JSON.parse(query || '{{}}');
const id = params.connection_id;
if (!id) return JSON.stringify({{error: 'Required: {{"connection_id": "<id>"}}'  }});
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/connections/${{id}}`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  return JSON.stringify(data);
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_GET_EXPORT = f"""
const params = JSON.parse(query || '{{}}');
const id = params.export_id;
if (!id) return JSON.stringify({{error: 'Required: {{"export_id": "<id>"}}'  }});
// Strip high-volume fields (mappings/hooks can be 100KB+ in large exports)
const HEAVY = new Set(['mappings', 'responseMapping', 'filter', 'transform', 'inputFilter', 'hooks']);
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/exports/${{id}}`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  return JSON.stringify(Object.fromEntries(Object.entries(data).filter(([k]) => !HEAVY.has(k))));
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_GET_IMPORT = f"""
const params = JSON.parse(query || '{{}}');
const id = params.import_id;
if (!id) return JSON.stringify({{error: 'Required: {{"import_id": "<id>"}}'  }});
// Strip high-volume fields (mappings can be 100KB+ for large imports)
const HEAVY = new Set(['mappings', 'responseMapping', 'filter', 'transform', 'inputFilter', 'hooks']);
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/imports/${{id}}`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  return JSON.stringify(Object.fromEntries(Object.entries(data).filter(([k]) => !HEAVY.has(k))));
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_LIST_FLOW_DESCENDANTS = f"""
const params = JSON.parse(query || '{{}}');
const id = params.flow_id;
if (!id) return JSON.stringify({{error: 'Required: {{"flow_id": "<id>"}}'  }});
const HEAVY = new Set(['mappings', 'responseMapping', 'filter', 'transform', 'inputFilter', 'hooks']);
const slim = o => Object.fromEntries(Object.entries(o).filter(([k]) => !HEAVY.has(k)));
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/flows/${{id}}/descendants`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  return JSON.stringify({{
    exports: (data.exports || []).map(slim),
    imports: (data.imports || []).map(slim),
  }});
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()


# ---------------------------------------------------------------------------
# Wave 2 JavaScript snippets (Groups 5-8, 17 new tools)
# ---------------------------------------------------------------------------

# --- List tools that need whitelist slimming ---

# Replaces the toolHttpRequest for list_all_flows (flows can be 10KB+ each)
JS_LIST_ALL_FLOWS = f"""
const KEEP = ['_id', 'name', '_integrationId', 'disabled', 'lastModified', 'lastExecutedAt', 'free'];
const slim = f => Object.fromEntries(KEEP.filter(k => f[k] !== undefined).map(k => [k, f[k]]));
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/flows`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  return JSON.stringify((Array.isArray(data) ? data : []).map(slim));
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

# --- Group 5: Job History & Analytics ---

JS_LIST_FLOW_JOBS = f"""
const params = JSON.parse(query || '{{}}');
const id = params.flow_id;
const limit = params.limit || 20;
if (!id) return JSON.stringify({{error: 'Required: {{"flow_id": "<id>"}}. Optional: {{"limit": 20}}'  }});
const KEEP = ['_id', 'type', 'status', 'startedAt', 'endedAt', 'numSuccess', 'numError', 'numIgnore', '_flowId', '_integrationId'];
const slim = j => Object.fromEntries(KEEP.filter(k => j[k] !== undefined).map(k => [k, j[k]]));
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/jobs?flow_id=${{id}}&type=flow`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  return JSON.stringify((Array.isArray(data) ? data : []).slice(0, limit).map(slim));
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_GET_JOB = f"""
const params = JSON.parse(query || '{{}}');
const id = params.job_id;
if (!id) return JSON.stringify({{error: 'Required: {{"job_id": "<id>"}}'  }});
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/jobs/${{id}}`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  return JSON.stringify(data);
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_LIST_RECENT_FAILED_JOBS = f"""
const params = JSON.parse(query || '{{}}');
const days = params.days || 1;
const cutoff = Date.now() - days * 86400000;
const KEEP = ['_id', 'type', 'status', 'startedAt', 'endedAt', 'numSuccess', 'numError', 'numIgnore', '_flowId', '_integrationId'];
const slim = j => Object.fromEntries(KEEP.filter(k => j[k] !== undefined).map(k => [k, j[k]]));
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/jobs?status=failed&type=flow&createdAt_gte=${{cutoff}}`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  const jobs = (Array.isArray(data) ? data : []).map(slim);
  return JSON.stringify({{days, job_count: jobs.length, jobs}});
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_GET_FLOW_LAST_EXPORT_TIME = f"""
const params = JSON.parse(query || '{{}}');
const id = params.flow_id;
if (!id) return JSON.stringify({{error: 'Required: {{"flow_id": "<id>"}}'  }});
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/flows/${{id}}/lastExportDateTime`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  return JSON.stringify(data);
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

# --- Group 6: Scripts & Reference Data ---

JS_GET_SCRIPT = f"""
const params = JSON.parse(query || '{{}}');
const id = params.script_id;
if (!id) return JSON.stringify({{error: 'Required: {{"script_id": "<id>"}}'  }});
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/scripts/${{id}}`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  const result = Object.assign({{}}, data);
  if (result.content && result.content.length > 50000) {{
    result.content = result.content.slice(0, 50000) + '\\n// [TRUNCATED at 50KB]';
  }}
  return JSON.stringify(result);
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_GET_LOOKUP_CACHE = f"""
const params = JSON.parse(query || '{{}}');
const id = params.cache_id;
if (!id) return JSON.stringify({{error: 'Required: {{"cache_id": "<id>"}}'  }});
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/lookupcaches/${{id}}`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  return JSON.stringify(data);
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_GET_FLOW_DEPENDENCIES = f"""
const params = JSON.parse(query || '{{}}');
const id = params.flow_id;
if (!id) return JSON.stringify({{error: 'Required: {{"flow_id": "<id>"}}'  }});
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/flows/${{id}}/dependencies`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  return JSON.stringify(data);
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

# --- Group 7: Account & Access ---

JS_GET_USER = f"""
const params = JSON.parse(query || '{{}}');
const id = params.user_id;
if (!id) return JSON.stringify({{error: 'Required: {{"user_id": "<ashare-id>"}}'  }});
try {{
  const data = await this.helpers.httpRequest({{
    method: 'GET', url: `{CELIGO_BASE}/ashares/${{id}}`,
    headers: {{Authorization: 'Bearer {CELIGO_API_KEY}'}},
  }});
  return JSON.stringify(data);
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

# --- Group 8: EDI Analytics ---

JS_PARSE_EDI_FLOWS = f"""
const EDI_RE = /^(.+?)\\s*-\\s*EDI\\s+(\\d{{3}})\\s+(IB|OB|INB)\\b/i;
const STAGING_RE = /\\(\\d{{1,2}}\\/\\d{{1,2}}\\/\\d{{4}}\\)$/;
const hdrs = {{Authorization: 'Bearer {CELIGO_API_KEY}'}};
try {{
  const flows = await this.helpers.httpRequest({{method: 'GET', url: `{CELIGO_BASE}/flows`, headers: hdrs}});
  const integrations = await this.helpers.httpRequest({{method: 'GET', url: `{CELIGO_BASE}/integrations`, headers: hdrs}});
  const intMap = {{}};
  (Array.isArray(integrations) ? integrations : []).forEach(i => intMap[i._id] = i.name);
  const partners = {{}};
  (Array.isArray(flows) ? flows : []).forEach(f => {{
    const m = f.name.match(EDI_RE);
    if (!m) return;
    const partner = m[1].trim();
    const isStaging = STAGING_RE.test(f.name);
    if (!partners[partner]) partners[partner] = {{name: partner, staging: false, flows: []}};
    if (isStaging) partners[partner].staging = true;
    partners[partner].flows.push({{
      _id: f._id, name: f.name, docType: m[2], direction: m[3].toUpperCase(),
      disabled: f.disabled, staging: isStaging,
      integration: intMap[f._integrationId] || f._integrationId,
    }});
  }});
  const partnerList = Object.values(partners).sort((a, b) => a.name.localeCompare(b.name));
  return JSON.stringify({{
    edi_partner_count: partnerList.length,
    total_edi_flows: partnerList.reduce((s, p) => s + p.flows.length, 0),
    partners: partnerList,
  }});
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_GET_EDI_ERROR_SUMMARY = f"""
const EDI_RE = /^(.+?)\\s*-\\s*EDI\\s+(\\d{{3}})\\s+(IB|OB|INB)\\b/i;
const STAGING_RE = /\\(\\d{{1,2}}\\/\\d{{1,2}}\\/\\d{{4}}\\)$/;
const hdrs = {{Authorization: 'Bearer {CELIGO_API_KEY}'}};
try {{
  const flows = await this.helpers.httpRequest({{method: 'GET', url: `{CELIGO_BASE}/flows`, headers: hdrs}});
  const ediIntegrations = new Set();
  const ediFlowMap = {{}};
  (Array.isArray(flows) ? flows : []).forEach(f => {{
    const m = f.name.match(EDI_RE);
    if (!m) return;
    ediFlowMap[f._id] = {{partner: m[1].trim(), docType: m[2], direction: m[3].toUpperCase(), staging: STAGING_RE.test(f.name)}};
    if (f._integrationId) ediIntegrations.add(f._integrationId);
  }});
  const partners = {{}};
  for (const intId of ediIntegrations) {{
    try {{
      const errors = await this.helpers.httpRequest({{method: 'GET', url: `{CELIGO_BASE}/integrations/${{intId}}/errors`, headers: hdrs}});
      (Array.isArray(errors) ? errors : []).forEach(e => {{
        const flow = ediFlowMap[e._flowId];
        if (!flow || !e.numError) return;
        if (!partners[flow.partner]) partners[flow.partner] = {{name: flow.partner, total_errors: 0, errored_flows: []}};
        partners[flow.partner].total_errors += e.numError;
        partners[flow.partner].errored_flows.push({{
          _flowId: e._flowId, numError: e.numError, lastErrorAt: e.lastErrorAt,
          docType: flow.docType, direction: flow.direction, staging: flow.staging,
        }});
      }});
    }} catch(e) {{ /* skip */ }}
  }}
  const partnerList = Object.values(partners).sort((a, b) => b.total_errors - a.total_errors);
  return JSON.stringify({{
    partners_with_errors: partnerList.length,
    grand_total_errors: partnerList.reduce((s, p) => s + p.total_errors, 0),
    partners: partnerList,
  }});
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()

JS_GET_EDI_DASHBOARD = f"""
const EDI_RE = /^(.+?)\\s*-\\s*EDI\\s+(\\d{{3}})\\s+(IB|OB|INB)\\b/i;
const STAGING_RE = /\\(\\d{{1,2}}\\/\\d{{1,2}}\\/\\d{{4}}\\)$/;
const hdrs = {{Authorization: 'Bearer {CELIGO_API_KEY}'}};
try {{
  const flows = await this.helpers.httpRequest({{method: 'GET', url: `{CELIGO_BASE}/flows`, headers: hdrs}});
  const integrations = await this.helpers.httpRequest({{method: 'GET', url: `{CELIGO_BASE}/integrations`, headers: hdrs}});
  const intMap = {{}};
  (Array.isArray(integrations) ? integrations : []).forEach(i => intMap[i._id] = i.name);
  const partners = {{}};
  const ediIntegrations = new Set();
  (Array.isArray(flows) ? flows : []).forEach(f => {{
    const m = f.name.match(EDI_RE);
    if (!m) return;
    const partner = m[1].trim();
    const isStaging = STAGING_RE.test(f.name);
    if (!partners[partner]) partners[partner] = {{name: partner, flows: [], error_count: 0, active_flows: 0, disabled_flows: 0, doc_types: [], staging: false}};
    if (isStaging) partners[partner].staging = true;
    partners[partner].flows.push({{_id: f._id, docType: m[2], direction: m[3].toUpperCase(), disabled: f.disabled, staging: isStaging}});
    if (f._integrationId) ediIntegrations.add(f._integrationId);
  }});
  const flowErrorMap = {{}};
  for (const intId of ediIntegrations) {{
    try {{
      const errors = await this.helpers.httpRequest({{method: 'GET', url: `{CELIGO_BASE}/integrations/${{intId}}/errors`, headers: hdrs}});
      (Array.isArray(errors) ? errors : []).forEach(e => {{
        if (e.numError) flowErrorMap[e._flowId] = (flowErrorMap[e._flowId] || 0) + e.numError;
      }});
    }} catch(e) {{ /* skip */ }}
  }}
  Object.values(partners).forEach(p => {{
    p.error_count = p.flows.reduce((s, f) => s + (flowErrorMap[f._id] || 0), 0);
    p.active_flows = p.flows.filter(f => !f.disabled).length;
    p.disabled_flows = p.flows.filter(f => f.disabled).length;
    p.doc_types = [...new Set(p.flows.map(f => f.docType))].sort();
  }});
  const partnerList = Object.values(partners).sort((a, b) => b.error_count - a.error_count || a.name.localeCompare(b.name));
  return JSON.stringify({{
    summary: {{
      partner_count: partnerList.length,
      grand_total_errors: partnerList.reduce((s, p) => s + p.error_count, 0),
      partners_with_errors: partnerList.filter(p => p.error_count > 0).length,
      total_edi_flows: partnerList.reduce((s, p) => s + p.flows.length, 0),
    }},
    partners: partnerList,
  }});
}} catch (e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()


# ---------------------------------------------------------------------------
# Wave 0: 3 prototype tools
# ---------------------------------------------------------------------------

def build_wave0():
    """Build Wave 0 workflow — 3 tools validating all patterns."""
    tool_nodes = [
        tool_http(
            name="list_integrations",
            description=(
                "List all Celigo integrations. Returns array of integration objects with "
                "_id, name, sandbox, lastModified, and status. No input required."
            ),
            url=f"{CELIGO_BASE}/integrations",
        ),
        tool_code(
            name="list_step_errors",
            description=(
                "List error records for a specific step (export or import) within a Celigo flow. "
                'Input JSON: {"flow_id": "<celigo-flow-id>", "step_id": "<export-or-import-id>"}. '
                "Returns error objects with message, retryDataKey, source, and timestamps."
            ),
            js_code=JS_LIST_STEP_ERRORS,
        ),
        tool_code(
            name="get_integration_summary",
            description=(
                "Get a composite summary of a Celigo integration: integration details, all flows, "
                "and error counts per flow. "
                'Input JSON: {"integration_id": "<celigo-integration-id>"}. '
                "Returns integration object, flows list, errors array, and a summary with totals."
            ),
            js_code=JS_GET_INTEGRATION_SUMMARY,
        ),
    ]
    return tool_nodes


# ---------------------------------------------------------------------------
# Wave 1: 20 tools (Groups 1-4)
# ---------------------------------------------------------------------------

def build_wave1():
    """Build Wave 1 workflow — 20 tools across Groups 1-4."""
    return [
        # --- Group 1: Integration Discovery (5) ---
        tool_http(
            name="list_integrations",
            description=(
                "List all Celigo integrations. Returns array of integration objects with "
                "_id, name, sandbox, lastModified, and status. No input required."
            ),
            url=f"{CELIGO_BASE}/integrations",
        ),
        tool_code("get_integration",
            "Get details of a single Celigo integration by ID. "
            'Input JSON: {"integration_id": "<id>"}. '
            "Returns full integration object including _id, name, sandbox, install steps.",
            JS_GET_INTEGRATION),
        tool_code("list_integration_flows",
            "List all flows in a Celigo integration. "
            'Input JSON: {"integration_id": "<id>"}. '
            "Returns array of flows with _id, name, disabled, schedule, lastModified.",
            JS_LIST_INTEGRATION_FLOWS),
        tool_code("list_integration_errors",
            "Get error counts per flow for a Celigo integration. "
            'Input JSON: {"integration_id": "<id>"}. '
            "Returns [{_flowId, numError, lastErrorAt}] plus summary totals.",
            JS_LIST_INTEGRATION_ERRORS),
        tool_code("get_integration_summary",
            "Get a composite summary of a Celigo integration: details, all flows, and error counts. "
            'Input JSON: {"integration_id": "<id>"}. '
            "Returns integration object, flows list, error counts, and totals summary.",
            JS_GET_INTEGRATION_SUMMARY),

        # --- Group 2: Flow Inspection (5) ---
        tool_code("list_all_flows",
            "List all Celigo flows across all integrations. No input required. "
            "Returns slimmed array: [{_id, name, _integrationId, disabled, lastModified, lastExecutedAt}]. "
            "Use get_flow for full details on a specific flow.",
            JS_LIST_ALL_FLOWS),
        tool_code("get_flow",
            "Get full definition of a single Celigo flow by ID including pageGenerators (exports) and pageProcessors (imports). "
            'Input JSON: {"flow_id": "<id>"}. '
            "Returns the complete flow object.",
            JS_GET_FLOW),
        tool_code("get_flow_last_run",
            "Get the most recent job execution result for a Celigo flow. "
            'Input JSON: {"flow_id": "<id>"}. '
            "Returns array of latest jobs with status, numSuccess, numError, startedAt, endedAt.",
            JS_GET_FLOW_LAST_RUN),
        tool_code("get_flow_step_error_counts",
            "Get error counts broken down by step (export/import) for a Celigo flow. "
            'Input JSON: {"flow_id": "<id>"}. '
            "Returns {steps: [{_expOrImpId, numError, lastErrorAt}], total_errors, steps_with_errors}.",
            JS_GET_FLOW_STEP_ERROR_COUNTS),
        tool_code("get_flow_audit_log",
            "Get the audit/change history for a Celigo flow showing recent configuration changes. "
            'Input JSON: {"flow_id": "<id>"}. Optional: {"limit": 20}. '
            "Returns array of audit entries with timestamp, user, and change details.",
            JS_GET_FLOW_AUDIT_LOG),

        # --- Group 3: Error Investigation (5) ---
        tool_code("get_step_errors",
            "List error records for a specific step (export or import) within a Celigo flow. "
            'Input JSON: {"flow_id": "<id>", "step_id": "<export-or-import-id>"}. '
            "Returns error objects with message, retryDataKey, source, and timestamps.",
            JS_LIST_STEP_ERRORS),
        tool_code("list_flows_with_errors",
            "List only the flows that currently have errors in a Celigo integration. "
            'Input JSON: {"integration_id": "<id>"}. '
            "Returns {flows_with_errors: [{_flowId, numError, lastErrorAt}], count}.",
            JS_LIST_FLOWS_WITH_ERRORS),
        tool_code("list_all_errored_flows",
            "Sweep ALL integrations and return every flow that currently has errors. "
            "No input required (pass empty object {}). "
            "Returns {errored_integrations: [{integration, flows_with_errors}], grand_total_errors}. "
            "Note: makes one API call per integration — may be slow for large accounts.",
            JS_LIST_ALL_ERRORED_FLOWS),
        tool_code("get_flow_health",
            "Get a health summary for a Celigo flow: enabled/disabled status, total errors by step, and last run result. "
            'Input JSON: {"flow_id": "<id>"}. '
            "Returns {flow, health: {status, totalErrors, stepsWithErrors}, lastRun}.",
            JS_GET_FLOW_HEALTH),
        tool_code("get_all_step_errors",
            "Get error records for ALL steps in a flow that currently have errors. "
            'Input JSON: {"flow_id": "<id>"}. '
            "Automatically loops through all errored steps and returns their error records. "
            "Returns {flow_id, total_steps_with_errors, steps: [{step_id, numError, errors}]}.",
            JS_GET_ALL_STEP_ERRORS),

        # --- Group 4: Resources & Connections (5) ---
        tool_http(
            name="list_connections",
            description=(
                "List all Celigo connections (API credentials and endpoints). "
                "Returns array of connection objects with _id, name, type, lastModified. No input required."
            ),
            url=f"{CELIGO_BASE}/connections",
        ),
        tool_code("get_connection",
            "Get details of a single Celigo connection by ID. "
            'Input JSON: {"connection_id": "<id>"}. '
            "Returns the full connection object including type, configuration, and last tested status.",
            JS_GET_CONNECTION),
        tool_code("get_export",
            "Get the definition of a Celigo export (source step) by ID. "
            'Input JSON: {"export_id": "<id>"}. '
            "Returns export config (adaptor, connection, query, pagination, etc.). "
            "Note: mappings/hooks stripped — use list_flow_descendants to see full step configs.",
            JS_GET_EXPORT),
        tool_code("get_import",
            "Get the definition of a Celigo import (destination step) by ID. "
            'Input JSON: {"import_id": "<id>"}. '
            "Returns import config (adaptor, connection, type, lookups, etc.). "
            "Note: mappings/hooks stripped — use list_flow_descendants to see full step configs.",
            JS_GET_IMPORT),
        tool_code("list_flow_descendants",
            "Get export and import configurations for all steps in a Celigo flow. "
            'Input JSON: {"flow_id": "<id>"}. '
            "Returns {exports: [...], imports: [...]} with config slimmed (mappings/hooks stripped). "
            "Best tool for understanding flow structure without mapping noise.",
            JS_LIST_FLOW_DESCENDANTS),
    ]


# ---------------------------------------------------------------------------
# Wave 2: 37 tools (Wave 1 + Groups 5-8)
# ---------------------------------------------------------------------------

def build_wave2():
    """Build Wave 2 workflow — all 37 tools across Groups 1-8."""
    return build_wave1() + [
        # --- Group 5: Job History & Analytics (5) ---
        tool_code("list_flow_jobs",
            "List recent job executions for a Celigo flow. "
            'Input JSON: {"flow_id": "<id>"}. Optional: {"limit": 20}. '
            "Returns array of job objects with status, numSuccess, numError, startedAt, endedAt.",
            JS_LIST_FLOW_JOBS),
        tool_code("get_job",
            "Get full details of a single Celigo job execution by ID. "
            'Input JSON: {"job_id": "<id>"}. '
            "Returns job object including timing, record counts, and step-level error details.",
            JS_GET_JOB),
        tool_http(
            name="list_running_jobs",
            description=(
                "List all currently running Celigo flow jobs. "
                "Returns array of active job objects with flow ID, start time, and record counts. No input required."
            ),
            url=f"{CELIGO_BASE}/jobs?status=running&type=flow",
        ),
        tool_code("list_recent_failed_jobs",
            "List recently failed Celigo flow jobs. "
            'Input JSON: {} (defaults to last 1 day). Optional: {"days": 1}. '
            "Returns {days, job_count, jobs} with failed jobs from the last N days.",
            JS_LIST_RECENT_FAILED_JOBS),
        tool_code("get_flow_last_export_time",
            "Get the timestamp of the last successful export run for a Celigo flow. "
            'Input JSON: {"flow_id": "<id>"}. '
            "Returns the lastExportDateTime value indicating when the flow last ran successfully.",
            JS_GET_FLOW_LAST_EXPORT_TIME),

        # --- Group 6: Scripts & Reference Data (5) ---
        tool_http(
            name="list_scripts",
            description=(
                "List all Celigo scripts. "
                "Returns array of script objects with _id, name, lastModified. No input required."
            ),
            url=f"{CELIGO_BASE}/scripts",
        ),
        tool_code("get_script",
            "Get the full content of a Celigo script by ID. "
            'Input JSON: {"script_id": "<id>"}. '
            "Returns script object with name, content (truncated at 50KB), and metadata.",
            JS_GET_SCRIPT),
        tool_http(
            name="list_lookup_caches",
            description=(
                "List all Celigo lookup caches. "
                "Returns array of cache objects with _id, name, lastModified. No input required."
            ),
            url=f"{CELIGO_BASE}/lookupcaches",
        ),
        tool_code("get_lookup_cache",
            "Get metadata for a Celigo lookup cache by ID. "
            'Input JSON: {"cache_id": "<id>"}. '
            "Returns cache object with name, configuration, and status.",
            JS_GET_LOOKUP_CACHE),
        tool_code("get_flow_dependencies",
            "Get all dependencies (connections, exports, imports, scripts, lookups) for a Celigo flow. "
            'Input JSON: {"flow_id": "<id>"}. '
            "Returns dependency graph showing what resources the flow depends on.",
            JS_GET_FLOW_DEPENDENCIES),

        # --- Group 7: Account & Access (2) ---
        tool_http(
            name="list_users",
            description=(
                "List all users with access to this Celigo account. "
                "Returns array of user objects with _id, email, name, accessLevel. No input required."
            ),
            url=f"{CELIGO_BASE}/ashares",
        ),
        tool_code("get_user",
            "Get details of a single Celigo user by ashare ID. "
            'Input JSON: {"user_id": "<ashare-id>"}. '
            "Returns user object with email, name, accessLevel, and lastLogin.",
            JS_GET_USER),

        # --- Group 8: EDI Analytics (3) ---
        tool_code("parse_edi_flows",
            "Parse all Celigo flows to identify EDI trading partners and their flows by document type and direction. "
            "No input required (pass empty object {}). "
            "Detects flows matching 'Partner - EDI 850 IB' naming pattern. "
            "Returns {edi_partner_count, total_edi_flows, partners: [{name, staging, flows: [{docType, direction, disabled}]}]}.",
            JS_PARSE_EDI_FLOWS),
        tool_code("get_edi_error_summary",
            "Get a summary of current errors grouped by EDI trading partner. "
            "No input required (pass empty object {}). "
            "Returns {partners_with_errors, grand_total_errors, partners: [{name, total_errors, errored_flows}]} sorted by error count.",
            JS_GET_EDI_ERROR_SUMMARY),
        tool_code("get_edi_dashboard",
            "Get a comprehensive EDI health dashboard: all trading partners ranked by errors with flow counts, "
            "active/disabled counts, and document types. "
            "No input required (pass empty object {}). "
            "Returns {summary: {partner_count, grand_total_errors, partners_with_errors, total_edi_flows}, "
            "partners: [{name, error_count, active_flows, disabled_flows, doc_types, staging, flows}]}.",
            JS_GET_EDI_DASHBOARD),
    ]


# ---------------------------------------------------------------------------
# Workflow assembly
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

    # All tool nodes connect to trigger via ai_tool
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
    parser = argparse.ArgumentParser(description="Create Celigo MCP workflow in n8n")
    parser.add_argument("--dry-run", action="store_true", help="Print workflow JSON without creating")
    parser.add_argument("--wave", type=int, default=1, choices=[0, 1, 2], help="Which wave to deploy (default: 1)")
    parser.add_argument("--path", default=MCP_PATH, help=f"MCP path (default: {MCP_PATH})")
    parser.add_argument("--name", default=WORKFLOW_NAME, help="Workflow name")
    args = parser.parse_args()

    # Build tool nodes for chosen wave
    if args.wave == 0:
        tool_nodes = build_wave0()
        wf_name = args.name
    elif args.wave == 1:
        tool_nodes = build_wave1()
        wf_name = args.name.replace("Wave 0 Prototype", "Wave 1")
        if wf_name == args.name and args.name == WORKFLOW_NAME:
            wf_name = "Celigo MCP: Wave 1"
    elif args.wave == 2:
        tool_nodes = build_wave2()
        wf_name = "Celigo MCP: Wave 2 (37 tools)"
    else:
        print(f"Wave {args.wave} not yet implemented", file=sys.stderr)
        sys.exit(1)

    workflow = build_workflow(tool_nodes, wf_name, args.path)

    if args.dry_run:
        print(json.dumps(workflow, indent=2))
        return

    # Get n8n credentials
    n8n_url, n8n_key = get_api_credentials()

    print(f"n8n:      {n8n_url}")
    print(f"Workflow: {wf_name}")
    print(f"Tools:    {len(tool_nodes)}")
    print(f"MCP path: /mcp/{args.path}/sse")
    print()

    # Create workflow
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

    # Activate
    print("Activating...", end="", flush=True)
    try:
        n8n_api("POST", f"workflows/{wf_id}/activate", n8n_url, n8n_key)
        print(" active")
    except urllib.error.HTTPError as e:
        print(f" WARNING: activation failed: HTTP {e.code}")

    # Compute SSE endpoint
    base_url = n8n_url.rstrip("/")
    if base_url.endswith("/api/v1"):
        base_url = base_url[: -len("/api/v1")]

    print()
    print("=== Workflow created ===")
    print(f"ID:   {wf_id}")
    print(f"SSE:  {base_url}/mcp/{args.path}/sse")
    print()
    print("Test tools/list:")
    print(f"  curl -N -H 'X-N8N-API-KEY: {n8n_key[:8]}...' \\")
    print(f"    '{base_url}/mcp/{args.path}/sse'")


if __name__ == "__main__":
    main()
