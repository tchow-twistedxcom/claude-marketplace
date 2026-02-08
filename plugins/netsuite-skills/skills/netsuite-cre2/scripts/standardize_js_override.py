#!/usr/bin/env python3
"""
Standardize all CRE2 profiles to use the same JS override file.

Usage:
    python3 standardize_js_override.py --env sb2
    python3 standardize_js_override.py --env sb2 --dry-run
"""

import json
import urllib.request
import argparse
from typing import Dict, List

GATEWAY_URL = 'http://localhost:3001/api/suiteapi'

# Standard JS override file ID (from batch_create_profiles.py)
STANDARD_JS_OVERRIDE_ID = 52794157


def execute_query(query: str, account: str, environment: str) -> List[Dict]:
    """Execute a SuiteQL query and return results."""
    payload = {
        'action': 'queryRun',
        'procedure': 'queryRun',
        'query': query,
        'params': [],
        'returnAllRows': True,
        'netsuiteAccount': account,
        'netsuiteEnvironment': environment
    }

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

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('success'):
                if result.get('rows'):
                    return result['rows']
                if result.get('data', {}).get('records'):
                    return result['data']['records']
            return []
    except Exception as e:
        print(f"Query error: {e}")
        return []


def update_profile(profile_id: int, fields: Dict, account: str, environment: str) -> Dict:
    """Update a CRE2 profile record."""
    payload = {
        'action': 'execute',
        'procedure': 'twxUpsertRecord',
        'type': 'customrecord_pri_cre2_profile',
        'id': profile_id,
        'fields': fields,
        'netsuiteAccount': account,
        'netsuiteEnvironment': environment
    }

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

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {'success': False, 'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description='Standardize JS override file for all CRE2 profiles')
    parser.add_argument('--env', default='sb2', help='Environment: prod, sb1, sb2')
    parser.add_argument('--account', default='twx', help='Account: twx, dm')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated')
    args = parser.parse_args()

    account = 'twistedx' if args.account == 'twx' else args.account
    env = {'prod': 'production', 'sb1': 'sandbox', 'sb2': 'sandbox2'}.get(args.env, args.env)

    print(f"\nStandardizing JS override file to {STANDARD_JS_OVERRIDE_ID}...")
    print(f"Environment: {account}/{env}")
    print(f"Dry run: {args.dry_run}\n")

    # Find profiles with non-standard JS override
    query = f"""
    SELECT id, name, custrecord_pri_cre2_js_override as js_file
    FROM customrecord_pri_cre2_profile
    WHERE name LIKE 'TWX-EDI-%'
      AND custrecord_pri_cre2_js_override != {STANDARD_JS_OVERRIDE_ID}
      AND custrecord_pri_cre2_js_override IS NOT NULL
    ORDER BY name
    """

    profiles = execute_query(query, account, env)

    if not profiles:
        print("All profiles already using standard JS override file!")
        return

    print(f"Found {len(profiles)} profile(s) with non-standard JS override\n")

    updated = 0
    failed = 0

    for p in profiles:
        profile_id = p.get('id')
        profile_name = p.get('name', 'Unknown')
        current_js = p.get('js_file')

        if args.dry_run:
            print(f"[DRY RUN] Would update {profile_name} (ID: {profile_id}): {current_js} -> {STANDARD_JS_OVERRIDE_ID}")
            updated += 1
        else:
            print(f"Updating {profile_name}...", end=' ')

            result = update_profile(
                profile_id,
                {'custrecord_pri_cre2_js_override': STANDARD_JS_OVERRIDE_ID},
                account,
                env
            )

            if result.get('success'):
                print("OK")
                updated += 1
            else:
                print(f"FAILED: {result.get('error', 'Unknown error')}")
                failed += 1

    print(f"\n{'=' * 50}")
    print(f"Updated: {updated}")
    if failed:
        print(f"Failed: {failed}")
    print(f"\nAll profiles now use JS override file: {STANDARD_JS_OVERRIDE_ID}")


if __name__ == '__main__':
    main()
