#!/usr/bin/env python3
"""
Render a native NetSuite customer statement via SuiteAPI RESTlet.

Calls the statementRender procedure to invoke render.statement() server-side,
saves the PDF to File Cabinet, and returns the file URL.

Usage:
    python3 render_statement.py --customer-id 7258 --env sb2
    python3 render_statement.py -c 7258 -e sb2 --consolidate --open-browser
    python3 render_statement.py -c 7258 -e sb2 --statement-date 3/4/2026 --start-date 2/4/2026

Returns:
    JSON with success, data (entityId, fileId, fileName, pdfUrl)
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

DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox2'


def resolve_account(account: str) -> str:
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def get_netsuite_base_url(account: str, environment: str) -> Optional[str]:
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)
    account_id = ACCOUNT_IDS.get(resolved_account, {}).get(resolved_env)
    if not account_id:
        return None
    return f"https://{account_id}.app.netsuite.com"


def render_statement(
    customer_id: str,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT,
    statement_date: Optional[str] = None,
    start_date: Optional[str] = None,
    consolidate: bool = False,
    open_transactions_only: bool = True,
    form_id: Optional[str] = None,
    folder_id: Optional[str] = None,
    print_mode: str = 'PDF'
) -> Dict[str, Any]:
    """
    Call SuiteAPI statementRender to generate a native NetSuite statement PDF.

    Args:
        customer_id: Customer internal ID
        account: NetSuite account (twistedx, dutyman)
        environment: Environment (prod, sb1, sb2)
        statement_date: Statement as-of date (MM/DD/YYYY); defaults to today in NS
        start_date: Statement start date (MM/DD/YYYY); defaults to NS default
        consolidate: Whether to consolidate sub-customer statements
        open_transactions_only: Whether to show only open transactions (default True)
        form_id: Custom statement form ID
        folder_id: File Cabinet folder for the output PDF
        print_mode: 'PDF' or 'HTML'

    Returns:
        Dict with success, data (entityId, fileId, fileName, pdfUrl, fullPdfUrl)
    """
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    payload: Dict[str, Any] = {
        'action': 'statementRender',
        'procedure': 'statementRender',
        'entityId': str(customer_id),
        'consolidateStatements': consolidate,
        'openTransactionsOnly': open_transactions_only,
        'printMode': print_mode,
        'netsuiteAccount': resolved_account,
        'netsuiteEnvironment': resolved_env
    }

    if statement_date:
        payload['statementDate'] = statement_date
    if start_date:
        payload['startDate'] = start_date
    if form_id:
        payload['formId'] = str(form_id)
    if folder_id:
        payload['folderId'] = str(folder_id)

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
            return json.loads(error_body)
        except (json.JSONDecodeError, ValueError):
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
        description='Render native NetSuite customer statement via SuiteAPI Gateway',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 render_statement.py --customer-id 7258 --env sb2
  python3 render_statement.py -c 7258 -e sb2 --consolidate --open-browser
  python3 render_statement.py -c 7258 -e prod --statement-date 3/4/2026 --start-date 2/4/2026
        """
    )

    parser.add_argument('--customer-id', '-c', required=True, help='Customer internal ID')
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
    parser.add_argument('--statement-date', '-d', default=None, help='Statement date MM/DD/YYYY (default: today)')
    parser.add_argument('--start-date',     '-s', default=None, help='Start date MM/DD/YYYY (default: NS default)')
    parser.add_argument('--consolidate',    action='store_true', help='Consolidate sub-customer statements')
    parser.add_argument('--all-transactions', action='store_true', help='Include all transactions (default: open only)')
    parser.add_argument('--form-id',        default=None, help='Custom statement form ID')
    parser.add_argument('--folder-id',      default=None, help='File Cabinet folder ID for output PDF (default: -15)')
    parser.add_argument('--print-mode',     default='PDF', choices=['PDF', 'HTML'], help='Output format (default: PDF)')
    parser.add_argument('--open-browser',   '-o', action='store_true', help='Open the generated PDF in browser')
    parser.add_argument('--quiet',          '-q', action='store_true', help='Only output URL on success')

    args = parser.parse_args()

    result = render_statement(
        customer_id=args.customer_id,
        account=args.account,
        environment=args.env,
        statement_date=args.statement_date,
        start_date=args.start_date,
        consolidate=args.consolidate,
        open_transactions_only=not args.all_transactions,
        form_id=args.form_id,
        folder_id=args.folder_id,
        print_mode=args.print_mode
    )

    if args.quiet:
        if result.get('success'):
            url = result.get('data', {}).get('fullPdfUrl') or result.get('data', {}).get('pdfUrl', '')
            print(url)
            sys.exit(0)
        else:
            msg = result.get('error', {}).get('message', 'Unknown error')
            print(f"Error: {msg}", file=sys.stderr)
            sys.exit(1)
    else:
        print(json.dumps(result, indent=2))

    if args.open_browser and result.get('success'):
        url = result.get('data', {}).get('fullPdfUrl') or result.get('data', {}).get('pdfUrl')
        if url:
            if url.startswith('/'):
                base_url = get_netsuite_base_url(args.account, args.env)
                if base_url:
                    url = f"{base_url}{url}"
            print(f"\nOpening PDF in browser: {url}")
            webbrowser.open(url)

    sys.exit(0 if result.get('success') else 1)


if __name__ == '__main__':
    main()
