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

# Regex to extract partner name + doc type + direction from Celigo integration name
# Matches: "PartnerName - EDI 850 IB", "PartnerName - EDI 850 INB", "PartnerName - EDI 810 OB"
_EDI_FLOW_RE = re.compile(
    r"^(?P<partner>.+?)\s*-\s*EDI\s+(?P<doc_type>\d{3})\s+(?P<dir>IB|OB|INB)\b",
    re.IGNORECASE,
)
_STAGING_RE = re.compile(r"\(\d{1,2}/\d{1,2}/\d{4}\)\s*$")

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


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _http_get(url: str, headers: dict = None, timeout: int = DEFAULT_TIMEOUT) -> dict:
    headers = headers or {}
    for attempt in range(MAX_RETRIES):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
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
        "query": sql,
        "netsuiteAccount": NS_ACCOUNT,
        "netsuiteEnvironment": NS_ENVIRONMENT,
    }
    result = _http_post(NS_GATEWAY_URL, payload)
    if isinstance(result, dict) and result.get("error"):
        print(f"Fatal: NS gateway error: {result.get('message')} — {result.get('details', '')}",
              file=sys.stderr)
        sys.exit(2)
    # Gateway returns list of rows or {items: [...]}
    if isinstance(result, list):
        return result
    return result.get("items", result.get("rows", []))


def _ns_edi_history_inbound(doc_type_id: int, since_iso: str,
                            until_iso: str) -> list:
    """Fetch NS EDI History rows for an inbound doc type in the given window."""
    sql = (
        f"SELECT h.id, h.externalid, h.custrecord_twx_edi_history_status AS status, "
        f"h.custrecord_twx_edi_history_transaction AS transaction_id, "
        f"h.custrecord_twx_eth_edi_tp AS trading_partner_id, "
        f"h.created "
        f"FROM customrecord_twx_edi_history h "
        f"WHERE h.custrecord_twx_edi_type = {doc_type_id} "
        f"AND h.created >= '{since_iso}' AND h.created <= '{until_iso}' "
        f"FETCH FIRST 1000 ROWS ONLY"
    )
    return _ns_query(sql)


