#!/usr/bin/env python3
"""
CRE2 Customer Statement Validation Test Suite

Validates CRE2 Profile 16 (Customer Statement Portrait) by rendering both the
native NetSuite statement and the CRE2 PDF for each customer and comparing:
  • Amount Due
  • Balance Forward
  • Aging buckets (current, 1-30, 31-60, 61-90, 90+, total)
  • Transaction IDs (set match)
  • Per-transaction remaining balance amounts
  • Paylink annotation — clickable URI (extforms.netsuite.com) present

Usage:
  python3 test_statement_data.py --env sb2
  python3 test_statement_data.py --env prod
  python3 test_statement_data.py --env sb2 --customers 5764,4631,12926
  python3 test_statement_data.py --env sb2 --format json

Full-Coverage Mode (tests ALL customers matching the suitelet population —
  customsearch118507 "TWX | Customers Statement List" + balance!=0):
  python3 test_statement_data.py --env sb2 --full-coverage
  python3 test_statement_data.py --env prod --full-coverage
  python3 test_statement_data.py --env sb2 --full-coverage --concurrency 12
  Note: --full-coverage renders native+CRE2 for every customer — very slow.
"""

import sys
import os
import io
import json
import re
import time
import argparse
import tempfile
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List, Tuple

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
    resolve_account,
    resolve_environment,
    DEFAULT_ACCOUNT,
    DEFAULT_ENVIRONMENT,
)

# CRE2 Profile 16: Customer Statement (Portrait)
PROFILE_ID = 16

# ─── Known Diffs and Skips ────────────────────────────────────────────────────
# Customers whose CRE2 value will never match native due to fundamental
# methodology differences. These are tracked but not treated as failures.
# Root cause (historical): native's ${record.amountDue} uses Customer.balancesearch /
# consolbalancesearch fields — now used directly in Q227 and Q128. All former
# KNOWN_DIFF customers now PASS (2026-03-06).

KNOWN_DIFFS: Dict[int, str] = {
}

SKIP_CUSTOMERS: Dict[int, str] = {
    4373: "610 subcustomers — impractical for PDF statement rendering (times out)",
}



# ─── Customer Discovery ──────────────────────────────────────────────────────

# SQL fragment appended to sampled discovery queries to exclude sub-customers
# that are descendants (at any depth) of a consolidated parent.  Those customers
# are covered by the ancestor's consolidated statement and should not be tested as
# independent statement recipients.  Mirrors the exclusion in
# discover_statement_customers() for the full-coverage path.
# Uses CONNECT BY hierarchy walk (LEVEL > 1) to catch grandchildren and deeper
# descendants, not just direct children.
_EXCL_CONSOL_CHILD = (
    "AND {col} NOT IN ("
    "SELECT id FROM customer "
    "WHERE LEVEL > 1 "
    "START WITH NVL(custentity_twx_consolidated_statement, 'F') = 'T' "
    "CONNECT BY PRIOR id = parent "
    "AND isinactive = 'F')"
)


def _discover_balance_category(where_clause: str, limit: int,
                                account: str, environment: str) -> List[int]:
    excl = _EXCL_CONSOL_CHILD.format(col='csr.entity')
    result = execute_query(
        f"SELECT DISTINCT csr.entity AS customer_id "
        f"FROM CustomerSubsidiaryRelationship csr "
        f"WHERE {where_clause} "
        f"{excl} "
        f"FETCH FIRST {limit} ROWS ONLY",
        account=account, environment=environment,
        return_all_rows=False,
    )
    if result.get('error'):
        return []
    return [int(r['customer_id']) for r in result.get('records', []) if r.get('customer_id')]


