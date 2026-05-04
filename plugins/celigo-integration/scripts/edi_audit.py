#!/usr/bin/env python3
"""
EDI Cross-System Audit

Reconciles Celigo EDI job history against NetSuite EDI History records to
surface mismatches between what Celigo processed and what NetSuite recorded.

Inbound leg (850/856/860):
  For each successful Celigo job on an inbound EDI flow, verify a matching
  customrecord_twx_edi_history row exists in NetSuite with status=2 (success)
  and (for 850) a non-null transaction link.

Outbound leg (810/846/855/820):
  For each NetSuite EDI History row with status=2 (sent) on outbound doc types,
  verify a corresponding successful Celigo job exists in the same window.

Output: structured JSON + human-readable summary (three failure buckets).

Usage:
    python3 edi_audit.py [--since 24h] [--until now] [--partner NAME]
                         [--direction inbound|outbound|both]
                         [--json-only] [--exit-nonzero-on-mismatch]

Exit codes:
    0  No mismatches (or --exit-nonzero-on-mismatch not set)
    1  Mismatches found (when --exit-nonzero-on-mismatch is set)
    2  Fatal error (NS gateway unreachable, Celigo auth failure, etc.)
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
CONFIG_FILE = CONFIG_DIR / "celigo_config.json"

NS_GATEWAY_URL = "https://nsapi.twistedx.tech/api/suiteapi"
NS_ACCOUNT = "twistedx"
NS_ENVIRONMENT = "production"

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3

# EDI doc type code → NS custrecord_twx_edi_type value
NS_DOC_TYPE_MAP = {
    "850": 3,   # Purchase Order inbound
    "856": 5,   # ASN inbound
    "860": 14,  # PO Change inbound
    "810": 1,   # Invoice outbound
    "846": 2,   # Inventory Advice outbound
    "855": 7,   # PO Acknowledgement outbound
    "820": 9,   # Payment Order outbound
}

INBOUND_TYPES = frozenset(["850", "856", "860"])
OUTBOUND_TYPES = frozenset(["810", "846", "855", "820"])

# Regex to extract partner name + doc type + direction from Celigo FLOW names.
# Actual flow naming: "Amazon Vendor Central - 850 IB - EDI Purchase Order"
# Matches: "Partner - 850 IB", "Partner - 850 INB", "Partner - 810 OB"
_EDI_FLOW_RE = re.compile(
    r"^(?P<partner>.+?)\s*-\s*(?P<doc_type>\d{3})\s+(?P<dir>IB|OB|INB)\b",
    re.IGNORECASE,
)

# Integration name prefix for EDI integrations (matches "EDI - " and "EDI | ")
_EDI_INTEGRATION_RE = re.compile(r"^EDI\s*[-|]\s*", re.IGNORECASE)

# Regex to extract PO number from NS externalid: HIST_{PO}_{PARTNER}_00
_EXTERNALID_RE = re.compile(r"^HIST_(?P<po>.+?)_[^_]+_\d+$")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_since(value: str) -> datetime:
    """Parse a relative (e.g. '24h', '7d') or ISO 8601 timestamp into datetime."""
    if not value:
        return _now_utc() - timedelta(hours=24)
    m = re.match(r"^(\d+)(h|d|m)$", value.strip().lower())
    if m:
        n, unit = int(m.group(1)), m.group(2)
        delta = timedelta(hours=n) if unit == "h" else (timedelta(days=n) if unit == "d" else timedelta(minutes=n))
        return _now_utc() - delta
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_until(value: Optional[str]) -> datetime:
    if not value:
        return _now_utc()
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _ns_date(dt: datetime) -> str:
    """Format a datetime for NetSuite SuiteQL date comparisons (MM/DD/YYYY)."""
    return dt.strftime("%m/%d/%Y")


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _http_get(url: str, headers: dict = None, timeout: int = DEFAULT_TIMEOUT) -> dict:
    headers = headers or {}
    for attempt in range(MAX_RETRIES):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=timeout) as r:
                body = r.read().decode()
                return json.loads(body) if body.strip() else []
        except HTTPError as e:
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt * 10)
                continue
            body = e.read().decode() if e.fp else ""
            return {"error": True, "status": e.code, "message": e.reason, "details": body}
        except URLError as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            print(f"Fatal: HTTP request failed: {e.reason}", file=sys.stderr)
            sys.exit(2)
    return {"error": True, "message": "Max retries exceeded"}


def _http_post(url: str, payload: dict, headers: dict = None,
               timeout: int = DEFAULT_TIMEOUT) -> dict:
    headers = headers or {}
    headers["Content-Type"] = "application/json"
    body = json.dumps(payload).encode()
    for attempt in range(MAX_RETRIES):
        try:
            req = Request(url, data=body, headers=headers, method="POST")
            with urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except HTTPError as e:
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt * 10)
                continue
            body_err = e.read().decode() if e.fp else ""
            return {"error": True, "status": e.code, "message": e.reason, "details": body_err}
        except URLError as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            print(f"Fatal: NS gateway unreachable: {e.reason}", file=sys.stderr)
            sys.exit(2)
    return {"error": True, "message": "Max retries exceeded"}


# ---------------------------------------------------------------------------
# Celigo API calls
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    if not CONFIG_FILE.exists():
        print(f"Fatal: Config not found at {CONFIG_FILE}. Run celigo-setup.", file=sys.stderr)
        sys.exit(2)
    with open(CONFIG_FILE) as f:
        return json.load(f)


def _get_celigo_creds(env_name: str = None) -> tuple:
    config = _load_config()
    env_name = env_name or config.get("defaults", {}).get("environment", "production")
    env = config.get("environments", {}).get(env_name)
    if not env:
        print(f"Fatal: Celigo environment '{env_name}' not found in config.", file=sys.stderr)
        sys.exit(2)
    api_url = env.get("api_url", "https://api.integrator.io/v1")
    api_key = env.get("api_key", "")
    if not api_key or api_key.startswith("YOUR_"):
        print("Fatal: Celigo API key not configured.", file=sys.stderr)
        sys.exit(2)
    return api_url, api_key


def _celigo_get(api_url: str, api_key: str, endpoint: str,
                params: dict = None) -> list:
    url = f"{api_url}{endpoint}"
    if params:
        params = {k: v for k, v in params.items() if v is not None}
        if params:
            url += "?" + urlencode(params)
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    result = _http_get(url, headers)
    if isinstance(result, dict) and result.get("error"):
        print(f"Fatal: Celigo API error on {endpoint}: {result.get('message')}",
              file=sys.stderr)
        sys.exit(2)
    return result if isinstance(result, list) else [result]


# ---------------------------------------------------------------------------
# NetSuite SuiteQL queries
# ---------------------------------------------------------------------------

def _ns_query(sql: str) -> list:
    payload = {
        "action": "queryRun",
        "procedure": "queryRun",
        "query": sql,
        "params": [],
        "returnAllRows": True,
        "netsuiteAccount": NS_ACCOUNT,
        "netsuiteEnvironment": NS_ENVIRONMENT,
    }
    ns_api_key = os.environ.get("NETSUITE_API_KEY", "")
    headers = {"X-API-Key": ns_api_key} if ns_api_key else {}
    result = _http_post(NS_GATEWAY_URL, payload, headers=headers)
    # Gateway response: {success: bool, data: {records: [...]}} on success
    #                   {success: false, error: {message, type, ...}} on failure
    if isinstance(result, dict):
        if not result.get("success"):
            err = result.get("error") or {}
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            print(f"Fatal: NS gateway error: {msg}", file=sys.stderr)
            sys.exit(2)
        return result.get("data", {}).get("records", [])
    # Fallback: bare list (shouldn't happen with this gateway)
    if isinstance(result, list):
        return result
    return []


def _ns_edi_history_inbound(doc_type_id: int, since_dt: datetime,
                            until_dt: datetime) -> list:
    """Fetch NS EDI History rows for an inbound doc type in the given window."""
    since_ns = _ns_date(since_dt)
    # Use exclusive upper bound (next day) so records created on until_dt's date are included.
    # SuiteQL treats 'MM/DD/YYYY' as midnight, so <= today excludes records created after 00:00.
    until_exclusive = _ns_date(until_dt + timedelta(days=1))
    sql = (
        f"SELECT h.id, h.externalid, h.custrecord_twx_edi_history_status AS status, "
        f"h.custrecord_twx_edi_history_transaction AS transaction_id, "
        f"h.custrecord_twx_eth_edi_tp AS trading_partner_id, "
        f"h.created "
        f"FROM customrecord_twx_edi_history h "
        f"WHERE h.custrecord_twx_edi_type = {doc_type_id} "
        f"AND h.created >= '{since_ns}' AND h.created < '{until_exclusive}' "
        f"FETCH FIRST 1000 ROWS ONLY"
    )
    return _ns_query(sql)


def _ns_edi_history_outbound(doc_type_id: int, since_dt: datetime,
                             until_dt: datetime) -> list:
    """Fetch NS EDI History rows for an outbound doc type marked sent (status=2)."""
    since_ns = _ns_date(since_dt)
    until_exclusive = _ns_date(until_dt + timedelta(days=1))
    sql = (
        f"SELECT h.id, h.externalid, h.custrecord_twx_edi_history_status AS status, "
        f"h.custrecord_twx_edi_history_transaction AS transaction_id, "
        f"h.custrecord_twx_eth_edi_tp AS trading_partner_id, "
        f"h.created "
        f"FROM customrecord_twx_edi_history h "
        f"WHERE h.custrecord_twx_edi_type = {doc_type_id} "
        f"AND h.custrecord_twx_edi_history_status = 2 "
        f"AND h.created >= '{since_ns}' AND h.created < '{until_exclusive}' "
        f"FETCH FIRST 1000 ROWS ONLY"
    )
    return _ns_query(sql)


def _extract_po_from_externalid(externalid: str) -> Optional[str]:
    if not externalid:
        return None
    m = _EXTERNALID_RE.match(externalid)
    return m.group("po") if m else None


# ---------------------------------------------------------------------------
# EDI integration discovery
# ---------------------------------------------------------------------------

def _get_edi_flows(api_url: str, api_key: str,
                   partner_filter: Optional[str] = None) -> list:
    """
    Return all enabled production EDI flows, parsed for partner/doc-type/direction.

    Flow naming convention: "PartnerName - 850 IB - Description"
    Integration naming convention: "EDI - PartnerName" (sandbox=False for production)
    """
    all_ints = _celigo_get(api_url, api_key, "/integrations")
    result = []
    for intg in all_ints:
        name = intg.get("name", "")
        # Skip sandbox (non-production) integrations
        if intg.get("sandbox") is True:
            continue
        # Only process integrations named "EDI - ..." or "EDI | ..."
        if not _EDI_INTEGRATION_RE.match(name):
            continue

        # List flows within this integration
        flows = _celigo_get(api_url, api_key, f"/integrations/{intg['_id']}/flows")
        for flow in flows:
            # Skip disabled flows
            if flow.get("disabled"):
                continue
            flow_name = flow.get("name", "")
            m = _EDI_FLOW_RE.match(flow_name)
            if not m:
                continue
            partner = m.group("partner").strip()
            doc_type = m.group("doc_type")
            direction = m.group("dir").upper()

            if partner_filter and partner_filter.lower() not in partner.lower():
                continue

            result.append({
                "_id": flow["_id"],
                "_integrationId": intg["_id"],
                "integration_name": name,
                "flow_name": flow_name,
                "partner": partner,
                "doc_type": doc_type,
                "direction": direction,
            })
    return result


def _get_jobs_for_integration(api_url: str, api_key: str,
                              integration_id: str, since_iso: str,
                              until_iso: str) -> list:
    """Fetch completed jobs for an integration in the given window."""
    return _celigo_get(api_url, api_key, "/jobs", {
        "_integrationId": integration_id,
        "status": "completed",
        "type": "flow",
        "createdAt_gte": since_iso,
        "createdAt_lte": until_iso,
        "pageSize": 1000,
    })


# ---------------------------------------------------------------------------
# Reconciliation logic
# ---------------------------------------------------------------------------

def _reconcile_inbound(celigo_num_success: int, ns_rows: list,
                       doc_type: str) -> list:
    """
    Compare Celigo activity (sum numSuccess) against NS EDI History rows for a doc type.
    Flags NS processing failures, 850s without linked SOs, and Celigo-only activity.
    """
    mismatches = []
    ns_success_rows = [r for r in ns_rows if str(r.get("status", "")) == "2"]
    ns_error_rows = [r for r in ns_rows if str(r.get("status", "")) != "2"]

    # NS processing failures
    for row in ns_error_rows:
        mismatches.append({
            "bucket": "ns_status_error",
            "type": "ns_processing_failed",
            "doc_type": doc_type,
            "ns_id": row.get("id"),
            "externalid": row.get("externalid"),
            "ns_status": row.get("status"),
            "created": row.get("created"),
        })

    # For 850: flag POs that landed in NS but have no linked SO
    if doc_type == "850":
        for row in ns_success_rows:
            if not row.get("transaction_id"):
                mismatches.append({
                    "bucket": "ns_status_error",
                    "type": "pos_without_order",
                    "doc_type": doc_type,
                    "ns_id": row.get("id"),
                    "externalid": row.get("externalid"),
                    "created": row.get("created"),
                })

    # Celigo processed records but NS has nothing in the window
    if celigo_num_success > 0 and len(ns_rows) == 0:
        mismatches.append({
            "bucket": "celigo_success_ns_missing",
            "type": "no_ns_records",
            "doc_type": doc_type,
            "celigo_num_success": celigo_num_success,
            "ns_record_count": 0,
            "note": f"Celigo processed {celigo_num_success} record(s) but NS has no {doc_type} history in window",
        })

    return mismatches


def _reconcile_outbound(celigo_num_success: int, ns_rows: list,
                        doc_type: str) -> list:
    """
    For outbound, NS is the source of truth for sent records.
    Flags when NS shows sent documents but Celigo had no activity.
    """
    mismatches = []
    ns_count = len(ns_rows)

    if ns_count > 0 and celigo_num_success == 0:
        mismatches.append({
            "bucket": "ns_sent_celigo_missing",
            "type": "no_celigo_activity",
            "doc_type": doc_type,
            "ns_sent_count": ns_count,
            "celigo_num_success": 0,
            "note": f"NS has {ns_count} sent {doc_type} record(s) but Celigo had no activity",
        })

    return mismatches


# ---------------------------------------------------------------------------
# Main audit runner
# ---------------------------------------------------------------------------

def run_audit(since: str, until: Optional[str], direction: str,
              partner_filter: Optional[str], env_name: Optional[str]) -> dict:
    since_dt = _parse_since(since)
    until_dt = _parse_until(until)
    since_iso = _iso(since_dt)
    until_iso = _iso(until_dt)

    api_url, api_key = _get_celigo_creds(env_name)

    _EMPTY = {
        "audit_window": {"since": since_iso, "until": until_iso},
        "direction": direction,
        "partner_filter": partner_filter,
        "flows_scanned": 0,
        "total_mismatches": 0,
        "buckets": {
            "celigo_success_ns_missing": [],
            "ns_sent_celigo_missing": [],
            "ns_status_error": [],
        },
    }

    edi_flows = _get_edi_flows(api_url, api_key, partner_filter)
    if not edi_flows:
        _EMPTY["summary"] = "No matching production EDI flows found."
        return _EMPTY

    # --- Step 1: Collect jobs per integration (one query per integration) ---
    # Group flows by integration to minimise API calls
    intg_flows: dict = {}
    for flow in edi_flows:
        intg_flows.setdefault(flow["_integrationId"], []).append(flow)

    jobs_by_flow: dict = {}   # _flowId -> [job, ...]
    for intg_id in intg_flows:
        intg_jobs = _get_jobs_for_integration(api_url, api_key, intg_id,
                                              since_iso, until_iso)
        for job in intg_jobs:
            fid = job.get("_flowId")
            if fid:
                jobs_by_flow.setdefault(fid, []).append(job)

    # --- Step 2: Aggregate Celigo activity per doc_type ---
    # celigo_by_doctype[doc_type] = {"num_success": int, "flow_count": int, "direction": str}
    celigo_by_doctype: dict = {}
    scanned = 0
    for flow in edi_flows:
        dt = flow["doc_type"]
        d = flow["direction"]
        is_inbound = d in ("IB", "INB")
        is_outbound = d == "OB"

        if direction == "inbound" and not is_inbound:
            continue
        if direction == "outbound" and not is_outbound:
            continue
        if dt not in INBOUND_TYPES and dt not in OUTBOUND_TYPES:
            continue

        flow_jobs = jobs_by_flow.get(flow["_id"], [])
        flow_success = sum(j.get("numSuccess", 0) for j in flow_jobs)
        scanned += 1

        if dt not in celigo_by_doctype:
            celigo_by_doctype[dt] = {
                "num_success": 0,
                "flow_count": 0,
                "job_count": 0,
                "direction": d,
            }
        celigo_by_doctype[dt]["num_success"] += flow_success
        celigo_by_doctype[dt]["flow_count"] += 1
        celigo_by_doctype[dt]["job_count"] += len(flow_jobs)

    # --- Step 3: Fetch NS data once per needed doc_type ---
    ns_by_doctype: dict = {}
    for dt, activity in celigo_by_doctype.items():
        ns_type_id = NS_DOC_TYPE_MAP.get(dt)
        if not ns_type_id:
            continue
        is_inbound = activity["direction"] in ("IB", "INB")
        if is_inbound:
            ns_by_doctype[dt] = _ns_edi_history_inbound(ns_type_id, since_dt, until_dt)
        else:
            ns_by_doctype[dt] = _ns_edi_history_outbound(ns_type_id, since_dt, until_dt)

    # --- Step 4: Reconcile per doc_type ---
    all_mismatches = []
    doc_type_summary = {}
    for dt, activity in celigo_by_doctype.items():
        ns_rows = ns_by_doctype.get(dt, [])
        is_inbound = activity["direction"] in ("IB", "INB")
        ns_ok = sum(1 for r in ns_rows if str(r.get("status", "")) == "2")
        ns_err = len(ns_rows) - ns_ok

        if is_inbound:
            mismatches = _reconcile_inbound(activity["num_success"], ns_rows, dt)
        else:
            mismatches = _reconcile_outbound(activity["num_success"], ns_rows, dt)
        all_mismatches.extend(mismatches)

        doc_type_summary[dt] = {
            "direction": "inbound" if is_inbound else "outbound",
            "celigo_flows": activity["flow_count"],
            "celigo_jobs": activity["job_count"],
            "celigo_num_success": activity["num_success"],
            "ns_records": len(ns_rows),
            "ns_ok": ns_ok,
            "ns_errors": ns_err,
            "mismatches": len(mismatches),
        }

    buckets = {
        "celigo_success_ns_missing": [m for m in all_mismatches
                                       if m["bucket"] == "celigo_success_ns_missing"],
        "ns_sent_celigo_missing": [m for m in all_mismatches
                                    if m["bucket"] == "ns_sent_celigo_missing"],
        "ns_status_error": [m for m in all_mismatches
                            if m["bucket"] == "ns_status_error"],
    }

    return {
        "audit_window": {"since": since_iso, "until": until_iso},
        "direction": direction,
        "partner_filter": partner_filter,
        "flows_scanned": scanned,
        "total_mismatches": len(all_mismatches),
        "doc_type_summary": doc_type_summary,
        "buckets": buckets,
    }


def _print_human_summary(result: dict) -> None:
    buckets = result.get("buckets", {})
    print("=" * 70)
    print("EDI Cross-System Audit Report")
    print(f"  Window:    {result['audit_window']['since']} → {result['audit_window']['until']}")
    print(f"  Partner:   {result.get('partner_filter') or 'all'}")
    print(f"  Direction: {result['direction']}")
    print(f"  Flows scanned: {result.get('flows_scanned', 0)}")
    print(f"  Total mismatches: {result['total_mismatches']}")
    print("=" * 70)

    # Per-doc-type activity table
    # Celigo 'num_success' counts processed line items (not documents) and is not
    # directly comparable to NS record counts, so the table shows job/flow counts instead.
    doc_summary = result.get("doc_type_summary", {})
    if doc_summary:
        print(f"\n{'DocType':<8} {'Dir':<9} {'Flows':>6} {'Jobs':>6} {'NS Records':>11} {'NS OK':>6} {'NS Err':>7} {'Flags':>6}")
        print("-" * 62)
        for dt in sorted(doc_summary.keys()):
            s = doc_summary[dt]
            print(f"{dt:<8} {s['direction']:<9} {s['celigo_flows']:>6} {s['celigo_jobs']:>6} "
                  f"{s['ns_records']:>11} {s['ns_ok']:>6} {s['ns_errors']:>7} {s['mismatches']:>6}")

    # Mismatch details
    for bucket, label in [
        ("celigo_success_ns_missing", "Celigo success / NS missing"),
        ("ns_sent_celigo_missing", "NS sent / Celigo missing"),
        ("ns_status_error", "NS processing errors"),
    ]:
        items = buckets.get(bucket, [])
        status = "✓ clean" if not items else f"✗ {len(items)} finding(s)"
        print(f"\n{label}: {status}")
        for item in items:
            exid = item.get("externalid", "")
            note = item.get("note", "")
            line = f"  - [{item.get('doc_type')}] {item.get('type')}"
            if exid:
                line += f" — {exid}"
            elif note:
                line += f" — {note}"
            print(line)

    if result["total_mismatches"] == 0:
        print("\n✓ All EDI records reconcile cleanly.")
    else:
        print(f"\n✗ {result['total_mismatches']} mismatch(es) require attention.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Reconcile Celigo EDI job history against NetSuite EDI History",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--since", default="24h",
                   help="Start of audit window (ISO 8601 or relative: 24h, 7d)")
    p.add_argument("--until", default=None,
                   help="End of audit window (ISO 8601 or relative; default: now)")
    p.add_argument("--partner",
                   help="Filter to integrations matching this partner name (substring)")
    p.add_argument("--direction", choices=["inbound", "outbound", "both"], default="both")
    p.add_argument("--env", default=None, help="Celigo environment (production/sandbox)")
    p.add_argument("--json-only", action="store_true",
                   help="Emit only JSON output; suppress human-readable summary")
    p.add_argument("--exit-nonzero-on-mismatch", action="store_true",
                   help="Exit with code 1 when mismatches are found (useful in CI)")
    return p


def main():
    parser = _build_parser()
    args = parser.parse_args()

    result = run_audit(
        since=args.since,
        until=args.until,
        direction=args.direction,
        partner_filter=args.partner,
        env_name=args.env,
    )

    print(json.dumps(result, indent=2))

    if not args.json_only:
        print()
        _print_human_summary(result)

    if args.exit_nonzero_on_mismatch and result.get("total_mismatches", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