def _ns_edi_history_outbound(doc_type_id: int, since_iso: str,
                             until_iso: str) -> list:
    """Fetch NS EDI History rows for an outbound doc type marked sent (status=2)."""
    sql = (
        f"SELECT h.id, h.externalid, h.custrecord_twx_edi_history_status AS status, "
        f"h.custrecord_twx_edi_history_transaction AS transaction_id, "
        f"h.custrecord_twx_eth_edi_tp AS trading_partner_id, "
        f"h.created "
        f"FROM customrecord_twx_edi_history h "
        f"WHERE h.custrecord_twx_edi_type = {doc_type_id} "
        f"AND h.custrecord_twx_edi_history_status = 2 "
        f"AND h.created >= '{since_iso}' AND h.created <= '{until_iso}' "
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

def _get_edi_integrations(api_url: str, api_key: str,
                          partner_filter: Optional[str] = None) -> list:
    """Return all non-staging EDI integrations, parsed for partner/doc-type/direction."""
    all_ints = _celigo_get(api_url, api_key, "/integrations")
    result = []
    for intg in all_ints:
        name = intg.get("name", "")
        if _STAGING_RE.search(name):
            continue
        m = _EDI_FLOW_RE.match(name)
        if not m:
            continue
        partner = m.group("partner").strip()
        doc_type = m.group("doc_type")
        direction = m.group("dir").upper()

        if partner_filter and partner_filter.lower() not in partner.lower():
            continue

        result.append({
            "_id": intg["_id"],
            "name": name,
            "partner": partner,
            "doc_type": doc_type,
            "direction": direction,
        })
    return result


def _get_jobs_for_integration(api_url: str, api_key: str,
                              integration_id: str, since_iso: str,
                              until_iso: str) -> list:
    """Fetch successful jobs for an integration in the given window."""
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

def _reconcile_inbound(celigo_jobs: list, ns_rows: list,
                       partner: str, doc_type: str) -> list:
    """
    Compare Celigo successful jobs (inbound) against NS EDI History rows.
    Returns list of mismatch dicts.
    """
    mismatches = []

    # Build NS lookup by PO number
    ns_by_po: dict = {}
    for row in ns_rows:
        po = _extract_po_from_externalid(row.get("externalid", ""))
        if po:
            ns_by_po[po] = row

    # Build NS lookup by NS id for status checks
    ns_errors = [r for r in ns_rows if str(r.get("status", "")) != "2"]
    for row in ns_errors:
        mismatches.append({
            "bucket": "ns_status_error",
            "type": "ns_processing_failed",
            "doc_type": doc_type,
            "partner": partner,
            "ns_id": row.get("id"),
            "externalid": row.get("externalid"),
            "ns_status": row.get("status"),
            "created": row.get("created"),
        })

    # For 850, check transaction link
    if doc_type == "850":
        for row in ns_rows:
            if str(row.get("status", "")) == "2" and not row.get("transaction_id"):
                mismatches.append({
                    "bucket": "ns_status_error",
                    "type": "pos_without_order",
                    "doc_type": doc_type,
                    "partner": partner,
                    "ns_id": row.get("id"),
                    "externalid": row.get("externalid"),
                    "created": row.get("created"),
                })

    # Count Celigo successes vs NS rows
    celigo_success_count = sum(1 for j in celigo_jobs if j.get("status") == "completed")
    ns_success_count = sum(1 for r in ns_rows if str(r.get("status", "")) == "2")

    if celigo_success_count > ns_success_count:
        mismatches.append({
            "bucket": "celigo_success_ns_missing",
            "type": "count_mismatch",
            "doc_type": doc_type,
            "partner": partner,
            "celigo_success_count": celigo_success_count,
            "ns_success_count": ns_success_count,
            "note": "More Celigo successes than NS records — some may not have landed",
        })

    return mismatches


def _reconcile_outbound(ns_rows: list, celigo_jobs: list,
                        partner: str, doc_type: str) -> list:
    """
    For outbound, NS is the source of truth for 'sent'.
    If NS shows a sent record but Celigo has no corresponding job, flag it.
    """
    mismatches = []
    celigo_job_count = len(celigo_jobs)
    ns_sent_count = len(ns_rows)

    if ns_sent_count > 0 and celigo_job_count == 0:
        mismatches.append({
            "bucket": "ns_sent_celigo_missing",
            "type": "no_celigo_jobs",
            "doc_type": doc_type,
            "partner": partner,
            "ns_sent_count": ns_sent_count,
            "celigo_job_count": celigo_job_count,
            "note": "NS shows sent records but no Celigo jobs found in window",
        })
    elif ns_sent_count > celigo_job_count * 2:
        # Significant mismatch — flag for review
        mismatches.append({
            "bucket": "ns_sent_celigo_missing",
            "type": "count_mismatch",
            "doc_type": doc_type,
            "partner": partner,
            "ns_sent_count": ns_sent_count,
            "celigo_job_count": celigo_job_count,
            "note": "NS sent count significantly higher than Celigo job count",
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

    integrations = _get_edi_integrations(api_url, api_key, partner_filter)
    if not integrations:
        return {
            "audit_window": {"since": since_iso, "until": until_iso},
            "direction": direction,
            "partner_filter": partner_filter,
            "integrations_scanned": 0,
            "mismatches": [],
            "summary": "No matching EDI integrations found.",
        }

    all_mismatches = []
    scanned = 0

    for intg in integrations:
        doc_type = intg["doc_type"]
        intg_direction = intg["direction"]
        partner = intg["partner"]
        ns_type_id = NS_DOC_TYPE_MAP.get(doc_type)
        if not ns_type_id:
            continue

        is_inbound = intg_direction in ("IB", "INB")
        is_outbound = intg_direction == "OB"

        if direction == "inbound" and not is_inbound:
            continue
        if direction == "outbound" and not is_outbound:
            continue
        if doc_type not in INBOUND_TYPES and doc_type not in OUTBOUND_TYPES:
            continue

        jobs = _get_jobs_for_integration(api_url, api_key, intg["_id"],
                                         since_iso, until_iso)
        scanned += 1

        if is_inbound and doc_type in INBOUND_TYPES:
            ns_rows = _ns_edi_history_inbound(ns_type_id, since_iso, until_iso)
            mismatches = _reconcile_inbound(jobs, ns_rows, partner, doc_type)
            all_mismatches.extend(mismatches)

        elif is_outbound and doc_type in OUTBOUND_TYPES:
            ns_rows = _ns_edi_history_outbound(ns_type_id, since_iso, until_iso)
            mismatches = _reconcile_outbound(ns_rows, jobs, partner, doc_type)
            all_mismatches.extend(mismatches)

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
        "integrations_scanned": scanned,
        "total_mismatches": len(all_mismatches),
        "buckets": buckets,
    }


def _print_human_summary(result: dict) -> None:
    buckets = result.get("buckets", {})
    print("=" * 60)
    print("EDI Cross-System Audit Report")
    print(f"  Window:   {result['audit_window']['since']} → {result['audit_window']['until']}")
    print(f"  Partner:  {result.get('partner_filter') or 'all'}")
    print(f"  Direction: {result['direction']}")
    print(f"  Integrations scanned: {result['integrations_scanned']}")
    print(f"  Total mismatches:     {result['total_mismatches']}")
    print("=" * 60)

    for bucket, label in [
        ("celigo_success_ns_missing", "Celigo success / NS missing"),
        ("ns_sent_celigo_missing", "NS sent / Celigo missing"),
        ("ns_status_error", "NS processing errors"),
    ]:
        items = buckets.get(bucket, [])
        status = "✓ clean" if not items else f"✗ {len(items)} finding(s)"
        print(f"\n{label}: {status}")
        for item in items:
            print(f"  - [{item.get('doc_type')}] {item.get('partner')}: "
                  f"{item.get('type')} — {item.get('note', '')}")

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