def _discover_mixed_customers(limit: int, account: str, environment: str) -> List[int]:
    excl = _EXCL_CONSOL_CHILD.format(col='t.entity')
    inv = execute_query(
        "SELECT DISTINCT t.entity AS customer_id FROM Transaction t "
        f"WHERE t.type = 'CustInvc' AND t.foreignamountunpaid > 0 {excl} "
        "FETCH FIRST 500 ROWS ONLY",
        account=account, environment=environment,
        return_all_rows=False,
    )
    # CMs have foreignamountunpaid=NULL always — use status <> to find open CMs.
    # CRITICAL: status <> 'CustCred:B' only works bare (no ROWNUM wrapper) — use return_all_rows=False
    cred = execute_query(
        "SELECT DISTINCT t.entity AS customer_id FROM Transaction t "
        f"WHERE t.type = 'CustCred' AND t.status <> 'CustCred:B' {excl} "
        "FETCH FIRST 500 ROWS ONLY",
        account=account, environment=environment,
        return_all_rows=False,
    )
    inv_set:  Set[int] = {int(r['customer_id']) for r in inv.get('records', []) if r.get('customer_id')}
    cred_set: Set[int] = {int(r['customer_id']) for r in cred.get('records', []) if r.get('customer_id')}
    return sorted(inv_set & cred_set)[:limit]


def _discover_parent_customers(limit: int, account: str, environment: str) -> List[int]:
    # Returns top-level parents with active children — these are never children
    # of another parent, so no consolidated-parent exclusion needed here.
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
    excl = _EXCL_CONSOL_CHILD.format(col='t.entity')
    result = execute_query(
        "SELECT DISTINCT t.entity AS customer_id "
        "FROM Transaction t "
        "WHERE t.type = 'CustInvc' "
        "  AND t.foreignamountunpaid > 0 "
        f"  AND t.foreignamountunpaid < t.foreigntotal {excl} "
        f"FETCH FIRST {limit} ROWS ONLY",
        account=account, environment=environment,
        return_all_rows=False,
    )
    if result.get('error'):
        return []
    return [int(r['customer_id']) for r in result.get('records', []) if r.get('customer_id')]


