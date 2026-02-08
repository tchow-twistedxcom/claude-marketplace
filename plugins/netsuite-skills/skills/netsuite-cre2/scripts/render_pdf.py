#!/usr/bin/env python3
"""
Render CRE2 PDF via SuiteAPI RESTlet and return external URL.

This script calls the cre2Render procedure in the NetSuite SuiteAPI RESTlet
to generate a PDF using a CRE2 profile and record ID.

Usage:
    python3 render_pdf.py --profile-id 16 --record-id 12345 --env sb2
    python3 render_pdf.py --profile-id 16 --record-id 12345 --env sb2 --open-browser
    python3 render_pdf.py --profile-id 16 --record-id 12345 --account twx --env prod

Returns:
    JSON with pdf_url, file_id, file_name
"""

import sys
import json
import argparse
import webbrowser
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

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

    Args:
        profile_id: CRE2 profile ID
        record_id: Source record ID to render
        account: NetSuite account (twistedx, dutyman)
        environment: Environment (prod, sb1, sb2)

    Returns:
        Dict with success, data (pdfUrl, fileId, fileName) or error
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

        with urllib.request.urlopen(req, timeout=60) as response:
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
                'error': {
                    'message': f"HTTP {e.code}: {error_body}",
                    'type': 'HTTP_ERROR'
                }
            }
    except urllib.error.URLError as e:
        return {
            'success': False,
            'error': {
                'message': f"Connection error: {e.reason}",
                'type': 'CONNECTION_ERROR'
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': {
                'message': str(e),
                'type': 'UNKNOWN_ERROR'
            }
        }


def main():
    parser = argparse.ArgumentParser(
        description='Render CRE2 PDF via NetSuite SuiteAPI Gateway',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 render_pdf.py --profile-id 16 --record-id 9427278 --env sb2
  python3 render_pdf.py --profile-id 116 --record-id 9427278 --env sb2 --open-browser
  python3 render_pdf.py -p 16 -r 9427278 -e sb2 --open-browser
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
        '--open-browser', '-o',
        action='store_true',
        help='Open the generated PDF in the default browser'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Only output URL on success'
    )

    args = parser.parse_args()

    result = render_pdf(
        args.profile_id,
        args.record_id,
        args.account,
        args.env
    )

    if args.quiet:
        if result.get('success'):
            full_url = result.get('data', {}).get('fullPdfUrl')
            if full_url:
                print(full_url)
                sys.exit(0)
            else:
                pdf_url = result.get('data', {}).get('pdfUrl', '')
                print(pdf_url)
                sys.exit(0)
        else:
            error_msg = result.get('error', {}).get('message', 'Unknown error')
            print(f"Error: {error_msg}", file=sys.stderr)
            sys.exit(1)
    else:
        print(json.dumps(result, indent=2))

    # Open browser if requested and we have a URL
    if args.open_browser and result.get('success'):
        full_url = result.get('data', {}).get('fullPdfUrl')
        if full_url:
            print(f"\nOpening PDF in browser: {full_url}")
            webbrowser.open(full_url)
        else:
            pdf_url = result.get('data', {}).get('pdfUrl')
            if pdf_url:
                base_url = get_netsuite_base_url(args.account, args.env)
                if base_url and pdf_url.startswith('/'):
                    full_url = f"{base_url}{pdf_url}"
                    print(f"\nOpening PDF in browser: {full_url}")
                    webbrowser.open(full_url)

    sys.exit(0 if result.get('success') else 1)


if __name__ == '__main__':
    main()
