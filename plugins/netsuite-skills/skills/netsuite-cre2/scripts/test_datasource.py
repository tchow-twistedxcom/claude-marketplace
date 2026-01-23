#!/usr/bin/env python3
"""
NetSuite CRE 2.0 Data Source Tester

Test CRE2 profile data sources with a specific record and show detailed output.
Useful for debugging template rendering issues by verifying query results.

Usage:
  python3 test_datasource.py <profile_id> <record_id> --env sb2
  python3 test_datasource.py <profile_id> <record_id> --env sb2 --format json
  python3 test_datasource.py <profile_id> <record_id> --env sb2 --show-data
"""

import sys
import json
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
    'prod': 'production',
    'production': 'production',
    'sb1': 'sandbox',
    'sandbox': 'sandbox',
    'sandbox1': 'sandbox',
    'sb2': 'sandbox2',
    'sandbox2': 'sandbox2'
}

DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox2'


def resolve_account(account: str) -> str:
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def execute_query(
    query: str,
    params: Optional[List[Any]] = None,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """Execute a SuiteQL query via the API Gateway."""
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    payload = {
        'action': 'queryRun',
        'procedure': 'queryRun',
        'query': query,
        'params': params or [],
        'returnAllRows': True,
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
                'Origin': 'http://localhost:3000'
            }
        )

        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))

            records = []
            if result.get('success') and result.get('data'):
                records = result.get('data', {}).get('records', [])

            return {
                'records': records,
                'count': len(records),
                'error': result.get('error') if not result.get('success') else None
            }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            error_json = json.loads(error_body)
            error_msg = error_json.get('error', {}).get('message', error_body)
        except:
            error_msg = error_body
        return {'error': f'HTTP {e.code}: {error_msg}', 'records': [], 'count': 0}

    except urllib.error.URLError as e:
        return {'error': f'Gateway connection error: {str(e.reason)}', 'records': [], 'count': 0}

    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}', 'records': [], 'count': 0}


def get_profile_info(profile_id: int, account: str, environment: str) -> Optional[Dict]:
    """Get profile basic info."""
    query = """
    SELECT
        p.id,
        p.name,
        BUILTIN.DF(p.custrecord_pri_cre2_rectype) AS record_type
    FROM customrecord_pri_cre2_profile p
    WHERE p.id = ?
    """
    result = execute_query(query, params=[profile_id], account=account, environment=environment)
    if result.get('records'):
        return result['records'][0]
    return None


def get_datasources(profile_id: int, account: str, environment: str) -> List[Dict]:
    """Get data sources for a profile."""
    query = """
    SELECT
        q.id,
        q.name,
        q.custrecord_pri_cre2q_query AS query_sql,
        q.custrecord_pri_cre2q_paged AS paged,
        q.custrecord_pri_cre2q_single_record_json AS single_record_json
    FROM customrecord_pri_cre2_query q
    WHERE q.custrecord_pri_cre2q_parent = ?
    ORDER BY q.name
    """

    results = execute_query(query, params=[profile_id], account=account, environment=environment)
    if results.get('error') or results['count'] == 0:
        return []

    return results['records']


def format_value(value: Any, max_length: int = 100) -> str:
    """Format a value for display, truncating if necessary."""
    if value is None:
        return 'null'

    str_val = str(value)

    # Check if it's JSON
    if str_val.startswith('{') or str_val.startswith('['):
        try:
            parsed = json.loads(str_val)
            # Pretty print but truncate
            formatted = json.dumps(parsed, indent=2)
            if len(formatted) > max_length:
                return formatted[:max_length] + '... (truncated)'
            return formatted
        except:
            pass

    if len(str_val) > max_length:
        return str_val[:max_length] + '...'
    return str_val


def test_datasource(
    profile_id: int,
    record_id: int,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT,
    output_format: str = 'table',
    show_data: bool = False
) -> Dict[str, Any]:
    """
    Test data sources for a profile with a specific record.

    Args:
        profile_id: CRE2 profile internal ID
        record_id: Target record internal ID
        account: NetSuite account
        environment: NetSuite environment
        output_format: 'table' or 'json'
        show_data: Whether to show full data values

    Returns:
        Dictionary with test results
    """
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    results = {
        'profile_id': profile_id,
        'record_id': record_id,
        'account': resolved_account,
        'environment': resolved_env,
        'datasources': []
    }

    # Get profile info
    profile = get_profile_info(profile_id, account, environment)
    if not profile:
        results['error'] = f'Profile {profile_id} not found'
        return results

    results['profile_name'] = profile.get('name', '')
    results['record_type'] = profile.get('record_type', '')

    # Get data sources
    datasources = get_datasources(profile_id, account, environment)
    if not datasources:
        results['error'] = 'No data sources configured for this profile'
        return results

    # Test each data source
    for ds in datasources:
        ds_result = {
            'name': ds.get('name', 'Unnamed'),
            'query_id': ds.get('id'),
            'paged': ds.get('paged') == 'T',
            'single_record_json': ds.get('single_record_json') == 'T',
            'success': False,
            'row_count': 0,
            'fields': [],
            'data': []
        }

        query_sql = ds.get('query_sql')
        if not query_sql:
            ds_result['error'] = 'No SQL query configured'
            results['datasources'].append(ds_result)
            continue

        # Replace ${record.id} with actual record ID
        test_sql = query_sql.replace('${record.id}', str(record_id))
        ds_result['sql'] = test_sql

        # Execute the query
        query_result = execute_query(test_sql, account=account, environment=environment)

        if query_result.get('error'):
            ds_result['error'] = str(query_result['error'])
            results['datasources'].append(ds_result)
            continue

        ds_result['success'] = True
        ds_result['row_count'] = query_result['count']

        if query_result['records']:
            ds_result['fields'] = list(query_result['records'][0].keys())
            if show_data or output_format == 'json':
                ds_result['data'] = query_result['records']

        results['datasources'].append(ds_result)

    return results


