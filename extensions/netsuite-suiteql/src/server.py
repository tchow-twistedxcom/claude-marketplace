#!/usr/bin/env python3
"""
NetSuite SuiteQL MCP Server

Schema-aware SuiteQL querying via the NetSuite API Gateway.
The gateway handles all OAuth — no credentials needed here.

Bundled schema (twistedx/production snapshot):
  - tables.json:       2042 tables
  - columns.json:      19363 columns with types, lengths, descriptions
  - fkeys.json:        6313 foreign key relationships
  - custom_records.json: 621 custom record types
  - custom_fields.json: 4837 custom fields with human-readable labels

Schema resolution order (for each tool call):
  1. ~/.cache/netsuite-schema/{account}/{env}/ — fresh data from refresh tool
  2. data/schema/ bundled in this extension  — production snapshot

Supported accounts:
  twistedx (twx): Twisted X, OAuth 1.0a TBA, account 4829859
  dutyman (dm): Dutyman, OAuth 2.0 M2M, account 8055418

Supported environments: production, sandbox, sandbox2
  (Dutyman: production and sandbox only)
"""

import fnmatch
import json
import os
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

# =============================================================================
# System prompt
# =============================================================================

SYSTEM_PROMPT = """You have access to NetSuite SuiteQL schema and query tools.

## CRITICAL: Schema-First Workflow
ALWAYS call netsuite_describe_table or netsuite_search_schema BEFORE writing any
SuiteQL query for an unfamiliar table. Column names in SuiteQL DIFFER from NetSuite
UI field labels and many fields are not exposed in SuiteQL at all. Never guess.

## Quick Schema Lookup Workflow
1. Unsure which table? → netsuite_search_schema("keyword") or netsuite_list_tables("pattern*")
2. Know the table? → netsuite_describe_table("TableName")
3. Planning JOINs? → netsuite_show_relationships("TableName")
4. Need query examples? → netsuite_query_examples("keyword")
5. Run the query → netsuite_run_suiteql("SELECT ...")

## SuiteQL Critical Rules
- Use ROWNUM (not LIMIT): WHERE ROWNUM <= 100
- BUILTIN.DF() is expensive — avoid in large result sets
- Transaction.status: SELECT returns short codes ('B'), WHERE needs full format ('PurchOrd:B')
- String comparisons are case-sensitive on some fields
- Custom fields: scriptid format is custbody_xxx, custrecord_xxx, custentity_xxx
- Parameterized queries: use ? placeholders, pass params array

## Top 30 Tables (Quick Reference)
Standard: Customer, Transaction, TransactionLine, TransactionShipment, Item, ItemLocation,
Vendor, VendorCategory, Employee, Department, Location, Subsidiary, Currency,
Account, AccountingPeriod, TaxType, UnitType, Classification, PriceLevel,
Contact, Address, PhoneNumber, BillingAddress, ShippingAddress
Transaction types (Transaction.type filter): SalesOrd, PurchOrd, ItemShip, ItemRcpt,
  CustInvc, VendBill, TrnfrOrd, WorkOrd, Assembly
Custom records: query netsuite_list_tables("customrecord*") for full list

## Account / Environment Reference
| Account   | Alias | Environments          | Auth     |
|-----------|-------|-----------------------|----------|
| twistedx  | twx   | production, sandbox, sandbox2 | OAuth 1.0a |
| dutyman   | dm    | production, sandbox   | OAuth 2.0 |

Default: twistedx / production
"""

# =============================================================================
# Configuration
# =============================================================================

BYTE_HARD_LIMIT = 900_000  # Claude Desktop 1MB limit safety buffer

mcp = FastMCP("netsuite_suiteql", instructions=SYSTEM_PROMPT)

GATEWAY_URL = os.environ.get("NETSUITE_GATEWAY_URL", "https://api.twistedx.com")
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

# Paths
_EXTENSION_DIR = Path(__file__).parent.parent
_BUNDLED_SCHEMA_DIR = _EXTENSION_DIR / "data" / "schema"
_REFERENCES_DIR = _EXTENSION_DIR / "data" / "references"
_CACHE_ROOT = Path.home() / ".cache" / "netsuite-schema"


# =============================================================================
# Schema helpers
# =============================================================================

