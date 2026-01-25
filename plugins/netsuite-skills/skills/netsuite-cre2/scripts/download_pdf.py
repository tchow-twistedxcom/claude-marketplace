#!/usr/bin/env python3
"""
Render and Open CRE2 PDF.

This script renders a CRE2 PDF and opens it in your default browser for visual verification.
The PDF is generated in NetSuite and accessed via an authenticated URL.

Usage:
    python3 download_pdf.py --profile-id 1116 --record-id 7470800 --env sb2
    python3 download_pdf.py --profile-id 1116 --record-id 7470800 --env sb2 --open

Note: Opening the PDF requires an active NetSuite session in your browser.
      Log into NetSuite first, then run with --open to view the PDF.
"""

import sys
import json
import argparse
import webbrowser
import urllib.request
import urllib.error
from typing import Dict, Any

# NetSuite API Gateway endpoint
GATEWAY_URL = 'http://localhost:3001/api/suiteapi'

# Account aliases
ACCOUNT_ALIASES = {
    'twx': 'twistedx', 'twisted': 'twistedx', 'twistedx': 'twistedx',
    'dm': 'dutyman', 'duty': 'dutyman', 'dutyman': 'dutyman'
}

# Environment aliases
ENV_ALIASES = {
    'prod': 'production',
    'production': 'production',
    'sb1': 'sandbox',
    'sandbox': 'sandbox',
    'sandbox1': 'sandbox',
    'sb2': 'sandbox2',
    'sandbox2': 'sandbox2'
}

# NetSuite account IDs for URL building (use dashes, not underscores)
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

# Default settings
DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox2'


def resolve_account(account: str) -> str:
    """Resolve account alias to canonical name."""
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    """Resolve environment alias to canonical name."""
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def get_netsuite_base_url(account: str, environment: str) -> str:
    """Get the NetSuite base URL for a given account and environment."""
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    account_id = ACCOUNT_IDS.get(resolved_account, {}).get(resolved_env)
    if not account_id:
        return None

    return f"https://{account_id}.app.netsuite.com"


def render_pdf(
    profile_id: str,
    record_id: str,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """
    Call SuiteAPI with cre2Render action to generate a PDF.
    Returns file ID, URL, and name for the generated PDF.
    """
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    payload = {
        'action': 'cre2Render',
        'procedure': 'cre2Render',
        'profileId': profile_id,
        'recordId': record_id,
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

        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))

            # Build full URL if we have a relative pdfUrl
            if result.get('success') and result.get('data', {}).get('pdfUrl'):
                pdf_url = result['data']['pdfUrl']
                if pdf_url.startswith('/'):
                    base_url = get_netsuite_base_url(account, environment)
                    if base_url:
                        result['data']['fullPdfUrl'] = f"{base_url}{pdf_url}"

            return result

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        try:
            error_json = json.loads(error_body)
            return error_json
        except json.JSONDecodeError:
            return {
                'success': False,
                'error': {'message': f"HTTP {e.code}: {error_body}", 'type': 'HTTP_ERROR'}
            }
    except urllib.error.URLError as e:
        return {
            'success': False,
            'error': {'message': f"Connection error: {e.reason}", 'type': 'CONNECTION_ERROR'}
        }
    except Exception as e:
        return {
            'success': False,
            'error': {'message': str(e), 'type': 'UNKNOWN_ERROR'}
        }


def main():
    parser = argparse.ArgumentParser(
        description='Render CRE2 PDF and open in browser for visual verification',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Render PDF and show URL
  python3 download_pdf.py --profile-id 1116 --record-id 7470800 --env sb2

  # Render and open in browser immediately
  python3 download_pdf.py --profile-id 1116 --record-id 7470800 --env sb2 --open

  # Use short flags
  python3 download_pdf.py -p 1116 -r 7470800 -e sb2 --open

Note: Opening the PDF in browser requires an active NetSuite session.
      Log into NetSuite in your browser first, then use --open to view the PDF.
        """
    )

    parser.add_argument(
        '--profile-id', '-p',
        required=True,
        help='CRE2 profile ID'
    )
    parser.add_argument(
        '--record-id', '-r',
        required=True,
        help='Source record ID to render'
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
        '--open',
        action='store_true',
        dest='open_browser',
        help='Open the PDF in default browser (requires NetSuite login)'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Only output URL on success'
    )

    args = parser.parse_args()

    resolved_account = resolve_account(args.account)
    resolved_env = resolve_environment(args.env)

    # Render the PDF
    if not args.quiet:
        print(f"Rendering PDF with profile {args.profile_id} for record {args.record_id}...")
        print(f"  Account: {resolved_account}")
        print(f"  Environment: {resolved_env}")

    result = render_pdf(
        args.profile_id,
        args.record_id,
        args.account,
        args.env
    )

    if not result.get('success'):
        error_msg = result.get('error', {}).get('message', 'Unknown error')
        print(f"ERROR: Failed to render PDF - {error_msg}", file=sys.stderr)
        sys.exit(1)

    data = result.get('data', {})
    file_id = data.get('fileId')
    file_name = data.get('fileName', 'unknown.pdf')
    full_url = data.get('fullPdfUrl')
    pdf_url = data.get('pdfUrl')

    if args.quiet:
        if full_url:
            print(full_url)
        else:
            print(pdf_url or '')
        sys.exit(0)

    print(f"\nSUCCESS: PDF rendered")
    print(f"  File Name: {file_name}")
    print(f"  File ID: {file_id}")
    if full_url:
        print(f"  URL: {full_url}")
    elif pdf_url:
        base_url = get_netsuite_base_url(args.account, args.env)
        print(f"  URL: {base_url}{pdf_url}" if base_url else f"  URL: {pdf_url}")

    # Open in browser if requested
    if args.open_browser and full_url:
        print(f"\nOpening PDF in browser...")
        print("  (Make sure you're logged into NetSuite)")
        webbrowser.open(full_url)
    elif args.open_browser:
        print("\nWARNING: Could not build full URL to open in browser")
        if pdf_url:
            print(f"  Relative URL: {pdf_url}")

    sys.exit(0)


if __name__ == '__main__':
    main()
