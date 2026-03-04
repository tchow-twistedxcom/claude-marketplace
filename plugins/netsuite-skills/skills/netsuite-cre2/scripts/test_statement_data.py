#!/usr/bin/env python3
"""
CRE2 Customer Statement Data Validation Test Suite

Validates that CRE2 Profile 16 (Customer Statement Portrait) produces correct,
complete statements by running checks at two layers:

DATA LAYER  (always run — fast, no rendering)
  1. balance          — scalar balance matches CustomerSubsidiaryRelationship
  2. transactions     — set of open transaction IDs matches reference
  3. tran_amounts     — per-transaction foreignamountunpaid matches reference
  4. tran_fields      — tran datasource contains required template fields
  5. balance_forward  — balance_forward sanity (WARN if suspiciously large)

COMPARE LAYER  (--compare-check, top 3 customers per category by transaction count)
  6. compare          — render both native NS statement + CRE2 → compare:
                        • Amount Due
                        • Balance Forward
                        • Aging buckets (current, 1-30, 31-60, 61-90, 90+, total)
                        • Transaction IDs (set match)
                        • Per-transaction remaining balance amounts
                        • Paylink annotation — clickable URI (extforms.netsuite.com) present

Usage:
  python3 test_statement_data.py --env sb2
  python3 test_statement_data.py --env prod
  python3 test_statement_data.py --env sb2 --compare-check
  python3 test_statement_data.py --env sb2 --customers 5764,4631,12926
  python3 test_statement_data.py --env sb2 --format json

Full-Coverage Mode (tests ALL statement-eligible customers):
  python3 test_statement_data.py --env sb2 --full-coverage
  python3 test_statement_data.py --env prod --full-coverage
  python3 test_statement_data.py --env sb2 --full-coverage --compare-check
  python3 test_statement_data.py --env sb2 --full-coverage --concurrency 12
"""

import sys
import os
import io
import json
import math
import re
import time
import argparse
import tempfile
import base64
import contextlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List, Set, Tuple, FrozenSet

# Add this scripts directory to path so sibling scripts can be imported
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPTS_DIR)

# Also add the netsuite-file-cabinet scripts directory
# Structure: skills/netsuite-cre2/scripts/ → go up 2 to skills/, then into netsuite-file-cabinet/
_FILE_CAB_DIR = os.path.join(
    _SCRIPTS_DIR, '..', '..', 'netsuite-file-cabinet', 'scripts'
)
sys.path.insert(0, os.path.normpath(_FILE_CAB_DIR))

from test_datasource import (
    execute_query,
    get_datasources,
    resolve_account,
    resolve_environment,
    DEFAULT_ACCOUNT,
    DEFAULT_ENVIRONMENT,
)

# CRE2 Profile 16: Customer Statement (Portrait)
PROFILE_ID = 16

BALANCE_TOLERANCE = 0.01          # Within 1 cent
BALANCE_FORWARD_WARN_RATIO = 10.0 # Warn if |BF| > ratio × |total|

# ── Template field requirements ───────────────────────────────────────────────
# REQUIRED groups → FAIL if none of the fields in the tuple are present.
# EXPECTED groups → WARN if none are present.

REQUIRED_TRAN_FIELD_GROUPS: List[Tuple[str, ...]] = [
    ('id', 'internalid'),
    ('tranid', 'documentnumber', 'tran_id'),
    ('foreignamountunpaid', 'amountremaining', 'openamount'),
]
EXPECTED_TRAN_FIELD_GROUPS: List[Tuple[str, ...]] = [
    ('trandate', 'date', 'transactiondate'),
    ('duedate', 'due_date'),
    ('foreigntotal', 'foreignamount', 'total', 'amount'),
]


# ─── Reference Queries ───────────────────────────────────────────────────────

REFERENCE_BALANCE_QUERY = """
SELECT SUM(csr.balance) AS balance
FROM CustomerSubsidiaryRelationship csr
WHERE csr.entity = ?
"""

# SuiteQL quirk: status <> 'CustCred:B' only works at the OUTERMOST query level.
# It is silently dropped when inside a subquery, OR condition, or UNION ALL branch
# that is wrapped in a subquery.  The only reliable pattern is a bare top-level UNION ALL
# where each branch has its own simple WHERE clause (no OR, no subquery wrapper).
# This template uses {entity_ids} substitution (not ? params) to avoid having to
# bind the same value twice in UNION ALL.  {entity_ids} is replaced with a
# comma-separated list of IDs (parent + consolidated children).
REFERENCE_TRAN_QUERY_TEMPLATE = """
SELECT t.id, t.foreignamountunpaid AS amount_remaining
FROM Transaction t
WHERE t.entity IN ({entity_ids})
  AND t.type = 'CustInvc'
  AND t.foreignamountunpaid <> 0
UNION ALL
SELECT t.id, COALESCE(t.foreignamountunpaid, t.foreigntotal) AS amount_remaining
FROM Transaction t
WHERE t.entity IN ({entity_ids})
  AND t.type = 'CustCred'
  AND t.status NOT IN ('CustCred:B', 'CustCred:V')
  AND COALESCE(t.foreignamountunpaid, t.foreigntotal) <> 0
ORDER BY 1
"""

REFERENCE_BALANCE_QUERY_MULTI = """
SELECT SUM(csr.balance) AS balance
FROM CustomerSubsidiaryRelationship csr
WHERE csr.entity IN ({entity_ids})
"""


# ─── Customer Discovery ──────────────────────────────────────────────────────

def _discover_balance_category(where_clause: str, limit: int,
                                account: str, environment: str) -> List[int]:
    result = execute_query(
        f"SELECT DISTINCT csr.entity AS customer_id "
        f"FROM CustomerSubsidiaryRelationship csr "
        f"WHERE {where_clause} "
        f"FETCH FIRST {limit} ROWS ONLY",
        account=account, environment=environment,
        return_all_rows=False,
    )
    if result.get('error'):
        return []
    return [int(r['customer_id']) for r in result.get('records', []) if r.get('customer_id')]


def _discover_mixed_customers(limit: int, account: str, environment: str) -> List[int]:
    inv = execute_query(
        "SELECT DISTINCT t.entity AS customer_id FROM Transaction t "
        "WHERE t.type = 'CustInvc' AND t.foreignamountunpaid > 0 "
        "FETCH FIRST 500 ROWS ONLY",
        account=account, environment=environment,
        return_all_rows=False,
    )
    # CMs have foreignamountunpaid=NULL always — use status <> to find open CMs.
    # CRITICAL: status <> 'CustCred:B' only works bare (no ROWNUM wrapper) — use return_all_rows=False
    cred = execute_query(
        "SELECT DISTINCT t.entity AS customer_id FROM Transaction t "
        "WHERE t.type = 'CustCred' AND t.status <> 'CustCred:B' "
        "FETCH FIRST 500 ROWS ONLY",
        account=account, environment=environment,
        return_all_rows=False,
    )
    inv_set:  Set[int] = {int(r['customer_id']) for r in inv.get('records', []) if r.get('customer_id')}
    cred_set: Set[int] = {int(r['customer_id']) for r in cred.get('records', []) if r.get('customer_id')}
    return sorted(inv_set & cred_set)[:limit]


def _discover_parent_customers(limit: int, account: str, environment: str) -> List[int]:
    result = execute_query(
        "SELECT DISTINCT c.id AS customer_id "
        "FROM customer c "
        "INNER JOIN customer child ON child.parent = c.id "
        "WHERE child.isinactive = 'F' AND c.isinactive = 'F' "
        f"FETCH FIRST {limit} ROWS ONLY",
        account=account, environment=environment,
        return_all_rows=False,
    )
    if result.get('error'):
        return []
    return [int(r['customer_id']) for r in result.get('records', []) if r.get('customer_id')]


