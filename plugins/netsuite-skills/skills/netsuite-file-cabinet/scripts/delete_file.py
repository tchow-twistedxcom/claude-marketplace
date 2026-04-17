#!/usr/bin/env python3
"""
NetSuite PCI File Deletion Tool

Reads the scan report from pci_scan.py and deletes CONFIRMED files
from the NetSuite Filing Cabinet via the fileDelete RESTlet procedure.

Features:
- Dry-run mode by default (preview without deleting)
- Requires --confirm flag to execute real deletions
- Rate-limited to avoid API throttling
- Full audit log for PCI compliance records

Usage:
  # Preview what would be deleted
  python3 delete_file.py --report /tmp/pci-scan-results/scan_report.json --dry-run

  # Execute deletions (irreversible!)
  python3 delete_file.py --report /tmp/pci-scan-results/scan_report.json --confirm

  # Delete specific file by ID (for manual cleanup)
  python3 delete_file.py --file-id 98765 --name "example.xlsx" --confirm
"""

import sys
import os
import json
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# ---------------------------------------------------------------------------
# NetSuite API Gateway (same pattern as query_netsuite.py)
# ---------------------------------------------------------------------------

import os as _os
_gw_base = _os.environ.get('NETSUITE_GATEWAY_URL', 'https://nsapi.twistedx.tech').rstrip('/')
GATEWAY_URL = f'{_gw_base}/api/suiteapi'
_API_KEY = _os.environ.get('NETSUITE_API_KEY', '')

DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'production'
DELETE_RATE_LIMIT = 0.5  # seconds between deletions (conservative — irreversible)

ACCOUNT_ALIASES = {
    'twx': 'twistedx', 'twisted': 'twistedx', 'twistedx': 'twistedx',
}
ENV_ALIASES = {
    'prod': 'production', 'production': 'production',
    'sb1': 'sandbox', 'sandbox': 'sandbox',
}


def _gateway_headers() -> dict:
    if _API_KEY:
        return {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-API-Key': _API_KEY}
    return {'Content-Type': 'application/json', 'Accept': 'application/json', 'Origin': _gw_base}


def resolve_account(account: str) -> str:
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def delete_file(
    file_id: int,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT,
) -> Dict[str, Any]:
    """
    Delete a file from NetSuite Filing Cabinet via the fileDelete RESTlet.
    Returns {'success': bool, 'error': str|None, 'response': dict|None}.
    """
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
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error from gateway'),
                    'response': result,
                }
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else str(e)
        return {'success': False, 'error': f"HTTP {e.code}: {body}", 'response': None}
    except Exception as e:
        return {'success': False, 'error': str(e), 'response': None}


# ---------------------------------------------------------------------------
# Report reading
# ---------------------------------------------------------------------------

def load_confirmed_files(report_path: str) -> List[Dict]:
    """Load CONFIRMED files from a pci_scan.py JSON report."""
    with open(report_path) as f:
        report = json.load(f)
    confirmed = report.get('confirmed', [])
    # Filter to entries that have a valid file_id
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
    print(f"\nDRY RUN — {len(files)} files would be deleted:\n")
    for i, f in enumerate(files, 1):
        hits = f.get('card_hits', [])
        hit_summary = ', '.join(h['card_type'] for h in hits[:3])
        print(f"  {i:3d}. [file_id={f['file_id']}] {f['subfolder_name']}/{f['filename']}")
        if hit_summary:
            print(f"       Cards: {hit_summary}")
    print(f"\nRun with --confirm to execute these {len(files)} deletion(s).")


# ---------------------------------------------------------------------------
# Execute deletions
# ---------------------------------------------------------------------------

def execute_deletions(
    files: List[Dict],
    account: str,
    environment: str,
    audit_log_path: Path,
) -> None:
    """Delete each file and write a per-operation audit log."""
    total = len(files)
    succeeded = 0
    failed = 0
    audit_entries = []

    print(f"\nDeleting {total} files from NetSuite ({account}/{environment})...\n")

    for i, file_entry in enumerate(files, 1):
        file_id = file_entry['file_id']
        subfolder = file_entry.get('subfolder_name', '')
        filename = file_entry.get('filename', '')
        print(f"  [{i}/{total}] file_id={file_id} {subfolder}/{filename}... ", end='', flush=True)

        result = delete_file(file_id, account, environment)
        timestamp = datetime.now().isoformat()

        audit_entry = {
            'timestamp': timestamp,
            'file_id': file_id,
            'subfolder_name': subfolder,
            'filename': filename,
            'folder_id': file_entry.get('folder_id'),
            'success': result['success'],
            'error': result.get('error'),
        }
        audit_entries.append(audit_entry)

        if result['success']:
            succeeded += 1
            print("DELETED")
        else:
            failed += 1
            print(f"FAILED — {result['error']}")

        # Write audit log after every deletion (so it's available even if interrupted)
        _write_audit_log(audit_entries, audit_log_path)
        time.sleep(DELETE_RATE_LIMIT)

    print(f"\n=== Deletion complete ===")
    print(f"  Deleted:  {succeeded}/{total}")
    print(f"  Failed:   {failed}/{total}")
    print(f"  Audit log: {audit_log_path}")

    if failed:
        print(f"\n  {failed} deletion(s) failed — check audit log for details.")


def _write_audit_log(entries: List[Dict], path: Path) -> None:
    """Write audit log JSON (overwrite each time for atomicity)."""
    log = {
        'generated_at': datetime.now().isoformat(),
        'total_operations': len(entries),
        'succeeded': sum(1 for e in entries if e['success']),
        'failed': sum(1 for e in entries if not e['success']),
        'operations': entries,
    }
    with open(path, 'w') as f:
        json.dump(log, f, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Delete PCI-flagged files from NetSuite Filing Cabinet.'
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true',
                      help='Preview what would be deleted (safe, no changes made)')
    mode.add_argument('--confirm', action='store_true',
                      help='Execute deletions (IRREVERSIBLE — use after reviewing dry-run)')

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--report',
                        help='Path to scan_report.json from pci_scan.py')
    source.add_argument('--file-id', type=int,
                        help='Delete a single file by NetSuite internal ID')

    parser.add_argument('--name', default='',
                        help='File name for audit log (used with --file-id)')
    parser.add_argument('--output-dir', default='/tmp/pci-scan-results',
                        help='Directory for audit log (default: /tmp/pci-scan-results)')
    parser.add_argument('--account', default=DEFAULT_ACCOUNT,
                        help=f'NetSuite account (default: {DEFAULT_ACCOUNT})')
    parser.add_argument('--env', default=DEFAULT_ENVIRONMENT,
                        help=f'NetSuite environment (default: {DEFAULT_ENVIRONMENT})')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_log_path = output_dir / f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    print(f"NetSuite PCI File Deletion Tool")
    print(f"  Mode:    {'DRY RUN (no changes)' if args.dry_run else 'EXECUTE (IRREVERSIBLE)'}")
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
        print(f"  Confirmed files to delete: {len(files)}")

    if not files:
        print("\nNo files to delete.")
        return

    if args.dry_run:
        print_dry_run(files)
    else:
        # Extra safety confirmation for large batches
        if len(files) > 50:
            print(f"\n  WARNING: About to permanently delete {len(files)} files from NetSuite.")
            print(f"  This cannot be undone. Type 'DELETE' to proceed: ", end='', flush=True)
            confirm = input().strip()
            if confirm != 'DELETE':
                print("  Aborted.")
                sys.exit(0)

        execute_deletions(files, args.account, args.env, audit_log_path)


if __name__ == '__main__':
    main()
