#!/usr/bin/env python3
"""
NetSuite File Deletion Tool

Delete files from the NetSuite File Cabinet via the fileDelete RESTlet procedure,
with automatic local backup for restore. Each deleted file is downloaded to a
local "trash bin" directory first, and a restore manifest is written listing
every file's original location and metadata so the deletion can be reversed.

Features:
- Dry-run mode (default-blocking — must pass --dry-run or --confirm explicitly)
- Local backup of every file BEFORE deletion (opt-out with --force-without-backup)
- Per-run trash directory keyed by timestamp + environment
- Restore manifest (restore_manifest.json) capturing folder_id, name, type, size,
  backup path, and deletion status for each file
- Rate-limited to avoid API throttling
- Bulk deletion from a report OR single-file deletion by ID

Trash bin layout:
  ./trash-bin/
    └── 20260420_193045_sandbox2/
         ├── restore_manifest.json
         └── files/
              ├── 55342202_twx_CS_CommChannel.js
              └── 55342201_twx_CS_CommPref.js

Usage:
  # Preview what would be deleted (no backup, no changes)
  python3 delete_file.py --file-id 55342202 --name "old.js" --dry-run --env sb2

  # Delete a single file (backs up first, then deletes)
  python3 delete_file.py --file-id 55342202 --name "old.js" --confirm --env sb2

  # Bulk delete from a report (e.g. pci_scan.py output)
  python3 delete_file.py --report /tmp/pci-scan-results/scan_report.json --confirm

  # Override the trash bin location
  python3 delete_file.py --file-id 55342202 --confirm --env sb2 \\
      --trash-dir /home/tchow/NetSuiteBundlet/trash-bin

Restore:
  Given a restore_manifest.json, re-upload each file to its original folder:
      python3 upload_file.py --file <trash_dir>/files/<backup_name> \\
          --folder-id <folder_id> --name <original_name> --env <env>
  (A dedicated --restore flag / script is a likely follow-up.)
"""

import sys
import os
import json
import time
import base64
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# ---------------------------------------------------------------------------
# NetSuite API Gateway (same pattern as query_netsuite.py)
# ---------------------------------------------------------------------------

_gw_base = os.environ.get('NETSUITE_GATEWAY_URL', 'https://nsapi.twistedx.tech').rstrip('/')
GATEWAY_URL = f'{_gw_base}/api/suiteapi'
_API_KEY = os.environ.get('NETSUITE_API_KEY', '')

DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'production'
DELETE_RATE_LIMIT = 0.5  # seconds between deletions (conservative — irreversible)

ACCOUNT_ALIASES = {
    'twx': 'twistedx', 'twisted': 'twistedx', 'twistedx': 'twistedx',
    'dm': 'dutyman', 'duty': 'dutyman', 'dutyman': 'dutyman',
}
ENV_ALIASES = {
    'prod': 'production', 'production': 'production',
    'sb1': 'sandbox', 'sandbox': 'sandbox', 'sandbox1': 'sandbox',
    'sb2': 'sandbox2', 'sandbox2': 'sandbox2',
}


