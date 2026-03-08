#!/usr/bin/env python3
"""
NetSuite EDI Analytics MCP Server

FastMCP server for querying NetSuite EDI customer and transaction data
via the NetSuite API Gateway. The gateway handles all OAuth authentication —
no credentials needed in this extension.

Supported accounts:
  - twistedx (twx): Twisted X, OAuth 1.0a TBA, account 4138030
  - dutyman (dm): Dutyman, OAuth 2.0 M2M, account 8055418

Supported environments: production, sandbox, sandbox2
"""

import json
import os
from datetime import date, timedelta
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

# =============================================================================
# Configuration
# =============================================================================

BYTE_HARD_LIMIT = 900_000  # Claude Desktop 1MB limit safety buffer

mcp = FastMCP("netsuite_edi")

GATEWAY_URL = os.environ.get("NETSUITE_GATEWAY_URL", "https://nsapi.twistedx.tech")
GATEWAY_API_KEY = os.environ.get("NETSUITE_API_KEY", "")
DEFAULT_ACCOUNT = os.environ.get("NETSUITE_ACCOUNT", "twistedx")
DEFAULT_ENVIRONMENT = os.environ.get("NETSUITE_ENVIRONMENT", "production")

ACCOUNT_ALIASES = {
    "twx": "twistedx", "twisted": "twistedx", "twistedx": "twistedx",
    "dm": "dutyman", "duty": "dutyman", "dutyman": "dutyman",
}

ENV_ALIASES = {
    "prod": "production", "production": "production",
    "sb1": "sandbox", "sandbox": "sandbox", "sandbox1": "sandbox",
    "sb2": "sandbox2", "sandbox2": "sandbox2",
}

# EDI document type code → NetSuite internal ID
DOCTYPE_MAP: dict[str, int] = {
    "810": 1, "850": 3, "855": 4, "856": 5, "860": 6,
    "846": 2, "852": 11, "820": 16, "824": 13, "812": 12, "864": 7,
}

# NetSuite internal ID → human-readable name
DOCTYPE_NAMES: dict[int, str] = {
    1: "810 - Invoice",
    2: "846 - Inventory Advice",
    3: "850 - Purchase Order",
    4: "855 - PO Acknowledgment",
    5: "856 - Advance Ship Notice",
    6: "860 - PO Change",
    7: "864 - Text Message",
    11: "852 - Product Activity Data",
    12: "812 - Credit/Debit Adjustment",
    13: "824 - Application Advice",
    16: "820 - Remittance Advice",
}


# =============================================================================
# Shared helpers
# =============================================================================

async def _query(
    sql: str,
    account: Optional[str] = None,
    environment: Optional[str] = None,
    return_all_rows: bool = False,
) -> dict:
    """Execute a SuiteQL query via the NetSuite API Gateway.

    The gateway handles all OAuth. Returns dict with 'records' and 'count',
    or 'error' string on failure.
    """
    acct = ACCOUNT_ALIASES.get(
        (account or DEFAULT_ACCOUNT).lower(),
        (account or DEFAULT_ACCOUNT).lower(),
    )
    env = ENV_ALIASES.get(
        (environment or DEFAULT_ENVIRONMENT).lower(),
        (environment or DEFAULT_ENVIRONMENT).lower(),
    )

    payload = {
        "action": "queryRun",
        "procedure": "queryRun",
        "query": sql,
        "params": [],
        "returnAllRows": return_all_rows,
        "netsuiteAccount": acct,
        "netsuiteEnvironment": env,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{GATEWAY_URL.rstrip('/')}/api/suiteapi",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                **( {"X-API-Key": GATEWAY_API_KEY} if GATEWAY_API_KEY else {"Origin": "http://localhost:3000"} ),
            },
        )
        resp.raise_for_status()
        body = resp.json()

    if not body.get("success"):
        error = body.get("error", {})
        if isinstance(error, dict):
            msg = error.get("message", str(error))
        else:
            msg = str(error)
        return {"records": [], "count": 0, "error": msg, "account": acct, "environment": env}

    records = body.get("data", {}).get("records", [])
    return {
        "records": records,
        "count": len(records),
        "account": acct,
        "environment": env,
    }


