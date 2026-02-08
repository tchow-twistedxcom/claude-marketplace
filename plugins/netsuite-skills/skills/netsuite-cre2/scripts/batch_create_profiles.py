#!/usr/bin/env python3
"""
CRE2 Batch Profile Creator

Creates CRE2 profiles for all active trading partners across all document types.
Uses the twxUpsertRecord procedure to create profiles in NetSuite.

Usage:
    python3 batch_create_profiles.py [options]

Options:
    --env ENV           Environment: prod, sb1, sb2 (default: sb2)
    --account ACCOUNT   Account: twx, dm (default: twx)
    --dry-run           Show what would be created without actually creating
    --partner PARTNER   Create profiles only for specified partner code
    --doctype DOCTYPE   Create profiles only for specified document type (810, 850, etc.)
    --skip-existing     Skip if profile name already exists (default behavior)
    --list-partners     List all active partners and exit
    --list-doctypes     List document type configurations and exit

Examples:
    # Create all profiles in sandbox2
    python3 batch_create_profiles.py --env sb2

    # Dry run to preview
    python3 batch_create_profiles.py --env sb2 --dry-run

    # Create only for Cavenders
    python3 batch_create_profiles.py --env sb2 --partner CAVENDERS

    # Create only 810 profiles
    python3 batch_create_profiles.py --env sb2 --doctype 810
"""

import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Any, Optional
import time

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

# CRE2 Profile Configuration
# Record type ID for customrecord_twx_edi_history
RECORD_TYPE_ID = 2288

# JS Override (Data Extractor) - shared across all profiles
JS_OVERRIDE_ID = 52794157

# Data source query - same for all profiles
# Fetches EDI JSON and trading partner info for the current record
DATA_SOURCE_QUERY = """SELECT h.id, h.name, h.custrecord_twx_edi_history_json AS edi_json, h.custrecord_twx_eth_edi_tp AS trading_partner, h.custrecord_twx_edi_type AS doc_type, h.custrecord_twx_edi_history_status AS status, h.created AS created_date, tp.custrecord_twx_edi_tp_logo AS tp_logo_id, tp.name AS tp_name FROM customrecord_twx_edi_history h LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id WHERE h.id = ${record.id}"""

# Document Type Configurations (Default/Generic Templates)
DOCUMENT_TYPES = {
    '810': {
        'name': 'Invoice',
        'template_id': 52794158,  # TWX_EDI_810_PDF.html
        'edi_type_id': 1,  # NetSuite list value for 810
        'file_name': 'EDI_810_${record.id}.pdf'
    },
    '850': {
        'name': 'Purchase Order',
        'template_id': 52794159,  # TWX_EDI_850_PDF.html
        'edi_type_id': 3,  # NetSuite list value for 850
        'file_name': 'EDI_850_${record.id}.pdf'
    },
    '855': {
        'name': 'PO Acknowledgment',
        'template_id': 52794160,  # TWX_EDI_855_PDF.html
        'edi_type_id': 4,  # NetSuite list value for 855
        'file_name': 'EDI_855_${record.id}.pdf'
    },
    '856': {
        'name': 'Advance Ship Notice',
        'template_id': 52794161,  # TWX_EDI_856_PDF.html
        'edi_type_id': 5,  # NetSuite list value for 856
        'file_name': 'EDI_856_${record.id}.pdf'
    },
    '860': {
        'name': 'PO Change',
        'template_id': 52794162,  # TWX_EDI_860_PDF.html
        'edi_type_id': 6,  # NetSuite list value for 860
        'file_name': 'EDI_860_${record.id}.pdf'
    },
    '846': {
        'name': 'Inventory Advice',
        'template_id': 52797358,  # TWX_EDI_846_ROCKY_PDF.html (Rocky-specific for now)
        'edi_type_id': 2,  # NetSuite list value for 846
        'file_name': 'EDI_846_${record.id}.pdf'
    },
    '820': {
        'name': 'Payment Order/Remittance Advice',
        'template_id': 52797363,  # TWX_EDI_820_AMAZONVENDORCENTRAL_PDF.html
        'edi_type_id': 7,  # NetSuite list value for 820
        'file_name': 'EDI_820_${record.id}.pdf'
    },
    '824': {
        'name': 'Application Advice',
        'template_id': 52797558,  # TWX_EDI_824_AMAZONVENDORCENTRAL_PDF.html
        'edi_type_id': 12,  # NetSuite list value for 824
        'file_name': 'EDI_824_${record.id}.pdf'
    },
    '852': {
        'name': 'Product Activity Data',
        'template_id': 52798761,  # TWX_EDI_852_PDF.html
        'edi_type_id': 11,  # NetSuite list value for 852
        'file_name': 'EDI_852_${record.id}.pdf'
    },
    '864': {
        'name': 'Text Message',
        'template_id': 52798858,  # TWX_EDI_864_PDF.html
        'edi_type_id': 7,  # NetSuite list value for 864
        'file_name': 'EDI_864_${record.id}.pdf'
    },
    # Warehouse Document Types (for 3PL warehouses like Next Point Logistics)
    '940': {
        'name': 'Warehouse Shipping Order',
        'template_id': 52797959,  # TWX_EDI_940_NXTP_PDF.html
        'edi_type_id': 8,  # NetSuite list value for 940
        'file_name': 'EDI_940_${record.id}.pdf'
    },
    '943': {
        'name': 'Stock Transfer Shipment',
        'template_id': 52797960,  # TWX_EDI_943_NXTP_PDF.html
        'edi_type_id': 14,  # NetSuite list value for 943
        'file_name': 'EDI_943_${record.id}.pdf'
    },
    '944': {
        'name': 'Stock Transfer Receipt',
        'template_id': 52797961,  # TWX_EDI_944_NXTP_PDF.html
        'edi_type_id': 15,  # NetSuite list value for 944
        'file_name': 'EDI_944_${record.id}.pdf'
    },
    '945': {
        'name': 'Warehouse Shipping Advice',
        'template_id': 52797962,  # TWX_EDI_945_NXTP_PDF.html
        'edi_type_id': 9,  # NetSuite list value for 945
        'file_name': 'EDI_945_${record.id}.pdf'
    }
}