def _discover_partial_payment_customers(limit: int, account: str, environment: str) -> List[int]:
    result = execute_query(
        "SELECT DISTINCT t.entity AS customer_id "
        "FROM Transaction t "
        "WHERE t.type = 'CustInvc' "
        "  AND t.foreignamountunpaid > 0 "
        "  AND t.foreignamountunpaid < t.foreigntotal "
        f"FETCH FIRST {limit} ROWS ONLY",
        account=account, environment=environment,
        return_all_rows=False,
    )
    if result.get('error'):
        return []
    return [int(r['customer_id']) for r in result.get('records', []) if r.get('customer_id')]


def discover_test_customers(account: str, environment: str) -> Dict[str, List[int]]:
    """Return {category: [customer_id, ...]} for all six balance/transaction categories."""
    return {
        'positive_balance':  _discover_balance_category('csr.balance > 0', 3, account, environment),
        'credit_balance':    _discover_balance_category('csr.balance < 0', 3, account, environment),
        'zero_balance':      _discover_balance_category('csr.balance = 0', 2, account, environment),
        'mixed_inv_credits': _discover_mixed_customers(3, account, environment),
        'parent_customer':   _discover_parent_customers(2, account, environment),
        'partial_payment':   _discover_partial_payment_customers(3, account, environment),
    }


# ─── Full-Coverage Discovery ──────────────────────────────────────────────────

# Category priority order for display (when customer matches multiple categories)
_CATEGORY_PRIORITY = [
    'mixed_inv_credits',  # most interesting (CM bug target)
    'credit_balance',
    'partial_payment',
    'consolidated',
    'positive_balance',
    'zero_balance',
]


def discover_statement_customers(
    account: str,
    environment: str,
) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, List[int]]]:
    """Discover ALL statement-eligible customers matching the actual batch run population.

    Uses the same selection criteria as the TWX Dashboard/Prolecto Suitelet:
      - Top-level customers only (parent IS NULL)
      - Active (isinactive = 'F')
      - Entity status 13 (Customer - Active)

    Returns:
        customers: Dict[customer_id, {balance, categories, consolidated, sub_count}]
        categories: Dict[category_name, [customer_ids]]  — customer's primary category
    """
    print("Discovering statement-eligible customers...", file=sys.stderr)

    # Single broad query mirroring the batch run selection criteria.
    # The LEFT JOIN to CustomerSubsidiaryRelationship is a derived subquery — safe
    # with return_all_rows=True (no status filter, simple aggregate).
    discovery_sql = """
    SELECT
        c.id AS customer_id,
        NVL(c.custentity_twx_consolidated_statement, 'F') AS consolidated_pref,
        COALESCE(csr.total_balance, 0) AS total_balance,
        (SELECT COUNT(*)
         FROM customer child
         WHERE child.parent = c.id AND child.isinactive = 'F') AS sub_count
    FROM customer c
    LEFT JOIN (
        SELECT entity, SUM(balance) AS total_balance
        FROM CustomerSubsidiaryRelationship
        GROUP BY entity
    ) csr ON csr.entity = c.id
    WHERE c.parent IS NULL
      AND c.isinactive = 'F'
      AND c.entitystatus = 13
    ORDER BY c.id
    """
    result = execute_query(discovery_sql, account=account, environment=environment,
                           return_all_rows=True)
    if result.get('error'):
        print(f"  ERROR in discovery query: {result['error']}", file=sys.stderr)
        return {}, {}

    records = result.get('records', [])
    print(f"  Found {len(records)} top-level active customers", file=sys.stderr)

    # Build customer info map and classify by balance
    customers: Dict[int, Dict[str, Any]] = {}
    for r in records:
        cid_raw = r.get('customer_id')
        if cid_raw is None:
            continue
        try:
            cid = int(cid_raw)
        except (ValueError, TypeError):
            continue
        try:
            balance = float(r.get('total_balance') or 0)
        except (ValueError, TypeError):
            balance = 0.0
        try:
            sub_count = int(r.get('sub_count') or 0)
        except (ValueError, TypeError):
            sub_count = 0
        consolidated = (r.get('consolidated_pref') or 'F') == 'T'

        cats: Set[str] = set()
        if balance > 0:
            cats.add('positive_balance')
        elif balance < 0:
            cats.add('credit_balance')
        else:
            cats.add('zero_balance')
        if consolidated and sub_count > 0:
            cats.add('consolidated')

        customers[cid] = {
            'balance':      balance,
            'categories':   cats,
            'consolidated': consolidated,
            'sub_count':    sub_count,
        }

    if not customers:
        return {}, {}

    # Supplemental: tag customers with open credit memos (mixed_inv_credits)
    print("  Tagging mixed_inv_credits customers...", file=sys.stderr)
    cred_result = execute_query(
        "SELECT DISTINCT t.entity AS customer_id "
        "FROM Transaction t "
        "WHERE t.type = 'CustCred' AND t.status <> 'CustCred:B'",
        account=account, environment=environment,
        return_all_rows=False,
    )
    open_cm_ids: Set[int] = set()
    for r in cred_result.get('records', []):
        try:
            open_cm_ids.add(int(r['customer_id']))
        except (KeyError, ValueError, TypeError):
            pass

    inv_result = execute_query(
        "SELECT DISTINCT t.entity AS customer_id "
        "FROM Transaction t "
        "WHERE t.type = 'CustInvc' AND t.foreignamountunpaid > 0",
        account=account, environment=environment,
        return_all_rows=False,
    )
    open_inv_ids: Set[int] = set()
    for r in inv_result.get('records', []):
        try:
            open_inv_ids.add(int(r['customer_id']))
        except (KeyError, ValueError, TypeError):
            pass

    for cid in customers:
        if cid in open_cm_ids and cid in open_inv_ids:
            customers[cid]['categories'].add('mixed_inv_credits')
            customers[cid]['categories'].discard('positive_balance')

    # Supplemental: tag customers with partial payments
    print("  Tagging partial_payment customers...", file=sys.stderr)
    partial_result = execute_query(
        "SELECT DISTINCT t.entity AS customer_id "
        "FROM Transaction t "
        "WHERE t.type = 'CustInvc' "
        "  AND t.foreignamountunpaid > 0 "
        "  AND t.foreignamountunpaid < t.foreigntotal",
        account=account, environment=environment,
        return_all_rows=False,
    )
    for r in partial_result.get('records', []):
        try:
            cid = int(r['customer_id'])
        except (KeyError, ValueError, TypeError):
            continue
        if cid in customers:
            customers[cid]['categories'].add('partial_payment')

    # Assign primary category per customer (priority order)
    for cid, info in customers.items():
        cats = info['categories']
        primary = None
        for cat in _CATEGORY_PRIORITY:
            if cat in cats:
                primary = cat
                break
        if primary is None:
            primary = next(iter(cats)) if cats else 'positive_balance'
        info['primary_category'] = primary

    # Build per-category lists (each customer in its primary category only)
    categories: Dict[str, List[int]] = {}
    for cid, info in customers.items():
        cat = info['primary_category']
        categories.setdefault(cat, []).append(cid)

    # Log category summary
    for cat in _CATEGORY_PRIORITY:
        count = len(categories.get(cat, []))
        if count:
            print(f"  {cat.replace('_', ' ').title():<26}  {count}", file=sys.stderr)

    return customers, categories


