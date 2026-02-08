#!/usr/bin/env python3
"""
NetSuite File Cabinet - Download Entire Folder Tree

Uses hierarchical query to efficiently download all files from a folder
and all its subfolders without recursive API calls.

Usage:
  python3 download_folder_tree.py --folder-id 18625 --output ./backup --env prod
  python3 download_folder_tree.py --folder-id 18625 --output ./backup --env prod --dry-run
  python3 download_folder_tree.py --folder-id 18625 --output ./backup --env prod --limit 100
"""

import sys
import os
import json
import urllib.request
import urllib.error
import base64
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

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
DEFAULT_ENVIRONMENT = 'production'
BATCH_SIZE = 1000
RATE_LIMIT_DELAY = 0.2  # seconds between downloads


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

        with urllib.request.urlopen(req, timeout=300) as response:
            result = json.loads(response.read().decode('utf-8'))

            records = []
            if 'data' in result and 'records' in result['data']:
                records = result['data']['records']
            elif 'records' in result:
                records = result['records']
            elif 'data' in result:
                records = result['data'] if isinstance(result['data'], list) else []

            return {'records': records, 'error': None}

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        return {'records': [], 'error': f"HTTP {e.code}: {error_body}"}
    except Exception as e:
        return {'records': [], 'error': str(e)}


def get_all_files_hierarchical(
    root_folder_id: int,
    account: str,
    environment: str,
    min_id: int = 0,
    limit: int = BATCH_SIZE
) -> Dict[str, Any]:
    """Get all files in folder tree using hierarchical query with ID-based pagination."""
    # Use ID-based pagination instead of OFFSET (OFFSET doesn't work well with CONNECT BY)
    query = f"""
    SELECT
        f.id,
        f.name,
        f.folder,
        mf.name as folder_name,
        f.filesize,
        f.filetype,
        f.url
    FROM File f
    JOIN MediaItemFolder mf ON f.folder = mf.id
    WHERE f.id > {min_id}
      AND f.folder IN (
        SELECT DISTINCT id FROM MediaItemFolder
        START WITH id = {root_folder_id}
        CONNECT BY PRIOR id = parent
    )
    ORDER BY f.id
    FETCH FIRST {limit} ROWS ONLY
    """
    return execute_query(query, [], account, environment)


def count_files_in_tree(root_folder_id: int, account: str, environment: str) -> int:
    """Count total files in folder tree."""
    query = f"""
    SELECT COUNT(DISTINCT f.id) as total
    FROM File f
    WHERE f.folder IN (
        SELECT DISTINCT id FROM MediaItemFolder
        START WITH id = {root_folder_id}
        CONNECT BY PRIOR id = parent
    )
    """
    result = execute_query(query, [], account, environment)
    if result.get('records'):
        return int(result['records'][0].get('total', 0))
    return 0


def get_folder_path(folder_id: int, account: str, environment: str) -> str:
    """Get full folder path using hierarchical query."""
    query = f"""
    SELECT name
    FROM MediaItemFolder
    START WITH id = {folder_id}
    CONNECT BY PRIOR parent = id
    ORDER BY LEVEL DESC
    """
    result = execute_query(query, [], account, environment)
    if result.get('records'):
        return '/'.join(r.get('name', '') for r in result['records'])
    return ''


