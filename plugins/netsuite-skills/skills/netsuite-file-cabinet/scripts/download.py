#!/usr/bin/env python3
"""
NetSuite File Cabinet - Unified Download Tool

Downloads files from NetSuite File Cabinet with automatic strategy selection:
- Small/shallow folders: Recursive traversal (fast for bundles)
- Large/deep folders: Hierarchical query with ID-based pagination

Features:
- Auto-detection of optimal download strategy
- Resume support (--resume continues from last file ID)
- Rate limiting to prevent API throttling
- Manifest generation for tracking
- Skip existing files
- Deduplication for hierarchical queries

Usage:
  python3 download.py --bundle 311735 --output ./backup --env prod
  python3 download.py --folder-id 18625 --output ./backup --env prod
  python3 download.py --folder-id 18625 --output ./backup --env prod --resume
  python3 download.py --folder-id 18625 --output ./backup --env prod --dry-run
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

# Thresholds for strategy selection
MAX_FOLDERS_FOR_RECURSIVE = 100  # Use hierarchical if more subfolders
MAX_FILES_FOR_RECURSIVE = 500    # Use hierarchical if more files


def resolve_account(account: str) -> str:
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def execute_query(
    query: str,
    params: Optional[List[Any]] = None,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT,
    timeout: int = 300
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

        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode('utf-8'))

            records = []
            if result.get('success') and result.get('data'):
                records = result.get('data', {}).get('records', [])
            elif 'data' in result and 'records' in result['data']:
                records = result['data']['records']
            elif 'records' in result:
                records = result['records']

            return {'records': records, 'error': None}

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        return {'records': [], 'error': f"HTTP {e.code}: {error_body}"}
    except Exception as e:
        return {'records': [], 'error': str(e)}


# =============================================================================
# Strategy Detection
# =============================================================================

def count_subfolders(folder_id: int, account: str, environment: str) -> int:
    """Count subfolders to determine strategy."""
    query = f"""
    SELECT COUNT(DISTINCT id) as cnt
    FROM MediaItemFolder
    START WITH id = {folder_id}
    CONNECT BY PRIOR id = parent
    """
    result = execute_query(query, [], account, environment)
    if result.get('records'):
        return int(result['records'][0].get('cnt', 0))
    return 0


def count_files_in_tree(folder_id: int, account: str, environment: str) -> int:
    """Count total files in folder tree."""
    query = f"""
    SELECT COUNT(DISTINCT f.id) as total
    FROM File f
    WHERE f.folder IN (
        SELECT DISTINCT id FROM MediaItemFolder
        START WITH id = {folder_id}
        CONNECT BY PRIOR id = parent
    )
    """
    result = execute_query(query, [], account, environment)
    if result.get('records'):
        return int(result['records'][0].get('total', 0))
    return 0


def detect_strategy(folder_id: int, account: str, environment: str) -> str:
    """Detect optimal download strategy based on folder structure."""
    folder_count = count_subfolders(folder_id, account, environment)

    if folder_count > MAX_FOLDERS_FOR_RECURSIVE:
        return 'hierarchical'

    file_count = count_files_in_tree(folder_id, account, environment)

    if file_count > MAX_FILES_FOR_RECURSIVE:
        return 'hierarchical'

    return 'recursive'


# =============================================================================
# Recursive Strategy (for small/shallow folders)
# =============================================================================

def get_folder_info(folder_id: int, account: str, environment: str) -> Optional[Dict]:
    """Get folder name and parent."""
    query = "SELECT id, name, parent FROM mediaitemfolder WHERE id = ?"
    result = execute_query(query, [folder_id], account, environment)
    if result.get('records'):
        return result['records'][0]
    return None


def list_subfolders(parent_folder_id: int, account: str, environment: str) -> List[Dict]:
    """List all subfolders of a folder."""
    query = "SELECT id, name, parent FROM mediaitemfolder WHERE parent = ? ORDER BY name"
    result = execute_query(query, [parent_folder_id], account, environment)
    return result.get('records', [])


def list_files_in_folder(folder_id: int, account: str, environment: str) -> List[Dict]:
    """List all files in a folder."""
    query = "SELECT id, name, filetype, filesize, url, folder FROM file WHERE folder = ? ORDER BY name"
    result = execute_query(query, [folder_id], account, environment)
    return result.get('records', [])


def get_files_recursive(
    folder_id: int,
    account: str,
    environment: str,
    base_path: str = "",
    all_files: List[Dict] = None
) -> List[Dict]:
    """Recursively get all files in a folder and its subfolders."""
    if all_files is None:
        all_files = []

    folder_info = get_folder_info(folder_id, account, environment)
    folder_name = folder_info.get('name', '') if folder_info else ''
    current_path = f"{base_path}/{folder_name}" if base_path else folder_name

    files = list_files_in_folder(folder_id, account, environment)
    for f in files:
        f['folder_name'] = folder_name
        f['relative_path'] = current_path
        all_files.append(f)

    subfolders = list_subfolders(folder_id, account, environment)
    for subfolder in subfolders:
        get_files_recursive(subfolder['id'], account, environment, current_path, all_files)

    return all_files


# =============================================================================
# Hierarchical Strategy (for large/deep folders)
# =============================================================================

def get_files_hierarchical(
    folder_id: int,
    account: str,
    environment: str,
    min_id: int = 0,
    limit: int = BATCH_SIZE
) -> Dict[str, Any]:
    """Get files using hierarchical query with ID-based pagination."""
    query = f"""
    SELECT
        f.id, f.name, f.folder, mf.name as folder_name,
        f.filesize, f.filetype, f.url
    FROM File f
    JOIN MediaItemFolder mf ON f.folder = mf.id
    WHERE f.id > {min_id}
      AND f.folder IN (
        SELECT DISTINCT id FROM MediaItemFolder
        START WITH id = {folder_id}
        CONNECT BY PRIOR id = parent
    )
    ORDER BY f.id
    FETCH FIRST {limit} ROWS ONLY
    """
    return execute_query(query, [], account, environment)


def collect_files_hierarchical(
    folder_id: int,
    account: str,
    environment: str,
    min_id: int = 0,
    max_files: Optional[int] = None
) -> List[Dict]:
    """Collect all files using hierarchical strategy with deduplication."""
    all_files = []
    seen_ids = set()
    current_min_id = min_id

    while True:
        if max_files and len(all_files) >= max_files:
            break

        batch_size = min(BATCH_SIZE, (max_files - len(all_files)) if max_files else BATCH_SIZE)
        result = get_files_hierarchical(folder_id, account, environment, current_min_id, batch_size)

        if result.get('error'):
            print(f"ERROR: {result['error']}", file=sys.stderr)
            break

        records = result.get('records', [])
        if not records:
            break

        new_records = []
        for r in records:
            file_id = r.get('id')
            if file_id and file_id not in seen_ids:
                seen_ids.add(file_id)
                new_records.append(r)
                current_min_id = max(current_min_id, file_id)

        if not new_records:
            break

        all_files.extend(new_records)
        print(f"  Collected {len(all_files)} files (last ID: {current_min_id})...", end='\r')

    print()
    return all_files


# =============================================================================
# Download Functions
# =============================================================================

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

            file_data = None
            if result.get('success') and result.get('data'):
                file_data = result.get('data', {})
                content = file_data.get('content', '')
                encoding = file_data.get('encoding', 'UTF-8')
                if encoding == 'BASE64' or file_data.get('isBase64'):
                    return base64.b64decode(content)
                return content.encode('utf-8')
            elif 'data' in result and 'file' in result['data']:
                file_data = result['data']['file']
            elif 'file' in result:
                file_data = result['file']

            if file_data and 'content' in file_data:
                return base64.b64decode(file_data['content'])

            return None

    except Exception as e:
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


def sanitize_path(name: str) -> str:
    """Create safe filename/folder name."""
    return "".join(c if c.isalnum() or c in '._- ' else '_' for c in str(name))


def load_manifest(manifest_path: Path) -> Optional[Dict]:
    """Load existing manifest for resume."""
    if manifest_path.exists():
        try:
            with open(manifest_path) as f:
                return json.load(f)
        except:
            pass
    return None


def get_last_downloaded_id(manifest: Dict) -> int:
    """Get the last successfully downloaded file ID from manifest."""
    max_id = 0
    for f in manifest.get('files', []):
        if f.get('status') == 'downloaded':
            file_id = f.get('id', 0)
            if file_id > max_id:
                max_id = file_id
    return max_id


# =============================================================================
# Bundle Support
# =============================================================================

def find_bundle_folder(bundle_number: str, account: str, environment: str) -> Optional[Dict]:
    """Find the SuiteBundle folder by bundle number."""
    bundle_folder_name = f"Bundle {bundle_number}"
    query = "SELECT id, name, parent FROM mediaitemfolder WHERE name = ?"
    result = execute_query(query, [bundle_folder_name], account, environment)

    if not result.get('records'):
        bundle_folder_name = f"Bundle{bundle_number}"
        result = execute_query(query, [bundle_folder_name], account, environment)

    if result.get('records'):
        return result['records'][0]
    return None


# =============================================================================
# Main
# =============================================================================

def print_usage():
    print("""NetSuite File Cabinet - Unified Download Tool