# Partner-Specific Template Overrides
# Format: ('PARTNER_CODE', 'DOC_TYPE') -> template_file_id
# When a partner-specific template exists, it overrides the default
PARTNER_TEMPLATES = {
    # Rocky Brands
    ('ROCKY', '810'): 52794156,   # TWX_EDI_810_ROCKY_PDF.html
    ('ROCKY', '850'): 52794801,   # TWX_EDI_850_ROCKY_PDF.html
    ('ROCKY', '856'): 52794680,   # TWX_EDI_856_ROCKY_PDF.html
    ('ROCKY', '846'): 52797358,   # TWX_EDI_846_ROCKY_PDF.html
    # Amazon Vendor Central
    ('AMAZONVENDORCENTRAL', '810'): 52794748,  # TWX_EDI_810_AMAZONVENDORCENTRAL_PDF.html
    ('AMAZONVENDORCENTRAL', '850'): 52794890,  # TWX_EDI_850_AMAZONVENDORCENTRAL_PDF.html
    ('AMAZONVENDORCENTRAL', '855'): 52794891,  # TWX_EDI_855_AMAZONVENDORCENTRAL_PDF.html
    ('AMAZONVENDORCENTRAL', '856'): 52795160,  # TWX_EDI_856_AMAZONVENDORCENTRAL_PDF.html
    ('AMAZONVENDORCENTRAL', '820'): 52797363,  # TWX_EDI_820_AMAZONVENDORCENTRAL_PDF.html
    ('AMAZONVENDORCENTRAL', '824'): 52797558,  # TWX_EDI_824_AMAZONVENDORCENTRAL_PDF.html
    # Academy
    ('ACADEMY', '810'): 52794658,  # TWX_EDI_810_ACADEMY_PDF.html
    ('ACADEMY', '850'): 52794659,  # TWX_EDI_850_ACADEMY_PDF.html
    ('ACADEMY', '856'): 52794661,  # TWX_EDI_856_ACADEMY_PDF.html
    # Atwoods
    ('ATWOODS', '850'): 52797560,  # TWX_EDI_850_ATWOODS_PDF.html
    # Bomgaars
    ('BOMGAARS', '810'): 52794561,  # TWX_EDI_810_BOMGAARS_PDF.html
    ('BOMGAARS', '850'): 52794562,  # TWX_EDI_850_BOMGAARS_PDF.html
    # Boot Barn
    ('BOOTBARN', '810'): 52794565,  # TWX_EDI_810_BOOTBARN_PDF.html
    ('BOOTBARN', '850'): 52794668,  # TWX_EDI_850_BOOTBARN_PDF.html
    ('BOOTBARN', '855'): 52794566,  # TWX_EDI_855_BOOTBARN_PDF.html
    ('BOOTBARN', '856'): 52794567,  # TWX_EDI_856_BOOTBARN_PDF.html
    # Mid-States Distributing
    ('MIDSYORK', '824'): 52797858,  # TWX_EDI_824_MIDSTATES_PDF.html
    # Next Point Logistics (Warehouse Documents Only)
    ('NXTP', '940'): 52797959,  # TWX_EDI_940_NXTP_PDF.html
    ('NXTP', '943'): 52797960,  # TWX_EDI_943_NXTP_PDF.html
    ('NXTP', '944'): 52797961,  # TWX_EDI_944_NXTP_PDF.html
    ('NXTP', '945'): 52797962,  # TWX_EDI_945_NXTP_PDF.html
}