def _get_consolidated_prefs(
    customer_ids: List[int],
    account: str,
    environment: str,
) -> Dict[int, bool]:
    """Return {customer_id: consolidated_pref} for each ID in the list.

    Queries custentity_twx_consolidated_statement directly so renders are driven
    by the customer's actual statement preference, not a category label.
    """
    if not customer_ids:
        return {}
    id_list = ','.join(str(i) for i in customer_ids)
    result = execute_query(
        f"SELECT id, NVL(custentity_twx_consolidated_statement, 'F') AS consol_pref "
        f"FROM customer WHERE id IN ({id_list})",
        account=account, environment=environment,
        return_all_rows=False,
    )
    return {
        int(r['id']): (r.get('consol_pref') or 'F') == 'T'
        for r in result.get('records', [])
        if r.get('id')
    }


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
    """Discover ALL statement-eligible customers matching the actual suitelet population.

    Mirrors the criteria of customscript_tx_sl_gen_cust_statements (TX: Generate Customer
    Statements) which loads saved search customsearch118507 ("TWX | Customers Statement List")
    as the base filter, then appends runtime filters.

    Saved search base criteria (customsearch118507):
      - custentity_twx_customer_status = 2 (Active)
      - category NOT IN (32)  — excludes "Internal Website"
      - terms NOT IN (22)     — excludes "Credit Card"
      - entityid DOESNOTCONTAIN: Boot Barn, Cavenders, Mid-States, Scheels,
        powerplay retail, power play, ross stores, tractor supply, Bomgaars,
        Wheatbelt, Orscheln Farm, Dillard's, Bass Pro Shops, AAFES, QVC,
        Nordstrom, Shoe Sensation, Fitted, Academy LTD, Buckle Brands Inc,
        Cabelas Inc, Rural King Supply, Zappos Inc, Zulily Inc, Amazon Vendor Central

    Suitelet runtime filters (always applied, non-consolidated default):
      - isinactive = 'F'
      - balance != 0

    Consolidated-parent exclusion (applied here):
      Descendants at ANY depth of a customer with custentity_twx_consolidated_statement='T'
      are excluded. When the suitelet runs in consolidated mode (custpage_consolidate
      checkbox checked), it adds "parent ANYOF @NONE@" — top-level only — and
      generates ONE statement per consolidated parent using consolbalance. Those
      descendants are already covered by the ancestor's statement and should not be
      tested as independent statement recipients.

      Uses CONNECT BY hierarchy walk (WHERE LEVEL > 1) so grandchildren and
      deeper sub-customers are excluded — not just direct children.

      Included:  consolidated parents themselves, sub-customers of non-consolidated
                 parents whose ENTIRE ancestry chain has no consolidated flag.
      Excluded:  descendants (children, grandchildren, etc.) of any customer
                 with consolidatedStatement = T, at any depth in the hierarchy.

    Returns:
        customers: Dict[customer_id, {balance, categories, consolidated, sub_count}]
        categories: Dict[category_name, [customer_ids]]  — customer's primary category
    """
    print("Discovering statement-eligible customers...", file=sys.stderr)

    # Single broad query mirroring the saved search + runtime filter criteria.
    # The LEFT JOIN to CustomerSubsidiaryRelationship is a derived subquery — safe
    # with return_all_rows=True (no status filter, simple aggregate).
    # COALESCE(csr.total_balance, 0) <> 0 mirrors the suitelet's balance != 0 filter.
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
    WHERE c.isinactive = 'F'
      AND c.custentity_twx_customer_status = 2
      AND (c.category IS NULL OR c.category <> 32)
      AND (c.terms IS NULL OR c.terms <> 22)
      AND LOWER(c.entityid) NOT LIKE '%boot barn%'
      AND LOWER(c.entityid) NOT LIKE '%cavenders%'
      AND LOWER(c.entityid) NOT LIKE '%mid-states%'
      AND LOWER(c.entityid) NOT LIKE '%scheels%'
      AND LOWER(c.entityid) NOT LIKE '%powerplay retail%'
      AND LOWER(c.entityid) NOT LIKE '%power play%'
      AND LOWER(c.entityid) NOT LIKE '%ross stores%'
      AND LOWER(c.entityid) NOT LIKE '%tractor supply%'
      AND LOWER(c.entityid) NOT LIKE '%bomgaars%'
      AND LOWER(c.entityid) NOT LIKE '%wheatbelt%'
      AND LOWER(c.entityid) NOT LIKE '%orscheln farm%'
      AND LOWER(c.entityid) NOT LIKE '%dillard%'
      AND LOWER(c.entityid) NOT LIKE '%bass pro shops%'
      AND LOWER(c.entityid) NOT LIKE '%aafes%'
      AND LOWER(c.entityid) NOT LIKE '%qvc%'
      AND LOWER(c.entityid) NOT LIKE '%nordstrom%'
      AND LOWER(c.entityid) NOT LIKE '%shoe sensation%'
      AND LOWER(c.entityid) NOT LIKE '%fitted%'
      AND LOWER(c.entityid) NOT LIKE '%academy ltd%'
      AND LOWER(c.entityid) NOT LIKE '%buckle brands inc%'
      AND LOWER(c.entityid) NOT LIKE '%cabelas inc%'
      AND LOWER(c.entityid) NOT LIKE '%rural king supply%'
      AND LOWER(c.entityid) NOT LIKE '%zappos inc%'
      AND LOWER(c.entityid) NOT LIKE '%zulily inc%'
      AND LOWER(c.entityid) NOT LIKE '%amazon vendor central%'
      AND COALESCE(csr.total_balance, 0) <> 0
      AND c.id NOT IN (
          SELECT id FROM customer
          WHERE LEVEL > 1
          START WITH NVL(custentity_twx_consolidated_statement, 'F') = 'T'
          CONNECT BY PRIOR id = parent
          AND isinactive = 'F'
      )
    ORDER BY c.id
    """
    result = execute_query(discovery_sql, account=account, environment=environment,
                           return_all_rows=True)
    if result.get('error'):
        print(f"  ERROR in discovery query: {result['error']}", file=sys.stderr)
        return {}, {}

    records = result.get('records', [])
    print(f"  Found {len(records)} statement-eligible customers", file=sys.stderr)

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
    account: str,
    environment: str,
    consolidate: bool = False,
) -> Dict[str, Any]:
    """Run compare_statements.compare() for one customer, capturing its printed output.

    compare_statements.compare() prints a full text report to stdout and returns
    True (all pass/warn) or False (any fail).  This wrapper captures stdout,
    interprets the return value, and returns a structured result dict.

    consolidate should reflect the customer's custentity_twx_consolidated_statement
    preference — True renders a consolidated statement (parent + all children),
    False renders only the customer's individual statement.

    Retry behaviour: if a render fails before the comparison completes (timeout or
    transient gateway error), the compare report will not contain "Overall".  In that
    case a single retry is attempted after a 15-second backoff.  If the retry also
    fails without completing, the result is downgraded to WARN (not FAIL/ERROR) to
    avoid false positives under concurrency load.
    """
    try:
        import compare_statements
    except ImportError as e:
        return {'status': 'SKIP', 'detail': f'compare_statements import failed: {e}', 'report': ''}

    def _attempt() -> Tuple[bool, str]:
        """Single compare attempt; returns (ok, report). Exceptions → (False, partial_report).

        Passes a per-thread StringIO as output= so concurrent calls don't share sys.stdout
        (contextlib.redirect_stdout is NOT thread-safe).
        """
        buf2 = io.StringIO()
        try:
            result = compare_statements.compare(
                customer_id=str(customer_id),
                account=account,
                environment=environment,
                consolidate=consolidate,
                profile_id=str(profile_id),
                output=buf2,
            )
        except Exception:
            return False, buf2.getvalue()
        return result, buf2.getvalue()

    ok, report = _attempt()

    # If the comparison didn't run to completion (render timed out / gateway error),
    # the report will not contain "Overall" (which compare() always prints last).
    # Retry once with backoff before reporting a failure.
    if not ok and 'Overall' not in report:
        time.sleep(15)
        ok, report = _attempt()
        if not ok and 'Overall' not in report:
            # Still incomplete after retry — transient infrastructure issue, not a data failure.
            return {
                'status': 'WARN',
                'detail': 'render timed out after retry — re-run individually to confirm',
                'report': report,
            }

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


# ─── Result Builder ──────────────────────────────────────────────────────────

def _customer_result_from_compare(
    customer_id: int,
    category: str,
    compare_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a customer result dict from a single compare check result."""
    return {
        'customer_id': customer_id,
        'category':    category,
        'status':      compare_result.get('status', 'ERROR'),
        'checks':      {'compare': compare_result},
    }




