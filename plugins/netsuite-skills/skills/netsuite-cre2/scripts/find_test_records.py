#!/usr/bin/env python3
"""
Find valid test records for CRE2 PDF testing.

Queries EDI History records to find records with actual JSON data
for a specific partner and document type combination.

Usage:
    python3 find_test_records.py --partner ATWOODS --doctype 850 --env sb2
    python3 find_test_records.py --partner AMAZONVENDORCENTRAL --doctype 824 --env sb2
    python3 find_test_records.py --doctype 810 --env sb2  # All partners with 810
    python3 find_test_records.py --list-partners --env sb2  # List all partners
    python3 find_test_records.py --list-doctypes --env sb2  # List all doc types with counts

Returns:
    JSON with record details or "No valid records found"
"""

import sys
import json
import argparse
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List

# NetSuite API Gateway endpoint
GATEWAY_URL = 'http://localhost:3001/api/suiteapi'

# Account aliases
ACCOUNT_ALIASES = {
    'twx': 'twistedx', 'twisted': 'twistedx', 'twistedx': 'twistedx',
    'dm': 'dutyman', 'duty': 'dutyman', 'dutyman': 'dutyman'
}

# Environment aliases
ENV_ALIASES = {
    'prod': 'production', 'production': 'production',
    'sb1': 'sandbox', 'sandbox': 'sandbox', 'sandbox1': 'sandbox',
    'sb2': 'sandbox2', 'sandbox2': 'sandbox2'
}

# Document type code to NetSuite ID mapping
DOCTYPE_MAP = {
    '810': 1,   # Invoice
    '850': 3,   # Purchase Order
    '855': 4,   # PO Acknowledgment
    '856': 5,   # Advance Ship Notice
    '860': 6,   # PO Change
    '846': 2,   # Inventory Advice
    '852': 11,  # Product Activity Data
    '820': 16,  # Remittance Advice
    '824': 13,  # Application Advice
    '812': 12,  # Credit/Debit Adjustment
    '864': 7,   # Text Message
}

# Reverse mapping for display
DOCTYPE_NAMES = {
    1: '810 - Invoice',
    2: '846 - Inventory Advice',
    3: '850 - Purchase Order',
    4: '855 - PO Acknowledgment',
    5: '856 - Advance Ship Notice',
    6: '860 - PO Change',
    7: '864 - Text Message',
    11: '852 - Product Activity Data',
    12: '812 - Credit/Debit Adjustment',
    13: '824 - Application Advice',
    16: '820 - Remittance Advice',
}

DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox2'


def resolve_account(account: str) -> str:
    """Resolve account alias to canonical name."""
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    """Resolve environment alias to canonical name."""
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def execute_suiteql(
    query: str,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """Execute a SuiteQL query via the API Gateway."""
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    payload = {
        'action': 'execute',
        'procedure': 'queryRun',
        'query': query,
        'netsuiteAccount': resolved_account,
        'netsuiteEnvironment': resolved_env
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            GATEWAY_URL,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Origin': 'http://localhost:3002'
            }
        )

        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode('utf-8'))

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        try:
            return json.loads(error_body)
        except json.JSONDecodeError:
            return {'success': False, 'error': {'message': f"HTTP {e.code}: {error_body}"}}
    except urllib.error.URLError as e:
        return {'success': False, 'error': {'message': f"Connection error: {e.reason}"}}
    except Exception as e:
        return {'success': False, 'error': {'message': str(e)}}


