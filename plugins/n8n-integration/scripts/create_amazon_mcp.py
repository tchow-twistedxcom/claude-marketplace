#!/usr/bin/env python3
"""
Create Amazon SP-API MCP workflow in n8n.

Builds an n8n workflow with toolCode nodes connected to an MCP Server Trigger,
exposing Amazon Selling Partner API operations as MCP tools for Claude Desktop
and other MCP clients.

Tools (5 total):
  search_catalog         - Search catalog by keywords or ASIN/UPC/EAN
  get_competitive_pricing - Competitive prices for up to 20 ASINs
  get_offer_pricing      - Lowest prices and Buy Box info per ASIN
  create_report          - Request a Seller Central report
  download_report        - Get report document URL and download content

Usage:
    python3 create_amazon_mcp.py              # Create and activate
    python3 create_amazon_mcp.py --dry-run    # Print workflow JSON without creating
    python3 create_amazon_mcp.py --profile vendor  # Use vendor profile creds
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

# Load SP-API credentials from spapi_config.json
SPAPI_CONFIG_PATH = (
    Path(__file__).parent.parent.parent
    / "amazon-spapi" / "config" / "spapi_config.json"
)

# Workflow config
WORKFLOW_NAME = "Amazon SP-API MCP Tools"
MCP_PATH = "amazon-tools"
SP_BASE = "https://sellingpartnerapi-na.amazon.com"
LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
MARKETPLACE_ID = "ATVPDKIKX0DER"  # US


def load_spapi_creds(profile="seller"):
    """Load SP-API credentials from spapi_config.json."""
    if not SPAPI_CONFIG_PATH.exists():
        print(f"ERROR: spapi_config.json not found at {SPAPI_CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(SPAPI_CONFIG_PATH) as f:
        config = json.load(f)
    profiles = config.get("profiles", {})
    if profile not in profiles:
        available = list(profiles.keys())
        print(f"ERROR: profile '{profile}' not found. Available: {available}", file=sys.stderr)
        sys.exit(1)
    p = profiles[profile]
    return p["lwa_client_id"], p["lwa_client_secret"], p["refresh_token"]


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
    """Build a toolCode node (JavaScript, arbitrary HTTP calls)."""
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
# Shared JS auth helper (injected at top of every toolCode snippet)
# ---------------------------------------------------------------------------

def make_auth_helper(lwa_client_id, lwa_client_secret, refresh_token):
    return f"""
const LWA_URL = '{LWA_TOKEN_URL}';
const LWA_CID = '{lwa_client_id}';
const LWA_SEC = '{lwa_client_secret}';
const LWA_RT = '{refresh_token}';
const SP_BASE = '{SP_BASE}';
const MKTP = '{MARKETPLACE_ID}';

async function getToken() {{
  // Try static data cache first (1hr TTL)
  try {{
    const sd = $getWorkflowStaticData('global');
    if (sd.sp_tok && sd.sp_exp > Date.now() + 60000) return sd.sp_tok;
    const resp = await this.helpers.httpRequest({{
      method: 'POST', url: LWA_URL,
      headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
      body: `grant_type=refresh_token&refresh_token=${{encodeURIComponent(LWA_RT)}}&client_id=${{encodeURIComponent(LWA_CID)}}&client_secret=${{encodeURIComponent(LWA_SEC)}}`,
    }});
    sd.sp_tok = resp.access_token;
    sd.sp_exp = Date.now() + (resp.expires_in || 3600) * 1000;
    return resp.access_token;
  }} catch (cacheErr) {{
    // Fallback: per-request refresh (if $getWorkflowStaticData unavailable)
    const resp = await this.helpers.httpRequest({{
      method: 'POST', url: LWA_URL,
      headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
      body: `grant_type=refresh_token&refresh_token=${{encodeURIComponent(LWA_RT)}}&client_id=${{encodeURIComponent(LWA_CID)}}&client_secret=${{encodeURIComponent(LWA_SEC)}}`,
    }});
    return resp.access_token;
  }}
}}

