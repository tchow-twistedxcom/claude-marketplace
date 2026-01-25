#!/usr/bin/env python3
"""
NetSuite SuiteQL Query Executor

Execute SuiteQL queries against NetSuite using the NetSuite API Gateway.
Supports multiple accounts (twistedx, dutyman) and environments (production, sandbox, sandbox2)
with OAuth authentication handled transparently by the gateway.

Multi-Account Support:
  - twistedx (twx): Twisted X account using OAuth 1.0a
  - dutyman (dm): Dutyman account using OAuth 2.0 M2M

Environment Support:
  - production (prod): Production environment
  - sandbox (sb1): Sandbox 1 environment
  - sandbox2 (sb2): Sandbox 2 environment
"""

import sys
import json
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any

# NetSuite API Gateway endpoint
GATEWAY_URL = 'http://localhost:3001/api/suiteapi'

# Account aliases
ACCOUNT_ALIASES = {
    'twx': 'twistedx',
    'twisted': 'twistedx',
    'twistedx': 'twistedx',
    'dm': 'dutyman',
    'duty': 'dutyman',
    'dutyman': 'dutyman'
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

# Default account and environment
DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox2'


def resolve_account(account: str) -> str:
    """Resolve account alias to canonical name."""
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    """Resolve environment alias to canonical name."""
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def list_accounts() -> Dict[str, Any]:
    """
    List available accounts and their environments from the gateway.

    Returns:
        Dictionary with account information
    """
    try:
        req = urllib.request.Request(
            'http://localhost:3001/api/common/accounts',
            headers={
                'Accept': 'application/json',
                'Origin': 'http://localhost:3000'
            }
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result

    except Exception as e:
        return {'error': str(e)}


def execute_query(
    query: str,
    params: Optional[List[Any]] = None,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT,
    return_all_rows: bool = False
) -> Dict[str, Any]:
    """
    Execute a SuiteQL query against NetSuite via the API Gateway.

    Args:
        query: SuiteQL query string (use ? for parameterized queries)
        params: Optional list of parameter values
        account: Account to query ('twistedx'/'twx' or 'dutyman'/'dm')
        environment: 'prod'/'production', 'sb1'/'sandbox', or 'sb2'/'sandbox2'
        return_all_rows: If True, fetch all rows with pagination

    Returns:
        Dictionary with:
        - records: List of result objects
        - count: Number of records
        - account: Resolved account name
        - environment: Resolved environment name
        - authType: Authentication type used (oauth1 or oauth2)
        - analysis: Execution stats (if return_all_rows=True)
        - error: Error message if failed
    """
    # Resolve aliases
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    # Validate account
    if resolved_account not in ['twistedx', 'dutyman']:
        return {
            'error': f"Invalid account: {account}. Valid options: twistedx (twx), dutyman (dm)",
            'records': [],
            'count': 0
        }

    # Validate environment
    if resolved_env not in ['production', 'sandbox', 'sandbox2']:
        return {
            'error': f"Invalid environment: {environment}. Valid options: production (prod), sandbox (sb1), sandbox2 (sb2)",
            'records': [],
            'count': 0
        }

    # Build request payload for gateway
    payload = {
        'action': 'queryRun',
        'procedure': 'queryRun',
        'query': query,
        'params': params or [],
        'returnAllRows': return_all_rows,
        'netsuiteAccount': resolved_account,
        'netsuiteEnvironment': resolved_env
    }

    try:
        # Prepare request to gateway
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            GATEWAY_URL,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Origin': 'http://localhost:3000'  # Required by gateway CORS validation
            }
        )

        # Execute request through gateway
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))

            # Gateway returns nested format: {success, data: {records}}
            records = []
            if result.get('success') and result.get('data'):
                records = result.get('data', {}).get('records', [])

            return {
                'records': records,
                'count': len(records),
                'account': resolved_account,
                'environment': resolved_env,
                'authType': result.get('authType', 'unknown'),
                'analysis': result.get('analysis'),
                'error': result.get('error') if not result.get('success') else None
            }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            error_json = json.loads(error_body)
            error_msg = error_json.get('error', {}).get('message', error_body)
        except:
            error_msg = error_body

        return {
            'error': f'HTTP {e.code}: {error_msg}',
            'records': [],
            'count': 0,
            'account': resolved_account,
            'environment': resolved_env
        }

    except urllib.error.URLError as e:
        return {
            'error': f'Gateway connection error: {str(e.reason)}. Is the gateway running at {GATEWAY_URL}?',
            'records': [],
            'count': 0,
            'account': resolved_account,
            'environment': resolved_env
        }

    except Exception as e:
        return {
            'error': f'Unexpected error: {str(e)}',
            'records': [],
            'count': 0,
            'account': resolved_account,
            'environment': resolved_env
        }


