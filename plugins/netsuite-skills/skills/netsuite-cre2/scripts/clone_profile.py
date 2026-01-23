#!/usr/bin/env python3
"""
NetSuite CRE 2.0 Profile Cloner

Clone an existing CRE2 profile for a new trading partner or variant.
Creates new profile with same settings and clones all data sources.

Usage:
  python3 clone_profile.py <source_id> --name "New Profile Name" [options]

Examples:
  # Clone profile 17 for Rocky Brands
  python3 clone_profile.py 17 --name "TWX-EDI-810-ROCKY-PDF" --env sb2

  # Clone with new template file
  python3 clone_profile.py 17 --name "TWX-EDI-810-ACME-PDF" --template 52794300 --env sb2
"""

import sys
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List

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
            records = result.get('data', {}).get('records', []) if result.get('success') else []
            return {
                'records': records,
                'count': len(records),
                'error': result.get('error') if not result.get('success') else None
            }

    except Exception as e:
        return {'error': str(e), 'records': [], 'count': 0}


def create_record(
    record_type: str,
    fields: Dict[str, Any],
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """Create a new record via the API Gateway."""
    payload = {
        'action': 'recordCreate',
        'procedure': 'recordCreate',
        'recordType': record_type,
        'fields': fields,
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
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'id': None,
                    'error': result.get('error', 'Unknown error')
                }

    except Exception as e:
        return {'success': False, 'id': None, 'error': str(e)}


def get_profile(profile_id: int, account: str, environment: str) -> Optional[Dict]:
    """Get profile details."""
    query = """
    SELECT
        id,
        name,
        custrecord_pri_cre2_rectype AS record_type_id,
        custrecord_pri_cre2_recname AS record_name_field,
        custrecord_pri_cre2_gen_file_tmpl_doc AS template_id,
        custrecord_pri_cre2_js_override AS js_hook_id,
        custrecord_pri_cre2_send_email AS send_email,
        custrecord_pri_cre2_email_to AS email_to,
        custrecord_pri_cre2_email_subject AS email_subject,
        custrecord_pri_cre2_email_body AS email_body,
        isinactive AS inactive
    FROM customrecord_pri_cre2_profile
    WHERE id = ?
    """
    result = execute_query(query, params=[profile_id], account=account, environment=environment)
    if result.get('records'):
        return result['records'][0]
    return None


def get_datasources(profile_id: int, account: str, environment: str) -> List[Dict]:
    """Get data sources for a profile."""
    query = """
    SELECT
        id,
        name,
        custrecord_pri_cre2q_query AS query_sql,
        custrecord_pri_cre2q_querytype AS query_type,
        custrecord_pri_cre2q_paged AS paged,
        custrecord_pri_cre2q_single_record_json AS single_record_json
    FROM customrecord_pri_cre2_query
    WHERE custrecord_pri_cre2q_parent = ?
    ORDER BY name
    """
    result = execute_query(query, params=[profile_id], account=account, environment=environment)
    return result.get('records', [])


def clone_profile(
    source_id: int,
    new_name: str,
    new_template_id: Optional[int] = None,
    new_js_hook_id: Optional[int] = None,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """Clone a CRE2 profile and its data sources."""

    # Step 1: Get source profile
    print(f"Fetching source profile {source_id}...")
    source = get_profile(source_id, account, environment)
    if not source:
        return {'success': False, 'error': f'Source profile {source_id} not found'}

    print(f"  Source: {source.get('name')}")

    # Step 2: Get source data sources
    print("Fetching data sources...")
    datasources = get_datasources(source_id, account, environment)
    print(f"  Found {len(datasources)} data source(s)")

    # Step 3: Create new profile
    print(f"\nCreating new profile: {new_name}")
    profile_fields = {
        'name': new_name,
        'custrecord_pri_cre2_rectype': source.get('record_type_id'),
        'custrecord_pri_cre2_recname': source.get('record_name_field') or 'record',
        'custrecord_pri_cre2_gen_file_tmpl_doc': new_template_id or source.get('template_id'),
        'custrecord_pri_cre2_js_override': new_js_hook_id or source.get('js_hook_id'),
        'isinactive': 'F'
    }

    # Copy email settings if present
    if source.get('send_email') == 'T':
        profile_fields['custrecord_pri_cre2_send_email'] = 'T'
        if source.get('email_to'):
            profile_fields['custrecord_pri_cre2_email_to'] = source.get('email_to')
        if source.get('email_subject'):
            profile_fields['custrecord_pri_cre2_email_subject'] = source.get('email_subject')
        if source.get('email_body'):
            profile_fields['custrecord_pri_cre2_email_body'] = source.get('email_body')

    # Remove None values
    profile_fields = {k: v for k, v in profile_fields.items() if v is not None}

    profile_result = create_record('customrecord_pri_cre2_profile', profile_fields, account, environment)

    if not profile_result.get('success'):
        return {'success': False, 'error': f"Failed to create profile: {profile_result.get('error')}"}

    new_profile_id = profile_result.get('id')
    print(f"  ✅ Created profile ID: {new_profile_id}")

    # Step 4: Clone data sources
    cloned_queries = []
    for ds in datasources:
        print(f"  Cloning data source: {ds.get('name')}...")
        query_fields = {
            'name': ds.get('name'),
            'custrecord_pri_cre2q_parent': new_profile_id,
            'custrecord_pri_cre2q_query': ds.get('query_sql'),
        }

        # Copy optional fields
        if ds.get('query_type'):
            query_fields['custrecord_pri_cre2q_querytype'] = ds.get('query_type')
        if ds.get('paged') == 'T':
            query_fields['custrecord_pri_cre2q_paged'] = 'T'
        if ds.get('single_record_json') == 'T':
            query_fields['custrecord_pri_cre2q_single_record_json'] = 'T'

        query_result = create_record('customrecord_pri_cre2_query', query_fields, account, environment)

        if query_result.get('success'):
            cloned_queries.append({
                'name': ds.get('name'),
                'source_id': ds.get('id'),
                'new_id': query_result.get('id')
            })
            print(f"    ✅ Created query ID: {query_result.get('id')}")
        else:
            print(f"    ❌ Failed: {query_result.get('error')}")

    return {
        'success': True,
        'source_profile_id': source_id,
        'new_profile_id': new_profile_id,
        'new_profile_name': new_name,
        'template_id': new_template_id or source.get('template_id'),
        'js_hook_id': new_js_hook_id or source.get('js_hook_id'),
        'cloned_queries': cloned_queries
    }


def print_usage():
    print("""CRE 2.0 Profile Cloner

Usage: python3 clone_profile.py <source_id> --name "New Name" [options]

Required:
  <source_id>            Source profile ID to clone
  --name <name>          Name for the new profile

Options:
  --template <id>        New template file ID (defaults to source template)
  --js-hook <id>         New JS hook file ID (defaults to source JS hook)
  --account <account>    Account: twx, dm (default: twistedx)
  --env <environment>    Environment: prod, sb1, sb2 (default: sb2)

Examples:
  # Clone profile 17 for Rocky Brands
  python3 clone_profile.py 17 --name "TWX-EDI-810-ROCKY-PDF" --env sb2

  # Clone with new template
  python3 clone_profile.py 17 --name "TWX-EDI-810-ACME-PDF" --template 52794300 --env sb2

Note: The NetSuite API Gateway must be running at http://localhost:3001
""")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help', 'help']:
        print_usage()
        sys.exit(0)

    # Parse arguments
    source_id = None
    new_name = None
    new_template_id = None
    new_js_hook_id = None
    account = DEFAULT_ACCOUNT
    environment = DEFAULT_ENVIRONMENT

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg == '--name' and i + 1 < len(sys.argv):
            new_name = sys.argv[i + 1]
            i += 2
        elif arg == '--template' and i + 1 < len(sys.argv):
            new_template_id = int(sys.argv[i + 1])
            i += 2
        elif arg == '--js-hook' and i + 1 < len(sys.argv):
            new_js_hook_id = int(sys.argv[i + 1])
            i += 2
        elif arg == '--account' and i + 1 < len(sys.argv):
            account = sys.argv[i + 1]
            i += 2
        elif arg == '--env' and i + 1 < len(sys.argv):
            environment = sys.argv[i + 1]
            i += 2
        elif source_id is None and not arg.startswith('--'):
            source_id = int(arg)
            i += 1
        else:
            i += 1

    # Validate required arguments
    if source_id is None:
        print("ERROR: Source profile ID required")
        print_usage()
        sys.exit(1)

    if new_name is None:
        print("ERROR: --name is required")
        print_usage()
        sys.exit(1)

    # Execute clone
    print(f"\nCloning profile {source_id} in {resolve_account(account)}/{resolve_environment(environment)}...")
    print("=" * 60)

    result = clone_profile(
        source_id=source_id,
        new_name=new_name,
        new_template_id=new_template_id,
        new_js_hook_id=new_js_hook_id,
        account=account,
        environment=environment
    )

    print("\n" + "=" * 60)
    if result.get('success'):
        print("✅ Clone successful!")
        print(f"\nNew Profile:")
        print(f"  ID:       {result.get('new_profile_id')}")
        print(f"  Name:     {result.get('new_profile_name')}")
        print(f"  Template: {result.get('template_id')}")
        print(f"  JS Hook:  {result.get('js_hook_id')}")
        if result.get('cloned_queries'):
            print(f"\nCloned Queries:")
            for q in result.get('cloned_queries', []):
                print(f"  - {q.get('name')}: {q.get('source_id')} → {q.get('new_id')}")
    else:
        print(f"❌ Clone failed: {result.get('error')}")
        sys.exit(1)


if __name__ == '__main__':
    main()
