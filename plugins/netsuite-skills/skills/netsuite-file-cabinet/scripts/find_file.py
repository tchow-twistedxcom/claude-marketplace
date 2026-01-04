#!/usr/bin/env python3
"""
NetSuite File Finder

Find files in NetSuite File Cabinet by name, pattern, or folder.

Usage:
  python3 find_file.py --name "inventoryPartUserEvent.js" --env prod
  python3 find_file.py --pattern "twx_%" --env sb2
  python3 find_file.py --folder-id 137935 --env prod
  python3 find_file.py --name "script.js" --folder-id 137935 --env sb2
"""

import sys
import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List

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

DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox2'


def resolve_account(account: str) -> str:
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def query_run(query: str, account: str, environment: str) -> Dict[str, Any]:
    """Execute a SuiteQL query via the gateway."""
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
                'Origin': 'http://localhost:3000'
            }
        )

        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))

            if result.get('success'):
                return {
                    'success': True,
                    'records': result.get('data', {}).get('records', [])
                }
            else:
                return {
                    'error': result.get('error', {}).get('message', 'Unknown error')
                }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            error_json = json.loads(error_body)
            error_msg = error_json.get('error', {}).get('message', error_body)
        except:
            error_msg = error_body
        return {'error': f'HTTP {e.code}: {error_msg}'}

    except urllib.error.URLError as e:
        return {'error': f'Gateway connection error: {str(e.reason)}'}

    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}


def find_files(
    name: Optional[str] = None,
    pattern: Optional[str] = None,
    folder_id: Optional[int] = None,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Find files in NetSuite File Cabinet.

    Args:
        name: Exact file name to search for
        pattern: SQL LIKE pattern (e.g., "twx_%" for files starting with twx_)
        folder_id: Limit search to specific folder
        account: NetSuite account
        environment: NetSuite environment
        limit: Maximum results to return

    Returns:
        Dictionary with files or error
    """
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    # Validate account
    if resolved_account not in ['twistedx', 'dutyman']:
        return {'error': f"Invalid account: {account}"}

    # Validate environment
    if resolved_env not in ['production', 'sandbox', 'sandbox2']:
        return {'error': f"Invalid environment: {environment}"}

    # Build query
    query = """
        SELECT
            f.id,
            f.name,
            f.folder,
            BUILTIN.DF(f.folder) AS folder_name,
            f.filesize,
            f.filetype,
            f.lastmodifieddate
        FROM file f
        WHERE 1=1
    """

    conditions = []
    if name:
        conditions.append(f"f.name = '{name}'")
    if pattern:
        conditions.append(f"f.name LIKE '{pattern}'")
    if folder_id:
        conditions.append(f"f.folder = {folder_id}")

    if conditions:
        query += " AND " + " AND ".join(conditions)

    query += f" ORDER BY f.lastmodifieddate DESC FETCH FIRST {limit} ROWS ONLY"

    result = query_run(query, account, environment)

    if result.get('error'):
        return result

    files = result.get('records', [])
    return {
        'success': True,
        'count': len(files),
        'files': files,
        'account': resolved_account,
        'environment': resolved_env
    }


def print_usage():
    print("""NetSuite File Finder

Usage: python3 find_file.py [options]

Search Options (at least one required):
  --name <name>          Exact file name to search for
  --pattern <pattern>    SQL LIKE pattern (e.g., "twx_%" or "%userEvent%")
  --folder-id <id>       List files in specific folder

Options:
  --account <account>    Account (default: twistedx)
  --env <environment>    Environment (default: sandbox2)
  --limit <n>            Max results (default: 100)
  --format <format>      Output format: table, json (default: table)

Examples:
  # Find file by exact name
  python3 find_file.py --name "inventoryPartUserEvent.js" --env prod

  # Find files matching pattern
  python3 find_file.py --pattern "twx_edi%" --env prod

  # List all files in a folder
  python3 find_file.py --folder-id 137935 --env prod

  # Combine search criteria
  python3 find_file.py --pattern "%.js" --folder-id 137935 --env sb2

  # Output as JSON
  python3 find_file.py --name "script.js" --env prod --format json
""")


def format_size(size):
    """Format file size in human-readable format."""
    if size is None:
        return '-'
    try:
        size = int(size)
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size // 1024}KB"
        else:
            return f"{size // (1024 * 1024)}MB"
    except:
        return str(size)


def print_table(files: List[Dict]):
    """Print files in table format."""
    if not files:
        print("No files found.")
        return

    # Calculate column widths
    id_width = max(len(str(f.get('id', ''))) for f in files)
    id_width = max(id_width, 6)

    name_width = max(len(str(f.get('name', ''))) for f in files)
    name_width = min(max(name_width, 20), 50)

    folder_width = max(len(str(f.get('folder_name', ''))) for f in files)
    folder_width = min(max(folder_width, 15), 40)

    # Print header
    header = f"{'ID':<{id_width}}  {'Name':<{name_width}}  {'Folder':<{folder_width}}  {'Size':>8}  {'Modified'}"
    print(header)
    print("-" * len(header))

    # Print rows
    for f in files:
        file_id = str(f.get('id', ''))
        name = str(f.get('name', ''))[:50]
        folder = str(f.get('folder_name', ''))[:40]
        size = format_size(f.get('filesize'))
        modified = str(f.get('lastmodifieddate', ''))[:19]  # Trim to datetime

        print(f"{file_id:<{id_width}}  {name:<{name_width}}  {folder:<{folder_width}}  {size:>8}  {modified}")


def main():
    if len(sys.argv) < 2 or '--help' in sys.argv or '-h' in sys.argv:
        print_usage()
        sys.exit(0)

    name = None
    pattern = None
    folder_id = None
    account = DEFAULT_ACCOUNT
    environment = DEFAULT_ENVIRONMENT
    limit = 100
    output_format = 'table'

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--name' and i + 1 < len(sys.argv):
            name = sys.argv[i + 1]
            i += 2
        elif arg == '--pattern' and i + 1 < len(sys.argv):
            pattern = sys.argv[i + 1]
            i += 2
        elif arg == '--folder-id' and i + 1 < len(sys.argv):
            folder_id = int(sys.argv[i + 1])
            i += 2
        elif arg == '--account' and i + 1 < len(sys.argv):
            account = sys.argv[i + 1]
            i += 2
        elif arg == '--env' and i + 1 < len(sys.argv):
            environment = sys.argv[i + 1]
            i += 2
        elif arg == '--limit' and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
            i += 2
        elif arg == '--format' and i + 1 < len(sys.argv):
            output_format = sys.argv[i + 1].lower()
            i += 2
        else:
            i += 1

    if not name and not pattern and not folder_id:
        print("ERROR: At least one of --name, --pattern, or --folder-id is required")
        print_usage()
        sys.exit(1)

    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)
    print(f"Searching in {resolved_account}/{resolved_env}...")

    result = find_files(name, pattern, folder_id, account, environment, limit)

    if result.get('error'):
        print(f"ERROR: {result.get('error')}")
        sys.exit(1)

    files = result.get('files', [])
    print(f"Found {len(files)} file(s)\n")

    if output_format == 'json':
        print(json.dumps(result, indent=2))
    else:
        print_table(files)


if __name__ == '__main__':
    main()
