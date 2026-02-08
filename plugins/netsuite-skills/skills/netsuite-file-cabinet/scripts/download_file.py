#!/usr/bin/env python3
"""
NetSuite File Cabinet - Get File Info

Get file metadata and optionally content from NetSuite File Cabinet.

Usage:
  python3 download_file.py --file-id 52793356 --env sb2
  python3 download_file.py --file-id 52793356 --env sb2 --format json
  python3 download_file.py --file-id 52793356 --env sb2 --content  # Get actual file content
"""

import sys
import json
import base64
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


def get_file_info(
    file_id: int,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """
    Get file metadata from NetSuite.

    Args:
        file_id: NetSuite file internal ID
        account: NetSuite account
        environment: NetSuite environment

    Returns:
        Dictionary with file info or error
    """
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    # Query file info
    query = """
    SELECT
        f.id,
        f.name,
        f.filetype,
        f.filesize,
        f.folder,
        fld.name as folder_name,
        f.url,
        f.lastmodifieddate
    FROM file f
    LEFT JOIN mediaitemfolder fld ON f.folder = fld.id
    WHERE f.id = ?
    """

    result = execute_query(query, [file_id], account, environment)

    if result.get('error'):
        return {'error': result['error']}

    if result['count'] == 0:
        return {'error': f'File {file_id} not found'}

    file_data = result['records'][0]

    # Build NetSuite URLs
    account_id = ACCOUNT_IDS.get(resolved_account, {}).get(resolved_env, '')
    base_domain = f"{account_id.replace('_', '-').lower()}.app.netsuite.com"

    # Preview URL (no auth required if file is public)
    preview_url = f"https://{base_domain}/core/media/previewmedia.nl?id={file_id}"

    # Direct download URL (requires auth)
    download_url = file_data.get('url', '')
    if download_url and not download_url.startswith('http'):
        download_url = f"https://{base_domain}{download_url}"

    return {
        'success': True,
        'file_id': file_id,
        'name': file_data.get('name', ''),
        'file_type': file_data.get('filetype', ''),
        'size': file_data.get('filesize', 0),
        'folder_id': file_data.get('folder', ''),
        'folder_name': file_data.get('folder_name', ''),
        'last_modified': file_data.get('lastmodifieddate', ''),
        'preview_url': preview_url,
        'download_url': download_url,
        'account': resolved_account,
        'environment': resolved_env
    }


def get_file_content(
    file_id: int,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """
    Get actual file content from NetSuite via gateway fileGet procedure.

    Args:
        file_id: NetSuite file internal ID
        account: NetSuite account
        environment: NetSuite environment

    Returns:
        Dictionary with file content (decoded) or error
    """
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    payload = {
        'action': 'fileGet',
        'procedure': 'fileGet',
        'id': file_id,
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

        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))

            if not result.get('success'):
                error_msg = result.get('error', {}).get('message', 'Unknown error')
                return {'error': error_msg}

            file_data = result.get('data', {}).get('file', {})
            file_info = file_data.get('info', {})
            content_b64 = file_data.get('content', '')

            if not content_b64:
                return {'error': 'No content returned from gateway'}

            # Decode base64 content
            try:
                content = base64.b64decode(content_b64).decode('utf-8')
            except UnicodeDecodeError:
                # Binary file - return as bytes
                content = base64.b64decode(content_b64)

            return {
                'success': True,
                'file_id': file_id,
                'name': file_info.get('name', ''),
                'file_type': file_info.get('fileType', ''),
                'size': file_info.get('size', 0),
                'path': file_info.get('path', ''),
                'content': content,
                'is_binary': isinstance(content, bytes),
                'account': resolved_account,
                'environment': resolved_env
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


def print_usage():
    print("""NetSuite File Cabinet - Get File Info

Usage: python3 download_file.py --file-id <id> [options]

Required:
  --file-id <id>         NetSuite file internal ID

Options:
  --account <account>    Account (default: twistedx)
  --env <environment>    Environment (default: sandbox2)
  --format <format>      Output format: table, json (default: table)
  --url-only             Only print the preview URL
  --content              Get actual file content via authenticated gateway

Examples:
  # Get file info
  python3 download_file.py --file-id 52793356 --env sb2

  # Output as JSON
  python3 download_file.py --file-id 52793356 --env sb2 --format json

  # Just get the preview URL
  python3 download_file.py --file-id 52793356 --env sb2 --url-only

  # Get actual file content (uses gateway fileGet - authenticated)
  python3 download_file.py --file-id 33015424 --env sb1 --content

  # Get content as JSON (includes metadata)
  python3 download_file.py --file-id 33015424 --env sb1 --content --format json

Note: The --content flag uses the authenticated API gateway (localhost:3001)
      to retrieve actual file content. Public URLs require NetSuite login.
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

    file_id = None
    account = DEFAULT_ACCOUNT
    environment = DEFAULT_ENVIRONMENT
    output_format = 'table'
    url_only = False
    get_content = False

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
        elif arg == '--url-only':
            url_only = True
            i += 1
        elif arg == '--content':
            get_content = True
            i += 1
        else:
            i += 1

    if not file_id:
        print("ERROR: --file-id is required")
        print_usage()
        sys.exit(1)

    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    # Handle --content flag: get actual file content via gateway
    if get_content:
        print(f"Getting file content for {file_id} from {resolved_account}/{resolved_env}...", file=sys.stderr)
        result = get_file_content(file_id, account, environment)

        if result.get('error'):
            print(f"ERROR: {result['error']}", file=sys.stderr)
            sys.exit(1)

        if output_format == 'json':
            # For JSON output, include metadata but handle binary content
            output = {
                'success': True,
                'file_id': result['file_id'],
                'name': result['name'],
                'file_type': result['file_type'],
                'size': result['size'],
                'path': result['path'],
                'is_binary': result['is_binary'],
                'account': result['account'],
                'environment': result['environment']
            }
            if not result['is_binary']:
                output['content'] = result['content']
            else:
                output['content'] = '<binary content - not displayed>'
            print(json.dumps(output, indent=2))
        else:
            # For table format, just output the content directly
            if result['is_binary']:
                print(f"ERROR: Binary file content cannot be displayed in table format", file=sys.stderr)
                print(f"Use --format json for binary files", file=sys.stderr)
                sys.exit(1)
            print(result['content'])
        sys.exit(0)

    if not url_only:
        print(f"Getting file info for {file_id} from {resolved_account}/{resolved_env}...", file=sys.stderr)

    result = get_file_info(file_id, account, environment)

    if result.get('error'):
        print(f"ERROR: {result['error']}", file=sys.stderr)
        sys.exit(1)

    if url_only:
        print(result['preview_url'])
        sys.exit(0)

    if output_format == 'json':
        print(json.dumps(result, indent=2))
    else:
        print(f"\nFile: {result['name']}")
        print(f"  ID:           {result['file_id']}")
        print(f"  Type:         {result['file_type']}")
        print(f"  Size:         {format_size(result['size'])}")
        print(f"  Folder:       {result['folder_name']} (ID: {result['folder_id']})")
        print(f"  Modified:     {result['last_modified']}")
        print(f"\nPreview URL:    {result['preview_url']}")
        if result['download_url']:
            print(f"Download URL:   {result['download_url']}")


if __name__ == '__main__':
    main()