Usage: python3 download.py [options]

Required (one of):
  --bundle <number>      Bundle number to download
  --folder-id <id>       Folder ID to download

Options:
  --output <path>        Output directory (required for download)
  --account <account>    Account: twx, dm (default: twx)
  --env <environment>    Environment: prod, sb1, sb2 (default: prod)
  --dry-run              List files without downloading
  --resume               Resume from last downloaded file
  --offset <id>          Start from specific file ID
  --limit <n>            Limit number of files
  --strategy <type>      Force strategy: recursive, hierarchical, auto (default: auto)
  --format <fmt>         Output format: table, json (default: table)

Examples:
  # Download a bundle
  python3 download.py --bundle 311735 --output ./backup --env prod

  # Download large attachment folder
  python3 download.py --folder-id 18625 --output ./backup --env prod

  # Resume interrupted download
  python3 download.py --folder-id 18625 --output ./backup --env prod --resume

  # Dry run to preview files
  python3 download.py --folder-id 18625 --env prod --dry-run
""")


def main():
    if len(sys.argv) < 2 or '--help' in sys.argv or '-h' in sys.argv:
        print_usage()
        return

    # Parse arguments
    bundle_number = None
    folder_id = None
    output_dir = None
    account = DEFAULT_ACCOUNT
    environment = DEFAULT_ENVIRONMENT
    dry_run = False
    resume = False
    offset = 0
    limit = None
    strategy = 'auto'
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
            output_dir = Path(sys.argv[i + 1])
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
        elif arg == '--resume':
            resume = True
            i += 1
        elif arg == '--offset' and i + 1 < len(sys.argv):
            offset = int(sys.argv[i + 1])
            i += 2
        elif arg == '--limit' and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
            i += 2
        elif arg == '--strategy' and i + 1 < len(sys.argv):
            strategy = sys.argv[i + 1]
            i += 2
        elif arg == '--format' and i + 1 < len(sys.argv):
            output_format = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    if not bundle_number and not folder_id:
        print("ERROR: --bundle or --folder-id is required")
        print_usage()
        return

    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    print(f"Target: {resolved_account}/{resolved_env}")

    # Find bundle folder if specified
    if bundle_number:
        print(f"Finding Bundle {bundle_number}...")
        folder_info = find_bundle_folder(bundle_number, account, environment)
        if not folder_info:
            print(f"ERROR: Bundle {bundle_number} not found")
            return
        folder_id = folder_info['id']
        print(f"Found folder ID: {folder_id}")

    # Handle resume
    manifest_path = output_dir / '_manifest.json' if output_dir else None
    if resume and manifest_path:
        manifest = load_manifest(manifest_path)
        if manifest:
            offset = get_last_downloaded_id(manifest)
            print(f"Resuming from file ID: {offset}")

    # Detect or use specified strategy
    if strategy == 'auto':
        print("Detecting optimal strategy...")
        strategy = detect_strategy(folder_id, account, environment)
        print(f"Using strategy: {strategy}")
    else:
        print(f"Using strategy: {strategy} (forced)")

    # Count files
    print("Counting files...")
    total_files = count_files_in_tree(folder_id, account, environment)
    print(f"Total files in tree: {total_files}")

    if total_files == 0:
        print("No files found.")
        return

    # Collect files
    print("\nCollecting file metadata...")
    if strategy == 'recursive':
        all_files = get_files_recursive(folder_id, account, environment)
        if offset > 0:
            all_files = [f for f in all_files if f.get('id', 0) > offset]
    else:
        all_files = collect_files_hierarchical(folder_id, account, environment, offset, limit)

    if limit:
        all_files = all_files[:limit]

    print(f"Collected {len(all_files)} files")

    # Output file list
    if output_format == 'json':
        print(json.dumps({
            'folder_id': folder_id,
            'bundle': bundle_number,
            'total_files': len(all_files),
            'files': all_files
        }, indent=2))

    if dry_run:
        if output_format != 'json':
            print(f"\n{'ID':<10} {'Size':<12} {'Folder':<30} {'Name'}")
            print("-" * 100)
            for f in all_files[:50]:  # Show first 50 in table mode
                file_id = f.get('id', '')
                size = f.get('filesize', 0)
                size_str = f"{size:,}" if size else "?"
                folder_name = str(f.get('folder_name', ''))[:28]
                name = f.get('name', '')
                print(f"{file_id:<10} {size_str:<12} {folder_name:<30} {name}")
            if len(all_files) > 50:
                print(f"... and {len(all_files) - 50} more files")
        print(f"\nDry run - no files downloaded")
        print(f"Total: {len(all_files)} files")
        return

    # Download
    if not output_dir:
        print("ERROR: --output is required for downloading")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nDownloading to: {output_dir}")

    # Create/update manifest
    manifest = {
        'download_date': datetime.now().isoformat(),
        'account': resolved_account,
        'environment': resolved_env,
        'folder_id': folder_id,
        'bundle': bundle_number,
        'strategy': strategy,
        'total_files': len(all_files),
        'files': []
    }

    downloaded = 0
    skipped = 0
    failed = 0

    for i, f in enumerate(all_files):
        file_id = f.get('id')
        name = f.get('name', f'file_{file_id}')
        folder_name = f.get('folder_name') or f.get('relative_path', '').split('/')[-1] or 'unknown'

        safe_folder = sanitize_path(folder_name)
        safe_name = sanitize_path(name)
        output_path = output_dir / safe_folder / safe_name

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

        time.sleep(RATE_LIMIT_DELAY)

    # Save manifest
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    print(f"Downloaded: {downloaded}")
    print(f"Skipped:    {skipped}")
    print(f"Failed:     {failed}")
    print(f"Total:      {len(all_files)}")
    print(f"\nManifest saved to: {manifest_path}")


if __name__ == '__main__':
    main()
