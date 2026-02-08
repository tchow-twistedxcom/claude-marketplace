#!/usr/bin/env python3
"""
Batch Test CRE2 Profiles - Phase 3 & 4 of Implementation Plan

Phase 3: Find test records for each partner/document type combination
Phase 4: Test each profile with render_pdf.py

Usage:
  python3 batch_test_profiles.py --env sb2 --dry-run
  python3 batch_test_profiles.py --env sb2
  python3 batch_test_profiles.py --env sb2 --partner ROCKY --doc-type 810
"""

import sys
import os
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# NetSuite API Gateway endpoint
GATEWAY_URL = 'http://localhost:3001/api/suiteapi'

# Account/Environment aliases
ACCOUNT_ALIASES = {
    'twx': 'twistedx', 'twisted': 'twistedx', 'twistedx': 'twistedx',
    'dm': 'dutyman', 'duty': 'dutyman', 'dutyman': 'dutyman'
}

ENV_ALIASES = {
    'prod': 'production', 'production': 'production',
    'sb1': 'sandbox', 'sandbox': 'sandbox', 'sandbox1': 'sandbox',
    'sb2': 'sandbox2', 'sandbox2': 'sandbox2'
}

# Document type mapping (EDI Code -> NetSuite Type ID)
DOC_TYPE_IDS = {
    '810': 1,  # Invoice
    '850': 3,  # Purchase Order
    '855': 4,  # PO Acknowledgment
    '856': 5,  # Advance Ship Notice
    '860': 6,  # PO Change
}

DOC_TYPE_NAMES = {
    '810': 'Invoice',
    '850': 'Purchase Order',
    '855': 'PO Acknowledgment',
    '856': 'Advance Ship Notice',
    '860': 'PO Change',
}

# NetSuite account IDs for URL building
ACCOUNT_IDS = {
    'twistedx': {
        'production': '4138030',
        'sandbox': '4138030-sb1',
        'sandbox2': '4138030-sb2'
    },
    'dutyman': {
        'production': '3611820',
        'sandbox': '3611820-sb1',
        'sandbox2': '3611820-sb2'
    }
}

DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox2'


def resolve_account(account: str) -> str:
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def execute_query(query: str, account: str = DEFAULT_ACCOUNT, environment: str = DEFAULT_ENVIRONMENT) -> List[Dict]:
    """Execute a SuiteQL query."""
    payload = {
        'action': 'queryRun',
        'procedure': 'queryRun',
        'query': query,
        'params': [],
        'returnAllRows': True,
        'netsuiteAccount': resolve_account(account),
        'netsuiteEnvironment': resolve_environment(environment)
    }

    try:
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
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('data', {}).get('records', [])
    except Exception as e:
        print(f"Query error: {e}")
        return []


