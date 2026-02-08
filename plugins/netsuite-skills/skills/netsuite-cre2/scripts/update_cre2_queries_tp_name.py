#!/usr/bin/env python3
"""
Update all CRE2 query records to include tp.name AS tp_name in the data source query.

This fixes the issue where 810 PDFs show billing name instead of trading partner name.

Usage:
    python3 update_cre2_queries_tp_name.py --env sb2
    python3 update_cre2_queries_tp_name.py --env sb2 --dry-run
"""

import sys
import json
import urllib.request
import urllib.error
from typing import Dict, List, Any
import argparse

GATEWAY_URL = 'http://localhost:3001/api/suiteapi'

# The corrected data source query with tp.name included
NEW_QUERY = """SELECT h.id, h.name, h.custrecord_twx_edi_history_json AS edi_json, h.custrecord_twx_eth_edi_tp AS trading_partner, h.custrecord_twx_edi_type AS doc_type, h.custrecord_twx_edi_history_status AS status, h.created AS created_date, tp.custrecord_twx_edi_tp_logo AS tp_logo_id, tp.name AS tp_name FROM customrecord_twx_edi_history h LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id WHERE h.id = ${record.id}"""

# Old query pattern (without tp.name)
OLD_QUERY_PATTERN = "SELECT h.id, h.name, h.custrecord_twx_edi_history_json AS edi_json"

# Account/env resolution
ACCOUNT_ALIASES = {
    'twx': 'twistedx', 'twisted': 'twistedx', 'twistedx': 'twistedx',
    'dm': 'dutyman', 'duty': 'dutyman', 'dutyman': 'dutyman'
}

ENV_ALIASES = {
    'prod': 'production', 'production': 'production',
    'sb1': 'sandbox', 'sandbox': 'sandbox', 'sandbox1': 'sandbox',
    'sb2': 'sandbox2', 'sandbox2': 'sandbox2'
}


def resolve_account(account: str) -> str:
    return ACCOUNT_ALIASES.get(account.lower(), account)


def resolve_environment(env: str) -> str:
    return ENV_ALIASES.get(env.lower(), env)


def execute_query(query: str, account: str, environment: str) -> List[Dict]:
    """Execute a SuiteQL query and return results."""
    payload = {
        'action': 'queryRun',
        'procedure': 'queryRun',
        'query': query,
        'params': [],
        'returnAllRows': True,
        'netsuiteAccount': resolve_account(account),
        'netsuiteEnvironment': resolve_environment(environment)
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        GATEWAY_URL,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Origin': 'http://localhost:3000'
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('success'):
                # Try different response formats
                if result.get('rows'):
                    return result['rows']
                if result.get('data', {}).get('records'):
                    return result['data']['records']
            return []
    except Exception as e:
        print(f"Query error: {e}")
        return []


def update_record(record_type: str, record_id: int, fields: Dict, account: str, environment: str) -> Dict:
    """Update a NetSuite record."""
    payload = {
        'action': 'execute',
        'procedure': 'twxUpsertRecord',
        'type': record_type,
        'id': record_id,
        'fields': fields,
        'netsuiteAccount': resolve_account(account),
        'netsuiteEnvironment': resolve_environment(environment)
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        GATEWAY_URL,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Origin': 'http://localhost:3000'
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_cre2_queries(account: str, environment: str) -> List[Dict]:
    """Get all CRE2 query records that need updating."""
    # Get queries linked to TWX-EDI profiles
    query = """
    SELECT
        q.id,
        q.name as query_name,
        p.id as profile_id,
        p.name as profile_name
    FROM customrecord_pri_cre2_query q
    LEFT JOIN customrecord_pri_cre2_profile p ON q.custrecord_pri_cre2q_parent = p.id
    WHERE p.name LIKE 'TWX-EDI-%'
    ORDER BY p.name
    """
    return execute_query(query, account, environment)


def main():
    parser = argparse.ArgumentParser(description='Update CRE2 queries to include tp.name')
    parser.add_argument('--env', default='sb2', help='Environment: prod, sb1, sb2')
    parser.add_argument('--account', default='twx', help='Account: twx, dm')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated')
    args = parser.parse_args()

    print(f"\nUpdating CRE2 queries to include tp.name AS tp_name...")
    print(f"Environment: {args.account}/{args.env}")
    print(f"Dry run: {args.dry_run}\n")

    # Get all CRE2 queries linked to EDI profiles
    queries = get_cre2_queries(args.account, args.env)

    if not queries:
        print("No CRE2 queries found for TWX-EDI profiles.")
        return

    print(f"Found {len(queries)} CRE2 query record(s)\n")

    updated = 0
    failed = 0

    for q in queries:
        query_id = q.get('id')
        profile_name = q.get('profile_name', 'Unknown')

        if args.dry_run:
            print(f"[DRY RUN] Would update query {query_id} for {profile_name}")
            updated += 1
        else:
            print(f"Updating query {query_id} for {profile_name}...", end=' ')

            result = update_record(
                'customrecord_pri_cre2_query',
                query_id,
                {'custrecord_pri_cre2q_query': NEW_QUERY},
                args.account,
                args.env
            )

            if result.get('success'):
                print("OK")
                updated += 1
            else:
                print(f"FAILED: {result.get('error', 'Unknown error')}")
                failed += 1

    print(f"\n{'=' * 50}")
    print(f"Updated: {updated}")
    if failed:
        print(f"Failed: {failed}")
    print(f"\nNew query includes: tp.name AS tp_name")


if __name__ == '__main__':
    main()
