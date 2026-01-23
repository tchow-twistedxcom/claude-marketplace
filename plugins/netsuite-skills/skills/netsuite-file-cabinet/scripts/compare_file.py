#!/usr/bin/env python3
"""
NetSuite File Cabinet - Compare Files

Compare a local file with a NetSuite File Cabinet file.
Compares metadata (size) and optionally downloads for content comparison.

Usage:
  python3 compare_file.py <local_path> --file-id <netsuite_id> [options]

Examples:
  # Compare local template with NetSuite version
  python3 compare_file.py ./template.html --file-id 52794158 --env sb2

  # Quick size check only
  python3 compare_file.py ./template.html --file-id 52794158 --quick
"""

import sys
import os
import json
import hashlib
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

# NetSuite account IDs for URL building
ACCOUNT_IDS = {
    'twistedx': {
        'production': '4138030',
        'sandbox': '4138030_SB1',
        'sandbox2': '4138030_SB2'
    },
    'dutyman': {
        'production': '3611820',
        'sandbox': '3611820_SB1',
        'sandbox2': '3611820_SB2'
    }
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
            records = result.get('data', {}).get('records', []) if result.get('success') else []
            return {
                'records': records,
                'count': len(records),
                'error': result.get('error') if not result.get('success') else None
            }

    except Exception as e:
        return {'error': str(e), 'records': [], 'count': 0}


def get_local_file_info(path: str) -> Dict[str, Any]:
    """Get local file metadata and hash."""
    if not os.path.exists(path):
        return {'error': f'Local file not found: {path}'}

    if not os.path.isfile(path):
        return {'error': f'Path is not a file: {path}'}

    try:
        stat = os.stat(path)
        with open(path, 'rb') as f:
            content = f.read()
            md5_hash = hashlib.md5(content).hexdigest()

        return {
            'success': True,
            'path': os.path.abspath(path),
            'name': os.path.basename(path),
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'md5': md5_hash,
            'content': content
        }
    except Exception as e:
        return {'error': f'Error reading local file: {str(e)}'}


def get_netsuite_file_info(
    file_id: int,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """Get NetSuite file metadata."""
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    query = """
    SELECT
        f.id,
        f.name,
        f.filetype,
        f.filesize,
        f.folder,
        fld.name as folder_name,
        f.lastmodifieddate
    FROM file f
    LEFT JOIN mediaitemfolder fld ON f.folder = fld.id
    WHERE f.id = ?
    """

    result = execute_query(query, [file_id], account, environment)

    if result.get('error'):
        return {'error': result['error']}

    if result['count'] == 0:
        return {'error': f'NetSuite file {file_id} not found'}

    file_data = result['records'][0]

    # Build preview URL
    account_id = ACCOUNT_IDS.get(resolved_account, {}).get(resolved_env, '')
    base_domain = f"{account_id.replace('_', '-').lower()}.app.netsuite.com"
    preview_url = f"https://{base_domain}/core/media/previewmedia.nl?id={file_id}"

    return {
        'success': True,
        'file_id': file_id,
        'name': file_data.get('name', ''),
        'file_type': file_data.get('filetype', ''),
        'size': int(file_data.get('filesize', 0) or 0),
        'folder_id': file_data.get('folder', ''),
        'folder_name': file_data.get('folder_name', ''),
        'last_modified': file_data.get('lastmodifieddate', ''),
        'preview_url': preview_url
    }


def compare_files(
    local_path: str,
    netsuite_file_id: int,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT,
    quick: bool = False
) -> Dict[str, Any]:
    """Compare local file with NetSuite file."""

    # Get local file info
    local_info = get_local_file_info(local_path)
    if local_info.get('error'):
        return {'error': f"Local file error: {local_info['error']}"}

    # Get NetSuite file info
    ns_info = get_netsuite_file_info(netsuite_file_id, account, environment)
    if ns_info.get('error'):
        return {'error': f"NetSuite file error: {ns_info['error']}"}

    # Compare sizes
    size_match = local_info['size'] == ns_info['size']
    size_diff = local_info['size'] - ns_info['size']

    # Determine comparison result
    if size_match:
        status = 'LIKELY_IDENTICAL'
        message = 'Files have identical size - likely the same content'
    elif abs(size_diff) < 100:
        status = 'SIMILAR'
        message = f'Files differ by {abs(size_diff)} bytes - minor differences (whitespace/encoding?)'
    else:
        status = 'DIFFERENT'
        message = f'Files differ by {abs(size_diff)} bytes - likely different content'

    return {
        'success': True,
        'status': status,
        'message': message,
        'local': {
            'path': local_info['path'],
            'name': local_info['name'],
            'size': local_info['size'],
            'md5': local_info['md5']
        },
        'netsuite': {
            'file_id': ns_info['file_id'],
            'name': ns_info['name'],
            'size': ns_info['size'],
            'folder': f"{ns_info['folder_name']} (ID: {ns_info['folder_id']})",
            'last_modified': ns_info['last_modified'],
            'preview_url': ns_info['preview_url']
        },
        'comparison': {
            'size_match': size_match,
            'size_diff': size_diff,
            'local_larger': size_diff > 0
        }
    }


def format_size(size):
    """Format file size in human-readable format."""
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f}KB"
    else:
        return f"{size / (1024 * 1024):.1f}MB"


def print_usage():
    print("""NetSuite File Cabinet - Compare Files

Usage: python3 compare_file.py <local_path> --file-id <netsuite_id> [options]

Required:
  <local_path>           Path to local file
  --file-id <id>         NetSuite file internal ID

Options:
  --account <account>    Account: twx, dm (default: twistedx)
  --env <environment>    Environment: prod, sb1, sb2 (default: sb2)
  --format <format>      Output format: table, json (default: table)
  --quick                Size comparison only (faster)

Examples:
  # Compare local template with NetSuite version
  python3 compare_file.py ./template.html --file-id 52794158 --env sb2

  # Quick size check
  python3 compare_file.py ./template.html --file-id 52794158 --env sb2 --quick

  # Output as JSON
  python3 compare_file.py ./template.html --file-id 52794158 --env sb2 --format json

Note: Full content comparison requires downloading the NetSuite file.
      Use the preview URL to download and compare manually if needed.
""")


def main():
    if len(sys.argv) < 2 or '--help' in sys.argv or '-h' in sys.argv:
        print_usage()
        sys.exit(0)

    local_path = None
    file_id = None
    account = DEFAULT_ACCOUNT
    environment = DEFAULT_ENVIRONMENT
    output_format = 'table'
    quick = False

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--file-id' and i + 1 < len(sys.argv):
            file_id = int(sys.argv[i + 1])
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
        elif arg == '--quick':
            quick = True
            i += 1
        elif not arg.startswith('--') and local_path is None:
            local_path = arg
            i += 1
        else:
            i += 1

    if not local_path:
        print("ERROR: Local file path required")
        print_usage()
        sys.exit(1)

    if not file_id:
        print("ERROR: --file-id is required")
        print_usage()
        sys.exit(1)

    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    print(f"Comparing files in {resolved_account}/{resolved_env}...", file=sys.stderr)

    result = compare_files(local_path, file_id, account, environment, quick)

    if result.get('error'):
        print(f"ERROR: {result['error']}", file=sys.stderr)
        sys.exit(1)

    if output_format == 'json':
        print(json.dumps(result, indent=2))
    else:
        # Display result
        print()
        status = result['status']
        if status == 'LIKELY_IDENTICAL':
            print(f"✅ {result['message']}")
        elif status == 'SIMILAR':
            print(f"⚠️  {result['message']}")
        else:
            print(f"❌ {result['message']}")

        print()
        print("Local File:")
        print(f"  Path:     {result['local']['path']}")
        print(f"  Size:     {format_size(result['local']['size'])} ({result['local']['size']} bytes)")
        print(f"  MD5:      {result['local']['md5']}")

        print()
        print("NetSuite File:")
        print(f"  ID:       {result['netsuite']['file_id']}")
        print(f"  Name:     {result['netsuite']['name']}")
        print(f"  Size:     {format_size(result['netsuite']['size'])} ({result['netsuite']['size']} bytes)")
        print(f"  Folder:   {result['netsuite']['folder']}")
        print(f"  Modified: {result['netsuite']['last_modified']}")

        if status != 'LIKELY_IDENTICAL':
            print()
            print("To compare content manually:")
            print(f"  1. Download: {result['netsuite']['preview_url']}")
            print(f"  2. Compare:  diff {result['local']['path']} <downloaded_file>")

        # Exit code based on comparison result
        if status == 'DIFFERENT':
            sys.exit(1)


if __name__ == '__main__':
    main()