async function spGet(path, qp = {{}}) {{
  const tok = await getToken.call(this);
  const qs = Object.entries(qp).filter(([,v]) => v != null)
    .map(([k,v]) => `${{k}}=${{encodeURIComponent(v)}}`).join('&');
  return await this.helpers.httpRequest({{
    method: 'GET',
    url: `${{SP_BASE}}${{path}}${{qs ? '?' + qs : ''}}`,
    headers: {{'x-amz-access-token': tok}},
  }});
}}

async function spPost(path, body) {{
  const tok = await getToken.call(this);
  return await this.helpers.httpRequest({{
    method: 'POST',
    url: `${{SP_BASE}}${{path}}`,
    headers: {{
      'x-amz-access-token': tok,
      'Content-Type': 'application/json',
    }},
    body: JSON.stringify(body),
  }});
}}
""".strip()


# ---------------------------------------------------------------------------
# JavaScript tool snippets
# ---------------------------------------------------------------------------

def make_js_search_catalog(auth):
    return f"""
{auth}
const params = JSON.parse(query || '{{}}');
const keywords = params.keywords;
const identifiers = params.identifiers;
const identifiersType = params.identifiers_type || 'ASIN';
if (!keywords && !identifiers) {{
  return JSON.stringify({{
    error: 'Required: {{"keywords": "Twisted X casual"}} OR {{"identifiers": "B01DZZURW2", "identifiers_type": "ASIN"}}',
    identifiers_types: ['ASIN', 'UPC', 'EAN', 'ISBN'],
  }});
}}
try {{
  const qp = {{marketplaceIds: MKTP, includedData: 'summaries,images'}};
  if (keywords) qp.keywords = keywords;
  if (identifiers) {{
    qp.identifiers = identifiers;
    qp.identifiersType = identifiersType;
  }}
  const data = await spGet.call(this, '/catalog/2022-04-01/items', qp);
  const items = (data.items || []).map(i => ({{
    asin: i.asin,
    title: (i.summaries || [])[0]?.itemName,
    brand: (i.summaries || [])[0]?.brand,
    product_type: (i.summaries || [])[0]?.productType,
    main_image: (i.images || []).flatMap(g => g.images || []).find(img => img.variant === 'MAIN')?.link,
  }}));
  return JSON.stringify({{total: data.numberOfResults || items.length, items, pagination: data.pagination || null}});
}} catch(e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()


def make_js_competitive_pricing(auth):
    return f"""
{auth}
const params = JSON.parse(query || '{{}}');
const asins = params.asins;
if (!asins) return JSON.stringify({{error: 'Required: {{"asins": "B01DZZURW2,B07R14RJTZ"}} (comma-separated, max 20)'}});
try {{
  const asinList = asins.split(',').map(a => a.trim()).filter(Boolean).slice(0, 20);
  const tok = await getToken.call(this);
  const asinParams = asinList.map(a => `Asins=${{encodeURIComponent(a)}}`).join('&');
  const url = `${{SP_BASE}}/products/pricing/v0/competitivePrice?MarketplaceId=${{MKTP}}&ItemType=Asin&${{asinParams}}`;
  const data = await this.helpers.httpRequest({{
    method: 'GET', url,
    headers: {{'x-amz-access-token': tok}},
  }});
  const results = (data.payload || []).map(p => ({{
    asin: p.ASIN,
    status: p.status,
    competitive_prices: (p.Product?.CompetitivePricing?.CompetitivePrices || []).map(cp => ({{
      condition: cp.condition,
      belongs_to_us: cp.belongsToRequester,
      price: cp.Price?.LandedPrice,
    }})),
    num_offer_listings: p.Product?.CompetitivePricing?.NumberOfOfferListings || [],
  }}));
  return JSON.stringify({{count: results.length, results}});
}} catch(e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()


def make_js_offer_pricing(auth):
    return f"""
{auth}
const params = JSON.parse(query || '{{}}');
const asin = params.asin;
if (!asin) return JSON.stringify({{error: 'Required: {{"asin": "B01DZZURW2"}}'}});
try {{
  const data = await spGet.call(this, '/products/pricing/v0/listings/offers', {{
    MarketplaceId: MKTP,
    ItemCondition: params.condition || 'New',
    Asin: asin,
  }});
  const payload = data.payload || {{}};
  const summary = payload.Summary || {{}};
  return JSON.stringify({{
    asin,
    lowest_prices: summary.LowestPrices || [],
    buy_box_prices: summary.BuyBoxPrices || [],
    buy_box_eligible_offers: summary.BuyBoxEligibleOffers || [],
    total_offer_count: summary.TotalOfferCount,
    offers: (payload.Offers || []).slice(0, 10).map(o => ({{
      condition: o.SubCondition,
      fulfillment: o.FulfillmentChannel,
      price: o.ListingPrice,
      shipping: o.Shipping,
      prime: o.PrimeInformation?.isPrime,
    }})),
  }});
}} catch(e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()


def make_js_create_report(auth):
    return f"""
{auth}
const params = JSON.parse(query || '{{}}');
const reportType = params.report_type;
if (!reportType) return JSON.stringify({{
  error: 'Required: {{"report_type": "GET_MERCHANT_LISTINGS_ALL_DATA"}}. Optional: {{"start_date": "2026-01-01", "end_date": "2026-02-28"}}',
  common_types: [
    'GET_MERCHANT_LISTINGS_ALL_DATA',
    'GET_FLAT_FILE_OPEN_LISTINGS_DATA',
    'GET_SALES_AND_TRAFFIC_REPORT',
    'GET_LEDGER_SUMMARY_VIEW_DATA',
    'GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA',
    'GET_FLAT_FILE_ALL_ORDERS_DATA_BY_LAST_UPDATE_GENERAL',
  ],
}});
try {{
  const body = {{reportType, marketplaceIds: [MKTP]}};
  if (params.start_date) body.dataStartTime = params.start_date;
  if (params.end_date) body.dataEndTime = params.end_date;
  const data = await spPost.call(this, '/reports/2021-06-30/reports', body);
  return JSON.stringify({{
    report_id: data.reportId,
    status: 'SUBMITTED',
    tip: 'Use download_report with this report_id to check status and download when ready.',
  }});
}} catch(e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()


def make_js_download_report(auth):
    return f"""
{auth}
const params = JSON.parse(query || '{{}}');
const reportId = params.report_id;
const documentId = params.document_id;
const maxLines = params.max_lines || 100;
if (!reportId && !documentId) return JSON.stringify({{
  error: 'Required: {{"report_id": "<from create_report>"}} OR {{"document_id": "<direct document id>"}}. Optional: {{"max_lines": 100}}',
}});
try {{
  let docId = documentId;
  // If given a report_id, check its status first
  if (!docId && reportId) {{
    const report = await spGet.call(this, `/reports/2021-06-30/reports/${{reportId}}`);
    if (report.processingStatus !== 'DONE') {{
      return JSON.stringify({{
        report_id: reportId,
        status: report.processingStatus,
        created: report.createdTime,
        tip: report.processingStatus === 'FATAL' ? 'Report failed. Try creating a new one.' : 'Report still processing. Try again in 30-60 seconds.',
      }});
    }}
    docId = report.reportDocumentId;
  }}
  // Get pre-signed download URL
  const doc = await spGet.call(this, `/reports/2021-06-30/documents/${{docId}}`);
  if (!doc.url) return JSON.stringify({{error: 'No download URL in report document', doc}});
  // Download the content (pre-signed S3 URL, no auth needed)
  const content = await this.helpers.httpRequest({{method: 'GET', url: doc.url}});
  const text = typeof content === 'string' ? content : JSON.stringify(content);
  const lines = text.split('\\n').filter(l => l.trim());
  const truncated = lines.length > maxLines;
  return JSON.stringify({{
    document_id: docId,
    total_lines: lines.length,
    truncated,
    data: lines.slice(0, maxLines).join('\\n'),
    tip: truncated ? `Showing ${{maxLines}} of ${{lines.length}} lines. Set max_lines higher to see more.` : null,
  }});
}} catch(e) {{ return JSON.stringify({{error: e.message}}); }}
""".strip()


# ---------------------------------------------------------------------------
# Workflow assembly
# ---------------------------------------------------------------------------

def assign_positions(tool_nodes):
    spacing = 220
    for i, node in enumerate(tool_nodes):
        node["position"] = [-(len(tool_nodes) - i) * spacing, 0]


def build_workflow(tool_nodes, workflow_name, mcp_path):
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
        "settings": {"executionOrder": "v1", "availableInMCP": True},
        "nodes": tool_nodes + [trigger],
        "connections": connections,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Create Amazon SP-API MCP workflow in n8n")
    parser.add_argument("--dry-run", action="store_true", help="Print workflow JSON without creating")
    parser.add_argument("--profile", default="seller", help="SP-API profile from spapi_config.json (default: seller)")
    parser.add_argument("--path", default=MCP_PATH, help=f"MCP path (default: {MCP_PATH})")
    parser.add_argument("--name", default=WORKFLOW_NAME, help="Workflow name")
    args = parser.parse_args()

    # Load SP-API credentials
    lwa_cid, lwa_sec, refresh_token = load_spapi_creds(args.profile)
    auth = make_auth_helper(lwa_cid, lwa_sec, refresh_token)

    # Build tools
    tool_nodes = [
        tool_code(
            "search_catalog",
            "Search Amazon product catalog by keywords or identifiers (ASIN, UPC, EAN). "
            'Input JSON: {"keywords": "Twisted X casual"} OR {"identifiers": "B01DZZURW2", "identifiers_type": "ASIN"}. '
            "Returns list of matching products with ASIN, title, brand, product type, and main image URL.",
            make_js_search_catalog(auth),
        ),
        tool_code(
            "get_competitive_pricing",
            "Get competitive pricing data for up to 20 ASINs. Shows current market prices by condition. "
            'Input JSON: {"asins": "B01DZZURW2,B07R14RJTZ"} (comma-separated, max 20). '
            "Returns competitive prices, offer listing counts, and whether Twisted X holds Buy Box.",
            make_js_competitive_pricing(auth),
        ),
        tool_code(
            "get_offer_pricing",
            "Get detailed offer pricing for a single ASIN: lowest prices, Buy Box prices, and top offers. "
            'Input JSON: {"asin": "B01DZZURW2"}. Optional: {"condition": "New"} (default). '
            "Returns lowest prices by fulfillment channel, Buy Box price, and up to 10 individual offers.",
            make_js_offer_pricing(auth),
        ),
        tool_code(
            "create_report",
            "Request an Amazon Seller Central report. Returns a report_id to use with download_report. "
            'Input JSON: {"report_type": "GET_MERCHANT_LISTINGS_ALL_DATA"}. '
            'Optional: {"start_date": "2026-01-01", "end_date": "2026-02-28"}. '
            "Common types: GET_MERCHANT_LISTINGS_ALL_DATA, GET_SALES_AND_TRAFFIC_REPORT, GET_LEDGER_SUMMARY_VIEW_DATA.",
            make_js_create_report(auth),
        ),
        tool_code(
            "download_report",
            "Download a completed Amazon report by report_id or document_id. "
            'Input JSON: {"report_id": "<from create_report>"}. '
            'OR {"document_id": "<direct document id>"}. '
            'Optional: {"max_lines": 100}. '
            "If report is still processing, returns current status. When done, returns report data (tab-separated).",
            make_js_download_report(auth),
        ),
    ]

    workflow = build_workflow(tool_nodes, args.name, args.path)

    if args.dry_run:
        print(json.dumps(workflow, indent=2))
        return

    # Get n8n credentials
    n8n_url, n8n_key = get_api_credentials()

    print(f"n8n:      {n8n_url}")
    print(f"Profile:  {args.profile}")
    print(f"Workflow: {args.name}")
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
    print("Test:")
    print(f"  curl -N -H 'X-N8N-API-KEY: {n8n_key[:8]}...' '{base_url}/mcp/{args.path}/sse'")


if __name__ == "__main__":
    main()
