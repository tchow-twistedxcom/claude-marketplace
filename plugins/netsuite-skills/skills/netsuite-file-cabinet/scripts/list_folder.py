#!/usr/bin/env python3
"""
NetSuite File Cabinet - List Folder Contents

List all files in a NetSuite File Cabinet folder.

Usage:
  python3 list_folder.py --folder-id 1159370 --env sb2
  python3 list_folder.py --folder-id 1159370 --env sb2 --format json
"""

import sys
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
        return {
            'error': f'Gateway connection error: {str(e.reason)}. Is the gateway running?',
            'records': [],
            'count': 0
        }

    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}', 'records': [], 'count': 0}


def get_folder_info(folder_id: int, account: str, environment: str) -> Optional[Dict]:
    """Get folder name and path."""
    query = """
    SELECT id, name, parent
    FROM mediaitemfolder
    WHERE id = ?
    """
    result = execute_query(query, [folder_id], account, environment)
    if result.get('records'):
        return result['records'][0]
    return None


def list_folder(
    folder_id: int,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT,
    output_format: str = 'table'
) -> Dict[str, Any]:
    """
    List all files in a folder.

    Args:
        folder_id: NetSuite folder internal ID
        account: NetSuite account
        environment: NetSuite environment
        output_format: 'table' or 'json'

    Returns:
        Dictionary with files list or error
    """
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    # Get folder info
    folder_info = get_folder_info(folder_id, account, environment)
    folder_name = folder_info.get('name', f'Folder {folder_id}') if folder_info else f'Folder {folder_id}'

    # Query files in folder
    query = """
    SELECT
        id,
        name,
        filetype,
        filesize,
        lastmodifieddate
    FROM file
    WHERE folder = ?
    ORDER BY name
    """

    result = execute_query(query, [folder_id], account, environment)

    if result.get('error'):
        return {'error': result['error']}

    files = result.get('records', [])

    return {
        'success': True,
        'folder_id': folder_id,
        'folder_name': folder_name,
        'files': files,
        'count': len(files),
        'account': resolved_account,
        'environment': resolved_env
    }


def print_usage():
    print("""NetSuite File Cabinet - List Folder Contents

Usage: python3 list_folder.py --folder-id <id> [options]

Required:
  --folder-id <id>       NetSuite folder internal ID

Options:
  --account <account>    Account (default: twistedx)
  --env <environment>    Environment (default: sandbox2)
  --format <format>      Output format: table, json (default: table)

Examples:
  # List files in folder
  python3 list_folder.py --folder-id 1159370 --env sb2

  # Output as JSON
  python3 list_folder.py --folder-id 1159370 --env sb2 --format json

  # List files in production
  python3 list_folder.py --folder-id 137935 --env prod
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
            return f"{size / 1024:.1f}KB"
        else:
            return f"{size / (1024 * 1024):.1f}MB"
    except:
        return str(size)


def main():
    if len(sys.argv) < 2 or '--help' in sys.argv or '-h' in sys.argv:
        print_usage()
        sys.exit(0)

    folder_id = None
    account = DEFAULT_ACCOUNT
    environment = DEFAULT_ENVIRONMENT
    output_format = 'table'

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--folder-id' and i + 1 < len(sys.argv):
            folder_id = int(sys.argv[i + 1])
            i += 2
        elif arg == '--account' and i + 1 < len(sys.argv):
            account = sys.argv[i + 1]
            i += 2
        elif arg == '--env' and i + 1 < len(sys.argv):
            environment = sys.argv[i + 1]
            i += 2
        elif arg == '--format' and i + 1 < len(sys.argv):
            output_format = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    if not folder_id:
        print("ERROR: --folder-id is required")
        print_usage()
        sys.exit(1)

    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)
    print(f"Listing folder {folder_id} in {resolved_account}/{resolved_env}...")

    result = list_folder(folder_id, account, environment, output_format)

    if result.get('error'):
        print(f"ERROR: {result['error']}")
        sys.exit(1)

    if output_format == 'json':
        print(json.dumps(result, indent=2))
    else:
        print(f"\nFolder: {result['folder_name']} (ID: {folder_id})")
        print(f"Files: {result['count']}\n")

        if result['count'] == 0:
            print("  (No files in this folder)")
        else:
            print(f"{'ID':<10} {'Name':<40} {'Type':<12} {'Size':<10} {'Modified'}")
            print("-" * 90)

            for f in result['files']:
                file_id = str(f.get('id', ''))
                name = f.get('name', '')[:40]
                file_type = f.get('filetype', '')[:12]
                size = format_size(f.get('filesize'))
                modified = f.get('lastmodifieddate', '')[:10]

                print(f"{file_id:<10} {name:<40} {file_type:<12} {size:<10} {modified}")


if __name__ == '__main__':
    main()