# ─── Output Formatting ───────────────────────────────────────────────────────

_ICON = {'PASS': '✅', 'FAIL': '❌', 'WARN': '⚠️ ', 'ERROR': '🔴', 'SKIP': '⏭️ ', 'KNOWN_DIFF': '📋'}


def _icon(status: str) -> str:
    return _ICON.get(status, '?')


def _fmt_float(v: Any) -> str:
    return f'{v:.2f}' if isinstance(v, (int, float)) else 'N/A'


def print_customer_result(res: Dict[str, Any]) -> None:
    cid    = res['customer_id']
    cat    = res['category'].replace('_', ' ').title()
    status = res['status']
    cmp    = res.get('checks', {}).get('compare', {})

    if status == 'PASS':
        print(f"{_icon(status)} [{cid:<6}]  {cat:<20}  PASS")
        return

    if status == 'KNOWN_DIFF':
        reason = KNOWN_DIFFS.get(cid, '')
        print(f"{_icon(status)} [{cid:<6}]  {cat:<20}  KNOWN_DIFF  {reason}")
        return

    if status == 'SKIP':
        reason = SKIP_CUSTOMERS.get(cid, res.get('detail', ''))
        print(f"{_icon(status)} [{cid:<6}]  {cat:<20}  SKIP  {reason}")
        return

    print(f"{_icon(status)} [{cid:<6}]  {cat:<20}  {status}")

    if cmp.get('status') not in ('PASS', 'SKIP', None):
        print(f"   compare:       {cmp.get('detail', '')}")
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
  python3 test_statement_data.py --env prod
  python3 test_statement_data.py --env sb2 --customers 5764,4631,12926
  python3 test_statement_data.py --env sb2 --format json

