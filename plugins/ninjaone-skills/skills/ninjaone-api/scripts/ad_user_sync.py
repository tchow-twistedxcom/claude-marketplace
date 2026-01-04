#!/usr/bin/env python3
"""
Azure AD to NinjaOne User Sync

Syncs Azure AD user information to NinjaOne device custom fields
based on last-logged-on-user data.

Usage:
    # Report mode - preview matches without changes
    python ad_user_sync.py report --org-name "Company Name"
    python ad_user_sync.py report --org-id 2 --format json

    # Sync mode - update NinjaOne custom fields
    python ad_user_sync.py sync --org-name "Company Name"
    python ad_user_sync.py sync --org-id 2 --display-name-field "adUserName"
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

# Path setup - Handle auth.py namespace collision between plugins
# Both plugins have auth.py with different classes, so we import sequentially
script_dir = Path(__file__).parent
azure_ad_path = script_dir.parents[3] / 'm365-skills' / 'skills' / 'azure-ad' / 'scripts'

# Step 1: Import Azure AD first (needs its own auth.py)
sys.path.insert(0, str(azure_ad_path))
try:
    from azure_ad_api import AzureADAPI, GraphAPIError
except ImportError:
    print("Error: Azure AD API not found. Ensure m365-skills plugin is installed.", file=sys.stderr)
    print(f"Expected path: {azure_ad_path}", file=sys.stderr)
    sys.exit(1)

# Step 2: Remove Azure AD path and all conflicting cached modules, then import NinjaOne
sys.path.remove(str(azure_ad_path))
# Both plugins have auth.py and formatters.py - clear them from cache
for mod in ['auth', 'formatters']:
    if mod in sys.modules:
        del sys.modules[mod]
sys.path.insert(0, str(script_dir))
from ninjaone_api import NinjaOneAPI, NinjaOneAPIError


class SyncError(Exception):
    """Custom exception for sync errors."""
    pass


class ADUserSync:
    """Synchronizes Azure AD user data to NinjaOne device custom fields."""

    def __init__(self, ninja_config: Optional[str] = None, azure_tenant: Optional[str] = None):
        """
        Initialize sync tool with both API clients.

        Args:
            ninja_config: Path to NinjaOne config file
            azure_tenant: Azure AD tenant name or alias
        """
        self.ninja_api = NinjaOneAPI(ninja_config)
        self.azure_api = AzureADAPI(tenant=azure_tenant)
        self.ad_user_cache: Dict[str, dict] = {}

    def normalize_username(self, ninja_username: str) -> Optional[str]:
        """
        Normalize NinjaOne username for AD lookup.

        Handles formats:
        - DOMAIN\\username -> username
        - DOMAIN/username -> username
        - username@domain.com -> username@domain.com (unchanged)
        - username -> username

        Args:
            ninja_username: Username from NinjaOne logged-on-users

        Returns:
            Normalized username for AD lookup, or None if empty
        """
        if not ninja_username:
            return None

        username = ninja_username.strip()

        # Handle DOMAIN\username format (Windows)
        if '\\' in username:
            username = username.split('\\')[-1]

        # Handle DOMAIN/username format (some systems)
        elif '/' in username and '@' not in username:
            username = username.split('/')[-1]

        # Strip Mac console/tty suffix: "jeffwammer (console)" -> "jeffwammer"
        if ' (' in username:
            username = username.split(' (')[0]

        return username.lower() if username else None

    def build_ad_user_cache(self) -> int:
        """
        Fetch all AD users and build multi-key lookup index.

        Keys indexed:
        - Full UPN (user@domain.com)
        - Email address (if different from UPN)
        - Username part only (before @)
        - sAMAccountName style (lowercase)

        Returns:
            Number of users cached
        """
        print("Fetching Azure AD users...", file=sys.stderr)

        try:
            response = self.azure_api.users_list(
                all_pages=True,
                select="id,displayName,userPrincipalName,mail,department,jobTitle"
            )
            users = response.get('value', [])
        except GraphAPIError as e:
            raise SyncError(f"Failed to fetch Azure AD users: {e}")

        for user in users:
            upn = user.get('userPrincipalName', '').lower()
            mail = (user.get('mail') or '').lower()
            username_part = upn.split('@')[0] if '@' in upn else upn

            user_info = {
                'id': user.get('id'),
                'displayName': user.get('displayName'),
                'email': mail or upn,
                'upn': upn,
                'department': user.get('department'),
                'jobTitle': user.get('jobTitle'),
            }

            # Index by multiple keys for flexible matching
            if upn:
                self.ad_user_cache[upn] = user_info
            if mail and mail != upn:
                self.ad_user_cache[mail] = user_info
            if username_part:
                self.ad_user_cache[username_part] = user_info

            # Index by concatenated display name (for Mac local accounts)
            # "Jeff Wammer" -> "jeffwammer" (matches Mac local username pattern)
            display_name = user.get('displayName', '')
            if display_name and ' ' in display_name:
                name_parts = display_name.lower().split()
                # Full concatenation: "jeffwammer"
                concat_name = ''.join(name_parts)
                if concat_name and concat_name not in self.ad_user_cache:
                    self.ad_user_cache[concat_name] = user_info

        print(f"Cached {len(users)} Azure AD users ({len(self.ad_user_cache)} lookup keys)", file=sys.stderr)
        return len(users)

    def lookup_ad_user(self, ninja_username: str) -> Optional[dict]:
        """
        Look up AD user from NinjaOne username.

        Args:
            ninja_username: Raw username from NinjaOne

        Returns:
            AD user info dict or None if not found
        """
        normalized = self.normalize_username(ninja_username)
        if not normalized:
            return None

        # Try direct lookup first
        if normalized in self.ad_user_cache:
            return self.ad_user_cache[normalized]

        # Try with common variations
        variations = [
            normalized,
            normalized.replace('.', ''),  # john.smith -> johnsmith
            normalized.split('.')[0] if '.' in normalized else None,  # john.smith -> john
        ]

        for variant in variations:
            if variant and variant in self.ad_user_cache:
                return self.ad_user_cache[variant]

        return None

    def get_devices_with_users(self, df: Optional[str] = None) -> List[dict]:
        """
        Get NinjaOne devices with their logged-on user data.

        Args:
            df: Device filter (e.g., "org = 2")

        Returns:
            List of device records with user information
        """
        print("Fetching NinjaOne logged-on users...", file=sys.stderr)

        try:
            response = self.ninja_api.query_logged_on_users(df=df)
            # Handle wrapped results
            if isinstance(response, dict) and 'results' in response:
                return response['results']
            return response if isinstance(response, list) else []
        except NinjaOneAPIError as e:
            raise SyncError(f"Failed to fetch NinjaOne users: {e}")

    def get_device_list(self, df: Optional[str] = None) -> Dict[int, dict]:
        """
        Get device ID to name mapping.

        Args:
            df: Device filter

        Returns:
            Dict mapping device_id to device info
        """
        try:
            devices = self.ninja_api.list_devices(df=df)
            return {d['id']: d for d in devices}
        except NinjaOneAPIError as e:
            raise SyncError(f"Failed to fetch device list: {e}")

    def run_report(self, df: Optional[str] = None) -> dict:
        """
        Run analysis and return report data without making changes.

        Args:
            df: Device filter

        Returns:
            Report dict with matched/unmatched devices and summary
        """
        # Get logged-on users from NinjaOne
        logged_on_users = self.get_devices_with_users(df=df)
        devices = self.get_device_list(df=df)

        matched = []
        unmatched = []

        for record in logged_on_users:
            device_id = record.get('deviceId')
            ninja_user = record.get('userName') or record.get('username') or record.get('user')
            device_info = devices.get(device_id, {})
            device_name = device_info.get('systemName') or device_info.get('dnsName') or f"Device {device_id}"

            if not ninja_user:
                unmatched.append({
                    'device_id': device_id,
                    'device_name': device_name,
                    'ninja_user': None,
                    'reason': 'No logged-on user'
                })
                continue

            ad_user = self.lookup_ad_user(ninja_user)

            if ad_user:
                matched.append({
                    'device_id': device_id,
                    'device_name': device_name,
                    'ninja_user': ninja_user,
                    'ad_user': {
                        'displayName': ad_user['displayName'],
                        'email': ad_user['email'],
                        'department': ad_user.get('department'),
                        'jobTitle': ad_user.get('jobTitle'),
                    }
                })
            else:
                unmatched.append({
                    'device_id': device_id,
                    'device_name': device_name,
                    'ninja_user': ninja_user,
                    'reason': 'No AD user found'
                })

        total = len(matched) + len(unmatched)
        match_rate = (len(matched) / total * 100) if total > 0 else 0

        return {
            'summary': {
                'devices_analyzed': total,
                'users_matched': len(matched),
                'users_not_found': len(unmatched),
                'match_rate': round(match_rate, 1)
            },
            'matched': matched,
            'unmatched': unmatched
        }

    def run_sync(
        self,
        df: Optional[str] = None,
        field_mapping: Optional[Dict[str, str]] = None,
        rate_limit: float = 0.5
    ) -> dict:
        """
        Sync AD user data to NinjaOne custom fields.

        Args:
            df: Device filter
            field_mapping: Dict mapping AD fields to NinjaOne custom field names
            rate_limit: Seconds between API calls (default 0.5)

        Returns:
            Summary dict with update counts and any errors
        """
        if field_mapping is None:
            field_mapping = {
                'displayName': 'adDisplayName',
                'email': 'adEmail'
            }

        results = {
            'updated': 0,
            'skipped': 0,
            'errors': [],
            'details': []
        }

        # Get matched devices from report
        report = self.run_report(df)

        print(f"\nSyncing {len(report['matched'])} devices...", file=sys.stderr)

        for i, match in enumerate(report['matched'], 1):
            device_id = match['device_id']
            ad_user = match['ad_user']

            # Build custom field payload
            fields = {}
            if field_mapping.get('displayName') and ad_user.get('displayName'):
                fields[field_mapping['displayName']] = ad_user['displayName']
            if field_mapping.get('email') and ad_user.get('email'):
                fields[field_mapping['email']] = ad_user['email']
            if field_mapping.get('department') and ad_user.get('department'):
                fields[field_mapping['department']] = ad_user['department']
            if field_mapping.get('jobTitle') and ad_user.get('jobTitle'):
                fields[field_mapping['jobTitle']] = ad_user['jobTitle']

            if not fields:
                results['skipped'] += 1
                continue

            try:
                self.ninja_api.update_device_custom_fields(device_id, fields)
                results['updated'] += 1
                results['details'].append({
                    'device_id': device_id,
                    'device_name': match['device_name'],
                    'status': 'updated',
                    'fields': fields
                })
                print(f"  [{i}/{len(report['matched'])}] Updated {match['device_name']}", file=sys.stderr)
            except NinjaOneAPIError as e:
                results['errors'].append({
                    'device_id': device_id,
                    'device_name': match['device_name'],
                    'error': str(e)
                })
                print(f"  [{i}/{len(report['matched'])}] Error on {match['device_name']}: {e}", file=sys.stderr)

            # Rate limiting
            if rate_limit > 0:
                time.sleep(rate_limit)

        results['skipped'] += len(report['unmatched'])

        return {
            'summary': {
                'devices_updated': results['updated'],
                'devices_skipped': results['skipped'],
                'errors_count': len(results['errors']),
                'field_mapping': field_mapping
            },
            'updated': results['details'],
            'errors': results['errors']
        }


def format_report_table(report: dict) -> str:
    """Format report as readable table."""
    lines = []
    summary = report['summary']

    lines.append("=" * 80)
    lines.append("AZURE AD USER SYNC REPORT")
    lines.append("=" * 80)
    lines.append(f"Devices Analyzed: {summary['devices_analyzed']}")
    lines.append(f"Users Matched:    {summary['users_matched']} ({summary['match_rate']}%)")
    lines.append(f"Users Not Found:  {summary['users_not_found']}")
    lines.append("")

    # Matched devices
    if report['matched']:
        lines.append("-" * 80)
        lines.append("MATCHED DEVICES (showing up to 20)")
        lines.append("-" * 80)
        lines.append(f"{'Device Name':<25} {'NinjaOne User':<20} {'AD Display Name':<20} {'AD Email':<30}")
        lines.append("-" * 80)
        for dev in report['matched'][:20]:
            ad = dev['ad_user']
            name = dev['device_name'][:24]
            ninja = (dev['ninja_user'] or '')[:19]
            display = (ad['displayName'] or '')[:19]
            email = (ad['email'] or '')[:29]
            lines.append(f"{name:<25} {ninja:<20} {display:<20} {email:<30}")
        if len(report['matched']) > 20:
            lines.append(f"... and {len(report['matched']) - 20} more")
        lines.append("")

    # Unmatched devices
    if report['unmatched']:
        lines.append("-" * 80)
        lines.append("UNMATCHED DEVICES (showing up to 20)")
        lines.append("-" * 80)
        lines.append(f"{'Device Name':<25} {'NinjaOne User':<25} {'Reason':<30}")
        lines.append("-" * 80)
        for dev in report['unmatched'][:20]:
            name = dev['device_name'][:24]
            ninja = (dev['ninja_user'] or '(none)')[:24]
            reason = dev['reason'][:29]
            lines.append(f"{name:<25} {ninja:<25} {reason:<30}")
        if len(report['unmatched']) > 20:
            lines.append(f"... and {len(report['unmatched']) - 20} more")

    lines.append("=" * 80)
    return "\n".join(lines)


def format_sync_table(result: dict) -> str:
    """Format sync result as readable table."""
    lines = []
    summary = result['summary']

    lines.append("=" * 80)
    lines.append("AZURE AD USER SYNC COMPLETE")
    lines.append("=" * 80)
    lines.append(f"Devices Updated:  {summary['devices_updated']}")
    lines.append(f"Devices Skipped:  {summary['devices_skipped']}")
    lines.append(f"Errors:           {summary['errors_count']}")
    lines.append("")
    lines.append("Field Mapping:")
    for ad_field, ninja_field in summary['field_mapping'].items():
        lines.append(f"  {ad_field} -> {ninja_field}")

    if result['errors']:
        lines.append("")
        lines.append("-" * 80)
        lines.append("ERRORS")
        lines.append("-" * 80)
        for err in result['errors']:
            lines.append(f"  {err['device_name']}: {err['error']}")

    lines.append("=" * 80)
    return "\n".join(lines)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description='Sync Azure AD user data to NinjaOne device custom fields',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Report mode - preview matches without changes
  python ad_user_sync.py report --org-name "Company Name"
  python ad_user_sync.py report --org-id 2 --format json

  # Sync mode - update NinjaOne custom fields
  python ad_user_sync.py sync --org-name "Company Name"
  python ad_user_sync.py sync --org-id 2 --display-name-field "UserName" --email-field "UserEmail"

Prerequisites:
  1. Create custom fields in NinjaOne Admin:
     - adDisplayName (text, device-level)
     - adEmail (text, device-level)
  2. Configure Azure AD credentials in m365-skills config
        """
    )

    parser.add_argument('action', choices=['report', 'sync'],
                        help='Action: report (dry-run) or sync (update fields)')

    # API configuration
    parser.add_argument('--ninja-config', help='Path to NinjaOne config file')
    parser.add_argument('--azure-tenant', '-t', help='Azure AD tenant name/alias')

    # Filtering
    parser.add_argument('--org-id', type=int, help='Filter by NinjaOne org ID')
    parser.add_argument('--org-name', help='Filter by NinjaOne org name')
    parser.add_argument('--filter', '--df', dest='df', help='Device filter expression')

    # Custom field mapping
    parser.add_argument('--display-name-field', default='adDisplayName',
                        help='NinjaOne custom field for AD display name (default: adDisplayName)')
    parser.add_argument('--email-field', default='adEmail',
                        help='NinjaOne custom field for AD email (default: adEmail)')
    parser.add_argument('--department-field',
                        help='Optional: NinjaOne custom field for department')
    parser.add_argument('--job-title-field',
                        help='Optional: NinjaOne custom field for job title')

    # Sync options
    parser.add_argument('--rate-limit', type=float, default=0.5,
                        help='Seconds between API calls (default: 0.5)')

    # Output options
    parser.add_argument('--format', '-f', choices=['table', 'json'],
                        default='table', help='Output format (default: table)')

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        syncer = ADUserSync(args.ninja_config, args.azure_tenant)

        # Build AD user cache
        syncer.build_ad_user_cache()

        # Build device filter
        df = args.df
        if args.org_name:
            org = syncer.ninja_api.find_organization_by_name(args.org_name)
            if not org:
                print(f"Error: Organization not found: {args.org_name}", file=sys.stderr)
                sys.exit(1)
            org_filter = f"org = {org['id']}"
            df = f"{df} AND {org_filter}" if df else org_filter
            print(f"Resolved '{args.org_name}' to organization ID {org['id']}", file=sys.stderr)
        elif args.org_id:
            org_filter = f"org = {args.org_id}"
            df = f"{df} AND {org_filter}" if df else org_filter

        # Build field mapping
        field_mapping = {
            'displayName': args.display_name_field,
            'email': args.email_field,
        }
        if args.department_field:
            field_mapping['department'] = args.department_field
        if args.job_title_field:
            field_mapping['jobTitle'] = args.job_title_field

        # Execute action
        if args.action == 'report':
            result = syncer.run_report(df=df)
            if args.format == 'json':
                print(json.dumps(result, indent=2))
            else:
                print(format_report_table(result))
        else:  # sync
            result = syncer.run_sync(df=df, field_mapping=field_mapping, rate_limit=args.rate_limit)
            if args.format == 'json':
                print(json.dumps(result, indent=2))
            else:
                print(format_sync_table(result))

    except GraphAPIError as e:
        print(f"Azure AD API error: {e}", file=sys.stderr)
        sys.exit(1)
    except NinjaOneAPIError as e:
        print(f"NinjaOne API error: {e}", file=sys.stderr)
        sys.exit(1)
    except SyncError as e:
        print(f"Sync error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
