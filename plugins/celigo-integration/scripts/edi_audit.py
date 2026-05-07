#!/usr/bin/env python3
"""
EDI Cross-System Audit

Reconciles Celigo EDI job history against NetSuite EDI History records to
surface mismatches between what Celigo processed and what NetSuite recorded.

Inbound leg (850/856/860):
  For each successful Celigo job on an inbound EDI flow, verify a matching
  customrecord_twx_edi_history row exists in NetSuite with status=2 (success)
  and (for 850) a non-null transaction link.

Outbound leg (810/846/855/856):
  For each NetSuite EDI History row with status=2 (sent) on outbound doc types,
  verify a corresponding successful Celigo job exists in the same window.

Output: structured JSON + human-readable summary (three failure buckets).

Usage:
    python3 edi_audit.py [--since 24h|today|yesterday] [--until now|today]
                         [--partner NAME] [--direction inbound|outbound|both]
                         [--tz America/Chicago] [--json-only]
                         [--exit-nonzero-on-mismatch]

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

try:
    from zoneinfo import ZoneInfo
except ImportError:
    try:
        from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]
    except ImportError:
        ZoneInfo = None  # type: ignore[assignment,misc]

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
DEFAULT_TZ = "America/Chicago"

# EDI doc type code → tuple of NS custrecord_twx_edi_type internal IDs.
# Multiple type IDs per doc type are supported (counts merged in reconciliation).
#
# Authoritative source: SELECT id, name FROM CUSTOMLIST_TWX_EDI_DOCUMENTS ORDER BY id
#   id=1   810 - Invoice
#   id=2   846 - Inventory Advice
#   id=3   850 - Purchase Order
#   id=4   855 - Purchase Order Acknowledgement
#   id=5   856 - Advance Ship Notice
#   id=6   860 - Purchase Order Change Request
#   id=7   864 - Text Message
#   id=8   940 - Warehouse Shipping Order         (NXP only, no Celigo flows)
#   id=9   945 - Warehouse Shipping Advice        (NXP only, no Celigo flows)
#   id=10  870 - Order Status Report              (no Celigo flows)
#   id=11  852 - Product Activity Data
#   id=12  812 - Credit/Debit Adjustment
#   id=13  824 - Application Advice
#   id=14  943 - Warehouse Stock Transfer Shipment Advice  (NXP only)
#   id=15  944 - Warehouse Stock Transfer Receipt Advice   (NXP only)
#   id=16  820 - Remittance Advice
#   id=17  940 V2                                 (NXP only, inactive)
#   id=18  BIG CSV IF Order                       (non-EDI CSV, no standard flows)
#   id=19  Inventory Feed CSV                     (non-EDI CSV, no standard flows)
#   id=20  816 - Organizational Relationships     (no Celigo flows)
#
# 997 (Functional Acknowledgement) has no list entry: 997 Celigo flows update the
# FA status field on existing EDI TH records — they do not create new records.
#
# NXP types (8,9,14,15,17), non-EDI CSV types (18,19), and types with no active
# Celigo flows (10,20) are intentionally absent from this map.
#
# 820 note: the only enabled Celigo 820 flow is Buckle, whose NS trading partner
# is tagged TrueCommerce (int=3) — those records are excluded by the int=6 filter,
# so 820 will typically show ns_records=0 in this audit.
NS_DOC_TYPE_MAP = {
    "810": (1,),   # Invoice (outbound)
    "812": (12,),  # Credit/Debit Adjustment (inbound) — Buckle, Rural King
    "820": (16,),  # Remittance Advice (inbound) — Buckle (TrueCommerce in NS, see note)
    "824": (13,),  # Application Advice (inbound)
    "846": (2,),   # Inventory Advice (outbound)
    "850": (3,),   # Purchase Order (inbound)
    "852": (11,),  # Product Activity Data (inbound)
    "855": (4,),   # PO Acknowledgement (outbound)
    "856": (5,),   # ASN (outbound)
    "860": (6,),   # PO Change Request (inbound)
    "864": (7,),   # Text Message (inbound) — Boot Barn, Shoe Carnival
}

INBOUND_TYPES = frozenset(["850", "812", "820", "824", "852", "860", "864"])
OUTBOUND_TYPES = frozenset(["810", "846", "855", "856"])

# NS trading partner field value for Celigo-integrated partners.
# Partners with int=3 are on TrueCommerce and must be excluded from this audit.
NS_CELIGO_INT = 6

# Regex to extract partner name + doc type + direction from Celigo FLOW names.
# Handles two naming conventions used in production:
#   "Partner - 850 IB - Description"          (minority, no EDI keyword)
#   "Partner - EDI 850 IB - Description"      (majority, has EDI keyword)
#   "Partner - EDI 850 - Inbound/Outbound"    (spelled-out direction)
_EDI_FLOW_RE = re.compile(
    r"^(?P<partner>.+?)\s*-\s*(?:EDI\s+)?(?P<doc_type>\d{3})\s+"
    r"(?P<dir>IB|OB|INB|Inbound|Outbound)\b",
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


def _get_tz(tz_name: str):
    """Return a ZoneInfo object, or None if zoneinfo is unavailable."""
    if ZoneInfo is None:
        return None
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return None


def _midnight_local(date_offset: int, tz_name: str) -> datetime:
    """Return midnight (start of day) offset days from today in the given timezone as UTC."""
    tz = _get_tz(tz_name)
    if tz is None:
        import sys as _sys
        _sys.stderr.write(
            f"WARNING: zoneinfo unavailable; --tz {tz_name!r} ignored, falling back to UTC. "
            "Install 'backports.zoneinfo' on Python < 3.9 for accurate local-midnight dates.\n"
        )
        base = _now_utc().replace(hour=0, minute=0, second=0, microsecond=0)
        return base + timedelta(days=date_offset)
    now_local = datetime.now(tz)
    target_date = (now_local + timedelta(days=date_offset)).date()
    midnight_local = datetime(target_date.year, target_date.month, target_date.day, tzinfo=tz)
    return midnight_local.astimezone(timezone.utc)


def _format_local(dt: datetime, tz_name: str) -> str:
    """Format a UTC datetime as a human-readable string in the given timezone."""
    tz = _get_tz(tz_name)
    if tz is None:
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    local = dt.astimezone(tz)
    return local.strftime("%Y-%m-%d %H:%M %Z")


def _parse_since(value: str, tz_name: str = DEFAULT_TZ) -> datetime:
    """Parse a relative (e.g. '24h', '7d'), keyword (today/yesterday), or ISO 8601 timestamp."""
    if not value:
        return _now_utc() - timedelta(hours=24)
    v = value.strip().lower()
    if v == "today":
        return _midnight_local(0, tz_name)
    if v == "yesterday":
        return _midnight_local(-1, tz_name)
    m = re.match(r"^(\d+)(h|d|m)$", v)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        delta = timedelta(hours=n) if unit == "h" else (timedelta(days=n) if unit == "d" else timedelta(minutes=n))
        return _now_utc() - delta
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_until(value: Optional[str], tz_name: str = DEFAULT_TZ) -> datetime:
    if not value:
        return _now_utc()
    v = value.strip().lower()
    if v == "today":
        # End of today = start of tomorrow
        return _midnight_local(1, tz_name)
    if v == "yesterday":
        return _midnight_local(0, tz_name)
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


def _ns_edi_summary(since_dt: datetime, until_dt: datetime) -> dict:
    """
    Single aggregated query: counts per doc type for the entire window.
    Returns: {str(type_id): {"total": int, "ok": int, "err": int}}

    Joins the trading partner record to filter to Celigo-only (int=NS_CELIGO_INT),
    excluding TrueCommerce (int=3) and other non-Celigo platforms.

    Uses COALESCE(custrecord_twx_edi_history_dat, created) so outbound records are
    bucketed by actual transmission date while inbound records (where dat is null)
    fall back to their creation date.
    """
    since_ns = _ns_date(since_dt)
    until_exclusive = _ns_date(until_dt)
    sql = (
        "SELECT h.custrecord_twx_edi_type AS doc_type_id, "
        "COUNT(*) AS total, "
        "SUM(CASE WHEN h.custrecord_twx_edi_history_status = 2 THEN 1 ELSE 0 END) AS ok_cnt, "
        "SUM(CASE WHEN h.custrecord_twx_edi_history_status != 2 THEN 1 ELSE 0 END) AS err_cnt "
        "FROM customrecord_twx_edi_history h "
        "JOIN customrecord_twx_edi_tp tp ON tp.id = h.custrecord_twx_eth_edi_tp "
        f"WHERE tp.custrecord_twx_edi_tp_int = {NS_CELIGO_INT} "
        f"AND COALESCE(h.custrecord_twx_edi_history_dat, h.created) >= '{since_ns}' "
        f"AND COALESCE(h.custrecord_twx_edi_history_dat, h.created) < '{until_exclusive}' "
        "GROUP BY h.custrecord_twx_edi_type"
    )
    rows = _ns_query(sql)
    result = {}
    for row in rows:
        tid = str(row.get("doc_type_id", ""))
        result[tid] = {
            "total": int(row.get("total", 0)),
            "ok": int(row.get("ok_cnt", 0)),
            "err": int(row.get("err_cnt", 0)),
        }
    return result


def _ns_edi_history_inbound(doc_type_ids: tuple, since_dt: datetime,
                            until_dt: datetime) -> list:
    """Fetch NS EDI History rows for an inbound doc type (Celigo partners only)."""
    since_ns = _ns_date(since_dt)
    until_exclusive = _ns_date(until_dt)
    type_id_sql = ",".join(str(i) for i in doc_type_ids)
    sql = (
        f"SELECT h.id, h.externalid, h.custrecord_twx_edi_history_status AS status, "
        f"h.custrecord_twx_edi_history_transaction AS transaction_id, "
        f"h.custrecord_twx_eth_edi_tp AS trading_partner_id, "
        f"h.created "
        f"FROM customrecord_twx_edi_history h "
        f"JOIN customrecord_twx_edi_tp tp ON tp.id = h.custrecord_twx_eth_edi_tp "
        f"WHERE tp.custrecord_twx_edi_tp_int = {NS_CELIGO_INT} "
        f"AND h.custrecord_twx_edi_type IN ({type_id_sql}) "
        f"AND h.created >= '{since_ns}' AND h.created < '{until_exclusive}' "
        f"FETCH FIRST 1000 ROWS ONLY"
    )
    rows = _ns_query(sql)
    if len(rows) == 1000:
        import sys as _sys
        _sys.stderr.write(
            f"WARNING: NS inbound detail query returned exactly 1000 rows for type IDs "
            f"{doc_type_ids}; results may be truncated. Narrow the time window to get "
            "accurate reconciliation.\n"
        )
    return rows


def _ns_edi_history_outbound(doc_type_ids: tuple, since_dt: datetime,
                             until_dt: datetime) -> list:
    """Fetch NS EDI History rows for an outbound doc type marked sent (Celigo partners only).
    Filters by custrecord_twx_edi_history_dat (actual transmission date/time).
    """
    since_ns = _ns_date(since_dt)
    until_exclusive = _ns_date(until_dt)
    type_id_sql = ",".join(str(i) for i in doc_type_ids)
    sql = (
        f"SELECT h.id, h.externalid, h.custrecord_twx_edi_history_status AS status, "
        f"h.custrecord_twx_edi_history_transaction AS transaction_id, "
        f"h.custrecord_twx_eth_edi_tp AS trading_partner_id, "
        f"h.custrecord_twx_edi_history_dat AS transmitted_at "
        f"FROM customrecord_twx_edi_history h "
        f"JOIN customrecord_twx_edi_tp tp ON tp.id = h.custrecord_twx_eth_edi_tp "
        f"WHERE tp.custrecord_twx_edi_tp_int = {NS_CELIGO_INT} "
        f"AND h.custrecord_twx_edi_type IN ({type_id_sql}) "
        f"AND h.custrecord_twx_edi_history_status = 2 "
        f"AND h.custrecord_twx_edi_history_dat >= '{since_ns}' "
        f"AND h.custrecord_twx_edi_history_dat < '{until_exclusive}' "
        f"FETCH FIRST 1000 ROWS ONLY"
    )
    rows = _ns_query(sql)
    if len(rows) == 1000:
        import sys as _sys
        _sys.stderr.write(
            f"WARNING: NS outbound detail query returned exactly 1000 rows for type IDs "
            f"{doc_type_ids}; results may be truncated. Narrow the time window to get "
            "accurate reconciliation.\n"
        )
    return rows


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
            raw_dir = m.group("dir").upper()
            direction = "IB" if raw_dir in ("IB", "INB", "INBOUND") else "OB"

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

def _reconcile_inbound(celigo_docs: int, ns_rows: list,
                       doc_type: str) -> list:
    """
    Compare Celigo EDI document count (numPagesGenerated) against NS EDI History rows.
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

    # Celigo processed EDI docs but NS has nothing in the window
    if celigo_docs > 0 and len(ns_rows) == 0:
        mismatches.append({
            "bucket": "celigo_success_ns_missing",
            "type": "no_ns_records",
            "doc_type": doc_type,
            "celigo_docs": celigo_docs,
            "ns_record_count": 0,
            "note": f"Celigo processed {celigo_docs} EDI doc(s) but NS has no {doc_type} history in window",
        })

    return mismatches