def print_usage():
    print("""CRE 2.0 Data Source Tester

Usage: python3 test_datasource.py <profile_id> <record_id> [options]

Arguments:
  profile_id        CRE2 profile internal ID
  record_id         Target record internal ID to test with

Options:
  --account <acct>  Account: twx, dm (default: twistedx)
  --env <env>       Environment: prod, sb1, sb2 (default: sb2)
  --format <fmt>    Output format: table, json (default: table)
  --show-data       Show full data values (table format only)

Examples:
  # Basic test - shows query success and available fields
  python3 test_datasource.py 17 7850220 --env sb2

  # Show full data values
  python3 test_datasource.py 17 7850220 --env sb2 --show-data

  # Output as JSON (always includes full data)
  python3 test_datasource.py 17 7850220 --env sb2 --format json

Use Cases:
  - Verify data source queries return expected data
  - Debug template variables (check available fields)
  - Validate JSON field contents before JS hook processing
  - Test record-specific query behavior

Note: The NetSuite API Gateway must be running at http://localhost:3001
""")


def main():
    if len(sys.argv) < 3 or '--help' in sys.argv or '-h' in sys.argv:
        print_usage()
        sys.exit(0)

    profile_id = int(sys.argv[1])
    record_id = int(sys.argv[2])
    account = DEFAULT_ACCOUNT
    environment = DEFAULT_ENVIRONMENT
    output_format = 'table'
    show_data = False

    # Parse options
    for i, arg in enumerate(sys.argv):
        if arg == '--account' and i + 1 < len(sys.argv):
            account = sys.argv[i + 1]
        elif arg == '--env' and i + 1 < len(sys.argv):
            environment = sys.argv[i + 1]
        elif arg == '--format' and i + 1 < len(sys.argv):
            output_format = sys.argv[i + 1]
        elif arg == '--show-data':
            show_data = True

    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    print(f"Testing data sources for profile {profile_id} with record {record_id}...", file=sys.stderr)
    print(f"Account: {resolved_account} | Environment: {resolved_env}\n", file=sys.stderr)

    results = test_datasource(profile_id, record_id, account, environment, output_format, show_data)

    if results.get('error'):
        print(f"ERROR: {results['error']}", file=sys.stderr)
        sys.exit(1)

    if output_format == 'json':
        print(json.dumps(results, indent=2))
        sys.exit(0)

    # Table format output
    print(f"{'='*70}")
    print(f"Profile: {results.get('profile_name', '')} (ID: {profile_id})")
    print(f"Record Type: {results.get('record_type', '')}")
    print(f"Test Record: {record_id}")
    print(f"{'='*70}")

    for ds in results['datasources']:
        print(f"\n--- Data Source: [{ds['name']}] (Query ID: {ds.get('query_id', '')}) ---")
        print(f"Paged: {'Yes' if ds.get('paged') else 'No'} | Single Record JSON: {'Yes' if ds.get('single_record_json') else 'No'}")

        if ds.get('error'):
            print(f"❌ ERROR: {ds['error']}")
            continue

        if ds.get('success'):
            print(f"✅ Query executed successfully")
            print(f"   Rows returned: {ds['row_count']}")

            if ds['fields']:
                print(f"\n   Available fields:")
                for field in ds['fields']:
                    print(f"     - {field}")

            if show_data and ds.get('data'):
                print(f"\n   Data preview:")
                for i, row in enumerate(ds['data'][:3]):  # Show first 3 rows
                    print(f"\n   Row {i + 1}:")
                    for key, value in row.items():
                        formatted = format_value(value, max_length=200)
                        # Handle multi-line values
                        if '\n' in formatted:
                            print(f"     {key}:")
                            for line in formatted.split('\n'):
                                print(f"       {line}")
                        else:
                            print(f"     {key}: {formatted}")

                if len(ds['data']) > 3:
                    print(f"\n   ... and {len(ds['data']) - 3} more row(s)")
        else:
            print(f"⚠️  No results returned")


if __name__ == '__main__':
    main()