def bulk_reference_transactions(
    customer_ids: List[int],
    account: str,
    environment: str,
    batch_size: int = 75,
    max_workers: int = 6,
) -> Dict[int, Dict[int, float]]:
    """Fetch reference transactions for all customers in parallel batches.

    Uses IN (...) batches to amortize gateway round-trips.
    CRITICAL: return_all_rows=False required because the UNION ALL contains
    status <> 'CustCred:B', which SuiteQL silently drops in a subquery context.
    """
    if not customer_ids:
        return {}

    # Split into batches
    batches = [
        customer_ids[i:i + batch_size]
        for i in range(0, len(customer_ids), batch_size)
    ]

    result: Dict[int, Dict[int, float]] = {cid: {} for cid in customer_ids}
    errors: List[str] = []

    def _fetch_batch(batch: List[int]) -> Dict[int, Dict[int, float]]:
        ids_str = ', '.join(str(i) for i in batch)
        query = f"""
SELECT t.entity AS customer_id, t.id, t.foreignamountunpaid AS amount_remaining
FROM Transaction t
WHERE t.entity IN ({ids_str})
  AND t.type = 'CustInvc'
  AND t.foreignamountunpaid <> 0
UNION ALL
SELECT t.entity AS customer_id, t.id, t.foreigntotal AS amount_remaining
FROM Transaction t
WHERE t.entity IN ({ids_str})
  AND t.type = 'CustCred'
  AND t.status <> 'CustCred:B'
ORDER BY 1, 2
"""
        for attempt in range(4):
            qr = execute_query(query, account=account, environment=environment,
                               return_all_rows=False)
            err = str(qr.get('error') or '')
            if '429' in err and 'too many requests' in err.lower():
                time.sleep(2 ** (attempt + 1))
                continue
            break

        batch_result: Dict[int, Dict[int, float]] = {}
        if qr.get('error'):
            return batch_result  # caller will notice missing customer_ids
        for row in qr.get('records', []):
            try:
                cid  = int(row['customer_id'])
                tid  = int(row['id'])
                amt  = float(row.get('amount_remaining') or 0)
            except (KeyError, ValueError, TypeError):
                continue
            batch_result.setdefault(cid, {})[tid] = amt
        return batch_result

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_fetch_batch, b): b for b in batches}
        for future in as_completed(futures):
            batch_data = future.result()
            for cid, tran_data in batch_data.items():
                result[cid] = tran_data

    elapsed = time.time() - t0
    print(
        f"  Reference transactions: {len(batches)} batch(es) in {elapsed:.1f}s",
        file=sys.stderr,
    )
    return result


def _is_429_error(result: Dict[str, Any]) -> bool:
    """Return True if the execute_query result is a gateway 429 rate-limit error."""
    err = str(result.get('error') or '')
    return '429' in err and 'too many requests' in err.lower()


def _validate_one_customer(
    profile_id: int,
    cid: int,
    category: str,
    datasources: List[Dict],
    ref_balance: float,
    ref_tran_data: Dict[int, float],
    account: str,
    environment: str,
    max_retries: int = 4,
) -> Dict[str, Any]:
    """Thread-safe per-customer CRE2 validation using pre-fetched reference data.

    Retries with exponential backoff on HTTP 429 rate-limit errors from the gateway.
    """
    ref_data = {
        'balance':   ref_balance,
        'tran_data': ref_tran_data,
        'error':     None,
    }

    for attempt in range(max_retries + 1):
        cre2_data = get_cre2_data(profile_id, cid, account, environment,
                                  datasources=datasources)

        # Check if ALL datasource calls failed with 429 — if so, retry after backoff
        err = cre2_data.get('error') or ''
        has_data = cre2_data.get('balance_ds') or cre2_data.get('tran_ds')
        all_429 = ('429' in err and 'too many requests' in err.lower() and not has_data)

        if all_429 and attempt < max_retries:
            wait_secs = 2 ** (attempt + 1)  # 2, 4, 8, 16 seconds
            time.sleep(wait_secs)
            continue

        return validate_customer(cid, category, cre2_data, ref_data)

    # All retries exhausted — return whatever we got
    return validate_customer(cid, category, cre2_data, ref_data)  # type: ignore[return-value]


# ─── Field Extraction Helpers ────────────────────────────────────────────────

def _first_match(row: Dict[str, Any], candidates: tuple) -> Optional[Any]:
    row_lower = {k.lower(): v for k, v in row.items()}
    for c in candidates:
        if c in row_lower:
            return row_lower[c]
    return None


def _extract_balance_value(rows: List[Dict]) -> Optional[float]:
    if not rows:
        return None
    row = rows[0]
    raw = _first_match(row, ('balance', 'amount', 'total', 'openbalance', 'foreignamount'))
    if raw is None:
        for v in row.values():
            try:
                return float(v)
            except (ValueError, TypeError):
                continue
        return None
    try:
        return float(raw) if raw is not None else None
    except (ValueError, TypeError):
        return None


def _extract_tran_amounts(rows: List[Dict]) -> Dict[int, float]:
    """Return {transaction_id: open_amount} for each tran datasource row."""
    result: Dict[int, float] = {}
    for row in rows:
        id_raw  = _first_match(row, ('id', 'internalid'))
        amt_raw = _first_match(row, ('foreignamountunpaid', 'amountremaining',
                                     'amount_remaining', 'openamount', 'foreignamount'))
        if id_raw is None:
            continue
        try:
            tran_id = int(id_raw)
        except (ValueError, TypeError):
            continue
        try:
            amount = float(amt_raw) if amt_raw is not None else 0.0
        except (ValueError, TypeError):
            amount = 0.0
        result[tran_id] = amount
    return result


def _extract_tran_fields(rows: List[Dict]) -> FrozenSet[str]:
    if not rows:
        return frozenset()
    return frozenset(k.lower() for k in rows[0].keys())


def _extract_tranids(rows: List[Dict]) -> List[str]:
    """Extract human-readable transaction number strings (e.g. 'INV-12345') from tran rows."""
    tranids = []
    for row in rows:
        val = _first_match(row, ('tranid', 'documentnumber', 'tran_id', 'invoice_number'))
        if val and str(val).strip():
            tranids.append(str(val).strip())
    return tranids


# ─── Entity ID Helper ────────────────────────────────────────────────────────

def get_entity_ids(customer_id: int, account: str, environment: str) -> List[int]:
    """Return all entity IDs for a customer: parent + active consolidated children.

    Uses the same query as the CRE2 cus_children datasource so that the test
    validates exactly the same population that CRE2 renders.
    """
    result = execute_query(
        "SELECT id FROM customer WHERE (id = ? OR parent = ?) AND isinactive = 'F'",
        params=[customer_id, customer_id],
        account=account, environment=environment,
        return_all_rows=False,
    )
    if result.get('error') or not result.get('records'):
        return [customer_id]
    return [int(r['id']) for r in result.get('records', []) if r.get('id')]