def get_template_id(partner_code: str, doc_type: str) -> int:
    """Get the template ID for a partner/doctype combination.
    Returns partner-specific template if exists, otherwise default.
    """
    key = (partner_code.upper(), doc_type)
    if key in PARTNER_TEMPLATES:
        return PARTNER_TEMPLATES[key]
    return DOCUMENT_TYPES[doc_type]['template_id']

DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox2'


def resolve_account(account: str) -> str:
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def load_partner_mappings() -> Dict[str, Any]:
    """Load partner mappings from the B2bDashboard config."""
    config_path = Path('/home/tchow/B2bDashboard/config/partner-mappings.json')

    if not config_path.exists():
        # Try relative path from current directory
        config_path = Path('config/partner-mappings.json')

    if not config_path.exists():
        raise FileNotFoundError(f"Partner mappings not found at {config_path}")

    with open(config_path, 'r') as f:
        return json.load(f)


def get_active_partners(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract active partners with valid NetSuite IDs."""
    partners = []
    for key, partner in config.get('partners', {}).items():
        # Only include active partners with valid numeric IDs
        if partner.get('isActive', False) and partner.get('partnerNumericId') is not None:
            partners.append({
                'directory': key,
                'code': partner.get('partnerCode', ''),
                'name': partner.get('partnerName', ''),
                'numeric_id': partner.get('partnerNumericId')
            })

    # Sort by partner code
    return sorted(partners, key=lambda x: x['code'])


def get_existing_profiles(account: str, environment: str) -> Dict[str, int]:
    """Query existing CRE2 profiles and return name -> id mapping."""
    query = "SELECT id, name FROM customrecord_pri_cre2_profile WHERE name LIKE 'TWX-EDI-%' AND isinactive = 'F'"

    payload = {
        'action': 'queryRun',
        'procedure': 'queryRun',
        'query': query,
        'params': [],
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
            if result.get('success'):
                records = result.get('data', {}).get('records', [])
                return {r['name']: r['id'] for r in records}
    except Exception as e:
        print(f"Warning: Could not fetch existing profiles: {e}")

    return {}


def create_profile(
    profile_name: str,
    template_id: int,
    file_name: str,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """Create a CRE2 profile using twxUpsertRecord."""

    payload = {
        'action': 'execute',
        'procedure': 'twxUpsertRecord',
        'type': 'customrecord_pri_cre2_profile',
        'id': 0,  # 0 = create new
        'fields': {
            'name': profile_name,
            'custrecord_pri_cre2_rectype': RECORD_TYPE_ID,
            'custrecord_pri_cre2_recname': 'record',
            'custrecord_pri_cre2_gen_file_tmpl_doc': template_id,
            'custrecord_pri_cre2_js_override': JS_OVERRIDE_ID,
            'custrecord_pri_cre2_gen_file_name': file_name,
            'custrecord_pri_cre2_gen_file_public': True,
            'isinactive': False
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
            if result.get('success'):
                return {
                    'success': True,
                    'id': result.get('data', {}).get('id'),
                    'name': profile_name
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'name': profile_name
                }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'name': profile_name
        }


def create_data_source(
    profile_id: int,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """Create a data source (query) record for a CRE2 profile."""

    payload = {
        'action': 'execute',
        'procedure': 'twxUpsertRecord',
        'type': 'customrecord_pri_cre2_query',
        'id': 0,  # 0 = create new
        'fields': {
            'name': 'edi',
            'custrecord_pri_cre2q_parent': profile_id,
            'custrecord_pri_cre2q_query': DATA_SOURCE_QUERY,
            'custrecord_pri_cre2q_paged': False,
            'custrecord_pri_cre2q_single_record_json': False
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
            if result.get('success'):
                return {
                    'success': True,
                    'id': result.get('data', {}).get('id'),
                    'profile_id': profile_id
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'profile_id': profile_id
                }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'profile_id': profile_id
        }


def print_usage():
    print(__doc__)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Create CRE2 profiles for all trading partners',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--env', '-e', default=DEFAULT_ENVIRONMENT,
                        help=f'NetSuite environment (default: {DEFAULT_ENVIRONMENT})')
    parser.add_argument('--account', '-a', default=DEFAULT_ACCOUNT,
                        help=f'NetSuite account (default: {DEFAULT_ACCOUNT})')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without creating')
    parser.add_argument('--partner', '-p',
                        help='Create profiles only for specified partner code')
    parser.add_argument('--doctype', '-d',
                        help='Create profiles only for specified document type')
    parser.add_argument('--skip-existing', action='store_true', default=True,
                        help='Skip profiles that already exist (default)')
    parser.add_argument('--list-partners', action='store_true',
                        help='List all active partners and exit')
    parser.add_argument('--list-doctypes', action='store_true',
                        help='List document type configurations and exit')

    args = parser.parse_args()

    # Load partner mappings
    try:
        config = load_partner_mappings()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    partners = get_active_partners(config)

    # Handle list commands
    if args.list_partners:
        print(f"\nActive Partners ({len(partners)}):")
        print("-" * 60)
        for p in partners:
            print(f"  {p['code']:15} | {p['name'][:35]:35} | NS ID: {p['numeric_id']}")
        sys.exit(0)

    if args.list_doctypes:
        print("\nDocument Type Configurations:")
        print("-" * 60)
        for code, cfg in DOCUMENT_TYPES.items():
            print(f"  {code} - {cfg['name']:20} | Template: {cfg['template_id']}")
        sys.exit(0)

    # Filter partners if specified
    if args.partner:
        partners = [p for p in partners if p['code'].upper() == args.partner.upper()]
        if not partners:
            print(f"ERROR: Partner '{args.partner}' not found")
            sys.exit(1)

    # Filter document types if specified
    doc_types = DOCUMENT_TYPES
    if args.doctype:
        if args.doctype not in DOCUMENT_TYPES:
            print(f"ERROR: Document type '{args.doctype}' not valid. Use: {', '.join(DOCUMENT_TYPES.keys())}")
            sys.exit(1)
        doc_types = {args.doctype: DOCUMENT_TYPES[args.doctype]}

    # Calculate total profiles to create
    total_profiles = len(partners) * len(doc_types)

    print(f"\nCRE2 Batch Profile Creator")
    print(f"=" * 60)
    print(f"Environment: {resolve_account(args.account)}/{resolve_environment(args.env)}")
    print(f"Partners: {len(partners)}")
    print(f"Document Types: {len(doc_types)}")
    print(f"Total Profiles: {total_profiles}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"=" * 60)

    if args.dry_run:
        print("\n[DRY RUN] Would create the following profiles:\n")
        for partner in partners:
            for doc_code, doc_cfg in doc_types.items():
                profile_name = f"TWX-EDI-{doc_code}-{partner['code']}-PDF"
                print(f"  {profile_name} (Template: {doc_cfg['template_id']})")
        print(f"\nTotal: {total_profiles} profiles")
        sys.exit(0)

    # Get existing profiles
    print("\nChecking existing profiles...")
    existing = get_existing_profiles(args.account, args.env)
    print(f"Found {len(existing)} existing EDI profiles")

    # Create profiles
    created = 0
    skipped = 0
    failed = 0
    errors = []

    print("\nCreating profiles...\n")

    for i, partner in enumerate(partners, 1):
        for doc_code, doc_cfg in doc_types.items():
            profile_name = f"TWX-EDI-{doc_code}-{partner['code']}-PDF"

            # Skip if already exists
            if profile_name in existing:
                print(f"  SKIP: {profile_name} (already exists)")
                skipped += 1
                continue

            # Get template ID (partner-specific if available, else default)
            template_id = get_template_id(partner['code'], doc_code)

            # Create profile
            result = create_profile(
                profile_name=profile_name,
                template_id=template_id,
                file_name=doc_cfg['file_name'],
                account=args.account,
                environment=args.env
            )

            if result.get('success'):
                profile_id = result.get('id')
                print(f"  ✓ Created: {profile_name} (ID: {profile_id})")

                # Create data source for the profile
                ds_result = create_data_source(
                    profile_id=profile_id,
                    account=args.account,
                    environment=args.env
                )
                if ds_result.get('success'):
                    print(f"    + Data source created (ID: {ds_result.get('id')})")
                else:
                    print(f"    ! Data source failed: {ds_result.get('error')}")

                created += 1
            else:
                print(f"  ✗ FAILED: {profile_name} - {result.get('error')}")
                failed += 1
                errors.append({
                    'name': profile_name,
                    'error': result.get('error')
                })

            # Small delay to avoid rate limiting
            time.sleep(0.2)

        # Progress indicator
        pct = (i / len(partners)) * 100
        print(f"\n  Progress: {i}/{len(partners)} partners ({pct:.0f}%)\n")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Created: {created}")
    print(f"Skipped: {skipped}")
    print(f"Failed:  {failed}")
    print(f"Total:   {created + skipped + failed}")

    if errors:
        print("\nErrors:")
        for err in errors:
            print(f"  - {err['name']}: {err['error']}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