def format_results(results: Dict[str, Any], format_type: str = 'json', show_meta: bool = True) -> str:
    """
    Format query results for display.

    Args:
        results: Query results dictionary
        format_type: 'json', 'table', or 'csv'
        show_meta: If True, show account/environment metadata

    Returns:
        Formatted string
    """
    if results.get('error'):
        return f"ERROR: {results['error']}"

    records = results['records']
    count = results['count']

    # Build metadata header
    meta = ""
    if show_meta and format_type != 'csv':
        account = results.get('account', 'unknown')
        env = results.get('environment', 'unknown')
        auth_type = results.get('authType', 'unknown')
        meta = f"[{account}/{env}] ({auth_type}) - {count} record(s)\n"
        if format_type == 'table':
            meta += "-" * 60 + "\n"

    if count == 0:
        return meta + "No results found."

    if format_type == 'json':
        return meta + json.dumps(results, indent=2)

    elif format_type == 'table':
        # Simple table format
        if not records:
            return meta + "No results."

        # Get column names from first record
        columns = list(records[0].keys())

        # Calculate column widths (max 40 chars per column)
        col_widths = {}
        for col in columns:
            max_width = len(col)
            for record in records[:50]:
                val = str(record.get(col, ''))
                max_width = max(max_width, min(len(val), 40))
            col_widths[col] = max_width

        # Build table
        lines = [meta]

        # Header
        header = ' | '.join(col.ljust(col_widths[col])[:col_widths[col]] for col in columns)
        lines.append(header)
        lines.append('-+-'.join('-' * col_widths[col] for col in columns))

        for record in records[:50]:  # Limit to first 50 rows
            values = []
            for col in columns:
                val = str(record.get(col, ''))
                if len(val) > col_widths[col]:
                    val = val[:col_widths[col]-3] + '...'
                values.append(val.ljust(col_widths[col]))
            lines.append(' | '.join(values))

        if count > 50:
            lines.append(f"\n(Showing 50 of {count} rows)")

        return '\n'.join(lines)

    elif format_type == 'csv':
        if not records:
            return "No results."

        columns = list(records[0].keys())
        lines = [','.join(columns)]

        for record in records:
            values = [str(record.get(col, '')).replace(',', ';').replace('\n', ' ') for col in columns]
            lines.append(','.join(values))

        return '\n'.join(lines)

    return json.dumps(results, indent=2)