def _preprocess_freemarker(sql: str, entity_ids: List[int]) -> str:
    """Substitute known CRE2 FreeMarker patterns so queries can be executed directly.

    Handles:
      • <#list cus_children.rows as C>,${C.id}</#list>
            → resolved to ,child1,child2,... (children beyond first entity)
      • <#if PARMS.startDate?has_content> ... </#if>
            → stripped (test runs without a startDate, so the block is inactive)
      • IN (SELECT id FROM customer WHERE (id = N<#if PARMS.consolidateStatements...> OR parent = N</#if>) AND isinactive = 'F')
            → replaced with IN (entity_id1, entity_id2, ...) using the full entity_ids list.
              entity_ids is always parent + all active children (same as get_entity_ids()),
              which matches both the reference query scope and the profile's consolidated view.
    """
    # Replace cus_children list expression with actual child IDs
    child_ids = entity_ids[1:] if len(entity_ids) > 1 else []
    child_suffix = ''.join(f',{cid}' for cid in child_ids)
    sql = re.sub(
        r'<#list cus_children\.rows as C>.*?</#list>',
        child_suffix,
        sql, flags=re.DOTALL,
    )
    # Strip PARMS.startDate conditional blocks (treat startDate as empty)
    sql = re.sub(
        r'<#if PARMS\.startDate\?has_content>.*?</#if>',
        '',
        sql, flags=re.DOTALL,
    )
    # Replace the entity subquery (which may contain a PARMS.consolidateStatements FreeMarker
    # conditional) with a direct IN list of all entity IDs.  The entity_ids list already
    # encodes the correct parent+child scope (same as get_entity_ids()), so this is equivalent
    # to what the profile renders and matches what the reference data query covers.
    entity_ids_str = ','.join(str(i) for i in entity_ids)
    sql = re.sub(
        r'IN\s*\(\s*SELECT\s+id\s+FROM\s+customer\s+WHERE\s*\(id\s*=\s*\d+'
        r'(?:<#if[^>]*>.*?</#if>)?\)\s*AND\s+isinactive\s*=\s*\'F\'\s*\)',
        f'IN ({entity_ids_str})',
        sql, flags=re.DOTALL | re.IGNORECASE,
    )
    return sql


# ─── CRE2 Datasource Classification ─────────────────────────────────────────

# Exact datasource names that are definitively one type.
# Used in a priority pre-pass so secondary datasources (discount_lines, cus_children, etc.)
# cannot steal the tran_ds slot before the real transaction datasource is processed.
_BALANCE_DS_EXACT: FrozenSet[str] = frozenset((
    'account_balance', 'balance', 'header', 'summary', 'customer_balance',
))
_TRAN_DS_EXACT: FrozenSet[str] = frozenset((
    'tran', 'transactions', 'transaction_lines', 'invoices', 'open_transactions',
    'open_invoices',
))


def _classify_datasource(name: str, paged: bool, single_json: bool) -> str:
    n = (name or '').lower()
    # Exact-name priority (prevents 'discount_lines' from stealing the tran slot)
    if n in _BALANCE_DS_EXACT:
        return 'balance'
    if n in _TRAN_DS_EXACT:
        return 'tran'
    # Keyword heuristics — NOTE: 'line' intentionally omitted to avoid false-matching
    # names like 'discount_lines', 'address_lines', etc.
    if any(kw in n for kw in ('balance', 'account', 'header', 'summary')):
        return 'balance'
    if any(kw in n for kw in ('tran', 'invoice')):
        return 'tran'
    if single_json:
        return 'balance'
    if paged:
        return 'tran'
    return 'unknown'


# ─── CRE2 Data Retrieval ─────────────────────────────────────────────────────