def download_file_content(file_id: int, account: str, environment: str) -> Optional[bytes]:
    """Download file content via gateway fileGet procedure."""
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    payload = {
        'action': 'fileGet',
        'procedure': 'fileGet',
        'id': file_id,
        'returnContent': True,
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

            # Extract content from response
            file_data = None
            if 'data' in result and 'file' in result['data']:
                file_data = result['data']['file']
            elif 'file' in result:
                file_data = result['file']

            if file_data and 'content' in file_data:
                return base64.b64decode(file_data['content'])

            return None

    except Exception as e:
        print(f"  Download error: {e}", file=sys.stderr)
        return None


def save_file(content: bytes, output_path: Path) -> bool:
    """Save file content to disk."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(content)
        return True
    except Exception as e:
        print(f"  Save error: {e}", file=sys.stderr)
        return False


def print_usage():
    print("""NetSuite File Cabinet - Download Entire Folder Tree

Usage:
  python3 download_folder_tree.py --folder-id <ID> --output <DIR> [options]

Required:
  --folder-id <ID>     Root folder ID to download
  --output <DIR>       Output directory for downloaded files

Options:
  --env <ENV>          Environment: prod, sb1, sb2 (default: prod)
  --account <ACCOUNT>  Account: twx, dm (default: twx)
  --dry-run            List files without downloading
  --limit <N>          Limit number of files to download
  --offset <N>         Start from file offset (for resuming)
  --format json        Output as JSON instead of table

Examples:
  python3 download_folder_tree.py --folder-id 18625 --output ./backup --env prod
  python3 download_folder_tree.py --folder-id 18625 --output ./backup --env prod --dry-run
  python3 download_folder_tree.py --folder-id 18625 --output ./backup --env prod --limit 100
""")


def main():
    # Parse arguments
    args = sys.argv[1:]
    if not args or '--help' in args or '-h' in args:
        print_usage()
        return

    folder_id = None
    output_dir = None
    account = DEFAULT_ACCOUNT
    environment = DEFAULT_ENVIRONMENT
    dry_run = False
    limit = None
    offset = 0
    output_format = 'table'

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--folder-id' and i + 1 < len(args):
            folder_id = int(args[i + 1])
            i += 2
        elif arg == '--output' and i + 1 < len(args):
            output_dir = Path(args[i + 1])
            i += 2
        elif arg in ('--env', '--environment') and i + 1 < len(args):
            environment = args[i + 1]
            i += 2
        elif arg == '--account' and i + 1 < len(args):
            account = args[i + 1]
            i += 2
        elif arg == '--dry-run':
            dry_run = True
            i += 1
        elif arg == '--limit' and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        elif arg == '--offset' and i + 1 < len(args):
            offset = int(args[i + 1])
            i += 2
        elif arg == '--format' and i + 1 < len(args):
            output_format = args[i + 1]
            i += 2
        else:
            i += 1

    if not folder_id:
        print("ERROR: --folder-id is required")
        print_usage()
        return

    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    print(f"Target: {resolved_account}/{resolved_env}")
    print(f"Root folder: {folder_id}")

    # Count total files
    print("Counting files...")
    total_files = count_files_in_tree(folder_id, account, environment)
    print(f"Total files in tree: {total_files}")

    if total_files == 0:
        print("No files found.")
        return

    # Collect all files in batches using ID-based pagination
    print("\nCollecting file metadata...")
    all_files = []
    seen_ids = set()
    min_id = offset  # Use offset as starting file ID
    fetch_limit = limit if limit else total_files

    while len(all_files) < fetch_limit:
        batch_size = min(BATCH_SIZE, fetch_limit - len(all_files))
        result = get_all_files_hierarchical(folder_id, account, environment, min_id, batch_size)

        if result.get('error'):
            print(f"ERROR: {result['error']}", file=sys.stderr)
            break

        records = result.get('records', [])
        if not records:
            break

        # Deduplicate and track max ID for next batch
        new_records = []
        for r in records:
            file_id = r.get('id')
            if file_id and file_id not in seen_ids:
                seen_ids.add(file_id)
                new_records.append(r)
                min_id = max(min_id, file_id)

        if not new_records:
            break

        all_files.extend(new_records)
        print(f"  Fetched {len(all_files)} unique files (min_id: {min_id})...", end='\r')

    print(f"\nCollected {len(all_files)} files")

    # Output file list
    if output_format == 'json':
        print(json.dumps({
            'root_folder': folder_id,
            'total_files': len(all_files),
            'files': all_files
        }, indent=2))
        if dry_run:
            return
    else:
        if dry_run:
            print(f"\n{'ID':<10} {'Size':<12} {'Folder':<30} {'Name'}")
            print("-" * 100)
            for f in all_files:
                file_id = f.get('id', '')
                size = f.get('filesize', 0)
                size_str = f"{size:,}" if size else "?"
                folder_name = f.get('folder_name', '')[:28]
                name = f.get('name', '')
                print(f"{file_id:<10} {size_str:<12} {folder_name:<30} {name}")
            print(f"\nDry run - no files downloaded")
            print(f"Total: {len(all_files)} files")
            return

    # Download files
    if not output_dir:
        print("ERROR: --output is required for downloading")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nDownloading to: {output_dir}")

    # Create manifest
    manifest = {
        'download_date': datetime.now().isoformat(),
        'account': resolved_account,
        'environment': resolved_env,
        'root_folder': folder_id,
        'total_files': len(all_files),
        'files': []
    }

    downloaded = 0
    failed = 0
    skipped = 0

    for i, f in enumerate(all_files):
        file_id = f.get('id')
        name = f.get('name', f'file_{file_id}')
        folder_name = f.get('folder_name', 'unknown')

        # Create safe filename
        safe_folder = "".join(c if c.isalnum() or c in '._- ' else '_' for c in folder_name)
        safe_name = "".join(c if c.isalnum() or c in '._- ' else '_' for c in name)

        output_path = output_dir / safe_folder / safe_name

        # Skip if already exists
        if output_path.exists():
            print(f"[{i+1}/{len(all_files)}] {folder_name}/{name} - SKIP (exists)")
            skipped += 1
            manifest['files'].append({**f, 'status': 'skipped', 'local_path': str(output_path)})
            continue

        print(f"[{i+1}/{len(all_files)}] {folder_name}/{name}... ", end='', flush=True)

        content = download_file_content(file_id, account, environment)

        if content:
            if save_file(content, output_path):
                print(f"OK ({len(content):,} bytes)")
                downloaded += 1
                manifest['files'].append({**f, 'status': 'downloaded', 'local_path': str(output_path)})
            else:
                print("SAVE FAILED")
                failed += 1
                manifest['files'].append({**f, 'status': 'save_failed'})
        else:
            print("DOWNLOAD FAILED")
            failed += 1
            manifest['files'].append({**f, 'status': 'download_failed'})

        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)

    # Save manifest
    manifest_path = output_dir / '_manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\n{'='*50}")
    print(f"SUMMARY")
    print(f"{'='*50}")
    print(f"Downloaded: {downloaded}")
    print(f"Skipped:    {skipped}")
    print(f"Failed:     {failed}")
    print(f"Total:      {len(all_files)}")
    print(f"\nManifest saved to: {manifest_path}")


if __name__ == '__main__':
    main()
