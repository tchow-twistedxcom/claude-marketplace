#!/usr/bin/env python3
"""
NetSuite File Cabinet - Download Entire Bundle

Recursively download all files from a NetSuite SuiteBundle folder.
Preserves folder structure and handles subdirectories.

Usage:
  python3 download_bundle.py --bundle 311735 --output ./SuiteBundles --env prod
  python3 download_bundle.py --folder-id 1234567 --output ./downloads --env sb2
  python3 download_bundle.py --bundle 311735 --output ./SuiteBundles --env prod --dry-run
"""

import sys
import os
import json
import urllib.request
import urllib.error
import base64
from typing import Dict, Any, Optional, List
from pathlib import Path

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
DEFAULT_ENVIRONMENT = 'production'


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

        with urllib.request.urlopen(req, timeout=120) as response:
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


def find_bundle_folder(bundle_number: str, account: str, environment: str) -> Optional[Dict]:
    """Find the SuiteBundle folder by bundle number."""
    # First find the SuiteBundles root folder
    query = """
    SELECT id, name, parent
    FROM mediaitemfolder
    WHERE name = ?
    """

    # Try to find the specific bundle folder
    bundle_folder_name = f"Bundle {bundle_number}"
    result = execute_query(query, [bundle_folder_name], account, environment)

    if result.get('error'):
        print(f"ERROR: {result['error']}", file=sys.stderr)
        return None

    if result['count'] == 0:
        # Try without space
        bundle_folder_name = f"Bundle{bundle_number}"
        result = execute_query(query, [bundle_folder_name], account, environment)

    if result['count'] == 0:
        print(f"ERROR: Bundle folder '{bundle_folder_name}' not found", file=sys.stderr)
        return None

    return result['records'][0]


def get_folder_info(folder_id: int, account: str, environment: str) -> Optional[Dict]:
    """Get folder name and parent."""
    query = """
    SELECT id, name, parent
    FROM mediaitemfolder
    WHERE id = ?
    """
    result = execute_query(query, [folder_id], account, environment)
    if result.get('records'):
        return result['records'][0]
    return None


def build_folder_path(folder_id: int, account: str, environment: str, path_parts: List[str] = None) -> str:
    """Build full folder path by traversing parent folders."""
    if path_parts is None:
        path_parts = []

    folder = get_folder_info(folder_id, account, environment)
    if folder:
        path_parts.insert(0, folder.get('name', ''))
        parent = folder.get('parent')
        if parent:
            return build_folder_path(parent, account, environment, path_parts)

    return '/'.join(path_parts)


def list_subfolders(parent_folder_id: int, account: str, environment: str) -> List[Dict]:
    """List all subfolders of a folder."""
    query = """
    SELECT id, name, parent
    FROM mediaitemfolder
    WHERE parent = ?
    ORDER BY name
    """
    result = execute_query(query, [parent_folder_id], account, environment)
    if result.get('error'):
        print(f"Warning: Could not list subfolders of {parent_folder_id}: {result['error']}", file=sys.stderr)
        return []
    return result.get('records', [])


def list_files_in_folder(folder_id: int, account: str, environment: str) -> List[Dict]:
    """List all files in a folder."""
    query = """
    SELECT id, name, filetype, filesize, url, folder
    FROM file
    WHERE folder = ?
    ORDER BY name
    """
    result = execute_query(query, [folder_id], account, environment)
    if result.get('error'):
        print(f"Warning: Could not list files in folder {folder_id}: {result['error']}", file=sys.stderr)
        return []
    return result.get('records', [])


def get_all_files_recursive(
    folder_id: int,
    account: str,
    environment: str,
    base_path: str = "",
    all_files: List[Dict] = None
) -> List[Dict]:
    """Recursively get all files in a folder and its subfolders."""
    if all_files is None:
        all_files = []

    # Get folder info for path building
    folder_info = get_folder_info(folder_id, account, environment)
    folder_name = folder_info.get('name', '') if folder_info else ''
    current_path = f"{base_path}/{folder_name}" if base_path else folder_name

    # Get files in this folder
    files = list_files_in_folder(folder_id, account, environment)
    for f in files:
        f['relative_path'] = current_path
        all_files.append(f)

    # Recursively process subfolders
    subfolders = list_subfolders(folder_id, account, environment)
    for subfolder in subfolders:
        get_all_files_recursive(
            subfolder['id'],
            account,
            environment,
            current_path,
            all_files
        )

    return all_files


