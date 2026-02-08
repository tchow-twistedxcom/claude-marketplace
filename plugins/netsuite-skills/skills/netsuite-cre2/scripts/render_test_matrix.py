#!/usr/bin/env python3
"""
Render CRE2 PDFs for a test matrix of profile:record pairs.

Batch-renders multiple PDFs and reports success/failure for each.
Useful for verifying template changes across multiple trading partners.

Usage:
    python3 render_test_matrix.py --records "16:9425522,721:9415784,617:9415483" --env sb2
    python3 render_test_matrix.py --records "16:9425522" --env sb2 --open-browser
    python3 render_test_matrix.py --doc-type 850 --env sb2  # Uses built-in test matrix

Built-in test matrix (3 DPI tiers per doc type):
    850: Runnings (200 DPI), Amazon (2000 DPI), Cavenders (2000 DPI)
"""

import sys
import json
import argparse
import webbrowser
import urllib.request
import urllib.error
from typing import List, Tuple, Dict, Any

# NetSuite API Gateway endpoint
GATEWAY_URL = 'http://localhost:3001/api/suiteapi'

# Account/environment config (shared with render_pdf.py)
ACCOUNT_IDS = {
    'twistedx': {
        'production': '4138030',
        'sandbox': '4138030-sb1',
        'sandbox2': '4138030-sb2'
    }
}

ENV_ALIASES = {
    'prod': 'production', 'production': 'production',
    'sb1': 'sandbox', 'sandbox': 'sandbox',
    'sb2': 'sandbox2', 'sandbox2': 'sandbox2'
}

# Built-in test matrices by doc type
# Format: list of (profile_id, record_id, label)
TEST_MATRICES = {
    '850': [
        ('16', '9425522', 'Runnings (DPI 200)'),
        ('721', '9415784', 'Amazon Vendor Central (DPI 2000)'),
        ('617', '9415483', 'Cavenders (DPI 2000)'),
    ],
    # Add more doc types as consolidated templates are created:
    # '810': [
    #     ('17', '<record_id>', 'Runnings (DPI 200)'),
    #     ('...', '<record_id>', 'Amazon (DPI 2000)'),
    # ],
}


def resolve_env(env: str) -> str:
    return ENV_ALIASES.get(env.lower(), env.lower())


def get_base_url(env: str) -> str:
    account_id = ACCOUNT_IDS.get('twistedx', {}).get(resolve_env(env))
    if account_id:
        return f"https://{account_id}.app.netsuite.com"
    return None


def render_single(profile_id: str, record_id: str, env: str) -> Dict[str, Any]:
    """Render a single PDF and return the result."""
    payload = {
        'action': 'cre2Render',
        'procedure': 'cre2Render',
        'profileId': profile_id,
        'recordId': record_id,
        'netsuiteAccount': 'twistedx',
        'netsuiteEnvironment': resolve_env(env)
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

            if result.get('success') and result.get('data', {}).get('pdfUrl'):
                pdf_url = result['data']['pdfUrl']
                if pdf_url.startswith('/'):
                    base_url = get_base_url(env)
                    if base_url:
                        result['data']['fullPdfUrl'] = f"{base_url}{pdf_url}"

            return result

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        try:
            return json.loads(error_body)
        except json.JSONDecodeError:
            return {'success': False, 'error': {'message': f"HTTP {e.code}: {error_body}"}}
    except Exception as e:
        return {'success': False, 'error': {'message': str(e)}}


def parse_records(records_str: str) -> List[Tuple[str, str, str]]:
    """Parse 'profile:record,profile:record' into list of (profile, record, label)."""
    pairs = []
    for pair in records_str.split(','):
        pair = pair.strip()
        if ':' not in pair:
            print(f"Warning: Skipping invalid pair '{pair}' (expected profile:record)", file=sys.stderr)
            continue
        profile_id, record_id = pair.split(':', 1)
        pairs.append((profile_id.strip(), record_id.strip(), f"Profile {profile_id.strip()}"))
    return pairs


def main():
    parser = argparse.ArgumentParser(
        description='Render CRE2 PDFs for a test matrix',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 render_test_matrix.py --records "16:9425522,721:9415784,617:9415483" --env sb2
  python3 render_test_matrix.py --doc-type 850 --env sb2
  python3 render_test_matrix.py --doc-type 850 --env sb2 --open-browser
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--records', '-r', help='Comma-separated profile:record pairs')
    group.add_argument('--doc-type', '-d', choices=list(TEST_MATRICES.keys()),
                       help='Use built-in test matrix for doc type')

    parser.add_argument('--env', '-e', default='sandbox2',
                       choices=['prod', 'sb1', 'sb2', 'sandbox', 'sandbox2'],
                       help='NetSuite environment (default: sandbox2)')
    parser.add_argument('--open-browser', '-o', action='store_true',
                       help='Open each successful PDF in browser')

    args = parser.parse_args()

    # Build test matrix
    if args.doc_type:
        matrix = TEST_MATRICES[args.doc_type]
        print(f"Using built-in test matrix for {args.doc_type} ({len(matrix)} records)")
    else:
        matrix = parse_records(args.records)

    if not matrix:
        print("Error: No valid test records", file=sys.stderr)
        sys.exit(1)

    # Render each
    results = []
    print(f"\n{'='*70}")
    print(f"CRE2 Test Matrix - {len(matrix)} renders")
    print(f"Environment: {args.env}")
    print(f"{'='*70}\n")

    for i, (profile_id, record_id, label) in enumerate(matrix, 1):
        print(f"[{i}/{len(matrix)}] Rendering {label} (profile={profile_id}, record={record_id})...", end=' ', flush=True)

        result = render_single(profile_id, record_id, args.env)
        success = result.get('success', False)

        if success:
            duration = result.get('duration', '?')
            file_name = result.get('data', {}).get('fileName', '?')
            full_url = result.get('data', {}).get('fullPdfUrl', '')
            print(f"✅ {file_name} ({duration}ms)")

            if args.open_browser and full_url:
                webbrowser.open(full_url)

            results.append({
                'label': label, 'profile': profile_id, 'record': record_id,
                'success': True, 'url': full_url, 'duration': duration
            })
        else:
            error_msg = result.get('error', {}).get('message', 'Unknown error')
            print(f"❌ {error_msg}")
            results.append({
                'label': label, 'profile': profile_id, 'record': record_id,
                'success': False, 'error': error_msg
            })

    # Summary
    passed = sum(1 for r in results if r['success'])
    failed = len(results) - passed

    print(f"\n{'='*70}")
    print(f"Results: {passed}/{len(results)} passed", end='')
    if failed:
        print(f", {failed} FAILED")
    else:
        print(" ✅ All passed")
    print(f"{'='*70}")

    if failed:
        print("\nFailed renders:")
        for r in results:
            if not r['success']:
                print(f"  ❌ {r['label']} (profile={r['profile']}, record={r['record']}): {r['error']}")

    # Output URLs for successful renders
    successful = [r for r in results if r['success'] and r.get('url')]
    if successful:
        print("\nPDF URLs:")
        for r in successful:
            print(f"  {r['label']}: {r['url']}")

    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