def render_pdf(profile_id: int, record_id: int, account: str, environment: str) -> Dict:
    """Call cre2Render to generate a PDF."""
    payload = {
        'action': 'cre2Render',
        'procedure': 'cre2Render',
        'profileId': str(profile_id),
        'recordId': str(record_id),
        'netsuiteAccount': resolve_account(account),
        'netsuiteEnvironment': resolve_environment(environment)
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

        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        try:
            return json.loads(error_body)
        except:
            return {'success': False, 'error': {'message': f"HTTP {e.code}: {error_body}"}}
    except Exception as e:
        return {'success': False, 'error': {'message': str(e)}}


def get_all_profiles(account: str, environment: str) -> Dict[str, Dict]:
    """Get all TWX-EDI profiles with their IDs and template IDs."""
    profiles = execute_query("""
        SELECT id, name, custrecord_pri_cre2_gen_file_tmpl_doc as template_id
        FROM customrecord_pri_cre2_profile
        WHERE name LIKE 'TWX-EDI-%'
          AND isinactive = 'F'
        ORDER BY name
    """, account, environment)

    result = {}
    for p in profiles:
        name = p['name']
        # Parse profile name: TWX-EDI-810-PARTNER-PDF
        parts = name.replace('TWX-EDI-', '').replace('-PDF', '').split('-')
        if len(parts) >= 2:
            doc_type = parts[0]
            partner = '-'.join(parts[1:])  # Handle partners with hyphens
            result[name] = {
                'id': p['id'],
                'name': name,
                'doc_type': doc_type,
                'partner': partner,
                'template_id': p.get('template_id')
            }
    return result


def get_trading_partners(account: str, environment: str) -> Dict[str, int]:
    """Get trading partner codes and their internal IDs."""
    partners = execute_query("""
        SELECT id, custrecord_twx_edi_tp_code as code, name
        FROM customrecord_twx_edi_tp
        WHERE isinactive = 'F'
    """, account, environment)

    return {p['code']: p['id'] for p in partners if p.get('code')}


def get_trading_partner_name_map(account: str, environment: str) -> Dict[int, str]:
    """Get trading partner ID to name mapping."""
    partners = execute_query("""
        SELECT id, name FROM customrecord_twx_edi_tp
    """, account, environment)
    return {p['id']: p['name'] for p in partners}


def normalize_partner_code(name: str) -> str:
    """Normalize partner name to profile code format."""
    # Map of known partner names to profile codes
    name_to_code = {
        'cavenders': 'CAVENDERS',
        'boot barn': 'BOOTBARN',
        'rocky brands': 'ROCKY',
        'bomgaars': 'BOMGAARS',
        'scheels': 'SCHEELS',
        'rural king': 'RURALKING',
        'sheplers': 'SHEPLERS',
        'murdochs': 'MURDOCHS',
        'houser shoes': 'HOUSER',
        'atwoods': 'ATWOOD',
        'shoe sensation': 'SHOESENSATION',
        'academy': 'ACADEMY',
        'runnings': 'RUNNINGS',
        'next point logistics': 'NXTP',
        'buchheit': 'BUCHHEIT',
        'family center farm & home': 'FAMILY',
        'mid-states distributing': 'MIDSYORK',
        'galls': 'GALLS',
        'starr western wear': 'STARR',
        'd&b supply': 'DBS',
        'deal rise': 'DEALRISE',
        'shoe carnival': 'SHOECARNIVAL',
        'super shoes': 'SUPERSHOES',
        'sun & ski sports': 'SUNANDSKI',
        'zulily': 'ZULILY',
        "lowe's": 'LOWES',
        'coastal farm & ranch': 'COASTAL',
        'safety wearhouse': 'SAFETY',
    }
    normalized = name.lower().strip()
    return name_to_code.get(normalized, name.upper().replace(' ', '').replace('-', '').replace('&', ''))


def find_test_records(account: str, environment: str) -> Dict[Tuple[str, str], int]:
    """
    Find test records for each partner/doc_type combination.
    Returns dict of (partner_code, doc_type) -> record_id
    """
    # Get partner name mapping
    partner_names = get_trading_partner_name_map(account, environment)

    # Get all EDI history records with JSON data
    records = execute_query("""
        SELECT
            h.id,
            h.custrecord_twx_edi_type as doc_type_id,
            h.custrecord_twx_eth_edi_tp as tp_id
        FROM customrecord_twx_edi_history h
        WHERE h.custrecord_twx_edi_history_json IS NOT NULL
        ORDER BY h.id DESC
    """, account, environment)

    # Reverse map doc type IDs to codes
    id_to_code = {v: k for k, v in DOC_TYPE_IDS.items()}

    # Build mapping - first record found for each combination
    result = {}
    for r in records:
        doc_type_id = r.get('doc_type_id')
        tp_id = r.get('tp_id')

        if doc_type_id and tp_id:
            doc_type = id_to_code.get(doc_type_id)
            partner_name = partner_names.get(tp_id)

            if doc_type and partner_name:
                partner_code = normalize_partner_code(partner_name)
                key = (partner_code, doc_type)
                if key not in result:
                    result[key] = r['id']

    return result


def test_single_profile(profile: Dict, test_records: Dict, fallback_records: Dict, account: str, environment: str) -> Dict:
    """Test a single profile and return results."""
    profile_id = profile['id']
    profile_name = profile['name']
    partner = profile['partner']
    doc_type = profile['doc_type']

    # Find matching test record
    key = (partner, doc_type)
    record_id = test_records.get(key)
    used_fallback = False

    if not record_id:
        # Try with a fallback record for this doc type
        record_id = fallback_records.get(doc_type)
        used_fallback = True

    if not record_id:
        return {
            'profile_id': profile_id,
            'profile_name': profile_name,
            'status': 'SKIPPED',
            'reason': f'No test record found for {partner}/{doc_type}'
        }

    # Render PDF
    result = render_pdf(profile_id, record_id, account, environment)

    if result.get('success'):
        return {
            'profile_id': profile_id,
            'profile_name': profile_name,
            'record_id': record_id,
            'status': 'SUCCESS',
            'file_id': result.get('data', {}).get('fileId'),
            'file_name': result.get('data', {}).get('fileName'),
            'pdf_url': result.get('data', {}).get('pdfUrl')
        }
    else:
        error_msg = result.get('error', {}).get('message', 'Unknown error')
        return {
            'profile_id': profile_id,
            'profile_name': profile_name,
            'record_id': record_id,
            'status': 'FAILED',
            'error': error_msg
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Batch test CRE2 profiles')
    parser.add_argument('--env', default='sandbox2', help='Environment (sb2, prod)')
    parser.add_argument('--account', default='twistedx', help='Account (twx, dm)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without testing')
    parser.add_argument('--partner', help='Test single partner only')
    parser.add_argument('--doc-type', help='Test single document type only (810, 850, etc.)')
    parser.add_argument('--parallel', type=int, default=5, help='Number of parallel tests')
    parser.add_argument('--output', help='Output file for results (JSON)')
    args = parser.parse_args()

    account = args.account
    environment = args.env

    print(f"\n{'='*70}")
    print(f"CRE2 Profile Batch Tester - Phase 3 & 4")
    print(f"{'='*70}")
    print(f"Account: {resolve_account(account)}")
    print(f"Environment: {resolve_environment(environment)}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Parallel workers: {args.parallel}")
    print(f"{'='*70}\n")

    # Phase 3: Find test records
    print("Phase 3: Finding test records...")
    test_records = find_test_records(account, environment)
    print(f"  Found {len(test_records)} partner/doc-type combinations with test data\n")

    # Show distribution
    by_doc_type = {}
    for (partner, doc_type), record_id in test_records.items():
        if doc_type not in by_doc_type:
            by_doc_type[doc_type] = []
        by_doc_type[doc_type].append(partner)

    print("  Test record distribution:")
    for doc_type in ['810', '850', '855', '856', '860']:
        partners = by_doc_type.get(doc_type, [])
        print(f"    {doc_type}: {len(partners)} partners")
    print()

    # Create fallback records (one per doc type)
    fallback_records = {}
    for (partner, doc_type), record_id in test_records.items():
        if doc_type not in fallback_records:
            fallback_records[doc_type] = record_id

    print("  Fallback records (for profiles without specific test data):")
    for doc_type in ['810', '850', '855', '856', '860']:
        if doc_type in fallback_records:
            print(f"    {doc_type}: Record {fallback_records[doc_type]}")
        else:
            print(f"    {doc_type}: NO FALLBACK")
    print()

    # Get all profiles
    print("Loading profiles...")
    profiles = get_all_profiles(account, environment)
    print(f"  Found {len(profiles)} profiles\n")

    # Filter if requested
    filtered_profiles = []
    for name, profile in profiles.items():
        if args.partner and profile['partner'] != args.partner.upper():
            continue
        if args.doc_type and profile['doc_type'] != args.doc_type:
            continue
        filtered_profiles.append(profile)

    print(f"Profiles to test: {len(filtered_profiles)}\n")

    if args.dry_run:
        print("DRY RUN - Would test these profiles:\n")
        for p in filtered_profiles[:20]:
            key = (p['partner'], p['doc_type'])
            record_id = test_records.get(key, 'NO RECORD')
            print(f"  {p['name']:40} → Record: {record_id}")
        if len(filtered_profiles) > 20:
            print(f"  ... and {len(filtered_profiles) - 20} more")
        return

    # Phase 4: Test each profile
    print(f"Phase 4: Testing {len(filtered_profiles)} profiles...\n")

    results = {
        'timestamp': datetime.now().isoformat(),
        'account': resolve_account(account),
        'environment': resolve_environment(environment),
        'total_profiles': len(filtered_profiles),
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'details': []
    }

    # Test profiles with progress tracking
    completed = 0
    for profile in filtered_profiles:
        result = test_single_profile(profile, test_records, fallback_records, account, environment)
        results['details'].append(result)

        status = result['status']
        if status == 'SUCCESS':
            results['success'] += 1
            symbol = '✓'
        elif status == 'FAILED':
            results['failed'] += 1
            symbol = '✗'
        else:
            results['skipped'] += 1
            symbol = '○'

        completed += 1
        print(f"  [{completed:3}/{len(filtered_profiles)}] {symbol} {result['profile_name']}")

        if status == 'FAILED':
            print(f"           Error: {result.get('error', 'Unknown')}")

        time.sleep(0.3)  # Rate limiting

    # Summary
    print(f"\n{'='*70}")
    print("TESTING COMPLETE")
    print(f"{'='*70}")
    print(f"Total: {len(filtered_profiles)}")
    print(f"Success: {results['success']}")
    print(f"Failed: {results['failed']}")
    print(f"Skipped: {results['skipped']}")
    print(f"{'='*70}\n")

    # Save results
    output_file = args.output or f"/tmp/cre2_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {output_file}")

    # Return exit code based on results
    if results['failed'] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