def download_file_content(file_url: str, account: str, environment: str) -> Optional[bytes]:
    """Download file content from NetSuite."""
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    # Build full URL
    account_id = ACCOUNT_IDS.get(resolved_account, {}).get(resolved_env, '')
    if not account_id:
        print(f"ERROR: Unknown account/environment: {resolved_account}/{resolved_env}", file=sys.stderr)
        return None

    # The file URL from SuiteQL is relative, build full URL
    if file_url.startswith('/'):
        base_domain = f"{account_id.replace('_', '-').lower()}.app.netsuite.com"
        full_url = f"https://{base_domain}{file_url}"
    else:
        full_url = file_url

    try:
        req = urllib.request.Request(
            full_url,
            headers={
                'User-Agent': 'Mozilla/5.0'
            }
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.read()
    except Exception as e:
        print(f"Warning: Could not download {full_url}: {e}", file=sys.stderr)
        return None


def download_via_gateway(file_id: int, account: str, environment: str) -> Optional[bytes]:
    """Download file content via the API Gateway."""
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    payload = {
        'action': 'fileGet',
        'procedure': 'fileGet',
        'id': file_id,  # Gateway expects 'id' not 'fileId'
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

            if result.get('success') and result.get('data'):
                file_data = result.get('data', {})
                content = file_data.get('content', '')
                encoding = file_data.get('encoding', 'UTF-8')

                # Check if content is base64 encoded
                if encoding == 'BASE64' or file_data.get('isBase64'):
                    return base64.b64decode(content)
                else:
                    return content.encode('utf-8')
            else:
                error = result.get('error', 'Unknown error')
                print(f"Warning: Gateway returned error for file {file_id}: {error}", file=sys.stderr)
                return None

    except Exception as e:
        print(f"Warning: Gateway request failed for file {file_id}: {e}", file=sys.stderr)
        return None


def save_file(content: bytes, output_path: str) -> bool:
    """Save file content to disk."""
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"ERROR: Could not save {output_path}: {e}", file=sys.stderr)
        return False


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


def print_usage():
    print("""NetSuite File Cabinet - Download Entire Bundle

Usage: python3 download_bundle.py [options]

Required (one of):
  --bundle <number>      Bundle number to download (e.g., 311735)
  --folder-id <id>       Folder ID to download recursively

Options:
  --output <path>        Output directory (default: ./SuiteBundles)
  --account <account>    Account (default: twistedx)
  --env <environment>    Environment: prod, sb1, sb2 (default: prod)
  --dry-run              List files without downloading
  --format <format>      Output format: table, json (default: table)

Examples:
  # Download Bundle 311735 to ./SuiteBundles
  python3 download_bundle.py --bundle 311735 --output ./SuiteBundles --env prod

  # Dry run - list files without downloading
  python3 download_bundle.py --bundle 311735 --env prod --dry-run

  # Download from sandbox
  python3 download_bundle.py --bundle 311735 --output ./SuiteBundles --env sb2

  # Download specific folder
  python3 download_bundle.py --folder-id 1234567 --output ./downloads --env prod
""")


def main():
    if len(sys.argv) < 2 or '--help' in sys.argv or '-h' in sys.argv:
        print_usage()
        sys.exit(0)

    bundle_number = None
    folder_id = None
    output_dir = './SuiteBundles'
    account = DEFAULT_ACCOUNT
    environment = DEFAULT_ENVIRONMENT
    dry_run = False
    output_format = 'table'

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--bundle' and i + 1 < len(sys.argv):
            bundle_number = sys.argv[i + 1]
            i += 2
        elif arg == '--folder-id' and i + 1 < len(sys.argv):
            folder_id = int(sys.argv[i + 1])
            i += 2
        elif arg == '--output' and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]
            i += 2
        elif arg == '--account' and i + 1 < len(sys.argv):
            account = sys.argv[i + 1]
            i += 2
        elif arg == '--env' and i + 1 < len(sys.argv):
            environment = sys.argv[i + 1]
            i += 2
        elif arg == '--dry-run':
            dry_run = True
            i += 1
        elif arg == '--format' and i + 1 < len(sys.argv):
            output_format = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    if not bundle_number and not folder_id:
        print("ERROR: --bundle or --folder-id is required")
        print_usage()
        sys.exit(1)

    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    print(f"Target: {resolved_account}/{resolved_env}")

    # Find the folder to download
    if bundle_number:
        print(f"Finding Bundle {bundle_number} folder...")
        folder_info = find_bundle_folder(bundle_number, account, environment)
        if not folder_info:
            sys.exit(1)
        folder_id = folder_info['id']
        print(f"Found folder ID: {folder_id}")

    # Get all files recursively
    print(f"Scanning folder {folder_id} recursively...")
    all_files = get_all_files_recursive(folder_id, account, environment)

    print(f"\nFound {len(all_files)} files\n")

    if output_format == 'json':
        print(json.dumps({
            'folder_id': folder_id,
            'bundle': bundle_number,
            'files': all_files,
            'count': len(all_files)
        }, indent=2))
        if dry_run:
            sys.exit(0)
    else:
        # Print table of files
        print(f"{'ID':<10} {'Size':<10} {'Path'}")
        print("-" * 80)
        for f in all_files:
            file_id = str(f.get('id', ''))
            size = format_size(f.get('filesize'))
            rel_path = f.get('relative_path', '')
            name = f.get('name', '')
            full_path = f"{rel_path}/{name}" if rel_path else name
            print(f"{file_id:<10} {size:<10} {full_path}")
        print()

    if dry_run:
        print("Dry run - no files downloaded")
        sys.exit(0)

    # Download files
    print(f"Downloading to: {output_dir}")
    print()

    downloaded = 0
    failed = 0

    for f in all_files:
        file_id = f.get('id')
        file_url = f.get('url', '')
        rel_path = f.get('relative_path', '')
        name = f.get('name', '')

        output_path = os.path.join(output_dir, rel_path, name)

        print(f"Downloading {rel_path}/{name}... ", end='', flush=True)

        # Try gateway first, fall back to URL download
        content = download_via_gateway(file_id, account, environment)

        if content is None and file_url:
            content = download_file_content(file_url, account, environment)

        if content:
            if save_file(content, output_path):
                print("✅")
                downloaded += 1
            else:
                print("❌ (save failed)")
                failed += 1
        else:
            print("❌ (download failed)")
            failed += 1

    print(f"\n=== Summary ===")
    print(f"Downloaded: {downloaded}")
    print(f"Failed: {failed}")
    print(f"Total: {len(all_files)}")


if __name__ == '__main__':
    main()