def print_usage():
    """Print usage information."""
    print("""NetSuite SuiteQL Query Executor

Usage: python3 query_netsuite.py <query> [options]
       python3 query_netsuite.py --list-accounts

Options:
  --account <account>    Account to query (default: twistedx)
                         Aliases: twistedx (twx), dutyman (dm)

  --env <environment>    Environment to query (default: sandbox2)
                         Aliases: production (prod), sandbox (sb1), sandbox2 (sb2)

  --params <p1,p2,...>   Comma-separated parameter values for ? placeholders

  --all-rows             Fetch all rows with automatic pagination

  --format <format>      Output format: json, table, csv (default: table)

  --list-accounts        List available accounts and environments

Examples:
  # Query Twisted X sandbox2 (default)
  python3 query_netsuite.py 'SELECT id, companyname FROM customer WHERE ROWNUM <= 5'

  # Query Dutyman production
  python3 query_netsuite.py 'SELECT id, companyname FROM customer WHERE ROWNUM <= 5' --account dm --env prod

  # Parameterized query
  python3 query_netsuite.py 'SELECT * FROM Transaction WHERE id = ?' --params 12345 --account twx --env sb2

  # JSON output for scripting
  python3 query_netsuite.py 'SELECT id FROM customer WHERE ROWNUM <= 3' --format json

  # List available accounts
  python3 query_netsuite.py --list-accounts

Accounts:
  twistedx (twx)  - Twisted X (OAuth 1.0a) - Environments: production, sandbox, sandbox2
  dutyman (dm)    - Dutyman (OAuth 2.0 M2M) - Environments: production, sandbox

Note: The NetSuite API Gateway must be running at http://localhost:3001
      Run 'docker compose up -d' in ~/NetSuiteApiGateway if needed
""")


def main():
    """CLI interface for query execution."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    # Check for --list-accounts
    if '--list-accounts' in sys.argv:
        print("Fetching account information from gateway...")
        accounts_info = list_accounts()
        if accounts_info.get('error'):
            print(f"Error: {accounts_info['error']}")
            print("\nConfigured accounts (from local config):")
            print("  twistedx (twx)  - OAuth 1.0a - production, sandbox, sandbox2")
            print("  dutyman (dm)    - OAuth 2.0  - production, sandbox")
        else:
            print(json.dumps(accounts_info, indent=2))
        sys.exit(0)

    # Check for help
    if sys.argv[1] in ['-h', '--help', 'help']:
        print_usage()
        sys.exit(0)

    # Check if first argument is an option (indicates wrong argument order)
    first_arg = sys.argv[1]
    if first_arg.startswith('-'):
        print(f"ERROR: Options must come AFTER the query, not before.")
        print(f"       You provided '{first_arg}' as the first argument.")
        print()
        print("Correct usage:")
        print("  python3 query_netsuite.py 'SELECT ...' --env sb2 --account twx")
        print()
        print("Wrong usage:")
        print("  python3 query_netsuite.py --env sb2 'SELECT ...'  # <- Options before query")
        print()
        print("Run with --help for more examples.")
        sys.exit(1)

    query = first_arg

    # Validate query looks like SQL
    query_upper = query.upper().strip()
    if not any(query_upper.startswith(kw) for kw in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH']):
        print(f"ERROR: First argument doesn't look like a SQL query: '{query[:50]}...'")
        print()
        print("The query must start with SELECT, INSERT, UPDATE, DELETE, or WITH.")
        print("Make sure to quote your query if it contains spaces:")
        print("  python3 query_netsuite.py 'SELECT id, name FROM customer'")
        print()
        print("Run with --help for more examples.")
        sys.exit(1)
    params = None
    account = DEFAULT_ACCOUNT
    environment = DEFAULT_ENVIRONMENT
    return_all_rows = False
    format_type = 'table'

    # Parse arguments
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--params' and i + 1 < len(sys.argv):
            params = sys.argv[i + 1].split(',')
            i += 2
        elif arg == '--account' and i + 1 < len(sys.argv):
            account = sys.argv[i + 1]
            i += 2
        elif arg == '--env' and i + 1 < len(sys.argv):
            environment = sys.argv[i + 1]
            i += 2
        elif arg == '--all-rows':
            return_all_rows = True
            i += 1
        elif arg == '--format' and i + 1 < len(sys.argv):
            format_type = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    # Show what we're querying
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)
    print(f"Querying {resolved_account}/{resolved_env}...\n")

    # Execute query
    results = execute_query(query, params, account, environment, return_all_rows)

    # Format and print results
    output = format_results(results, format_type)
    print(output)

    # Exit with error code if query failed
    if results.get('error'):
        sys.exit(1)


if __name__ == '__main__':
    main()