def _resolve_account(account: Optional[str]) -> str:
    a = (account or DEFAULT_ACCOUNT).lower()
    return ACCOUNT_ALIASES.get(a, a)


def _resolve_env(environment: Optional[str]) -> str:
    e = (environment or DEFAULT_ENVIRONMENT).lower()
    return ENV_ALIASES.get(e, e)


def _get_schema_dir(account: str, environment: str) -> Path:
    """Return user cache dir if present, otherwise bundled fallback."""
    user_dir = _CACHE_ROOT / account / environment
    if (user_dir / "tables.json").exists():
        return user_dir
    return _BUNDLED_SCHEMA_DIR


def _load_json(path: Path) -> Optional[dict]:
    """Load a JSON file; return None on error or missing."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _matches(text: str, pattern: str) -> bool:
    """Glob or substring match, case-insensitive."""
    if not pattern:
        return True
    t, p = text.lower(), pattern.lower()
    if "*" in p or "?" in p:
        return fnmatch.fnmatch(t, p)
    return p in t


# =============================================================================
# Gateway helpers (reused verbatim from netsuite-edi pattern)
# =============================================================================

async def _query(
    sql: str,
    account: Optional[str] = None,
    environment: Optional[str] = None,
    return_all_rows: bool = False,
    params: Optional[list] = None,
) -> dict:
    """Execute a SuiteQL query via the NetSuite API Gateway."""
    acct = _resolve_account(account)
    env = _resolve_env(environment)

    payload = {
        "action": "queryRun",
        "procedure": "queryRun",
        "query": sql,
        "params": params or [],
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
                **({"X-API-Key": GATEWAY_API_KEY} if GATEWAY_API_KEY else {"Origin": "http://localhost:3000"}),
            },
        )
        resp.raise_for_status()
        body = resp.json()

    if not body.get("success"):
        error = body.get("error", {})
        msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
        return {"records": [], "count": 0, "error": msg, "account": acct, "environment": env}

    records = body.get("data", {}).get("records", [])
    return {"records": records, "count": len(records), "account": acct, "environment": env}


def _handle_error(e: Exception) -> str:
    if isinstance(e, httpx.ConnectError):
        return (
            f"Error: Cannot connect to gateway at {GATEWAY_URL}. "
            "Check that the NetSuite API Gateway is running and reachable."
        )
    if isinstance(e, httpx.TimeoutException):
        return "Error: Gateway request timed out (120s). Add ROWNUM limits or narrow the date range."
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
    """Serialize to JSON/str with hard byte cap for Claude Desktop 1MB limit."""
    text = json.dumps(data, indent=2, default=str) if isinstance(data, (list, dict)) else str(data)
    encoded = text.encode("utf-8")
    if len(encoded) <= BYTE_HARD_LIMIT:
        return text
    trimmed = encoded[:BYTE_HARD_LIMIT].decode("utf-8", errors="ignore")
    cut = trimmed.rfind("\n")
    if cut > BYTE_HARD_LIMIT // 2:
        trimmed = trimmed[:cut]
    return trimmed + "\n// [TRUNCATED — add ROWNUM limits or narrow the query]"


# =============================================================================
# MCP Resources — reference docs
# =============================================================================

@mcp.resource("netsuite://references/table-reference")
def get_table_reference() -> str:
    """Curated guide to the most commonly used NetSuite SuiteQL tables."""
    p = _REFERENCES_DIR / "table_reference.md"
    return p.read_text(encoding="utf-8") if p.exists() else "table_reference.md not found"


@mcp.resource("netsuite://references/common-queries")
def get_common_queries() -> str:
    """Library of pre-built SuiteQL query patterns for common operations."""
    p = _REFERENCES_DIR / "common_queries.md"
    return p.read_text(encoding="utf-8") if p.exists() else "common_queries.md not found"


@mcp.resource("netsuite://references/suiteql-functions")
def get_suiteql_functions() -> str:
    """Supported and unsupported SQL functions in NetSuite SuiteQL."""
    p = _REFERENCES_DIR / "suiteql_functions.md"
    return p.read_text(encoding="utf-8") if p.exists() else "suiteql_functions.md not found"


# =============================================================================
# Tool: run_suiteql
# =============================================================================

@mcp.tool(
    annotations={"title": "Run SuiteQL Query", "readOnlyHint": True, "openWorldHint": True}
)
async def netsuite_run_suiteql(
    query: str,
    params: Optional[list] = None,
    account: Optional[str] = None,
    environment: Optional[str] = None,
    return_all_rows: bool = False,
) -> str:
    """Execute a raw SuiteQL SELECT query against NetSuite via the API Gateway.

    IMPORTANT: Always call netsuite_describe_table first to verify column names.
    Only SELECT queries are supported (read-only).

    Args:
        query: SuiteQL SELECT statement. Use ROWNUM (not LIMIT): WHERE ROWNUM <= 100.
        params: Optional list of ? parameter values for parameterized queries.
        account: 'twistedx' (twx) or 'dutyman' (dm). Default from config.
        environment: 'production', 'sandbox', or 'sandbox2'. Default from config.
        return_all_rows: Fetch all paginated results. Default False.

    Returns:
        JSON with records array, count, account, and environment.

    Examples:
        - Count customers: SELECT COUNT(*) AS total FROM Customer WHERE IsInactive = 'F'
        - Recent sales orders: SELECT id, tranid, TranDate FROM Transaction WHERE type = 'SalesOrd' AND TranDate >= CURRENT_DATE - 7 AND ROWNUM <= 50
        - Schema discovery: SELECT * FROM customrecord_twx_edi_history WHERE ROWNUM = 1
    """
    try:
        result = await _query(query, account, environment, return_all_rows, params)
        return _fmt(result)
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Tool: describe_table
# =============================================================================

@mcp.tool(
    annotations={"title": "Describe NetSuite Table", "readOnlyHint": True}
)
def netsuite_describe_table(
    table_name: str,
    account: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    """Show all columns, data types, lengths, FK relationships, and custom field labels
    for a NetSuite SuiteQL table.

    Use this BEFORE writing any query to verify exact column names. Column names in
    SuiteQL differ from NetSuite UI field labels, and many fields are not exposed.

    Args:
        table_name: Exact or case-insensitive table name (e.g. 'Transaction', 'Customer',
                    'customrecord_pri_frgt_cnt').
        account: 'twistedx' or 'dutyman'. Default from config.
        environment: 'production', 'sandbox', or 'sandbox2'. Default from config.

    Returns:
        JSON with columns (name, type, length, description), foreign keys, and primary keys.
    """
    acct = _resolve_account(account)
    env = _resolve_env(environment)
    schema_dir = _get_schema_dir(acct, env)

    cols_data = _load_json(schema_dir / "columns.json")
    fkeys_data = _load_json(schema_dir / "fkeys.json")
    custom_fields_data = _load_json(schema_dir / "custom_fields.json")

    # Find table (case-insensitive)
    odbc_columns = None
    canonical_table = table_name
    if cols_data:
        for key in cols_data.get("columns", {}):
            if key.lower() == table_name.lower():
                canonical_table = key
                odbc_columns = cols_data["columns"][key]
                break

    # Build custom field label map
    label_map: dict[str, str] = {}
    if custom_fields_data:
        for rec_key, fields in custom_fields_data.get("custom_fields", {}).items():
            if rec_key.lower() == table_name.lower():
                for f in fields:
                    sid = f.get("scriptid", "").lower()
                    lbl = f.get("label", "")
                    if sid and lbl:
                        label_map[sid] = lbl

    columns_to_show = []
    source = "bundled snapshot" if schema_dir == _BUNDLED_SCHEMA_DIR else "user cache"

    if odbc_columns:
        refreshed = (cols_data.get("_refreshed_at", "unknown") or "unknown")[:10]
        source = f"ODBC cache ({refreshed})"
        for c in odbc_columns:
            name = c.get("column_name", "")
            lbl = label_map.get(name.lower(), "")
            description = c.get("description") or lbl or ""
            columns_to_show.append({
                "name": name,
                "type": c.get("data_type", ""),
                "length": c.get("length"),
                "description": description,
            })

    elif table_name.lower().startswith("customrecord_") and custom_fields_data:
        # Custom cache fallback
        rec_fields = None
        for rec_key, fields in custom_fields_data.get("custom_fields", {}).items():
            if rec_key.lower() == table_name.lower():
                canonical_table = rec_key
                rec_fields = fields
                break
        if rec_fields:
            cf_refreshed = (custom_fields_data.get("_refreshed_at", "unknown") or "unknown")[:10]
            source = f"custom field cache ({cf_refreshed})"
            for name in ["ID", "Name", "Created", "LastModified", "Owner", "ExternalID"]:
                columns_to_show.append({"name": name, "type": "", "length": None, "description": ""})
            for f in rec_fields:
                columns_to_show.append({
                    "name": f.get("scriptid", ""),
                    "type": f.get("field_type", ""),
                    "length": None,
                    "description": f.get("label", ""),
                })
        else:
            return _fmt({
                "error": f"Table '{table_name}' not found in schema cache.",
                "suggestion": "Try netsuite_search_schema to find the correct table name, or run netsuite_refresh_custom_schema for custom records.",
                "account": acct,
                "environment": env,
            })

    else:
        return _fmt({
            "error": f"Table '{table_name}' not found in schema cache.",
            "suggestion": "Try netsuite_search_schema to find the correct table name, or run netsuite_refresh_custom_schema for custom records.",
            "account": acct,
            "environment": env,
        })

    # FK data
    fk_outbound = []
    fk_inbound = []
    pk_cols = []
    if fkeys_data:
        for fk in fkeys_data.get("foreign_keys", []):
            if fk.get("fk_table", "").lower() == canonical_table.lower():
                fk_outbound.append(fk)
            elif fk.get("pk_table", "").lower() == canonical_table.lower():
                fk_inbound.append(fk)
        for pk in fkeys_data.get("primary_keys", []):
            if pk.get("table_name", "").lower() == canonical_table.lower():
                pk_cols.append(pk.get("column_name", ""))

    # Enrich column descriptions with FK references
    fk_out_map = {fk.get("fk_column", "").lower(): f"→ {fk.get('pk_table','')}.{fk.get('pk_column','')}" for fk in fk_outbound}
    for col in columns_to_show:
        fk_ref = fk_out_map.get(col["name"].lower(), "")
        if fk_ref:
            col["fk_reference"] = fk_ref

    result = {
        "table": canonical_table,
        "account": acct,
        "environment": env,
        "source": source,
        "column_count": len(columns_to_show),
        "columns": columns_to_show,
        "foreign_keys": {
            "outbound": sorted(fk_outbound, key=lambda x: x.get("fk_column", "")),
            "inbound": sorted(fk_inbound, key=lambda x: x.get("fk_table", "")),
        },
        "primary_keys": pk_cols,
    }
    return _fmt(result)


# =============================================================================
# Tool: search_schema
# =============================================================================

@mcp.tool(
    annotations={"title": "Search NetSuite Schema", "readOnlyHint": True}
)
def netsuite_search_schema(
    pattern: str,
    account: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    """Search all NetSuite table and column names for a keyword or glob pattern.

    Use when unsure which table or column contains the data you need. Searches both
    table names and column names/descriptions simultaneously.

    Args:
        pattern: Search keyword or glob. Substring match by default.
                 Use * for wildcards: 'edi*', '*shipping*', 'custrecord_twx*'.
        account: 'twistedx' or 'dutyman'. Default from config.
        environment: 'production', 'sandbox', or 'sandbox2'. Default from config.

    Returns:
        JSON with matching tables and matching columns (table, column, type, description).

    Examples:
        - Find shipping-related tables: 'shipping'
        - Find all EDI columns: 'edi'
        - Find custom fields with 'amount': 'amount'
    """
    if not pattern:
        return _fmt({"error": "pattern is required"})

    acct = _resolve_account(account)
    env = _resolve_env(environment)
    schema_dir = _get_schema_dir(acct, env)

    tables_data = _load_json(schema_dir / "tables.json")
    cols_data = _load_json(schema_dir / "columns.json")
    custom_records_data = _load_json(schema_dir / "custom_records.json")
    custom_fields_data = _load_json(schema_dir / "custom_fields.json")

    table_matches = []
    col_matches = []

    if tables_data:
        for t in tables_data.get("tables", []):
            name = t.get("table_name", "")
            desc = t.get("description", "")
            if _matches(name, pattern) or _matches(desc, pattern):
                table_matches.append({
                    "table": name,
                    "description": desc,
                    "custom": t.get("is_custom", False),
                })
    elif custom_records_data:
        for r in custom_records_data.get("custom_record_types", []):
            name = r.get("scriptid", "")
            label = r.get("name", "")
            if _matches(name, pattern) or _matches(label, pattern):
                table_matches.append({"table": name, "description": label, "custom": True})

    if cols_data:
        for tname, cols in cols_data.get("columns", {}).items():
            for c in cols:
                cname = c.get("column_name", "")
                desc = c.get("description", "")
                if _matches(cname, pattern) or _matches(desc, pattern):
                    col_matches.append({
                        "table": tname,
                        "column": cname,
                        "type": c.get("data_type", ""),
                        "description": desc,
                    })
    elif custom_fields_data:
        for rec, fields in custom_fields_data.get("custom_fields", {}).items():
            for f in fields:
                sid = f.get("scriptid", "")
                lbl = f.get("label", "")
                if _matches(sid, pattern) or _matches(lbl, pattern):
                    col_matches.append({
                        "table": rec,
                        "column": sid,
                        "type": f.get("field_type", ""),
                        "description": lbl,
                    })

    result = {
        "pattern": pattern,
        "account": acct,
        "environment": env,
        "total_matches": len(table_matches) + len(col_matches),
        "tables": table_matches,
        "columns": col_matches,
    }
    return _fmt(result)


# =============================================================================
# Tool: list_tables
# =============================================================================

@mcp.tool(
    annotations={"title": "List NetSuite Tables", "readOnlyHint": True}
)
def netsuite_list_tables(
    pattern: Optional[str] = None,
    account: Optional[str] = None,
    environment: Optional[str] = None,
    limit: int = 200,
) -> str:
    """List NetSuite SuiteQL tables, optionally filtered by a glob or substring pattern.

    Args:
        pattern: Optional glob or substring filter. Examples: 'custom*', 'Transaction*',
                 '*shipment*', 'customrecord_twx*'. Without a pattern, returns first 200 tables.
        account: 'twistedx' or 'dutyman'. Default from config.
        environment: 'production', 'sandbox', or 'sandbox2'. Default from config.
        limit: Maximum tables to return. Default 200.

    Returns:
        JSON array of tables with name, is_custom, is_hidden, description.
    """
    acct = _resolve_account(account)
    env = _resolve_env(environment)
    schema_dir = _get_schema_dir(acct, env)
    limit = max(1, min(limit, 2042))

    tables_data = _load_json(schema_dir / "tables.json")
    custom_records_data = _load_json(schema_dir / "custom_records.json")

    results = []
    source = "bundled snapshot"

    if tables_data:
        refreshed = (tables_data.get("_refreshed_at", "unknown") or "unknown")[:10]
        source = f"ODBC cache ({refreshed})"
        for t in tables_data.get("tables", []):
            name = t.get("table_name", "")
            if not pattern or _matches(name, pattern):
                results.append({
                    "table_name": name,
                    "is_custom": t.get("is_custom", False),
                    "is_hidden": t.get("is_hidden", False),
                    "description": t.get("description", ""),
                })
    elif custom_records_data:
        refreshed = (custom_records_data.get("_refreshed_at", "unknown") or "unknown")[:10]
        source = f"custom records cache ({refreshed})"
        for r in custom_records_data.get("custom_record_types", []):
            name = r.get("scriptid", "")
            if not pattern or _matches(name, pattern):
                results.append({
                    "table_name": name,
                    "is_custom": True,
                    "is_hidden": False,
                    "description": r.get("name", ""),
                })

    total = len(results)
    truncated = total > limit
    results = results[:limit]

    return _fmt({
        "pattern": pattern,
        "account": acct,
        "environment": env,
        "source": source,
        "total_matches": total,
        "shown": len(results),
        "truncated": truncated,
        "tables": results,
    })


# =============================================================================
# Tool: show_relationships
# =============================================================================

@mcp.tool(
    annotations={"title": "Show Table Relationships", "readOnlyHint": True}
)
def netsuite_show_relationships(
    table_name: str,
    account: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    """Show foreign key relationships for a NetSuite table.

    Returns which tables this table references (outbound FKs) and which tables
    reference it (inbound FKs). Essential for planning JOIN queries.

    Args:
        table_name: Table name to get relationships for (e.g. 'Transaction', 'TransactionLine').
        account: 'twistedx' or 'dutyman'. Default from config.
        environment: 'production', 'sandbox', or 'sandbox2'. Default from config.

    Returns:
        JSON with primary_keys, outbound FK list, and inbound FK list.

    Example:
        netsuite_show_relationships("TransactionLine") →
          outbound: TransactionLine.Transaction → Transaction.ID
          inbound: many tables → TransactionLine.ID
    """
    acct = _resolve_account(account)
    env = _resolve_env(environment)
    schema_dir = _get_schema_dir(acct, env)

    fkeys_data = _load_json(schema_dir / "fkeys.json")
    if not fkeys_data:
        return _fmt({
            "error": f"FK cache not found for {acct}/{env}.",
            "suggestion": "The bundled schema should always have fkeys.json. Try refreshing: netsuite_refresh_custom_schema.",
        })

    # Case-insensitive canonical name resolution
    canonical = table_name
    all_tables: set[str] = set()
    for fk in fkeys_data.get("foreign_keys", []):
        all_tables.add(fk.get("fk_table", ""))
        all_tables.add(fk.get("pk_table", ""))
    for pk in fkeys_data.get("primary_keys", []):
        all_tables.add(pk.get("table_name", ""))
    for t in all_tables:
        if t.lower() == table_name.lower():
            canonical = t
            break

    outbound = sorted(
        [fk for fk in fkeys_data.get("foreign_keys", []) if fk.get("fk_table", "").lower() == canonical.lower()],
        key=lambda x: x.get("fk_column", ""),
    )
    inbound = sorted(
        [fk for fk in fkeys_data.get("foreign_keys", []) if fk.get("pk_table", "").lower() == canonical.lower()],
        key=lambda x: x.get("fk_table", ""),
    )
    pk_cols = [
        pk.get("column_name", "")
        for pk in fkeys_data.get("primary_keys", [])
        if pk.get("table_name", "").lower() == canonical.lower()
    ]

    refreshed = (fkeys_data.get("_refreshed_at", "unknown") or "unknown")[:10]
    return _fmt({
        "table": canonical,
        "account": acct,
        "environment": env,
        "source": f"ODBC cache ({refreshed})",
        "primary_keys": pk_cols,
        "outbound_fk_count": len(outbound),
        "inbound_fk_count": len(inbound),
        "outbound_fk": outbound,
        "inbound_fk": inbound,
    })


# =============================================================================
# Tool: refresh_custom_schema
# =============================================================================

@mcp.tool(
    annotations={"title": "Refresh Custom Schema", "readOnlyHint": False}
)
async def netsuite_refresh_custom_schema(
    account: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    """Refresh the custom records and custom fields cache from NetSuite via the gateway.

    Queries CustomRecordType and CustomField tables via SuiteQL to get an up-to-date
    list of all custom record types and their fields with human-readable labels.

    Run this when:
    - New custom record types have been added to NetSuite
    - Custom field labels have changed
    - describe_table shows outdated or missing custom field info

    This does NOT require ODBC — it uses the API gateway.
    For full schema refresh (standard tables), contact the NetSuite admin.

    Args:
        account: 'twistedx' or 'dutyman'. Default from config.
        environment: 'production', 'sandbox', or 'sandbox2'. Default from config.

    Returns:
        Summary of refreshed record types and fields count.
    """
    acct = _resolve_account(account)
    env = _resolve_env(environment)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cache_dir = _CACHE_ROOT / acct / env
    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Query custom record types
        crt_result = await _query(
            "SELECT internalid, scriptid, name, isinactive FROM CustomRecordType WHERE isinactive = 'F' ORDER BY name",
            account=acct,
            environment=env,
            return_all_rows=True,
        )
        if crt_result.get("error"):
            return _fmt({"error": f"Failed querying CustomRecordType: {crt_result['error']}"})

        custom_records = [
            {
                "id": r.get("internalid"),
                "scriptid": (r.get("scriptid") or "").lower(),
                "name": r.get("name") or "",
            }
            for r in crt_result.get("records", [])
        ]

        # Query custom fields
        cf_result = await _query(
            """SELECT cf.id, cf.scriptid, cf.name AS label, cf.fieldvaluetype, crt.scriptid AS record_scriptid
               FROM CustomField cf
               INNER JOIN CustomRecordType crt ON cf.recordtype = crt.internalid
               WHERE cf.fieldtype = 'RECORD' AND crt.isinactive = 'F'
               ORDER BY crt.scriptid, cf.name""",
            account=acct,
            environment=env,
            return_all_rows=True,
        )
        if cf_result.get("error"):
            return _fmt({"error": f"Failed querying CustomField: {cf_result['error']}"})

        custom_fields_grouped: dict[str, list] = {}
        for r in cf_result.get("records", []):
            applies_to = (r.get("record_scriptid") or "").lower()
            if not applies_to:
                continue
            custom_fields_grouped.setdefault(applies_to, []).append({
                "id": r.get("id"),
                "scriptid": (r.get("scriptid") or "").lower(),
                "label": r.get("label") or "",
                "field_type": r.get("fieldvaluetype") or "",
                "applies_to": applies_to,
            })

        total_fields = sum(len(v) for v in custom_fields_grouped.values())

        # Save to user cache dir
        (cache_dir / "custom_records.json").write_text(
            json.dumps({
                "_source": "suiteql",
                "_refreshed_at": ts,
                "_account": acct,
                "_environment": env,
                "_record_count": len(custom_records),
                "custom_record_types": custom_records,
            }, indent=2),
            encoding="utf-8",
        )
        (cache_dir / "custom_fields.json").write_text(
            json.dumps({
                "_source": "suiteql",
                "_refreshed_at": ts,
                "_account": acct,
                "_environment": env,
                "_record_count": total_fields,
                "custom_fields": custom_fields_grouped,
            }, indent=2),
            encoding="utf-8",
        )

        return _fmt({
            "status": "success",
            "account": acct,
            "environment": env,
            "refreshed_at": ts,
            "custom_record_types": len(custom_records),
            "custom_fields": total_fields,
            "cache_dir": str(cache_dir),
            "note": "Custom records/fields cache updated. Subsequent describe_table calls will use fresh data.",
        })

    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Tool: query_examples
# =============================================================================

@mcp.tool(
    annotations={"title": "Query Examples", "readOnlyHint": True}
)
def netsuite_query_examples(keyword: str) -> str:
    """Search the built-in SuiteQL query pattern library for examples matching a keyword.

    The library contains pre-built patterns for common NetSuite operations. Use this
    to find starting points for your queries.

    Args:
        keyword: Search term (e.g. 'customer', 'transaction', 'inventory', 'edi',
                 'item', 'vendor', 'shipment', 'purchase order').

    Returns:
        Matching sections from the common queries reference with SQL examples.
    """
    p = _REFERENCES_DIR / "common_queries.md"
    if not p.exists():
        return "common_queries.md not found in bundled references."

    content = p.read_text(encoding="utf-8")
    kw = keyword.lower()

    # Extract sections (## headings) that match the keyword
    sections = []
    current_section = []
    current_header = ""

    for line in content.splitlines():
        if line.startswith("## "):
            if current_section and kw in "\n".join(current_section).lower():
                sections.append((current_header, "\n".join(current_section)))
            current_header = line
            current_section = [line]
        else:
            current_section.append(line)

    # Check last section
    if current_section and kw in "\n".join(current_section).lower():
        sections.append((current_header, "\n".join(current_section)))

    if not sections:
        return _fmt({
            "keyword": keyword,
            "matches": 0,
            "message": f"No query examples found for '{keyword}'. Try: 'customer', 'transaction', 'item', 'vendor', 'edi', 'inventory', 'shipment'.",
        })

    result_text = f"# Query Examples: '{keyword}'\n\nFound {len(sections)} matching section(s):\n\n"
    for header, body in sections:
        result_text += body + "\n\n---\n\n"

    # Trim to byte limit
    encoded = result_text.encode("utf-8")
    if len(encoded) > BYTE_HARD_LIMIT:
        trimmed = encoded[:BYTE_HARD_LIMIT].decode("utf-8", errors="ignore")
        result_text = trimmed + "\n// [TRUNCATED]"

    return result_text


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    mcp.run()