def _handle_error(e: Exception) -> str:
    """Format exception as a helpful error string."""
    if isinstance(e, httpx.ConnectError):
        return (
            f"Error: Cannot connect to gateway at {GATEWAY_URL}. "
            "Is the NetSuite API Gateway running? Try: docker compose up -d"
        )
    if isinstance(e, httpx.TimeoutException):
        return "Error: Gateway request timed out (120s). Try adding ROWNUM limits or narrowing the date range."
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        try:
            body = e.response.json()
            msg = body.get("error", {}).get("message", e.response.text[:300])
        except Exception:
            msg = e.response.text[:300]
        return f"Error {code}: {msg}"
    return f"Error: {type(e).__name__}: {e}"


def _fmt(data) -> str:
    """Serialize to JSON with hard byte cap for Claude Desktop 1MB limit."""
    if isinstance(data, (list, dict)):
        text = json.dumps(data, indent=2, default=str)
    else:
        text = str(data)

    encoded = text.encode("utf-8")
    if len(encoded) <= BYTE_HARD_LIMIT:
        return text

    trimmed = encoded[:BYTE_HARD_LIMIT].decode("utf-8", errors="ignore")
    cut = trimmed.rfind("\n")
    if cut > BYTE_HARD_LIMIT // 2:
        trimmed = trimmed[:cut]
    return trimmed + "\n// [TRUNCATED — add ROWNUM limits or narrow date range]"


def _default_dates(
    start: Optional[str], end: Optional[str], lookback_days: int = 30
) -> tuple[str, str]:
    """Return (start_date, end_date) as YYYY-MM-DD strings with sensible defaults."""
    end_date = end or date.today().isoformat()
    start_date = start or (date.today() - timedelta(days=lookback_days)).isoformat()
    return start_date, end_date


def _doctype_filter(doc_type: Optional[str]) -> str:
    """Build AND clause for doc type filtering."""
    if not doc_type:
        return ""
    type_id = DOCTYPE_MAP.get(str(doc_type))
    if type_id is None:
        return ""
    return f"AND h.custrecord_twx_edi_type = {type_id}"


def _partner_filter(partner: Optional[str]) -> str:
    """Build AND clause for partner name (LIKE match, SQL-escaped)."""
    if not partner:
        return ""
    safe = partner.replace("'", "''").upper()
    return f"AND UPPER(tp.name) LIKE '%{safe}%'"


def _enrich_doc_types(records: list) -> list:
    """Add doc_type_name field to records that have doc_type_id."""
    for r in records:
        tid = r.get("doc_type_id")
        if tid is not None:
            r["doc_type_name"] = DOCTYPE_NAMES.get(int(tid) if tid else 0, f"Type {tid}")
    return records


# =============================================================================
# Tools
# =============================================================================