def find_test_records(
    partner_code: Optional[str] = None,
    doctype: Optional[str] = None,
    limit: int = 5,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """
    Find EDI History records with valid JSON data.

    Args:
        partner_code: Trading partner code (e.g., ATWOODS, AMAZONVENDORCENTRAL)
        doctype: Document type code (e.g., 810, 850, 855)
        limit: Maximum number of records to return
        account: NetSuite account
        environment: NetSuite environment

    Returns:
        Dict with success status and list of valid records
    """
    # Build the WHERE clause
    conditions = [
        "h.custrecord_twx_edi_history_json IS NOT NULL",
        "LENGTH(h.custrecord_twx_edi_history_json) > 10"  # Not empty or minimal
    ]

    if doctype:
        doctype_id = DOCTYPE_MAP.get(doctype)
        if doctype_id:
            conditions.append(f"h.custrecord_twx_edi_type = {doctype_id}")
        else:
            return {'success': False, 'error': {'message': f"Unknown doctype: {doctype}"}}

    if partner_code:
        # Need to join with trading partner table to filter by code
        conditions.append(f"UPPER(tp.name) LIKE '%{partner_code.upper()}%'")

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT TOP {limit}
            h.id,
            h.name,
            h.custrecord_twx_edi_type AS doc_type_id,
            tp.name AS partner_name,
            tp.id AS partner_id,
            h.created AS created_date,
            LENGTH(h.custrecord_twx_edi_history_json) AS json_length
        FROM customrecord_twx_edi_history h
        LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id
        WHERE {where_clause}
        ORDER BY h.id DESC
    """

    result = execute_suiteql(query, account, environment)

    if not result.get('success'):
        return result

    rows = result.get('data', {}).get('records', [])

    # Enhance with doctype names
    enhanced_rows = []
    for row in rows:
        doc_type_id = row.get('doc_type_id')
        row['doc_type_name'] = DOCTYPE_NAMES.get(doc_type_id, f"Type {doc_type_id}")
        enhanced_rows.append(row)

    return {
        'success': True,
        'count': len(enhanced_rows),
        'records': enhanced_rows
    }


def list_partners(
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """List all trading partners with EDI history records."""
    query = """
        SELECT
            tp.id,
            tp.name,
            COUNT(h.id) AS record_count
        FROM customrecord_twx_edi_history h
        LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id
        WHERE h.custrecord_twx_edi_history_json IS NOT NULL
        AND LENGTH(h.custrecord_twx_edi_history_json) > 10
        GROUP BY tp.id, tp.name
        ORDER BY tp.name
    """

    result = execute_suiteql(query, account, environment)

    if not result.get('success'):
        return result

    rows = result.get('data', {}).get('records', [])
    return {
        'success': True,
        'count': len(rows),
        'partners': rows
    }


def list_doctypes(
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """List all document types with counts of records that have JSON data."""
    query = """
        SELECT
            h.custrecord_twx_edi_type AS doc_type_id,
            COUNT(h.id) AS record_count
        FROM customrecord_twx_edi_history h
        WHERE h.custrecord_twx_edi_history_json IS NOT NULL
        AND LENGTH(h.custrecord_twx_edi_history_json) > 10
        GROUP BY h.custrecord_twx_edi_type
        ORDER BY h.custrecord_twx_edi_type
    """

    result = execute_suiteql(query, account, environment)

    if not result.get('success'):
        return result

    rows = result.get('data', {}).get('records', [])

    # Enhance with doctype names
    enhanced_rows = []
    for row in rows:
        doc_type_id = row.get('doc_type_id')
        row['doc_type_name'] = DOCTYPE_NAMES.get(doc_type_id, f"Type {doc_type_id}")
        enhanced_rows.append(row)

    return {
        'success': True,
        'count': len(enhanced_rows),
        'doctypes': enhanced_rows
    }


def list_partner_doctypes(
    partner_code: str,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """List all document types for a specific partner with record counts."""
    query = f"""
        SELECT
            h.custrecord_twx_edi_type AS doc_type_id,
            COUNT(h.id) AS record_count
        FROM customrecord_twx_edi_history h
        LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id
        WHERE h.custrecord_twx_edi_history_json IS NOT NULL
        AND LENGTH(h.custrecord_twx_edi_history_json) > 10
        AND UPPER(tp.name) LIKE '%{partner_code.upper()}%'
        GROUP BY h.custrecord_twx_edi_type
        ORDER BY h.custrecord_twx_edi_type
    """

    result = execute_suiteql(query, account, environment)

    if not result.get('success'):
        return result

    rows = result.get('data', {}).get('records', [])

    # Enhance with doctype names
    enhanced_rows = []
    for row in rows:
        doc_type_id = row.get('doc_type_id')
        row['doc_type_name'] = DOCTYPE_NAMES.get(doc_type_id, f"Type {doc_type_id}")
        enhanced_rows.append(row)

    return {
        'success': True,
        'partner': partner_code,
        'count': len(enhanced_rows),
        'doctypes': enhanced_rows
    }


def main():
    parser = argparse.ArgumentParser(
        description='Find valid test records for CRE2 PDF testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find test records for Atwoods 850
  python3 find_test_records.py --partner ATWOODS --doctype 850 --env sb2

  # Find all 810 records (any partner)
  python3 find_test_records.py --doctype 810 --env sb2

  # List all partners with test data
  python3 find_test_records.py --list-partners --env sb2

  # List doc types for a specific partner
  python3 find_test_records.py --partner AMAZONVENDORCENTRAL --list-doctypes --env sb2

  # Quick output - just the record ID
  python3 find_test_records.py --partner ATWOODS --doctype 850 --env sb2 --quick
        """
    )

    parser.add_argument(
        '--partner', '-p',
        help='Trading partner code (e.g., ATWOODS, AMAZONVENDORCENTRAL, ROCKY)'
    )
    parser.add_argument(
        '--doctype', '-d',
        choices=list(DOCTYPE_MAP.keys()),
        help='Document type code (810, 850, 855, etc.)'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=5,
        help='Maximum number of records to return (default: 5)'
    )
    parser.add_argument(
        '--account', '-a',
        default=DEFAULT_ACCOUNT,
        choices=['twx', 'twistedx', 'dm', 'dutyman'],
        help=f'NetSuite account (default: {DEFAULT_ACCOUNT})'
    )
    parser.add_argument(
        '--env', '-e',
        default=DEFAULT_ENVIRONMENT,
        choices=['prod', 'production', 'sb1', 'sandbox', 'sb2', 'sandbox2'],
        help=f'NetSuite environment (default: {DEFAULT_ENVIRONMENT})'
    )
    parser.add_argument(
        '--list-partners',
        action='store_true',
        help='List all trading partners with EDI data'
    )
    parser.add_argument(
        '--list-doctypes',
        action='store_true',
        help='List all document types with record counts'
    )
    parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='Quick output - only show record ID(s)'
    )

    args = parser.parse_args()

    # Handle list modes
    if args.list_partners:
        result = list_partners(args.account, args.env)
        if args.quick and result.get('success'):
            for p in result.get('partners', []):
                print(f"{p.get('name')}: {p.get('record_count')} records")
        else:
            print(json.dumps(result, indent=2))
        sys.exit(0 if result.get('success') else 1)

    if args.list_doctypes:
        if args.partner:
            result = list_partner_doctypes(args.partner, args.account, args.env)
        else:
            result = list_doctypes(args.account, args.env)

        if args.quick and result.get('success'):
            for dt in result.get('doctypes', []):
                print(f"{dt.get('doc_type_name')}: {dt.get('record_count')} records")
        else:
            print(json.dumps(result, indent=2))
        sys.exit(0 if result.get('success') else 1)

    # Find test records
    result = find_test_records(
        partner_code=args.partner,
        doctype=args.doctype,
        limit=args.limit,
        account=args.account,
        environment=args.env
    )

    if args.quick:
        if result.get('success') and result.get('records'):
            for rec in result.get('records', []):
                print(rec.get('id'))
        elif not result.get('success'):
            print(f"Error: {result.get('error', {}).get('message', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)
        else:
            print("No valid records found", file=sys.stderr)
            sys.exit(1)
    else:
        print(json.dumps(result, indent=2))

    sys.exit(0 if result.get('success') and result.get('records') else 1)


if __name__ == '__main__':
    main()