def _reconcile_outbound(celigo_docs: int, ns_rows: list,
                        doc_type: str) -> list:
    """
    For outbound, NS is the source of truth for sent records.
    Flags when NS shows sent documents but Celigo had no activity.
    """
    mismatches = []
    ns_count = len(ns_rows)

    if ns_count > 0 and celigo_docs == 0:
        mismatches.append({
            "bucket": "ns_sent_celigo_missing",
            "type": "no_celigo_activity",
            "doc_type": doc_type,
            "ns_sent_count": ns_count,
            "celigo_docs": 0,
            "note": f"NS has {ns_count} sent {doc_type} record(s) but Celigo had no activity",
        })

    return mismatches


# ---------------------------------------------------------------------------
# Main audit runner
# ---------------------------------------------------------------------------

def run_audit(since: str, until: Optional[str], direction: str,
              partner_filter: Optional[str], env_name: Optional[str],
              tz_name: str = DEFAULT_TZ) -> dict:
    since_dt = _parse_since(since, tz_name)
    until_dt = _parse_until(until, tz_name)
    since_iso = _iso(since_dt)
    until_iso = _iso(until_dt)

    api_url, api_key = _get_celigo_creds(env_name)

    _EMPTY = {
        "audit_window": {
            "since": since_iso,
            "until": until_iso,
            "since_local": _format_local(since_dt, tz_name),
            "until_local": _format_local(until_dt, tz_name),
            "tz": tz_name,
        },
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

    # --- Step 1: NS is the source of truth — one aggregated query for all doc types ---
    # This tells us exactly what was exchanged in the window without touching Celigo flows.
    # ns_rev_map: type_id_str → doc_type (supports multiple type_ids per doc type)
    ns_rev_map = {}
    for dt_code, type_ids in NS_DOC_TYPE_MAP.items():
        for tid in type_ids:
            ns_rev_map[str(tid)] = dt_code
    ns_agg_raw = _ns_edi_summary(since_dt, until_dt)  # {type_id_str: {total, ok, err}}

    # Merge multi-type_id doc types (e.g. 855 uses both type_id=4 and type_id=7)
    ns_agg: dict = {}  # {doc_type_code: {total, ok, err}}
    for type_id_str, counts in ns_agg_raw.items():
        dt_code = ns_rev_map.get(type_id_str)
        if not dt_code:
            continue  # NXP/unknown type_ids — intentionally excluded
        if dt_code not in ns_agg:
            ns_agg[dt_code] = {"total": 0, "ok": 0, "err": 0}
        ns_agg[dt_code]["total"] += counts["total"]
        ns_agg[dt_code]["ok"] += counts["ok"]
        ns_agg[dt_code]["err"] += counts["err"]

    # --- Step 2: Celigo flow discovery (needed for cross-validation) ---
    # Only enumerate flows — jobs are fetched per-integration below.
    edi_flows = _get_edi_flows(api_url, api_key, partner_filter)
    if not edi_flows and not ns_agg:
        _EMPTY["summary"] = "No EDI activity found in NS and no matching production flows."
        return _EMPTY

    # Group flows by integration to minimise Celigo API calls
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

    # --- Step 3: Aggregate Celigo activity per doc_type ---
    celigo_by_doctype: dict = {}
    scanned = 0
    for flow in edi_flows:
        dt = flow["doc_type"]
        d = flow["direction"]   # normalised to "IB" or "OB"
        is_inbound = d == "IB"

        if direction == "inbound" and not is_inbound:
            continue
        if direction == "outbound" and is_inbound:
            continue
        if dt not in NS_DOC_TYPE_MAP:
            continue  # no NS record type for this doc type; skip

        flow_jobs = jobs_by_flow.get(flow["_id"], [])
        # numPagesGenerated = pages from the source (pageGenerator) = EDI document count (1:1 with NS records)
        # numSuccess = inflated sum across all pipeline steps; not suitable for 1:1 comparison
        flow_docs = sum(j.get("numPagesGenerated", 0) for j in flow_jobs)
        flow_active = sum(1 for j in flow_jobs if j.get("numPagesGenerated", 0) > 0)
        scanned += 1

        if dt not in celigo_by_doctype:
            celigo_by_doctype[dt] = {
                "num_docs": 0,
                "flow_count": 0,
                "job_count": 0,
                "active_job_count": 0,
                "direction": d,
            }
        celigo_by_doctype[dt]["num_docs"] += flow_docs
        celigo_by_doctype[dt]["flow_count"] += 1
        celigo_by_doctype[dt]["job_count"] += len(flow_jobs)
        celigo_by_doctype[dt]["active_job_count"] += flow_active

    # --- Step 4: Build combined doc-type set (NS activity + Celigo activity) ---
    # Include doc types seen in NS even if no Celigo flows matched (and vice versa).
    # ns_agg is now keyed by doc_type directly (merged from multiple type_ids).
    all_doc_types = set(celigo_by_doctype.keys()) | set(ns_agg.keys())

    # --- Step 5: For 850 (needs per-row SO-link check) and types with NS errors,
    #             fetch individual rows; otherwise use aggregated counts ---
    ns_rows_cache: dict = {}  # dt -> list of NS rows (fetched on demand)

    def _get_ns_rows(dt: str, inbound: bool) -> list:
        if dt not in ns_rows_cache:
            type_ids = NS_DOC_TYPE_MAP.get(dt)
            if not type_ids:
                ns_rows_cache[dt] = []
            elif inbound:
                ns_rows_cache[dt] = _ns_edi_history_inbound(type_ids, since_dt, until_dt)
            else:
                ns_rows_cache[dt] = _ns_edi_history_outbound(type_ids, since_dt, until_dt)
        return ns_rows_cache[dt]

    # --- Step 6: Reconcile per doc_type ---
    all_mismatches = []
    doc_type_summary = {}
    for dt in sorted(all_doc_types):
        ns_counts = ns_agg.get(dt, {"total": 0, "ok": 0, "err": 0})

        # Direction: use actual flow data when available; fall back to type classification.
        # Celigo flows are the ground truth (e.g. 856 is OB for us even though the spec
        # allows both directions).
        if dt in celigo_by_doctype:
            actual_dir = celigo_by_doctype[dt]["direction"]   # "IB" or "OB"
        else:
            actual_dir = "IB" if dt in INBOUND_TYPES else "OB"
        is_inbound = actual_dir == "IB"
        dir_label = "inbound" if is_inbound else "outbound"

        activity = celigo_by_doctype.get(dt, {
            "num_docs": 0, "flow_count": 0, "job_count": 0, "active_job_count": 0, "direction": actual_dir,
        })

        if direction == "inbound" and not is_inbound:
            continue
        if direction == "outbound" and is_inbound:
            continue

        # Fetch per-row detail only when needed for deep reconciliation:
        #   - 850: check each row's transaction_id (SO-link audit)
        #   - any type with NS errors: surface the individual failed rows
        if dt == "850" or ns_counts["err"] > 0:
            ns_rows = _get_ns_rows(dt, is_inbound)
            mismatches = (_reconcile_inbound(activity["num_docs"], ns_rows, dt)
                          if is_inbound
                          else _reconcile_outbound(activity["num_docs"], ns_rows, dt))
        else:
            # Use aggregate counts only — no per-row fetch needed
            mismatches = []
            if is_inbound and activity["num_docs"] > 0 and ns_counts["total"] == 0:
                mismatches.append({
                    "bucket": "celigo_success_ns_missing",
                    "type": "no_ns_records",
                    "doc_type": dt,
                    "celigo_docs": activity["num_docs"],
                    "ns_record_count": 0,
                    "note": f"Celigo processed {activity['num_docs']} EDI doc(s) but NS has no {dt} history in window",
                })
            elif not is_inbound and ns_counts["ok"] > 0 and activity["job_count"] == 0:
                mismatches.append({
                    "bucket": "ns_sent_celigo_missing",
                    "type": "no_celigo_activity",
                    "doc_type": dt,
                    "ns_sent_count": ns_counts["ok"],
                    "celigo_docs": 0,
                    "note": f"NS has {ns_counts['ok']} sent {dt} record(s) but Celigo ran 0 jobs",
                })

        all_mismatches.extend(mismatches)
        doc_type_summary[dt] = {
            "direction": dir_label,
            "celigo_flows": activity["flow_count"],
            "celigo_jobs": activity["job_count"],
            "celigo_docs": activity["num_docs"],
            "ns_records": ns_counts["total"],
            "ns_ok": ns_counts["ok"],
            "ns_errors": ns_counts["err"],
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
        "audit_window": {
            "since": since_iso,
            "until": until_iso,
            "since_local": _format_local(since_dt, tz_name),
            "until_local": _format_local(until_dt, tz_name),
            "tz": tz_name,
        },
        "direction": direction,
        "partner_filter": partner_filter,
        "flows_scanned": scanned,
        "total_mismatches": len(all_mismatches),
        "doc_type_summary": doc_type_summary,
        "buckets": buckets,
    }


def _print_human_summary(result: dict) -> None:
    buckets = result.get("buckets", {})
    aw = result.get("audit_window", {})
    since_display = aw.get("since_local") or aw.get("since", "?")
    until_display = aw.get("until_local") or aw.get("until", "?")
    print("=" * 70)
    print("EDI Cross-System Audit Report")
    print(f"  Window:    {since_display} → {until_display}")
    print(f"  Partner:   {result.get('partner_filter') or 'all'}")
    print(f"  Direction: {result['direction']}")
    print(f"  Flows scanned: {result.get('flows_scanned', 0)}")
    print(f"  Total mismatches: {result['total_mismatches']}")
    print("=" * 70)

    # Per-doc-type activity table
    # "Celigo Docs" = numPagesGenerated sum — EDI documents processed (1:1 with NS records).
    doc_summary = result.get("doc_type_summary", {})
    if doc_summary:
        print(f"\n{'DocType':<8} {'Dir':<9} {'Flows':>6} {'Celigo Docs':>12} {'NS Records':>11} {'NS OK':>6} {'NS Err':>7} {'Flags':>6}")
        print("-" * 66)
        for dt in sorted(doc_summary.keys()):
            s = doc_summary[dt]
            print(f"{dt:<8} {s['direction']:<9} {s['celigo_flows']:>6} {s['celigo_docs']:>12} "
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
                   help="Start of audit window (ISO 8601, relative: 24h/7d, or: today/yesterday)")
    p.add_argument("--until", default=None,
                   help="End of audit window (ISO 8601, relative, today/yesterday; default: now)")
    p.add_argument("--partner",
                   help="Filter to integrations matching this partner name (substring)")
    p.add_argument("--direction", choices=["inbound", "outbound", "both"], default="both")
    p.add_argument("--tz", default=DEFAULT_TZ,
                   help="Timezone for today/yesterday keywords and display")
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
        tz_name=args.tz,
    )

    print(json.dumps(result, indent=2))

    if not args.json_only:
        print()
        _print_human_summary(result)

    if args.exit_nonzero_on_mismatch and result.get("total_mismatches", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