@mcp.tool(
    annotations={"title": "Run SuiteQL Query", "readOnlyHint": True, "openWorldHint": True}
)
async def netsuite_run_suiteql(
    query: str,
    account: Optional[str] = None,
    environment: Optional[str] = None,
    return_all_rows: bool = False,
) -> str:
    """Execute a raw SuiteQL query against NetSuite via the API Gateway.

    Args:
        query: SuiteQL SELECT statement. Always include ROWNUM limits (e.g. WHERE ROWNUM <= 100).
        account: 'twistedx' (twx) or 'dutyman' (dm). Default from config.
        environment: 'production', 'sandbox', or 'sandbox2'. Default from config.
        return_all_rows: Fetch all paginated results if True. Default False.

    Returns:
        JSON with records array, count, account, and environment.
        Use this tool to explore the schema or run custom analytics.

    Examples:
        - Schema discovery: SELECT * FROM customrecord_twx_edi_history WHERE ROWNUM = 1
        - Partner list: SELECT id, name FROM customrecord_twx_edi_tp ORDER BY name
        - Count all EDI records: SELECT COUNT(*) AS total FROM customrecord_twx_edi_history
    """
    try:
        result = await _query(query, account, environment, return_all_rows)
        return _fmt(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    annotations={"title": "List EDI Customers", "readOnlyHint": True, "openWorldHint": True}
)
async def netsuite_list_edi_customers(
    active_only: bool = True,
    limit: int = 100,
    account: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    """List customers with EDI trading partner associations.

    Args:
        active_only: Only show active customers. Default True.
        limit: Maximum number of customers to return (max 500). Default 100.
        account: NetSuite account. Default from config.
        environment: NetSuite environment. Default from config.

    Returns:
        JSON array of customers with ID, name, entity number, parent, and EDI transaction count.
    """
    limit = min(max(1, limit), 500)
    inactive_filter = "AND c.IsInactive = 'F'" if active_only else ""

    sql = f"""
SELECT * FROM (
    SELECT
        c.ID,
        c.EntityID AS customer_number,
        c.CompanyName AS company_name,
        BUILTIN.DF(c.Parent) AS parent_customer,
        c.IsInactive AS inactive,
        COUNT(h.id) AS edi_transaction_count
    FROM Customer c
    INNER JOIN customrecord_twx_edi_history h
        ON h.custrecord_twx_eth_edi_tp IN (
            SELECT id FROM customrecord_twx_edi_tp
            WHERE custrecord_twx_eth_edi_tp = c.ID
        )
    WHERE 1=1 {inactive_filter}
    GROUP BY c.ID, c.EntityID, c.CompanyName, c.Parent, c.IsInactive
    ORDER BY edi_transaction_count DESC
) WHERE ROWNUM <= {limit}
""".strip()

    try:
        result = await _query(sql, account, environment)
        if result.get("error"):
            # Fallback: query trading partners and their linked customers directly
            sql2 = f"""
SELECT * FROM (
    SELECT
        tp.id AS trading_partner_id,
        tp.name AS trading_partner,
        tp.custrecord_twx_edi_tp_code AS partner_code,
        COUNT(h.id) AS edi_transaction_count
    FROM customrecord_twx_edi_tp tp
    LEFT JOIN customrecord_twx_edi_history h ON h.custrecord_twx_eth_edi_tp = tp.id
    GROUP BY tp.id, tp.name, tp.custrecord_twx_edi_tp_code
    ORDER BY edi_transaction_count DESC
) WHERE ROWNUM <= {limit}
""".strip()
            result = await _query(sql2, account, environment)
        return _fmt(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    annotations={"title": "Search EDI Customer", "readOnlyHint": True, "openWorldHint": True}
)
async def netsuite_search_edi_customer(
    search: str,
    account: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    """Search for an EDI customer by company name, customer number, or internal ID.

    Args:
        search: Search term — matches against company name, entity ID, or internal ID.
        account: NetSuite account. Default from config.
        environment: NetSuite environment. Default from config.

    Returns:
        JSON array of matching customers (max 25) with contact info and EDI details.
    """
    safe = search.replace("'", "''")
    safe_upper = safe.upper()
    try:
        int_id = int(search)
        id_clause = f"OR c.ID = {int_id}"
    except ValueError:
        id_clause = ""

    sql = f"""
SELECT * FROM (
    SELECT
        c.ID,
        c.EntityID AS customer_number,
        c.CompanyName AS company_name,
        c.Email,
        c.Phone,
        BUILTIN.DF(c.Parent) AS parent_customer,
        c.IsInactive AS inactive
    FROM Customer c
    WHERE (
        UPPER(c.CompanyName) LIKE '%{safe_upper}%'
        OR c.EntityID LIKE '%{safe}%'
        {id_clause}
    )
    ORDER BY c.CompanyName
) WHERE ROWNUM <= 25
""".strip()

    try:
        result = await _query(sql, account, environment)
        return _fmt(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    annotations={"title": "EDI Trading Partners", "readOnlyHint": True, "openWorldHint": True}
)
async def netsuite_edi_trading_partners(
    account: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    """List all EDI trading partners with transaction counts by document type.

    Args:
        account: NetSuite account. Default from config.
        environment: NetSuite environment. Default from config.

    Returns:
        JSON array of trading partners with ID, name, partner code, and counts per doc type (850/856/810).
    """
    sql = """
SELECT
    tp.id,
    tp.name AS partner_name,
    tp.custrecord_twx_edi_tp_code AS partner_code,
    COUNT(h.id) AS total_transactions,
    SUM(CASE WHEN h.custrecord_twx_edi_type = 3 THEN 1 ELSE 0 END) AS po_850_count,
    SUM(CASE WHEN h.custrecord_twx_edi_type = 5 THEN 1 ELSE 0 END) AS asn_856_count,
    SUM(CASE WHEN h.custrecord_twx_edi_type = 1 THEN 1 ELSE 0 END) AS inv_810_count,
    SUM(CASE WHEN h.custrecord_twx_edi_type = 4 THEN 1 ELSE 0 END) AS ack_855_count,
    SUM(CASE WHEN h.custrecord_twx_edi_type = 6 THEN 1 ELSE 0 END) AS change_860_count
FROM customrecord_twx_edi_tp tp
LEFT JOIN customrecord_twx_edi_history h
    ON h.custrecord_twx_eth_edi_tp = tp.id
GROUP BY tp.id, tp.name, tp.custrecord_twx_edi_tp_code
ORDER BY total_transactions DESC
""".strip()

    try:
        result = await _query(sql, account, environment)
        return _fmt(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    annotations={"title": "EDI Volume by Customer", "readOnlyHint": True, "openWorldHint": True}
)
async def netsuite_edi_volume_by_customer(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    doc_type: Optional[str] = None,
    limit: int = 50,
    account: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    """EDI transaction counts grouped by trading partner for a date range.

    Args:
        start_date: Start date YYYY-MM-DD. Default: 30 days ago.
        end_date: End date YYYY-MM-DD. Default: today.
        doc_type: Filter by EDI doc type code: 850, 856, 810, 855, 860, etc. Default: all.
        limit: Max partners to return. Default 50.
        account: NetSuite account. Default from config.
        environment: NetSuite environment. Default from config.

    Returns:
        JSON with per-partner transaction counts, earliest and latest dates.
    """
    start, end = _default_dates(start_date, end_date, 30)
    limit = min(max(1, limit), 500)
    dtype_filter = _doctype_filter(doc_type)

    sql = f"""
SELECT * FROM (
    SELECT
        tp.name AS trading_partner,
        tp.custrecord_twx_edi_tp_code AS partner_code,
        COUNT(h.id) AS transaction_count,
        MIN(h.created) AS earliest_date,
        MAX(h.created) AS latest_date
    FROM customrecord_twx_edi_history h
    LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id
    WHERE h.created >= TO_DATE('{start}', 'YYYY-MM-DD')
      AND h.created < TO_DATE('{end}', 'YYYY-MM-DD') + 1
      {dtype_filter}
    GROUP BY tp.name, tp.custrecord_twx_edi_tp_code
    ORDER BY transaction_count DESC
) WHERE ROWNUM <= {limit}
""".strip()

    try:
        result = await _query(sql, account, environment)
        result["period"] = {"start": start, "end": end}
        if doc_type:
            result["doc_type_filter"] = doc_type
        return _fmt(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    annotations={"title": "EDI Dollars by Customer", "readOnlyHint": True, "openWorldHint": True}
)
async def netsuite_edi_dollars_by_customer(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    doc_type: Optional[str] = None,
    limit: int = 50,
    account: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    """EDI dollar amounts grouped by trading partner for a date range.

    Queries EDI History records and related sales transactions for dollar amounts.
    Note: Amount fields depend on your NetSuite configuration. If the EDI history
    record has no amount field, use netsuite_run_suiteql to explore the schema.

    Args:
        start_date: Start date YYYY-MM-DD. Default: 30 days ago.
        end_date: End date YYYY-MM-DD. Default: today.
        doc_type: Filter by doc type: 850, 810, 856, etc. Default: all.
        limit: Max partners. Default 50.
        account: NetSuite account. Default from config.
        environment: NetSuite environment. Default from config.

    Returns:
        JSON with per-partner transaction counts, total amounts, and averages.
        Run netsuite_run_suiteql("SELECT * FROM customrecord_twx_edi_history WHERE ROWNUM = 1")
        to discover amount field names if results show no amounts.
    """
    start, end = _default_dates(start_date, end_date, 30)
    limit = min(max(1, limit), 500)
    dtype_filter = _doctype_filter(doc_type)

    # First try querying with common amount field names on the EDI history record
    sql = f"""
SELECT * FROM (
    SELECT
        tp.name AS trading_partner,
        tp.custrecord_twx_edi_tp_code AS partner_code,
        COUNT(h.id) AS transaction_count,
        SUM(NVL(h.custrecord_twx_edi_amount, 0)) AS total_edi_amount,
        ROUND(AVG(NVL(h.custrecord_twx_edi_amount, 0)), 2) AS avg_edi_amount
    FROM customrecord_twx_edi_history h
    LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id
    WHERE h.created >= TO_DATE('{start}', 'YYYY-MM-DD')
      AND h.created < TO_DATE('{end}', 'YYYY-MM-DD') + 1
      {dtype_filter}
    GROUP BY tp.name, tp.custrecord_twx_edi_tp_code
    ORDER BY total_edi_amount DESC
) WHERE ROWNUM <= {limit}
""".strip()

    try:
        result = await _query(sql, account, environment)
        if result.get("error"):
            # Field doesn't exist — fall back to transaction-based amounts
            # Join EDI history → NetSuite Transaction via custrecord_twx_eth_netsuite_transaction
            sql2 = f"""
SELECT * FROM (
    SELECT
        tp.name AS trading_partner,
        tp.custrecord_twx_edi_tp_code AS partner_code,
        COUNT(DISTINCT h.id) AS edi_record_count,
        COUNT(DISTINCT t.id) AS transaction_count,
        SUM(NVL(tl.amount, 0)) AS total_amount
    FROM customrecord_twx_edi_history h
    LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id
    LEFT JOIN Transaction t ON h.custrecord_twx_eth_ns_transaction = t.id
    LEFT JOIN TransactionLine tl ON tl.Transaction = t.id AND tl.MainLine = 'T'
    WHERE h.created >= TO_DATE('{start}', 'YYYY-MM-DD')
      AND h.created < TO_DATE('{end}', 'YYYY-MM-DD') + 1
      {dtype_filter}
    GROUP BY tp.name, tp.custrecord_twx_edi_tp_code
    ORDER BY total_amount DESC
) WHERE ROWNUM <= {limit}
""".strip()
            result = await _query(sql2, account, environment)
            result["note"] = "Amounts from linked NetSuite transactions (EDI history amount field not available)"

        result["period"] = {"start": start, "end": end}
        if doc_type:
            result["doc_type_filter"] = doc_type
        return _fmt(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    annotations={"title": "EDI Summary by Period", "readOnlyHint": True, "openWorldHint": True}
)
async def netsuite_edi_summary_by_period(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: str = "month",
    trading_partner: Optional[str] = None,
    account: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    """EDI transaction summary aggregated by month or week with doc type breakdown.

    Args:
        start_date: Start YYYY-MM-DD. Default: 6 months ago.
        end_date: End YYYY-MM-DD. Default: today.
        period: Aggregation period: 'month' or 'week'. Default: month.
        trading_partner: Filter to a specific partner name (partial LIKE match). Default: all.
        account: NetSuite account. Default from config.
        environment: NetSuite environment. Default from config.

    Returns:
        JSON with per-period transaction counts, doc type breakdown (850/856/810/etc.).
    """
    lookback = 180 if period == "month" else 90
    start, end = _default_dates(start_date, end_date, lookback)
    partner_filter = _partner_filter(trading_partner)

    if period == "week":
        period_expr = "TO_CHAR(h.created, 'IYYY-IW')"
    else:
        period_expr = "TO_CHAR(h.created, 'YYYY-MM')"

    sql = f"""
SELECT
    {period_expr} AS period,
    COUNT(h.id) AS total_transactions,
    SUM(CASE WHEN h.custrecord_twx_edi_type = 3 THEN 1 ELSE 0 END) AS po_850,
    SUM(CASE WHEN h.custrecord_twx_edi_type = 5 THEN 1 ELSE 0 END) AS asn_856,
    SUM(CASE WHEN h.custrecord_twx_edi_type = 1 THEN 1 ELSE 0 END) AS inv_810,
    SUM(CASE WHEN h.custrecord_twx_edi_type = 4 THEN 1 ELSE 0 END) AS ack_855,
    SUM(CASE WHEN h.custrecord_twx_edi_type = 6 THEN 1 ELSE 0 END) AS change_860,
    SUM(CASE WHEN h.custrecord_twx_edi_type NOT IN (1,3,4,5,6) THEN 1 ELSE 0 END) AS other
FROM customrecord_twx_edi_history h
LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id
WHERE h.created >= TO_DATE('{start}', 'YYYY-MM-DD')
  AND h.created < TO_DATE('{end}', 'YYYY-MM-DD') + 1
  {partner_filter}
GROUP BY {period_expr}
ORDER BY period
""".strip()

    try:
        result = await _query(sql, account, environment)
        result["period_type"] = period
        result["date_range"] = {"start": start, "end": end}
        if trading_partner:
            result["partner_filter"] = trading_partner
        return _fmt(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    annotations={"title": "EDI Document Breakdown", "readOnlyHint": True, "openWorldHint": True}
)
async def netsuite_edi_document_breakdown(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    trading_partner: Optional[str] = None,
    account: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    """EDI transaction counts broken down by document type (850, 856, 810, etc.).

    Args:
        start_date: Start YYYY-MM-DD. Default: 30 days ago.
        end_date: End YYYY-MM-DD. Default: today.
        trading_partner: Filter by partner name (partial LIKE match). Default: all.
        account: NetSuite account. Default from config.
        environment: NetSuite environment. Default from config.

    Returns:
        JSON with per-document-type counts, percentages, and human-readable names.
    """
    start, end = _default_dates(start_date, end_date, 30)
    partner_filter = _partner_filter(trading_partner)

    sql = f"""
SELECT
    h.custrecord_twx_edi_type AS doc_type_id,
    COUNT(h.id) AS transaction_count
FROM customrecord_twx_edi_history h
LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id
WHERE h.created >= TO_DATE('{start}', 'YYYY-MM-DD')
  AND h.created < TO_DATE('{end}', 'YYYY-MM-DD') + 1
  {partner_filter}
GROUP BY h.custrecord_twx_edi_type
ORDER BY transaction_count DESC
""".strip()

    try:
        result = await _query(sql, account, environment)
        records = _enrich_doc_types(result.get("records", []))

        # Add percentages
        total = sum(r.get("transaction_count", 0) for r in records)
        for r in records:
            cnt = r.get("transaction_count", 0)
            r["percentage"] = round(cnt / total * 100, 1) if total else 0

        result["records"] = records
        result["total_transactions"] = total
        result["date_range"] = {"start": start, "end": end}
        if trading_partner:
            result["partner_filter"] = trading_partner
        return _fmt(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    annotations={"title": "Top EDI Customers", "readOnlyHint": True, "openWorldHint": True}
)
async def netsuite_edi_top_customers(
    rank_by: str = "volume",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 20,
    account: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    """Top EDI trading partners ranked by transaction volume or revenue.

    Args:
        rank_by: Ranking metric: 'volume' (transaction count) or 'revenue' (dollar amount if available). Default: volume.
        start_date: Start YYYY-MM-DD. Default: 90 days ago.
        end_date: End YYYY-MM-DD. Default: today.
        limit: Number of top partners to return. Default 20.
        account: NetSuite account. Default from config.
        environment: NetSuite environment. Default from config.

    Returns:
        JSON ranked list with partner name, code, transaction count, and rank number.
    """
    start, end = _default_dates(start_date, end_date, 90)
    limit = min(max(1, limit), 100)
    order_col = "total_amount DESC, transaction_count DESC" if rank_by == "revenue" else "transaction_count DESC"

    sql = f"""
SELECT * FROM (
    SELECT
        ROWNUM AS rank,
        q.*
    FROM (
        SELECT
            tp.name AS trading_partner,
            tp.custrecord_twx_edi_tp_code AS partner_code,
            COUNT(h.id) AS transaction_count,
            SUM(NVL(h.custrecord_twx_edi_amount, 0)) AS total_amount
        FROM customrecord_twx_edi_history h
        LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id
        WHERE h.created >= TO_DATE('{start}', 'YYYY-MM-DD')
          AND h.created < TO_DATE('{end}', 'YYYY-MM-DD') + 1
        GROUP BY tp.name, tp.custrecord_twx_edi_tp_code
        ORDER BY {order_col}
    ) q
) WHERE ROWNUM <= {limit}
""".strip()

    try:
        result = await _query(sql, account, environment)
        result["ranked_by"] = rank_by
        result["date_range"] = {"start": start, "end": end}
        return _fmt(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    annotations={"title": "EDI Transaction Detail", "readOnlyHint": True, "openWorldHint": True}
)
async def netsuite_edi_transaction_detail(
    trading_partner: Optional[str] = None,
    doc_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    account: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    """Get individual EDI transaction records with detail.

    Args:
        trading_partner: Filter by partner name (partial LIKE match). Default: all.
        doc_type: Filter by doc type: 850, 856, 810, 855, 860, etc. Default: all.
        start_date: Start YYYY-MM-DD. Default: 30 days ago.
        end_date: End YYYY-MM-DD. Default: today.
        limit: Max records to return (max 200). Default 50.
        account: NetSuite account. Default from config.
        environment: NetSuite environment. Default from config.

    Returns:
        JSON array of EDI history records with ID, name, partner, doc type, status, and date.
    """
    start, end = _default_dates(start_date, end_date, 30)
    limit = min(max(1, limit), 200)
    partner_filter = _partner_filter(trading_partner)
    dtype_filter = _doctype_filter(doc_type)

    sql = f"""
SELECT * FROM (
    SELECT
        h.id,
        h.name,
        tp.name AS trading_partner,
        h.custrecord_twx_edi_type AS doc_type_id,
        BUILTIN.DF(h.custrecord_twx_edi_history_status) AS status,
        h.created AS created_date
    FROM customrecord_twx_edi_history h
    LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id
    WHERE h.created >= TO_DATE('{start}', 'YYYY-MM-DD')
      AND h.created < TO_DATE('{end}', 'YYYY-MM-DD') + 1
      {partner_filter}
      {dtype_filter}
    ORDER BY h.created DESC
) WHERE ROWNUM <= {limit}
""".strip()

    try:
        result = await _query(sql, account, environment)
        result["records"] = _enrich_doc_types(result.get("records", []))
        result["date_range"] = {"start": start, "end": end}
        return _fmt(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    annotations={"title": "Recent EDI Activity", "readOnlyHint": True, "openWorldHint": True}
)
async def netsuite_edi_recent_activity(
    days: int = 7,
    limit: int = 50,
    account: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    """Most recent EDI transactions across all trading partners.

    Args:
        days: Look-back period in days. Default 7.
        limit: Max records to return (max 200). Default 50.
        account: NetSuite account. Default from config.
        environment: NetSuite environment. Default from config.

    Returns:
        JSON with recent transactions (newest first) plus summary stats (unique partners, doc type counts).
    """
    days = max(1, min(days, 365))
    limit = min(max(1, limit), 200)

    sql = f"""
SELECT * FROM (
    SELECT
        h.id,
        h.name,
        tp.name AS trading_partner,
        h.custrecord_twx_edi_type AS doc_type_id,
        BUILTIN.DF(h.custrecord_twx_edi_history_status) AS status,
        h.created AS created_date
    FROM customrecord_twx_edi_history h
    LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id
    WHERE h.created >= CURRENT_DATE - {days}
    ORDER BY h.created DESC
) WHERE ROWNUM <= {limit}
""".strip()

    # Summary query
    sql_summary = f"""
SELECT
    COUNT(h.id) AS total_transactions,
    COUNT(DISTINCT h.custrecord_twx_eth_edi_tp) AS unique_partners,
    SUM(CASE WHEN h.custrecord_twx_edi_type = 3 THEN 1 ELSE 0 END) AS po_850,
    SUM(CASE WHEN h.custrecord_twx_edi_type = 5 THEN 1 ELSE 0 END) AS asn_856,
    SUM(CASE WHEN h.custrecord_twx_edi_type = 1 THEN 1 ELSE 0 END) AS inv_810
FROM customrecord_twx_edi_history h
WHERE h.created >= CURRENT_DATE - {days}
""".strip()

    try:
        detail_result, summary_result = await _query(sql, account, environment), None
        summary_result = await _query(sql_summary, account, environment)

        records = _enrich_doc_types(detail_result.get("records", []))
        summary = summary_result.get("records", [{}])[0] if summary_result.get("records") else {}

        output = {
            "summary": {
                "lookback_days": days,
                "total_transactions": summary.get("total_transactions", len(records)),
                "unique_partners": summary.get("unique_partners"),
                "po_850": summary.get("po_850"),
                "asn_856": summary.get("asn_856"),
                "inv_810": summary.get("inv_810"),
            },
            "records": records,
            "count": len(records),
            "account": detail_result.get("account"),
            "environment": detail_result.get("environment"),
        }
        return _fmt(output)
    except Exception as e:
        return _handle_error(e)


if __name__ == "__main__":
    mcp.run()