def _gateway_headers() -> dict:
    if _API_KEY:
        return {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-API-Key': _API_KEY}
    return {'Content-Type': 'application/json', 'Accept': 'application/json', 'Origin': _gw_base}


def resolve_account(account: str) -> str:
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    return ENV_ALIASES.get(environment.lower(), environment.lower())


# ---------------------------------------------------------------------------
# Gateway operations
# ---------------------------------------------------------------------------

def _decode_gateway_content(content_b64: str) -> bytes:
    """Decode fileGet content, handling the gateway's double-base64 wrapping.

    Pattern lifted from download_file.py:decode_file_content — the gateway
    wraps the RESTlet's base64 response in another base64 layer for binary
    files. A single decode yields a base64 string; we detect and peel the
    inner layer.
    """
    first = base64.b64decode(content_b64)
    try:
        intermediate = first.decode('utf-8')
        return base64.b64decode(intermediate)
    except (UnicodeDecodeError, Exception):
        return first


def fetch_file_content(
    file_id: int,
    account: str,
    environment: str,
) -> Dict[str, Any]:
    """Fetch file content + metadata via the fileGet RESTlet procedure.

    Returns {'success': bool, 'error': str|None, 'info': dict, 'content_bytes': bytes, 'is_binary': bool}.
    """
    payload = {
        'action': 'fileGet',
        'procedure': 'fileGet',
        'id': file_id,
        'netsuiteAccount': resolve_account(account),
        'netsuiteEnvironment': resolve_environment(environment),
    }
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(GATEWAY_URL, data=data, headers=_gateway_headers())
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            if not result.get('success'):
                err = result.get('error', 'Unknown error from gateway')
                if isinstance(err, dict):
                    err = err.get('message', str(err))
                return {'success': False, 'error': err, 'info': {}, 'content_bytes': b'', 'is_binary': False}

            file_data = result.get('data', {}).get('file', {})
            info = file_data.get('info', {})
            content_b64 = file_data.get('content', '')
            if not content_b64:
                return {'success': False, 'error': 'No content returned from gateway', 'info': info,
                        'content_bytes': b'', 'is_binary': False}

            content_bytes = _decode_gateway_content(content_b64)
            # Heuristic: if the bytes decode cleanly as UTF-8, treat as text
            try:
                content_bytes.decode('utf-8')
                is_binary = False
            except UnicodeDecodeError:
                is_binary = True

            return {'success': True, 'error': None, 'info': info,
                    'content_bytes': content_bytes, 'is_binary': is_binary}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else str(e)
        return {'success': False, 'error': f"HTTP {e.code}: {body}",
                'info': {}, 'content_bytes': b'', 'is_binary': False}
    except Exception as e:
        return {'success': False, 'error': str(e),
                'info': {}, 'content_bytes': b'', 'is_binary': False}


def delete_file(
    file_id: int,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT,
) -> Dict[str, Any]:
    """Delete a file from NetSuite File Cabinet via the fileDelete RESTlet."""
    payload = {
        'action': 'fileDelete',
        'procedure': 'fileDelete',
        'id': file_id,
        'netsuiteAccount': resolve_account(account),
        'netsuiteEnvironment': resolve_environment(environment),
    }
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(GATEWAY_URL, data=data, headers=_gateway_headers())
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            if result.get('success'):
                return {'success': True, 'error': None, 'response': result}
            return {'success': False, 'error': result.get('error', 'Unknown error from gateway'),
                    'response': result}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else str(e)
        return {'success': False, 'error': f"HTTP {e.code}: {body}", 'response': None}
    except Exception as e:
        return {'success': False, 'error': str(e), 'response': None}


# ---------------------------------------------------------------------------
# Local backup
# ---------------------------------------------------------------------------

_SAFE_FILENAME_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")


def _safe_filename(name: str) -> str:
    """Sanitize a filename for local filesystem: replace unsafe chars with '_'."""
    if not name:
        return 'unnamed'
    return ''.join(c if c in _SAFE_FILENAME_CHARS else '_' for c in name)


def backup_file(
    file_id: int,
    fallback_name: str,
    files_dir: Path,
    account: str,
    environment: str,
) -> Dict[str, Any]:
    """Download file content to files_dir/<file_id>_<name> and return manifest metadata.

    Returns a dict with keys: success, error, backup_path (relative to trash_dir),
    name, folder_id, file_type, size, is_binary.
    """
    fetch = fetch_file_content(file_id, account, environment)
    if not fetch['success']:
        return {
            'success': False,
            'error': fetch['error'],
            'backup_path': None,
            'name': fallback_name,
            'folder_id': None,
            'file_type': None,
            'size': None,
            'is_binary': None,
        }

    info = fetch['info'] or {}
    ns_name = info.get('name') or fallback_name or f'file_{file_id}'
    safe = _safe_filename(ns_name)
    backup_filename = f"{file_id}_{safe}"
    backup_path = files_dir / backup_filename
    files_dir.mkdir(parents=True, exist_ok=True)
    try:
        with open(backup_path, 'wb') as f:
            f.write(fetch['content_bytes'])
    except OSError as e:
        return {
            'success': False,
            'error': f'Local write failed: {e}',
            'backup_path': None,
            'name': ns_name,
            'folder_id': info.get('folder'),
            'file_type': info.get('fileType'),
            'size': info.get('size'),
            'is_binary': fetch['is_binary'],
        }

    return {
        'success': True,
        'error': None,
        'backup_path': f'files/{backup_filename}',
        'name': ns_name,
        'folder_id': info.get('folder'),
        'file_type': info.get('fileType'),
        'size': info.get('size') if info.get('size') is not None else len(fetch['content_bytes']),
        'is_binary': fetch['is_binary'],
    }


# ---------------------------------------------------------------------------
# Report reading
# ---------------------------------------------------------------------------

def load_confirmed_files(report_path: str) -> List[Dict]:
    """Load CONFIRMED files from a pci_scan.py JSON report."""
    with open(report_path) as f:
        report = json.load(f)
    confirmed = report.get('confirmed', [])
    valid = [e for e in confirmed if e.get('file_id')]
    skipped = len(confirmed) - len(valid)
    if skipped:
        print(f"  WARN: {skipped} confirmed entries have no file_id — skipping", file=sys.stderr)
    return valid


# ---------------------------------------------------------------------------
# Dry-run preview
# ---------------------------------------------------------------------------

def print_dry_run(files: List[Dict]) -> None:
    """Print a preview of files that would be deleted."""
    print(f"\nDRY RUN — {len(files)} file(s) would be deleted:\n")
    for i, f in enumerate(files, 1):
        subfolder = f.get('subfolder_name') or ''
        filename = f.get('filename') or ''
        location = f"{subfolder}/{filename}" if subfolder else filename
        print(f"  {i:3d}. [file_id={f['file_id']}] {location}")
        hits = f.get('card_hits') or []
        if hits:
            print(f"       Cards: {', '.join(h['card_type'] for h in hits[:3])}")
    print(f"\nRun with --confirm to execute these {len(files)} deletion(s).")
    print("Each file will be backed up locally to the trash bin before deletion.")


# ---------------------------------------------------------------------------
# Execute deletions
# ---------------------------------------------------------------------------

def execute_deletions(
    files: List[Dict],
    account: str,
    environment: str,
    trash_dir: Path,
    manifest_path: Path,
    force_without_backup: bool,
) -> None:
    """Back up each file locally, then delete. Write a restore manifest."""
    total = len(files)
    deleted = 0
    failed_delete = 0
    skipped_no_backup = 0
    backup_failures = 0
    operations: List[Dict] = []

    files_dir = trash_dir / 'files'

    print(f"\nProcessing {total} file(s) from NetSuite ({account}/{environment})...")
    print(f"  Trash dir:      {trash_dir}")
    print(f"  Restore manifest: {manifest_path}\n")

    for i, entry in enumerate(files, 1):
        file_id = entry['file_id']
        subfolder = entry.get('subfolder_name') or ''
        fallback_name = entry.get('filename') or entry.get('name') or ''
        location_hint = f"{subfolder}/{fallback_name}" if subfolder else fallback_name
        print(f"  [{i}/{total}] file_id={file_id} {location_hint}")

        # 1) Back up
        print(f"         backing up... ", end='', flush=True)
        backup = backup_file(file_id, fallback_name, files_dir, account, environment)
        if backup['success']:
            print(f"OK → {backup['backup_path']} ({backup['size']} bytes)")
        else:
            backup_failures += 1
            print(f"FAILED — {backup['error']}")
            if not force_without_backup:
                skipped_no_backup += 1
                operations.append({
                    'timestamp': datetime.now().isoformat(),
                    'file_id': file_id,
                    'name': backup['name'],
                    'folder_id': backup['folder_id'],
                    'subfolder_name_from_report': subfolder,
                    'file_type': backup['file_type'],
                    'size': backup['size'],
                    'is_binary': backup['is_binary'],
                    'backup_path': None,
                    'backed_up': False,
                    'deleted': False,
                    'skipped_reason': 'backup_failed',
                    'error': backup['error'],
                })
                _write_manifest(operations, manifest_path, account, environment, trash_dir)
                time.sleep(DELETE_RATE_LIMIT)
                continue
            print("         --force-without-backup set, proceeding without backup")

        # 2) Delete
        print(f"         deleting...  ", end='', flush=True)
        result = delete_file(file_id, account, environment)
        timestamp = datetime.now().isoformat()

        op: Dict[str, Any] = {
            'timestamp': timestamp,
            'file_id': file_id,
            'name': backup['name'],
            'folder_id': backup['folder_id'],
            'subfolder_name_from_report': subfolder,
            'file_type': backup['file_type'],
            'size': backup['size'],
            'is_binary': backup['is_binary'],
            'backup_path': backup['backup_path'],
            'backed_up': backup['success'],
            'deleted': result['success'],
            'error': result.get('error'),
        }
        operations.append(op)

        if result['success']:
            deleted += 1
            print("DELETED")
        else:
            failed_delete += 1
            print(f"FAILED — {result['error']}")

        _write_manifest(operations, manifest_path, account, environment, trash_dir)
        time.sleep(DELETE_RATE_LIMIT)

    print(f"\n=== Run complete ===")
    print(f"  Deleted:            {deleted}/{total}")
    print(f"  Deletion failures:  {failed_delete}/{total}")
    print(f"  Backup failures:    {backup_failures}/{total}")
    print(f"  Skipped (no backup):{skipped_no_backup}/{total}")
    print(f"  Restore manifest:   {manifest_path}")

    if skipped_no_backup:
        print(f"\n  {skipped_no_backup} file(s) were NOT deleted because backup failed.")
        print(f"  Re-run to retry, or pass --force-without-backup to delete anyway (irreversible).")
    if failed_delete:
        print(f"\n  {failed_delete} deletion(s) failed — the backup copy is still in the trash bin.")


def _write_manifest(
    operations: List[Dict],
    path: Path,
    account: str,
    environment: str,
    trash_dir: Path,
) -> None:
    """Write restore manifest JSON atomically after each operation."""
    manifest = {
        'generated_at': datetime.now().isoformat(),
        'account': resolve_account(account),
        'environment': resolve_environment(environment),
        'trash_dir': str(trash_dir.resolve()),
        'total_operations': len(operations),
        'deleted': sum(1 for e in operations if e.get('deleted')),
        'deletion_failures': sum(1 for e in operations if e.get('backed_up') and not e.get('deleted')),
        'skipped_no_backup': sum(1 for e in operations if e.get('skipped_reason') == 'backup_failed'),
        'operations': operations,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.json.tmp')
    with open(tmp, 'w') as f:
        json.dump(manifest, f, indent=2)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Delete files from NetSuite File Cabinet with local backup & restore manifest.'
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true',
                      help='Preview what would be deleted (safe, no changes made)')
    mode.add_argument('--confirm', action='store_true',
                      help='Back up and execute deletions (irreversible on NetSuite side, but local backup preserves content)')

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--report',
                        help='Path to scan_report.json (e.g. from pci_scan.py)')
    source.add_argument('--file-id', type=int,
                        help='Delete a single file by NetSuite internal ID')

    parser.add_argument('--name', default='',
                        help='File name hint for manifest (used with --file-id; overridden by NetSuite metadata when available)')
    parser.add_argument('--trash-dir', default='./trash-bin',
                        help='Parent trash bin directory (default: ./trash-bin in CWD). A per-run subdirectory keyed by timestamp+env is created inside.')
    parser.add_argument('--output-dir', default=None,
                        help='[Deprecated] Alias for --trash-dir. Retained for backwards compatibility.')
    parser.add_argument('--force-without-backup', action='store_true',
                        help='Proceed with deletion even if local backup fails (DANGEROUS — unrecoverable).')
    parser.add_argument('--account', default=DEFAULT_ACCOUNT,
                        help=f'NetSuite account (default: {DEFAULT_ACCOUNT})')
    parser.add_argument('--env', default=DEFAULT_ENVIRONMENT,
                        help=f'NetSuite environment (default: {DEFAULT_ENVIRONMENT})')
    args = parser.parse_args()

    # Resolve trash bin parent (support legacy --output-dir as alias)
    trash_parent = Path(args.output_dir or args.trash_dir)
    resolved_env = resolve_environment(args.env)
    run_stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    trash_dir = trash_parent / f"{run_stamp}_{resolved_env}"
    manifest_path = trash_dir / 'restore_manifest.json'

    print(f"NetSuite File Deletion Tool")
    print(f"  Mode:    {'DRY RUN (no changes)' if args.dry_run else 'EXECUTE (with local backup)'}")
    print(f"  Account: {args.account} / {args.env}")

    # Build file list
    if args.file_id:
        files = [{
            'file_id': args.file_id,
            'subfolder_name': '',
            'filename': args.name,
            'folder_id': None,
            'card_hits': [],
        }]
    else:
        print(f"  Report:  {args.report}")
        files = load_confirmed_files(args.report)
        print(f"  Files to delete: {len(files)}")

    if not files:
        print("\nNo files to delete.")
        return

    if args.dry_run:
        print_dry_run(files)
        return

    # Extra safety confirmation for large batches
    if len(files) > 50:
        print(f"\n  WARNING: About to permanently delete {len(files)} files from NetSuite.")
        print(f"  Local backups will be written to {trash_dir} before deletion.")
        print(f"  Type 'DELETE' to proceed: ", end='', flush=True)
        confirm = input().strip()
        if confirm != 'DELETE':
            print("  Aborted.")
            sys.exit(0)

    trash_dir.mkdir(parents=True, exist_ok=True)
    execute_deletions(
        files,
        args.account,
        args.env,
        trash_dir,
        manifest_path,
        args.force_without_backup,
    )


if __name__ == '__main__':
    main()