def get_cre2_data(profile_id: int, customer_id: int,
                  account: str, environment: str,
                  datasources: Optional[List[Dict]] = None,
                  entity_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    if datasources is None:
        datasources = get_datasources(profile_id, account, environment)
    if not datasources:
        return {'balance_ds': None, 'tran_ds': None,
                'error': f'No datasources found for profile {profile_id}'}

    # Pre-fetch entity IDs (parent + children) for FreeMarker substitution.
    # Reuse caller-supplied value if available to avoid an extra round-trip.
    if entity_ids is None:
        entity_ids = get_entity_ids(customer_id, account, environment)

    result: Dict[str, Any] = {'balance_ds': None, 'tran_ds': None, 'error': None}
    errors: List[str] = []

    for ds in datasources:
        query_sql = ds.get('query_sql') or ''
        if not query_sql:
            continue

        test_sql = query_sql.replace('${record.id}', str(customer_id))
        # Substitute CRE2 FreeMarker patterns the test knows how to resolve.
        test_sql = _preprocess_freemarker(test_sql, entity_ids)

        # Guard: if the SQL still contains unresolved FreeMarker expressions after
        # substituting ${record.id} and known patterns, report explicitly.
        if '${' in test_sql or '<#' in test_sql:
            errors.append(
                f"Datasource '{ds.get('name', '?')}': SQL contains unresolved FreeMarker "
                f"expressions after substituting ${{record.id}} — test can only substitute "
                f"that placeholder; datasource skipped"
            )
            continue

        qr = execute_query(test_sql, account=account, environment=environment,
                            return_all_rows=False)

        if qr.get('error'):
            errors.append(f"Datasource '{ds.get('name', '?')}': {qr['error']}")
            continue

        rows = qr.get('records', [])
        ds_type = _classify_datasource(
            ds.get('name', ''), ds.get('paged') == 'T', ds.get('single_record_json') == 'T',
        )
        if ds_type == 'unknown':
            # Skip rather than guess — secondary datasources like 'discount_lines' or
            # 'cus_children' would otherwise steal the tran_ds slot by row-count heuristic.
            # Add names to _TRAN_DS_EXACT / _BALANCE_DS_EXACT if a valid ds is being skipped.
            continue

        if ds_type == 'balance' and result['balance_ds'] is None:
            result['balance_ds'] = {
                'name':    ds.get('name', ''),
                'rows':    rows,
                'balance': _extract_balance_value(rows),
            }
        elif ds_type == 'tran' and result['tran_ds'] is None:
            result['tran_ds'] = {
                'name':    ds.get('name', ''),
                'rows':    rows,
                'amounts': _extract_tran_amounts(rows),
                'fields':  _extract_tran_fields(rows),
            }

    if errors:
        result['error'] = '; '.join(errors)
    return result


# ─── Reference Data ──────────────────────────────────────────────────────────

def get_reference_data(customer_id: int, account: str, environment: str,
                       entity_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {'balance': None, 'tran_data': {}, 'error': None}
    errors: List[str] = []

    # Reuse caller-supplied entity_ids or fetch fresh (parent + children).
    if entity_ids is None:
        entity_ids = get_entity_ids(customer_id, account, environment)

    entity_ids_str = ','.join(str(i) for i in entity_ids)

    # Use multi-entity balance query so reference matches the CRE2 account_balance datasource.
    bal_query = REFERENCE_BALANCE_QUERY_MULTI.format(entity_ids=entity_ids_str)
    bal = execute_query(bal_query, account=account, environment=environment,
                        return_all_rows=False)
    if bal.get('error'):
        errors.append(f"Balance: {bal['error']}")
    elif bal.get('records'):
        raw = bal['records'][0].get('balance')
        try:
            result['balance'] = float(raw) if raw is not None else 0.0
        except (ValueError, TypeError):
            result['balance'] = None

    tran_query = REFERENCE_TRAN_QUERY_TEMPLATE.format(entity_ids=entity_ids_str)
    tran = execute_query(tran_query, account=account, environment=environment,
                         return_all_rows=False)
    if tran.get('error'):
        errors.append(f"Transactions: {tran['error']}")
    else:
        result['tran_data'] = {
            int(r['id']): float(r.get('amount_remaining') or 0)
            for r in tran.get('records', [])
            if r.get('id')
        }

    if errors:
        result['error'] = '; '.join(errors)
    return result


# ─── PDF Content Check ───────────────────────────────────────────────────────

def _check_paylink_annotations(pdf_path: str) -> Dict[str, Any]:
    """Verify the CRE2 statement has a clickable paylink button annotation.

    The JS hook (twx_CRE2_SecureTransactionLinks.js) generates a Suitelet URL
    containing 'extforms.netsuite.com' and 'customerId=' query param.

    Two failure modes are distinguished:
      • No paylink URI at all  → hook did not fire or template omitted the link
      • URI exists but zero-size rect → link has no hit-area, not clickable
        (known regression: template wraps the link around a zero-size element)

    Returns:
        found=True   — paylink URI annotation with non-zero area exists
        found=False  — paylink URI found but has zero area OR no paylink URI at all
        found=None   — check could not be performed (pdfplumber error)
    """
    PAYLINK_KEYWORDS = ('extforms.netsuite.com', 'customerId=')

    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return {'found': None, 'count': 0, 'urls': [],
                'detail': 'pdfplumber not available for annotation check'}

    try:
        paylinks: List[Dict[str, Any]] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                for annot in (page.annots or []):
                    uri = annot.get('uri') or annot.get('URI')
                    if not uri or not str(uri).strip():
                        continue
                    uri_str = str(uri).strip()
                    if not any(kw in uri_str for kw in PAYLINK_KEYWORDS):
                        continue
                    width  = float(annot.get('width',  0) or 0)
                    height = float(annot.get('height', 0) or 0)
                    paylinks.append({
                        'uri':      uri_str[:120],
                        'width':    width,
                        'height':   height,
                        'has_area': width > 0 and height > 0,
                    })

        if not paylinks:
            return {'found': False, 'count': 0, 'urls': [],
                    'detail': 'no paylink URI annotation found — hook may not have fired'}

        clickable = [p for p in paylinks if p['has_area']]
        broken    = [p for p in paylinks if not p['has_area']]

        if not clickable:
            b = broken[0]
            return {
                'found':          False,
                'count':          0,
                'urls':           [],
                'detail':         (
                    f'paylink annotation present but has zero dimensions '
                    f'(width={b["width"]}, height={b["height"]}) — '
                    f'not clickable; template wraps link around zero-size element'
                ),
                'broken_paylinks': broken,
            }

        return {
            'found': True,
            'count': len(clickable),
            'urls':  [p['uri'] for p in clickable[:3]],
        }

    except Exception as exc:
        return {'found': None, 'count': 0, 'urls': [],
                'detail': f'Annotation scan error: {exc}'}



def _paylink_check_by_file_id(file_id: int, account: str, environment: str) -> Dict[str, Any]:
    """Download a CRE2 PDF by fileId and check paylink URI annotations.

    Reuses the same gateway download path as the rest of the test suite.
    Returns the same dict shape as _check_paylink_annotations.
    """
    try:
        from download_file import get_file_content
    except ImportError as e:
        return {'found': None, 'count': 0, 'urls': [],
                'detail': f'download_file import failed: {e}'}

    content_result = get_file_content(file_id, account, environment)
    if content_result.get('error'):
        return {'found': None, 'count': 0, 'urls': [],
                'detail': f'fileGet failed for file {file_id}: {content_result["error"]}'}

    pdf_content = content_result.get('content')
    if isinstance(pdf_content, str):
        try:
            pdf_bytes = base64.b64decode(pdf_content)
        except Exception as exc:
            return {'found': None, 'count': 0, 'urls': [],
                    'detail': f'base64 decode failed: {exc}'}
    else:
        pdf_bytes = pdf_content

    if not isinstance(pdf_bytes, bytes):
        return {'found': None, 'count': 0, 'urls': [],
                'detail': 'Unexpected content type after decode'}

    fd, tmp_path = tempfile.mkstemp(suffix='.pdf', prefix='cre2_paylink_')
    os.close(fd)
    try:
        with open(tmp_path, 'wb') as f:
            f.write(pdf_bytes)
        return _check_paylink_annotations(tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def run_compare_check(
    profile_id: int,
    customer_id: int,
    category: str,
    account: str,
    environment: str,
) -> Dict[str, Any]:
    """Run compare_statements.compare() for one customer, capturing its printed output.

    compare_statements.compare() prints a full text report to stdout and returns
    True (all pass/warn) or False (any fail).  This wrapper captures stdout,
    interprets the return value, and returns a structured result dict.

    The 'consolidated' category maps to consolidate=True so child-customer
    transactions are included in the native statement request.
    """
    try:
        import compare_statements
    except ImportError as e:
        return {'status': 'SKIP', 'detail': f'compare_statements import failed: {e}', 'report': ''}

    consolidate = category in ('consolidated', 'parent_customer')

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            ok = compare_statements.compare(
                customer_id=str(customer_id),
                account=account,
                environment=environment,
                consolidate=consolidate,
                profile_id=str(profile_id),
            )
    except Exception as exc:
        report = buf.getvalue()
        return {
            'status': 'ERROR',
            'detail': f'compare raised exception: {exc}',
            'report': report,
        }

    report = buf.getvalue()

    # ── Paylink annotation check ───────────────────────────────────────────────
    # compare_statements prints "CRE2  → fileId=<N>" — parse that to get the file_id
    # so we can download the PDF and verify the clickable paylink annotation.
    paylink_info: Dict[str, Any] = {}
    m = re.search(r'CRE2\s*\u2192\s*fileId=(\d+)', report)
    if m:
        paylink_info = _paylink_check_by_file_id(int(m.group(1)), account, environment)
    else:
        paylink_info = {'found': None, 'count': 0, 'urls': [],
                        'detail': 'CRE2 fileId not found in compare report — paylink check skipped'}

    if ok:
        # Collect any WARN lines from the compare report (e.g. JE-in-AR aging pattern)
        warn_lines = [ln.strip() for ln in report.splitlines() if ln.strip().startswith('WARN')]

        # Paylink failure always wins
        if paylink_info.get('found') is False:
            return {
                'status': 'FAIL',
                'detail': f'paylink: {paylink_info.get("detail", "no clickable paylink annotation")}',
                'report': report,
                'paylink': paylink_info,
            }

        # Return WARN if the compare report itself had warnings, or paylink was skipped
        if warn_lines or paylink_info.get('found') is None:
            detail_parts = warn_lines[:2]
            if paylink_info.get('found') is None:
                detail_parts.append(f'paylink skipped: {paylink_info.get("detail", "")}')
            return {
                'status': 'WARN',
                'detail': '; '.join(detail_parts) or 'Comparison has warnings',
                'report': report,
                'paylink': paylink_info,
            }

        return {
            'status': 'PASS',
            'detail': f'All comparison checks passed; paylink={paylink_info.get("count", 0)} link(s)',
            'report': report,
            'paylink': paylink_info,
        }

    # One or more compare checks failed
    fail_lines = [ln.strip() for ln in report.splitlines() if 'FAIL' in ln]
    detail = fail_lines[0] if fail_lines else 'One or more comparison checks failed'
    return {'status': 'FAIL', 'detail': detail, 'report': report, 'paylink': paylink_info}


# ─── Validation ──────────────────────────────────────────────────────────────

def _make_check(status: str, detail: str = '', **extra) -> Dict[str, Any]:
    return {'status': status, 'detail': detail, **extra}


def validate_customer(
    customer_id: int,
    category: str,
    cre2_data: Dict[str, Any],
    ref_data: Dict[str, Any],
    compare_check_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run all data-layer checks (and attach optional compare result) for one customer."""
    out: Dict[str, Any] = {
        'customer_id': customer_id,
        'category':    category,
        'status':      'PASS',
        'checks':      {},
    }

    cre2_dead = cre2_data.get('error') and not cre2_data.get('balance_ds') and not cre2_data.get('tran_ds')
    ref_dead  = ref_data.get('error') and ref_data.get('balance') is None and not ref_data.get('tran_data')
    if cre2_dead or ref_dead:
        out['status'] = 'ERROR'
        out['error']  = cre2_data.get('error') or ref_data.get('error')
        return out

    check_statuses: List[str] = []
    bal_ds  = cre2_data.get('balance_ds') or {}
    tran_ds = cre2_data.get('tran_ds') or {}

    # ── 1. Balance ────────────────────────────────────────────────────────────
    cre2_balance: Optional[float] = bal_ds.get('balance')
    ref_balance:  Optional[float] = ref_data.get('balance')

    if not cre2_data.get('balance_ds'):
        bal_check = _make_check('FAIL', 'account_balance datasource not found in CRE2 profile — PDF would render without balance data')
    elif cre2_balance is None:
        bal_check = _make_check('WARN', 'Could not extract numeric balance from CRE2 result',
                                cre2=None, reference=ref_balance)
    elif ref_balance is None:
        bal_check = _make_check('WARN', 'Reference balance query returned no data',
                                cre2=cre2_balance, reference=None)
    elif not math.isclose(cre2_balance, ref_balance, abs_tol=BALANCE_TOLERANCE):
        bal_check = _make_check('FAIL',
                                f'CRE2={cre2_balance:.2f}, Reference={ref_balance:.2f}',
                                cre2=cre2_balance, reference=ref_balance)
    else:
        bal_check = _make_check('PASS', f'{cre2_balance:.2f}',
                                cre2=cre2_balance, reference=ref_balance)

    out['checks']['balance'] = bal_check
    if bal_check['status'] != 'SKIP':
        check_statuses.append(bal_check['status'])

    # ── 2. Transaction coverage ───────────────────────────────────────────────
    cre2_ids: Set[int] = set(tran_ds.get('amounts', {}).keys()) if cre2_data.get('tran_ds') else set()
    ref_ids:  Set[int] = set(ref_data.get('tran_data', {}).keys())
    missing = sorted(ref_ids - cre2_ids)
    extra   = sorted(cre2_ids - ref_ids)

    if missing or extra:
        parts = []
        if missing:
            parts.append(f'missing {len(missing)} tran(s)')
        if extra:
            parts.append(f'extra {len(extra)} tran(s)')
        tran_check = _make_check('FAIL', ', '.join(parts),
                                 cre2_count=len(cre2_ids), ref_count=len(ref_ids),
                                 missing=missing[:10], extra=extra[:10])
    else:
        tran_check = _make_check('PASS', f'{len(cre2_ids)} transaction(s) match',
                                 cre2_count=len(cre2_ids), ref_count=len(ref_ids),
                                 missing=[], extra=[])

    out['checks']['transactions'] = tran_check
    check_statuses.append(tran_check['status'])

    # ── 3. Per-transaction amounts ────────────────────────────────────────────
    cre2_amounts: Dict[int, float] = tran_ds.get('amounts', {}) if cre2_data.get('tran_ds') else {}
    ref_amounts:  Dict[int, float] = ref_data.get('tran_data', {})

    if not cre2_data.get('tran_ds'):
        amt_check = _make_check('FAIL', 'tran datasource not found in CRE2 profile — PDF would render without transaction amounts')
    elif not cre2_amounts:
        if not ref_amounts:
            # Zero open transactions in both CRE2 and reference — expected for zero/credit-balance customers
            amt_check = _make_check('PASS', 'No open transactions (zero balance customer)')
        else:
            amt_check = _make_check('WARN',
                                    'Could not extract transaction ID/amount pairs; '
                                    'field names may differ from expected')
    else:
        mismatches = []
        for tid in (cre2_ids & ref_ids):
            c_amt = cre2_amounts.get(tid, 0.0)
            r_amt = ref_amounts.get(tid, 0.0)
            if not math.isclose(c_amt, r_amt, abs_tol=BALANCE_TOLERANCE):
                mismatches.append({'id': tid, 'cre2': c_amt,
                                   'reference': r_amt, 'delta': round(c_amt - r_amt, 2)})
        if mismatches:
            amt_check = _make_check(
                'FAIL',
                f'{len(mismatches)} of {len(cre2_ids & ref_ids)} common transaction(s) '
                'have wrong open amount',
                mismatches=mismatches[:10],
            )
        else:
            amt_check = _make_check('PASS',
                                    f'All {len(cre2_ids & ref_ids)} common transaction amounts match')

    out['checks']['tran_amounts'] = amt_check
    if amt_check['status'] != 'SKIP':
        check_statuses.append(amt_check['status'])

    # ── 4. Template field completeness ───────────────────────────────────────
    tran_fields: FrozenSet[str] = tran_ds.get('fields', frozenset()) if cre2_data.get('tran_ds') else frozenset()

    if not cre2_data.get('tran_ds'):
        field_check = _make_check('FAIL', 'tran datasource not found in CRE2 profile — PDF would render without transactions')
    elif not tran_fields:
        field_check = _make_check('SKIP', 'Tran datasource returned 0 rows (cannot inspect fields)')
    else:
        missing_req = [grp for grp in REQUIRED_TRAN_FIELD_GROUPS
                       if not any(f in tran_fields for f in grp)]
        missing_exp = [grp for grp in EXPECTED_TRAN_FIELD_GROUPS
                       if not any(f in tran_fields for f in grp)]

        if missing_req:
            field_check = _make_check(
                'FAIL',
                f'Missing required field group(s): {["/".join(g) for g in missing_req]}',
                missing_required=['/'.join(g) for g in missing_req],
                missing_expected=['/'.join(g) for g in missing_exp],
                present=sorted(tran_fields),
            )
        elif missing_exp:
            field_check = _make_check(
                'WARN',
                f'Missing expected field group(s): {["/".join(g) for g in missing_exp]}; '
                'template may display blanks',
                missing_required=[],
                missing_expected=['/'.join(g) for g in missing_exp],
                present=sorted(tran_fields),
            )
        else:
            field_check = _make_check(
                'PASS',
                f'All required and expected field groups present ({len(tran_fields)} fields total)',
            )

    out['checks']['tran_fields'] = field_check
    if field_check['status'] != 'SKIP':
        check_statuses.append(field_check['status'])

    # ── 5. Balance Forward sanity ─────────────────────────────────────────────
    if not (cre2_data.get('balance_ds') and cre2_data.get('tran_ds')) or cre2_balance is None:
        bf_check = _make_check('SKIP', 'Requires both balance and tran datasources')
    else:
        tran_total = sum(cre2_amounts.values()) if cre2_amounts else 0.0
        bf_value   = cre2_balance - tran_total
        if ref_balance and abs(ref_balance) > BALANCE_TOLERANCE:
            ratio = abs(bf_value) / abs(ref_balance)
            if ratio > BALANCE_FORWARD_WARN_RATIO:
                bf_check = _make_check(
                    'WARN',
                    f'balance_forward={bf_value:.2f} ({ratio:.1f}× total {ref_balance:.2f}); '
                    'possible query drift',
                    value=round(bf_value, 2),
                )
            else:
                bf_check = _make_check('PASS', f'balance_forward={bf_value:.2f}',
                                       value=round(bf_value, 2))
        else:
            bf_check = _make_check('PASS', f'balance_forward={bf_value:.2f}',
                                   value=round(bf_value, 2))

    out['checks']['balance_forward'] = bf_check
    if bf_check['status'] not in ('SKIP',):
        check_statuses.append(bf_check['status'])

    # ── 6. Compare check (optional) ───────────────────────────────────────────
    if compare_check_result is not None:
        out['checks']['compare'] = compare_check_result
        if compare_check_result['status'] not in ('SKIP',):
            check_statuses.append(compare_check_result['status'])

    # ── Overall status ────────────────────────────────────────────────────────
    for s in ('ERROR', 'FAIL', 'WARN', 'PASS'):
        if s in check_statuses:
            out['status'] = s
            break

    return out


# ─── Output Formatting ───────────────────────────────────────────────────────

_ICON = {'PASS': '✅', 'FAIL': '❌', 'WARN': '⚠️ ', 'ERROR': '🔴', 'SKIP': '⏭️ '}


def _icon(status: str) -> str:
    return _ICON.get(status, '?')


def _fmt_float(v: Any) -> str:
    return f'{v:.2f}' if isinstance(v, (int, float)) else 'N/A'


def print_customer_result(res: Dict[str, Any]) -> None:
    cid    = res['customer_id']
    cat    = res['category'].replace('_', ' ').title()
    status = res['status']
    checks = res.get('checks', {})
    bal    = checks.get('balance', {})
    tran   = checks.get('transactions', {})

    if status == 'PASS':
        bal_str  = f"balance={_fmt_float(bal.get('cre2'))}"
        tran_str = f"tran={tran.get('cre2_count','?')}/{tran.get('ref_count','?')}"
        cmp_str  = ' cmp=✓' if checks.get('compare', {}).get('status') == 'PASS' else ''
        print(f"{_icon(status)} [{cid:<6}]  {cat:<20}  {bal_str}  {tran_str}{cmp_str}  PASS")
        return

    print(f"{_icon(status)} [{cid:<6}]  {cat:<20}  {status}")

    if bal.get('status') not in ('PASS', 'SKIP', None):
        sfx = '  ← MISMATCH' if bal.get('status') == 'FAIL' else ''
        print(f"   balance:       CRE2={_fmt_float(bal.get('cre2'))}, "
              f"Reference={_fmt_float(bal.get('reference'))}{sfx}")

    if tran.get('status') not in ('PASS', None):
        sfx = '  ← MISMATCH' if tran.get('status') == 'FAIL' else '  ← OK'
        print(f"   transactions:  CRE2={tran.get('cre2_count','?')}, "
              f"Reference={tran.get('ref_count','?')}{sfx}")
        for label, key in (('missing', 'missing'), ('extra', 'extra')):
            ids = tran.get(key, [])
            if ids:
                more = f'…+{len(ids)-5}' if len(ids) > 5 else ''
                print(f"   {label} IDs:    {ids[:5]}{more}")

    amt = checks.get('tran_amounts', {})
    if amt.get('status') not in ('PASS', 'SKIP', None):
        print(f"   tran_amounts:  {amt.get('detail', '')}")
        for m in (amt.get('mismatches') or [])[:3]:
            print(f"     id={m['id']}  CRE2={m['cre2']:.2f}  Ref={m['reference']:.2f}  "
                  f"Δ={m['delta']:+.2f}")

    fld = checks.get('tran_fields', {})
    if fld.get('status') not in ('PASS', 'SKIP', None):
        print(f"   tran_fields:   {fld.get('detail', '')}")
        if fld.get('missing_required'):
            print(f"     MISSING (required): {fld['missing_required']}")

    bf = checks.get('balance_forward', {})
    if bf.get('status') == 'WARN':
        print(f"   balance_fwd:   {bf.get('detail', '')}")

    cmp = checks.get('compare', {})
    if cmp.get('status') not in ('PASS', 'SKIP', None):
        print(f"   compare:       {cmp.get('detail', '')}")
        # Print first few FAIL lines from the captured report for context
        report = cmp.get('report', '')
        fail_lines = [ln.strip() for ln in report.splitlines() if 'FAIL' in ln]
        for fl in fail_lines[:5]:
            print(f"     {fl}")

    if res.get('error'):
        print(f"   error:         {res['error']}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='CRE2 Customer Statement Data Validation Test Suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 test_statement_data.py --env sb2
  python3 test_statement_data.py --env sb2 --compare-check
  python3 test_statement_data.py --env prod
  python3 test_statement_data.py --env sb2 --customers 5764,4631,12926
  python3 test_statement_data.py --env sb2 --format json

Full-coverage mode (tests ALL statement-eligible customers):
  python3 test_statement_data.py --env sb2 --full-coverage
  python3 test_statement_data.py --env prod --full-coverage --compare-check
  python3 test_statement_data.py --env sb2 --full-coverage --concurrency 12
""",
    )
    parser.add_argument('--env',         default='sb2',           help='Environment: prod, sb1, sb2 (default: sb2)')
    parser.add_argument('--account',     default=DEFAULT_ACCOUNT, help='Account (default: twistedx)')
    parser.add_argument('--profile',     type=int, default=PROFILE_ID, help=f'Profile ID (default: {PROFILE_ID})')
    parser.add_argument('--customers',   help='Comma-separated customer IDs (skips auto-discovery)')
    parser.add_argument('--compare-check', action='store_true',
                        help='Also render native+CRE2 statements and compare for one customer per category')
    parser.add_argument('--format',      choices=['table', 'json'], default='table')
    parser.add_argument('--full-coverage', action='store_true',
                        help='Validate ALL statement-eligible customers (parent IS NULL, active, entitystatus=13)')
    parser.add_argument('--concurrency', type=int, default=4,
                        help='Max parallel gateway requests in full-coverage mode (default: 4)')
    parser.add_argument('--batch-size',  type=int, default=75,
                        help='Customers per bulk reference-transaction batch (default: 75)')
    args = parser.parse_args()

    account     = resolve_account(args.account)
    environment = resolve_environment(args.env)
    is_table    = (args.format == 'table')

    run_start = time.time()

    if is_table:
        mode_label = 'full-coverage' if args.full_coverage else 'sampled'
        print(f"\nCRE2 Customer Statement Validation — {account}/{environment}  [{mode_label}]")
        print('═' * 62)
        print(f"Profile: {args.profile} (Customer Statement Portrait)")
        extra_layers = ' · compare' if args.compare_check else ''
        print(f"Layers:  balance · transactions · tran_amounts · tran_fields · "
              f"balance_forward{extra_layers}")
        print()

    # ══════════════════════════════════════════════════════════════
    # FULL-COVERAGE PATH
    # ══════════════════════════════════════════════════════════════
    if args.full_coverage and not args.customers:
        all_results: List[Dict[str, Any]] = []

        # Phase 1: Discover all statement-eligible customers
        customers_info, categories = discover_statement_customers(account, environment)

        if not customers_info:
            print("ERROR: Customer discovery returned no results.", file=sys.stderr)
            sys.exit(1)

        all_customer_ids = list(customers_info.keys())
        total_discovered = len(all_customer_ids)

        # Phase 2: Bulk-fetch reference transactions
        print("\nFetching bulk reference data...", file=sys.stderr)
        ref_transactions = bulk_reference_transactions(
            all_customer_ids, account, environment,
            batch_size=args.batch_size,
            max_workers=min(args.concurrency, 3),  # cap batch parallelism conservatively
        )

        # Phase 3: Cache datasources once
        datasources_cached = get_datasources(args.profile, account, environment)
        if not datasources_cached:
            print(f"ERROR: No datasources found for profile {args.profile}", file=sys.stderr)
            sys.exit(1)
        print(f"  Datasources cached: {len(datasources_cached)} query(ies)", file=sys.stderr)

        # Phase 4: Parallel per-customer CRE2 validation
        print(f"\nValidating {total_discovered} customers (concurrency={args.concurrency})...",
              file=sys.stderr)
        print("  (use --concurrency to adjust; >4 may trigger NetSuite 429 rate limits)",
              file=sys.stderr)

        # Build flat list of (cid, primary_category) in ID order
        work_items: List[Tuple[int, str]] = [
            (cid, customers_info[cid]['primary_category'])
            for cid in sorted(customers_info.keys())
        ]

        completed_count = 0
        phase4_start = time.time()

        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            future_to_cid = {
                executor.submit(
                    _validate_one_customer,
                    args.profile, cid, category,
                    datasources_cached,
                    customers_info[cid]['balance'],
                    ref_transactions.get(cid, {}),
                    account, environment,
                ): cid
                for cid, category in work_items
            }

            for future in as_completed(future_to_cid):
                result = future.result()
                all_results.append(result)
                completed_count += 1

                if is_table and completed_count % 250 == 0:
                    elapsed = time.time() - phase4_start
                    pct = completed_count * 100 // total_discovered
                    print(
                        f"  Progress: {completed_count}/{total_discovered} ({pct}%) "
                        f"— {elapsed:.0f}s elapsed",
                        file=sys.stderr,
                    )

        elapsed_total = time.time() - phase4_start
        print(
            f"  Done: {completed_count}/{total_discovered} in {elapsed_total:.0f}s",
            file=sys.stderr,
        )

        # Phase 5: Compare checks for subset (1 per category, serial)
        if args.compare_check:
            print("\nRunning compare checks (1 per category)...", file=sys.stderr)
            result_by_cid: Dict[int, Dict[str, Any]] = {r['customer_id']: r for r in all_results}

            for cat in _CATEGORY_PRIORITY:
                cat_ids = categories.get(cat, [])
                if not cat_ids:
                    continue
                cmp_cid = sorted(cat_ids)[0]
                cmp_result_entry = result_by_cid.get(cmp_cid)
                if cmp_result_entry is None:
                    continue

                compare_check_result = run_compare_check(
                    args.profile, cmp_cid, cat, account, environment
                )
                cmp_result_entry['checks']['compare'] = compare_check_result
                # Update overall status
                statuses = [c.get('status', 'PASS') for c in cmp_result_entry['checks'].values()
                            if c.get('status') != 'SKIP']
                for s in ('ERROR', 'FAIL', 'WARN', 'PASS'):
                    if s in statuses:
                        cmp_result_entry['status'] = s
                        break

        # Sort results by customer_id for consistent output
        all_results.sort(key=lambda r: r['customer_id'])

        if is_table:
            for res in all_results:
                print_customer_result(res)

        # Summary
        passed  = sum(1 for r in all_results if r['status'] == 'PASS')
        failed  = sum(1 for r in all_results if r['status'] == 'FAIL')
        warned  = sum(1 for r in all_results if r['status'] == 'WARN')
        errored = sum(1 for r in all_results if r['status'] == 'ERROR')
        total   = len(all_results)
        run_elapsed = time.time() - run_start

        # Category counts
        cat_counts = {cat: len(ids) for cat, ids in categories.items() if ids}

        if is_table:
            err_part = f", {errored} ERROR" if errored else ""
            print(f"\nResults: {passed}/{total} PASS, {failed} FAIL, {warned} WARN{err_part}")
            print(f"Time: {run_elapsed:.0f}s total")
        else:
            print(json.dumps({
                'profile_id':           args.profile,
                'account':              account,
                'environment':          environment,
                'mode':                 'full_coverage',
                'selection_criteria':   'parent IS NULL, active, entitystatus=13',
                'total_discovered':     total_discovered,
                'compare_check':        args.compare_check,
                'concurrency':          args.concurrency,
                'execution_time_seconds': round(run_elapsed, 1),
                'total':                total,
                'passed':               passed,
                'failed':               failed,
                'warned':               warned,
                'errored':              errored,
                'categories':           cat_counts,
                'results':              all_results,
            }, indent=2, default=lambda o: list(o) if isinstance(o, (set, frozenset)) else str(o)))

        if failed > 0 or errored > 0:
            sys.exit(1)
        sys.exit(0)

    # ══════════════════════════════════════════════════════════════
    # SAMPLED / MANUAL PATH  (original behavior, unchanged)
    # ══════════════════════════════════════════════════════════════

    # ── Discover or use provided customers ───────────────────────────────────
    if args.customers:
        try:
            ids = [int(c.strip()) for c in args.customers.split(',') if c.strip()]
        except ValueError as exc:
            print(f"ERROR: Invalid --customers: {exc}", file=sys.stderr)
            sys.exit(1)
        categories_sampled: Dict[str, List[int]] = {'manual': ids}
        if is_table:
            print(f"Testing {len(ids)} specified customer(s)...\n")
    else:
        if is_table:
            print("Discovering test customers...")
        categories_sampled = discover_test_customers(account, environment)
        if is_table:
            for cat, ids in categories_sampled.items():
                label = cat.replace('_', ' ').title()
                print(f"  {label:<22}  {ids if ids else '(none found)'}")
            total_s = sum(len(v) for v in categories_sampled.values())
            active_s = sum(1 for v in categories_sampled.values() if v)
            print(f"\nTesting {total_s} customers across {active_s} categories...\n")

    # ── Run data-layer validations ────────────────────────────────────────────
    all_results_sampled: List[Dict[str, Any]] = []

    for category, customer_ids in categories_sampled.items():
        for cid in customer_ids:
            entity_ids = get_entity_ids(cid, account, environment)
            cre2_data = get_cre2_data(args.profile, cid, account, environment,
                                      entity_ids=entity_ids)
            ref_data  = get_reference_data(cid, account, environment,
                                           entity_ids=entity_ids)

            result = validate_customer(cid, category, cre2_data, ref_data)
            all_results_sampled.append(result)

            if is_table and not args.compare_check:
                print_customer_result(result)

    # ── Compare checks: top 3 per category by transaction count ───────────────
    if args.compare_check:
        # Group results by category, sort each group by cre2_count descending
        by_cat: Dict[str, List[Dict[str, Any]]] = {}
        for r in all_results_sampled:
            by_cat.setdefault(r['category'], []).append(r)

        for cat, cat_results in by_cat.items():
            top3 = sorted(
                cat_results,
                key=lambda r: r.get('checks', {}).get('transactions', {}).get('cre2_count', 0),
                reverse=True,
            )[:3]
            for r in top3:
                cid = r['customer_id']
                cmp = run_compare_check(args.profile, cid, cat, account, environment)
                r['checks']['compare'] = cmp
                # Re-derive overall status
                statuses = [c.get('status', 'PASS') for c in r['checks'].values()
                            if c.get('status') != 'SKIP']
                for s in ('ERROR', 'FAIL', 'WARN', 'PASS'):
                    if s in statuses:
                        r['status'] = s
                        break

        if is_table:
            for r in all_results_sampled:
                print_customer_result(r)

    # ── Summary ───────────────────────────────────────────────────────────────
    passed  = sum(1 for r in all_results_sampled if r['status'] == 'PASS')
    failed  = sum(1 for r in all_results_sampled if r['status'] == 'FAIL')
    warned  = sum(1 for r in all_results_sampled if r['status'] == 'WARN')
    errored = sum(1 for r in all_results_sampled if r['status'] == 'ERROR')
    total   = len(all_results_sampled)

    if is_table:
        err_part = f", {errored} ERROR" if errored else ""
        print(f"\nResults: {passed}/{total} PASS, {failed} FAIL, {warned} WARN{err_part}")
    else:
        print(json.dumps({
            'profile_id':     args.profile,
            'account':        account,
            'environment':    environment,
            'mode':           'sampled',
            'compare_check':  args.compare_check,
            'total':          total,
            'passed':         passed,
            'failed':         failed,
            'warned':         warned,
            'errored':        errored,
            'results':        all_results_sampled,
        }, indent=2, default=lambda o: list(o) if isinstance(o, (set, frozenset)) else str(o)))

    if failed > 0 or errored > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