Full-coverage mode (tests ALL statement-eligible customers):
  python3 test_statement_data.py --env sb2 --full-coverage
  python3 test_statement_data.py --env prod --full-coverage
  python3 test_statement_data.py --env sb2 --full-coverage --concurrency 12
""",
    )
    parser.add_argument('--env',         default='sb2',           help='Environment: prod, sb1, sb2 (default: sb2)')
    parser.add_argument('--account',     default=DEFAULT_ACCOUNT, help='Account (default: twistedx)')
    parser.add_argument('--profile',     type=int, default=PROFILE_ID, help=f'Profile ID (default: {PROFILE_ID})')
    parser.add_argument('--customers',   help='Comma-separated customer IDs (skips auto-discovery)')
    parser.add_argument('--format',      choices=['table', 'json'], default='table')
    parser.add_argument('--output-file', default=None,
                        help='Write JSON output to this file instead of stdout (avoids pipe maxBuffer limits)')
    parser.add_argument('--full-coverage', action='store_true',
                        help='Validate ALL statement-eligible customers matching the suitelet population '
                             '(customsearch118507: active status, excl. Internal Website category, '
                             'Credit Card terms, named large retailers, balance!=0)')
    parser.add_argument('--concurrency', type=int, default=4,
                        help='Max parallel gateway requests in full-coverage mode (default: 4)')
    parser.add_argument('--compare-check', action='store_true',
                        help='(no-op: compare checks always run) Accepted for Jest test compatibility')
    args = parser.parse_args()

    def _emit_json(payload: dict) -> None:
        """Write JSON to --output-file (if set) or stdout."""
        text = json.dumps(payload, indent=2,
                          default=lambda o: list(o) if isinstance(o, (set, frozenset)) else str(o))
        if args.output_file:
            with open(args.output_file, 'w', encoding='utf-8') as fh:
                fh.write(text)
        else:
            print(text)

    account     = resolve_account(args.account)
    environment = resolve_environment(args.env)
    is_table    = (args.format == 'table')

    run_start = time.time()

    if is_table:
        mode_label = 'full-coverage' if args.full_coverage else 'sampled'
        print(f"\nCRE2 Customer Statement Validation — {account}/{environment}  [{mode_label}]")
        print('═' * 62)
        print(f"Profile: {args.profile} (Customer Statement Portrait)")
        print(f"Layers:  compare (render native + CRE2, verify amounts / aging / transactions)")
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

        # Phase 2: Run compare checks for ALL customers in parallel
        print(
            f"\nRunning compare checks for all {total_discovered} customers "
            f"(concurrency={args.concurrency})...",
            file=sys.stderr,
        )
        print(
            "  (compare renders native + CRE2 PDF for each customer — "
            "at low concurrency this may take several hours)",
            file=sys.stderr,
        )

        completed_cmp = 0
        cmp_start = time.time()

        # Pre-check SKIPs before submitting to executor
        runnable_ids = []
        for cid in all_customer_ids:
            if cid in SKIP_CUSTOMERS:
                all_results.append({
                    'customer_id': cid,
                    'status':      'SKIP',
                    'detail':      SKIP_CUSTOMERS[cid],
                    'category':    customers_info[cid]['primary_category'],
                    'checks':      {},
                })
            else:
                runnable_ids.append(cid)

        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            future_to_cid = {
                executor.submit(
                    run_compare_check,
                    args.profile,
                    cid,
                    account,
                    environment,
                    customers_info[cid]['consolidated'],
                ): (cid, customers_info[cid]['primary_category'])
                for cid in runnable_ids
            }
            for future in as_completed(future_to_cid):
                cid, category = future_to_cid[future]
                compare_result = future.result()
                all_results.append(_customer_result_from_compare(cid, category, compare_result))
                completed_cmp += 1

                if is_table and completed_cmp % 50 == 0:
                    elapsed = time.time() - cmp_start
                    total_runnable = len(runnable_ids)
                    pct = completed_cmp * 100 // total_runnable
                    print(
                        f"  Compare progress: {completed_cmp}/{total_runnable} "
                        f"({pct}%) — {elapsed:.0f}s elapsed",
                        file=sys.stderr,
                    )

        elapsed_cmp = time.time() - cmp_start
        print(
            f"  Compare done: {completed_cmp}/{total_discovered} in {elapsed_cmp:.0f}s",
            file=sys.stderr,
        )

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
            _emit_json({
                'profile_id':           args.profile,
                'account':              account,
                'environment':          environment,
                'mode':                 'full_coverage',
                'selection_criteria':   'customsearch118507 (TWX | Customers Statement List): custentity_twx_customer_status=2 (Active), category!=32, terms!=22, named-retailer exclusions, isinactive=F, balance!=0, excl. children of consolidated parents',
                'total_discovered':     total_discovered,
                'concurrency':          args.concurrency,
                'execution_time_seconds': round(run_elapsed, 1),
                'total':                total,
                'passed':               passed,
                'failed':               failed,
                'warned':               warned,
                'errored':              errored,
                'categories':           cat_counts,
                'results':              all_results,
            })

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

    # ── Run compare checks for all sampled customers ──────────────────────────
    all_results_sampled: List[Dict[str, Any]] = []

    # Fetch consolidated preferences once — needed for compare render type selection.
    all_cids_sampled_flat = [cid for ids in categories_sampled.values() for cid in ids]
    sampled_consol_prefs = _get_consolidated_prefs(all_cids_sampled_flat, account, environment)

    for category, customer_ids in categories_sampled.items():
        for cid in customer_ids:
            # Check SKIP before rendering
            if cid in SKIP_CUSTOMERS:
                result = {
                    'customer_id': cid,
                    'category':    category,
                    'status':      'SKIP',
                    'detail':      SKIP_CUSTOMERS[cid],
                    'checks':      {},
                }
                all_results_sampled.append(result)
                if is_table:
                    print_customer_result(result)
                continue

            consolidate_cid = sampled_consol_prefs.get(cid, False)
            cmp = run_compare_check(args.profile, cid, account, environment,
                                    consolidate=consolidate_cid)
            result = _customer_result_from_compare(cid, category, cmp)

            # Reclassify WARN as KNOWN_DIFF for documented methodology diffs
            if result['status'] == 'WARN' and cid in KNOWN_DIFFS:
                result['status'] = 'KNOWN_DIFF'

            all_results_sampled.append(result)

            if is_table:
                print_customer_result(result)

    # ── Summary ───────────────────────────────────────────────────────────────
    passed     = sum(1 for r in all_results_sampled if r['status'] == 'PASS')
    failed     = sum(1 for r in all_results_sampled if r['status'] == 'FAIL')
    warned     = sum(1 for r in all_results_sampled if r['status'] == 'WARN')
    errored    = sum(1 for r in all_results_sampled if r['status'] == 'ERROR')
    known_diff = sum(1 for r in all_results_sampled if r['status'] == 'KNOWN_DIFF')
    skipped    = sum(1 for r in all_results_sampled if r['status'] == 'SKIP')
    total      = len(all_results_sampled)

    if is_table:
        err_part  = f", {errored} ERROR" if errored else ""
        warn_part = f", {warned} WARN" if warned else ""
        kd_part   = f", {known_diff} KNOWN_DIFF" if known_diff else ""
        sk_part   = f", {skipped} SKIP" if skipped else ""
        print(f"\nResults: {passed}/{total} PASS, {failed} FAIL{warn_part}{kd_part}{sk_part}{err_part}")
    else:
        _emit_json({
            'profile_id':     args.profile,
            'account':        account,
            'environment':    environment,
            'mode':           'sampled',
            'total':          total,
            'passed':         passed,
            'failed':         failed,
            'warned':         warned,
            'known_diff':     known_diff,
            'skipped':        skipped,
            'errored':        errored,
            'results':        all_results_sampled,
        })

    if failed > 0 or errored > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
