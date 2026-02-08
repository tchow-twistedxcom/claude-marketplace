#!/usr/bin/env python3
"""
Batch Create Partner-Specific CRE2 Templates

Creates unique templates for each trading partner and document type combination.
Each partner gets their own template file so they can be customized independently.

Phase 1 of the CRE2 implementation plan.

Usage:
  python3 batch_create_templates.py --env sb2 --dry-run
  python3 batch_create_templates.py --env sb2
"""

import sys
import os
import json
import time
import base64
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List
from datetime import datetime

# NetSuite API Gateway endpoint
GATEWAY_URL = 'http://localhost:3001/api/suiteapi'

# Account/Environment aliases
ACCOUNT_ALIASES = {
    'twx': 'twistedx', 'twisted': 'twistedx', 'twistedx': 'twistedx',
    'dm': 'dutyman', 'duty': 'dutyman', 'dutyman': 'dutyman'
}

ENV_ALIASES = {
    'prod': 'production', 'production': 'production',
    'sb1': 'sandbox', 'sandbox': 'sandbox', 'sandbox1': 'sandbox',
    'sb2': 'sandbox2', 'sandbox2': 'sandbox2'
}

# Template folder in NetSuite File Cabinet
TEMPLATE_FOLDER_ID = 1285029

# Base templates - local file paths (SDF directory)
LOCAL_TEMPLATE_DIR = '/home/tchow/B2bDashboard/sdf/FileCabinet/SuiteScripts/Twisted X/CRE2/templates'
BASE_TEMPLATES = {
    '810': 'TWX_EDI_810_PDF.html',
    '850': 'TWX_EDI_850_PDF.html',
    '855': 'TWX_EDI_855_PDF.html',
    '856': 'TWX_EDI_856_PDF.html',
    '860': 'TWX_EDI_860_PDF.html',
}

# Document type descriptions
DOC_TYPE_DESCRIPTIONS = {
    '810': 'Invoice',
    '850': 'Purchase Order',
    '855': 'PO Acknowledgment',
    '856': 'Advance Ship Notice',
    '860': 'PO Change',
}

# Trading partners (from the plan)
TRADING_PARTNERS = [
    'ACADEMY',
    'ATWOOD',
    'BOMGAARS',
    'BOOTBARN',
    'BUCHHEIT',
    'CAVENDERS',
    'COASTAL',
    'COUNTRY',
    'DBS',
    'DEALRISE',
    'FAMILY',
    'GALLS',
    'HOUSER',
    'LOWES',
    'MIDSYORK',
    'MURDOCHS',
    'NXTP',
    'ROCKY',
    'RUNNINGS',
    'RURALKING',
    'SAFETY',
    'SCHEELS',
    'SHEPLERS',
    'SHOECARNIVAL',
    'SHOESENSATION',
    'STARR',
    'SUNANDSKI',
    'SUPERSHOES',
    'ZULILY',
]

DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox2'


def resolve_account(account: str) -> str:
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def execute_query(query: str, params: Optional[List] = None, account: str = DEFAULT_ACCOUNT, environment: str = DEFAULT_ENVIRONMENT) -> Dict:
    """Execute a SuiteQL query."""
    payload = {
        'action': 'queryRun',
        'procedure': 'queryRun',
        'query': query,
        'params': params or [],
        'returnAllRows': True,
        'netsuiteAccount': resolve_account(account),
        'netsuiteEnvironment': resolve_environment(environment)
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
            return result.get('data', {}).get('records', [])
    except Exception as e:
        print(f"Query error: {e}")
        return []


def get_local_template_content(filename: str) -> Optional[str]:
    """Read template content from local SDF directory."""
    filepath = os.path.join(LOCAL_TEMPLATE_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading local file {filepath}: {e}")
    return None


def upload_file(content: str, filename: str, folder_id: int, account: str, environment: str) -> Dict:
    """Upload a file to NetSuite File Cabinet."""
    payload = {
        'action': 'execute',
        'procedure': 'fileCreate',
        'name': filename,
        'fileType': 'HTMLDOC',
        'contents': content,
        'description': f'CRE2 partner-specific template - Generated {datetime.now().strftime("%Y-%m-%d")}',
        'encoding': 'UTF-8',
        'folderID': folder_id,
        'isOnline': False,
        'isInactive': False,
        'netsuiteAccount': resolve_account(account),
        'netsuiteEnvironment': resolve_environment(environment)
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
            if result.get('success'):
                file_info = result.get('data', {}).get('file', {}).get('info', {})
                return {'success': True, 'file_id': file_info.get('id'), 'name': file_info.get('name')}
            else:
                return {'success': False, 'error': result.get('error', {}).get('message', 'Unknown error')}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def update_profile_template(profile_id: int, template_id: int, account: str, environment: str) -> bool:
    """Update a CRE2 profile to use a specific template."""
    payload = {
        'action': 'execute',
        'procedure': 'twxUpsertRecord',
        'type': 'customrecord_pri_cre2_profile',
        'id': profile_id,
        'fields': {
            'custrecord_pri_cre2_gen_file_tmpl_doc': template_id
        },
        'netsuiteAccount': resolve_account(account),
        'netsuiteEnvironment': resolve_environment(environment)
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
            return result.get('success', False)
    except Exception as e:
        print(f"Error updating profile {profile_id}: {e}")
        return False


def customize_template(base_content: str, partner: str, doc_type: str) -> str:
    """Customize template header for a specific partner."""
    doc_desc = DOC_TYPE_DESCRIPTIONS.get(doc_type, doc_type)
    today = datetime.now().strftime('%Y-%m-%d')

    # Update the version comment in the template
    old_comment_patterns = [
        f'<!-- CRE2 Template: {doc_type} {doc_desc} PDF for Rocky Brands',
        f'<!-- CRE2 Template: {doc_type} {doc_desc} PDF - Generic',
        f'<!-- CRE2 Template: {doc_type} Invoice PDF',
        f'<!-- CRE2 Template: {doc_type} Purchase Order PDF',
        f'<!-- CRE2 Template: {doc_type} PO Acknowledgment PDF',
        f'<!-- CRE2 Template: {doc_type} Advance Ship Notice PDF',
        f'<!-- CRE2 Template: {doc_type} PO Change PDF',
    ]

    new_comment = f'<!-- CRE2 Template: {doc_type} {doc_desc} PDF for {partner} - v1.0.0 Generated {today} -->'

    # Replace version comment
    customized = base_content
    for old_pattern in old_comment_patterns:
        if old_pattern in customized:
            # Find the end of the comment line
            start = customized.find(old_pattern)
            end = customized.find('-->', start) + 3
            customized = customized[:start] + new_comment + customized[end:]
            break
    else:
        # If no pattern found, insert after <head>
        if '<head>' in customized:
            customized = customized.replace('<head>', f'<head>\n    {new_comment}', 1)

    return customized


def get_existing_profiles(account: str, environment: str) -> Dict[str, int]:
    """Get mapping of profile names to IDs."""
    profiles = execute_query(
        "SELECT id, name FROM customrecord_pri_cre2_profile WHERE name LIKE 'TWX-EDI-%' ORDER BY name",
        account=account, environment=environment
    )
    return {p['name']: p['id'] for p in profiles}


def get_existing_templates(account: str, environment: str) -> Dict[str, int]:
    """Get mapping of template filenames to IDs."""
    templates = execute_query(
        f"SELECT id, name FROM file WHERE folder = {TEMPLATE_FOLDER_ID}",
        account=account, environment=environment
    )
    return {t['name']: t['id'] for t in templates}


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Create partner-specific CRE2 templates')
    parser.add_argument('--env', default='sandbox2', help='Environment (sb2, prod)')
    parser.add_argument('--account', default='twistedx', help='Account (twx, dm)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')
    parser.add_argument('--partner', help='Process single partner only')
    parser.add_argument('--doc-type', help='Process single document type only (810, 850, etc.)')
    args = parser.parse_args()

    account = args.account
    environment = args.env
    dry_run = args.dry_run

    print(f"\n{'='*70}")
    print(f"CRE2 Partner-Specific Template Generator")
    print(f"{'='*70}")
    print(f"Account: {resolve_account(account)}")
    print(f"Environment: {resolve_environment(environment)}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"Template Folder ID: {TEMPLATE_FOLDER_ID}")
    print(f"{'='*70}\n")

    # Filter partners and doc types if specified
    partners = [args.partner.upper()] if args.partner else TRADING_PARTNERS
    doc_types = [args.doc_type] if args.doc_type else list(BASE_TEMPLATES.keys())

    total_templates = len(partners) * len(doc_types)
    print(f"Partners: {len(partners)}")
    print(f"Document types: {len(doc_types)}")
    print(f"Total templates to create: {total_templates}\n")

    if dry_run:
        print("DRY RUN - No changes will be made\n")
        for partner in partners:
            for doc_type in doc_types:
                filename = f"TWX_EDI_{doc_type}_{partner}_PDF.html"
                profile_name = f"TWX-EDI-{doc_type}-{partner}-PDF"
                print(f"  Would create: {filename} for profile {profile_name}")
        print(f"\nTotal: {total_templates} templates would be created")
        return

    # Get existing data
    print("Loading existing profiles...")
    existing_profiles = get_existing_profiles(account, environment)
    print(f"  Found {len(existing_profiles)} profiles")

    print("Loading existing templates...")
    existing_templates = get_existing_templates(account, environment)
    print(f"  Found {len(existing_templates)} templates\n")

    # Load base templates from local SDF directory
    print("Loading base templates from local SDF directory...")
    base_templates = {}
    for doc_type, filename in BASE_TEMPLATES.items():
        if doc_type not in doc_types:
            continue
        content = get_local_template_content(filename)
        if content:
            base_templates[doc_type] = content
            print(f"  {doc_type}: Loaded ({len(content)} chars) from {filename}")
        else:
            print(f"  {doc_type}: FAILED to load from {filename}")

    if not base_templates:
        print("\nERROR: No base templates loaded!")
        sys.exit(1)

    print(f"\nStarting template creation...\n")

    created = 0
    skipped = 0
    updated = 0
    failed = 0

    # Template creation results for profile updates
    template_map = {}  # {profile_name: template_id}

    for i, partner in enumerate(partners, 1):
        print(f"\n[{i}/{len(partners)}] {partner}")

        for doc_type in doc_types:
            filename = f"TWX_EDI_{doc_type}_{partner}_PDF.html"
            profile_name = f"TWX-EDI-{doc_type}-{partner}-PDF"

            # Skip if template already exists
            if filename in existing_templates:
                template_map[profile_name] = existing_templates[filename]
                print(f"  {doc_type}: Template exists (ID: {existing_templates[filename]})")
                skipped += 1
                continue

            # Skip Rocky's 810 - it already has a custom template
            if partner == 'ROCKY' and doc_type == '810':
                template_map[profile_name] = 52794257  # Existing Rocky template
                print(f"  {doc_type}: Using existing Rocky template (52794257)")
                skipped += 1
                continue

            # Get base template for this doc type
            if doc_type not in base_templates:
                print(f"  {doc_type}: No base template available - SKIPPED")
                skipped += 1
                continue

            # Customize and upload
            customized = customize_template(base_templates[doc_type], partner, doc_type)
            result = upload_file(customized, filename, TEMPLATE_FOLDER_ID, account, environment)

            if result.get('success'):
                file_id = result.get('file_id')
                template_map[profile_name] = file_id
                print(f"  {doc_type}: Created → ID: {file_id}")
                created += 1
            else:
                print(f"  {doc_type}: FAILED - {result.get('error')}")
                failed += 1

            time.sleep(0.2)  # Rate limiting

    print(f"\n{'='*70}")
    print("TEMPLATE CREATION COMPLETE")
    print(f"{'='*70}")
    print(f"Created: {created}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print(f"{'='*70}\n")

    # Now update profiles to use their specific templates
    print("Updating profiles with template assignments...\n")

    for profile_name, template_id in template_map.items():
        if profile_name not in existing_profiles:
            print(f"  {profile_name}: Profile not found - SKIPPED")
            continue

        profile_id = existing_profiles[profile_name]
        if update_profile_template(profile_id, template_id, account, environment):
            print(f"  {profile_name} (ID: {profile_id}) → Template: {template_id}")
            updated += 1
        else:
            print(f"  {profile_name}: Update FAILED")
            failed += 1

        time.sleep(0.1)

    print(f"\n{'='*70}")
    print("PROFILE UPDATE COMPLETE")
    print(f"{'='*70}")
    print(f"Templates created: {created}")
    print(f"Templates skipped: {skipped}")
    print(f"Profiles updated: {updated}")
    print(f"Failed: {failed}")
    print(f"{'='*70}\n")

    # Save results
    results = {
        'timestamp': datetime.now().isoformat(),
        'account': resolve_account(account),
        'environment': resolve_environment(environment),
        'templates_created': created,
        'templates_skipped': skipped,
        'profiles_updated': updated,
        'failed': failed,
        'template_map': template_map
    }

    results_file = f"/tmp/cre2_template_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {results_file}")


if __name__ == '__main__':
    main()
