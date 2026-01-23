#!/usr/bin/env python3
"""
NetSuite CRE 2.0 Profile Manager

List, view, and test CRE 2.0 profiles using the NetSuite API Gateway.
Supports multiple environments (production, sandbox, sandbox2).

Commands:
  list              List all CRE2 profiles
  get <id>          Get profile details including data sources
  full-config <id>  Get complete configuration including template and JS hook files
  test <id> <rec>   Test render profile for a record ID
  datasources <id>  List data sources for a profile
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
    'prod': 'production',
    'production': 'production',
    'sb1': 'sandbox',
    'sandbox': 'sandbox',
    'sandbox1': 'sandbox',
    'sb2': 'sandbox2',
    'sandbox2': 'sandbox2'
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

# Default settings
DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox2'


def resolve_account(account: str) -> str:
    """Resolve account alias to canonical name."""
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    """Resolve environment alias to canonical name."""
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

        with urllib.request.urlopen(req, timeout=60) as response:
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


def get_file_info(file_id: int, account: str, environment: str) -> Optional[Dict]:
    """Get file name and folder info."""
    if not file_id:
        return None

    query = """
    SELECT
        f.id,
        f.name,
        f.folder,
        fld.name AS folder_name
    FROM file f
    LEFT JOIN mediaitemfolder fld ON f.folder = fld.id
    WHERE f.id = ?
    """

    result = execute_query(query, params=[file_id], account=account, environment=environment)
    if result.get('records'):
        return result['records'][0]
    return None


def get_folder_path(folder_id: int, account: str, environment: str, max_depth: int = 5) -> str:
    """Build full folder path by walking up parent chain."""
    if not folder_id:
        return ""

    path_parts = []
    current_id = folder_id
    depth = 0

    while current_id and depth < max_depth:
        query = """
        SELECT id, name, parent
        FROM mediaitemfolder
        WHERE id = ?
        """
        result = execute_query(query, params=[current_id], account=account, environment=environment)
        if not result.get('records'):
            break

        folder = result['records'][0]
        path_parts.insert(0, folder.get('name', ''))
        current_id = folder.get('parent')
        depth += 1

    return '/' + '/'.join(path_parts) if path_parts else ''


def list_profiles(account: str = DEFAULT_ACCOUNT, environment: str = DEFAULT_ENVIRONMENT) -> None:
    """List all CRE2 profiles."""
    query = """
    SELECT
        ID,
        Name,
        BUILTIN.DF(custrecord_pri_cre2_rectype) AS RecordType,
        custrecord_pri_cre2_gen_file_tmpl_doc AS Template,
        custrecord_pri_cre2_send_email AS SendEmail,
        isinactive AS Inactive
    FROM customrecord_pri_cre2_profile
    ORDER BY Name
    """

    print(f"Fetching CRE2 profiles from {resolve_account(account)}/{resolve_environment(environment)}...")
    results = execute_query(query, account=account, environment=environment)

    if results.get('error'):
        print(f"ERROR: {results['error']}")
        return

    if results['count'] == 0:
        print("No CRE2 profiles found.")
        return

    print(f"\nFound {results['count']} CRE2 profile(s):\n")
    print(f"{'ID':<6} {'Name':<40} {'Record Type':<25} {'Email':<10} {'Active':<6}")
    print("-" * 95)

    for profile in results['records']:
        active = "No" if profile.get('inactive') == 'T' else "Yes"
        send_email = "Yes" if profile.get('sendemail') == 'T' else "No"
        print(f"{profile.get('id', ''):<6} {profile.get('name', '')[:40]:<40} "
              f"{profile.get('recordtype', '')[:25]:<25} {send_email:<10} {active:<6}")


def get_profile(profile_id: int, account: str = DEFAULT_ACCOUNT, environment: str = DEFAULT_ENVIRONMENT) -> None:
    """Get detailed information about a specific profile."""
    query = """
    SELECT
        ID,
        Name,
        BUILTIN.DF(custrecord_pri_cre2_rectype) AS RecordType,
        custrecord_pri_cre2_rectype AS RecordTypeId,
        custrecord_pri_cre2_gen_file_tmpl_doc AS Template,
        custrecord_pri_cre2_js_override AS JsHook,
        custrecord_pri_cre2_send_email AS SendEmail,
        custrecord_pri_cre2_email_to AS EmailTo,
        custrecord_pri_cre2_email_subject AS EmailSubject,
        custrecord_pri_cre2_email_body AS EmailBody,
        isinactive AS Inactive,
        created AS Created,
        lastmodified AS LastModified
    FROM customrecord_pri_cre2_profile
    WHERE ID = ?
    """

    print(f"Fetching profile {profile_id} from {resolve_account(account)}/{resolve_environment(environment)}...")
    results = execute_query(query, params=[profile_id], account=account, environment=environment)

    if results.get('error'):
        print(f"ERROR: {results['error']}")
        return

    if results['count'] == 0:
        print(f"Profile {profile_id} not found.")
        return

    profile = results['records'][0]

    print(f"\n{'='*60}")
    print(f"CRE2 Profile: {profile.get('name', 'Unknown')}")
    print(f"{'='*60}")
    print(f"ID:           {profile.get('id', '')}")
    print(f"Record Type:  {profile.get('recordtype', '')} (ID: {profile.get('recordtypeid', '')})")
    print(f"Template:     File ID {profile.get('template', 'None')}")
    print(f"JS Hook:      File ID {profile.get('jshook', 'None')}")
    print(f"Send Email:   {'Yes' if profile.get('sendemail') == 'T' else 'No'}")
    print(f"Active:       {'No' if profile.get('inactive') == 'T' else 'Yes'}")
    print(f"Created:      {profile.get('created', '')}")
    print(f"Modified:     {profile.get('lastmodified', '')}")

    if profile.get('emailto'):
        print(f"Email To:     {profile.get('emailto', '')}")
    if profile.get('emailsubject'):
        print(f"Email Subject: {profile.get('emailsubject', '')}")

    # Get data sources
    print(f"\n--- Data Sources ---")
    get_datasources(profile_id, account, environment, quiet=True)


def get_datasources(profile_id: int, account: str = DEFAULT_ACCOUNT, environment: str = DEFAULT_ENVIRONMENT, quiet: bool = False) -> List[Dict]:
    """List data sources (queries) for a profile."""
    # CRE2 uses customrecord_pri_cre2_query for data sources
    query = """
    SELECT
        q.id,
        q.name,
        q.custrecord_pri_cre2q_query AS query_sql,
        q.custrecord_pri_cre2q_querytype AS query_type,
        q.custrecord_pri_cre2q_paged AS paged,
        q.custrecord_pri_cre2q_single_record_json AS single_record_json
    FROM customrecord_pri_cre2_query q
    WHERE q.custrecord_pri_cre2q_parent = ?
    ORDER BY q.name
    """

    if not quiet:
        print(f"Fetching data sources for profile {profile_id}...")

    results = execute_query(query, params=[profile_id], account=account, environment=environment)

    if results.get('error'):
        print(f"  Error fetching data sources: {results['error']}")
        return []

    if results['count'] == 0:
        print("  No data sources (queries) found for this profile.")
        return []

    print(f"\n  Found {results['count']} data source(s):")
    print(f"  {'ID':<6} {'Name':<20} {'Paged':<8} {'JSON':<8} {'Query'}")
    print("  " + "-" * 80)

    for ds in results['records']:
        paged = 'Yes' if ds.get('paged') == 'T' else 'No'
        json_mode = 'Yes' if ds.get('single_record_json') == 'T' else 'No'
        if ds.get('query_sql'):
            sql = ds.get('query_sql', '')
            # Truncate for display
            details = sql[:40].replace('\n', ' ') + ('...' if len(sql) > 40 else '')
        else:
            details = "(No query configured)"

        print(f"  {ds.get('id', ''):<6} {ds.get('name', '')[:20]:<20} {paged:<8} {json_mode:<8} {details}")

    return results['records']


def full_config(profile_id: int, account: str = DEFAULT_ACCOUNT, environment: str = DEFAULT_ENVIRONMENT) -> None:
    """Get complete configuration including template and JS hook file details."""
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    # Get profile with all fields
    query = """
    SELECT
        p.id,
        p.name,
        BUILTIN.DF(p.custrecord_pri_cre2_rectype) AS record_type,
        p.custrecord_pri_cre2_rectype AS record_type_id,
        p.custrecord_pri_cre2_gen_file_tmpl_doc AS template_id,
        p.custrecord_pri_cre2_js_override AS js_hook_id,
        p.custrecord_pri_cre2_send_email AS send_email,
        p.custrecord_pri_cre2_email_to AS email_to,
        p.custrecord_pri_cre2_email_subject AS email_subject,
        p.isinactive AS inactive,
        p.created,
        p.lastmodified
    FROM customrecord_pri_cre2_profile p
    WHERE p.id = ?
    """

    print(f"Fetching full configuration for profile {profile_id}...")
    results = execute_query(query, params=[profile_id], account=account, environment=environment)

    if results.get('error'):
        print(f"ERROR: {results['error']}")
        return

    if results['count'] == 0:
        print(f"Profile {profile_id} not found.")
        return

    profile = results['records'][0]
    template_id = profile.get('template_id')
    js_hook_id = profile.get('js_hook_id')

    # Build NetSuite URLs
    account_id = ACCOUNT_IDS.get(resolved_account, {}).get(resolved_env, '')
    base_domain = f"{account_id.replace('_', '-').lower()}.app.netsuite.com" if account_id else ''

    print(f"\n{'='*70}")
    print(f"CRE2 Profile: {profile.get('name', 'Unknown')} (ID: {profile_id})")
    print(f"{'='*70}")
    print(f"Record Type:    {profile.get('record_type', '')} (ID: {profile.get('record_type_id', '')})")
    print(f"Active:         {'No' if profile.get('inactive') == 'T' else 'Yes'}")
    print(f"Send Email:     {'Yes' if profile.get('send_email') == 'T' else 'No'}")
    print(f"Created:        {profile.get('created', '')}")
    print(f"Last Modified:  {profile.get('lastmodified', '')}")

    # Template File Info
    print(f"\n--- Template File ---")
    if template_id:
        template_info = get_file_info(template_id, account, environment)
        if template_info:
            folder_path = get_folder_path(template_info.get('folder'), account, environment)
            print(f"  File ID:      {template_id}")
            print(f"  File Name:    {template_info.get('name', '')}")
            print(f"  Folder:       {folder_path} (ID: {template_info.get('folder', '')})")
            if base_domain:
                print(f"  Preview URL:  https://{base_domain}/core/media/previewmedia.nl?id={template_id}")
        else:
            print(f"  File ID: {template_id} (file details not found)")
    else:
        print("  No template file configured")

    # JS Hook File Info
    print(f"\n--- JavaScript Hook ---")
    if js_hook_id:
        js_info = get_file_info(js_hook_id, account, environment)
        if js_info:
            folder_path = get_folder_path(js_info.get('folder'), account, environment)
            print(f"  File ID:      {js_hook_id}")
            print(f"  File Name:    {js_info.get('name', '')}")
            print(f"  Folder:       {folder_path} (ID: {js_info.get('folder', '')})")
            if base_domain:
                print(f"  Preview URL:  https://{base_domain}/core/media/previewmedia.nl?id={js_hook_id}")
        else:
            print(f"  File ID: {js_hook_id} (file details not found)")
    else:
        print("  No JavaScript hook configured")

    # Email Configuration
    if profile.get('send_email') == 'T':
        print(f"\n--- Email Configuration ---")
        print(f"  To:           {profile.get('email_to', '(not set)')}")
        print(f"  Subject:      {profile.get('email_subject', '(not set)')}")

    # Data Sources with full SQL
    print(f"\n--- Data Sources ---")
    datasources = get_datasources_full(profile_id, account, environment)
    if not datasources:
        print("  No data sources configured")
    else:
        for ds in datasources:
            paged = 'Yes' if ds.get('paged') == 'T' else 'No'
            json_mode = 'Yes' if ds.get('single_record_json') == 'T' else 'No'
            print(f"\n  [{ds.get('name', 'Unnamed')}] (Query ID: {ds.get('id', '')})")
            print(f"  Paged: {paged} | Single Record JSON Mode: {json_mode}")
            if ds.get('query_sql'):
                print(f"  SQL:")
                # Format SQL nicely
                sql = ds.get('query_sql', '')
                for line in sql.strip().split('\n'):
                    print(f"    {line}")
            else:
                print(f"  (No query configured)")


def get_datasources_full(profile_id: int, account: str, environment: str) -> List[Dict]:
    """Get full data source details including complete SQL."""
    query = """
    SELECT
        q.id,
        q.name,
        q.custrecord_pri_cre2q_query AS query_sql,
        q.custrecord_pri_cre2q_querytype AS query_type,
        q.custrecord_pri_cre2q_paged AS paged,
        q.custrecord_pri_cre2q_single_record_json AS single_record_json
    FROM customrecord_pri_cre2_query q
    WHERE q.custrecord_pri_cre2q_parent = ?
    ORDER BY q.name
    """

    results = execute_query(query, params=[profile_id], account=account, environment=environment)
    if results.get('error') or results['count'] == 0:
        return []

    return results['records']


def test_profile(profile_id: int, record_id: int, account: str = DEFAULT_ACCOUNT, environment: str = DEFAULT_ENVIRONMENT) -> None:
    """Test render a profile for a specific record."""
    print(f"Testing profile {profile_id} with record {record_id}...")
    print("NOTE: Full rendering requires CRE2 engine in NetSuite.")
    print("      This command validates the profile configuration.\n")

    # First verify the profile exists
    query = """
    SELECT
        ID,
        Name,
        BUILTIN.DF(custrecord_pri_cre2_rectype) AS RecordType,
        custrecord_pri_cre2_gen_file_tmpl_doc AS Template
    FROM customrecord_pri_cre2_profile
    WHERE ID = ?
    """

    results = execute_query(query, params=[profile_id], account=account, environment=environment)

    if results.get('error'):
        print(f"ERROR: {results['error']}")
        return

    if results['count'] == 0:
        print(f"ERROR: Profile {profile_id} not found.")
        return

    profile = results['records'][0]
    record_type = profile.get('recordtype', '').lower()

    print(f"Profile: {profile.get('name', '')}")
    print(f"Record Type: {record_type}")
    print(f"Template: {profile.get('template', '')}")

    # Verify the record exists
    record_query = f"SELECT ID FROM {record_type} WHERE ID = ?"
    record_results = execute_query(record_query, params=[record_id], account=account, environment=environment)

    if record_results.get('error'):
        print(f"\nWARNING: Could not verify record: {record_results['error']}")
    elif record_results['count'] == 0:
        print(f"\nERROR: Record {record_id} not found in {record_type}")
        return
    else:
        print(f"\nRecord {record_id} found in {record_type} table.")

    # Get and test data sources
    print(f"\n--- Testing Data Sources ---")
    datasources = get_datasources_full(profile_id, account, environment)
    if datasources:
        for ds in datasources:
            ds_name = ds.get('name', 'Unnamed')
            if ds.get('query_sql'):
                # Replace ${record.id} with actual record ID for testing
                test_sql = ds.get('query_sql', '').replace('${record.id}', str(record_id))
                print(f"\nTesting query [{ds_name}]...")
                test_results = execute_query(test_sql, account=account, environment=environment)
                if test_results.get('error'):
                    print(f"  ❌ Error: {test_results['error']}")
                elif test_results['count'] == 0:
                    print(f"  ⚠️  No results returned")
                else:
                    print(f"  ✅ Returned {test_results['count']} row(s)")
                    # Show available fields
                    if test_results['records']:
                        fields = list(test_results['records'][0].keys())
                        print(f"  Available fields: {', '.join(fields)}")
            else:
                print(f"\n  [{ds_name}]: No SQL query to test")
    else:
        print("  No data sources to test")

    print("\n" + "="*60)
    print("To render this document in NetSuite:")
    print("1. Open: Customization > Printing & Branding > CRE2 Profiles")
    print(f"2. Open profile ID {profile_id}")
    print("3. Click Test/Preview")
    print(f"4. Enter record ID: {record_id}")
    print("="*60)


def print_usage():
    """Print usage information."""
    print("""CRE 2.0 Profile Manager

Usage: python3 cre2_profile.py <command> [options]

Commands:
  list                    List all CRE2 profiles
  get <profile_id>        Get profile details with data source summary
  full-config <profile_id> Get COMPLETE configuration including:
                          - Template file name and folder
                          - JS hook file name and folder
                          - Data sources with full SQL queries
  datasources <profile_id> List data sources for profile
  test <profile_id> <record_id>  Validate profile and test data sources

Options:
  --account <account>   Account: twx, dm (default: twistedx)
  --env <environment>   Environment: prod, sb1, sb2 (default: sb2)

Examples:
  python3 cre2_profile.py list --env sb2
  python3 cre2_profile.py get 17 --env sb2
  python3 cre2_profile.py full-config 17 --env sb2
  python3 cre2_profile.py datasources 17 --env sb2
  python3 cre2_profile.py test 17 7850220 --env sb2

Note: The NetSuite API Gateway must be running at http://localhost:3001
""")


def main():
    """CLI interface."""
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help', 'help']:
        print_usage()
        sys.exit(0)

    command = sys.argv[1]
    account = DEFAULT_ACCOUNT
    environment = DEFAULT_ENVIRONMENT

    # Parse --account and --env flags
    for i, arg in enumerate(sys.argv):
        if arg == '--account' and i + 1 < len(sys.argv):
            account = sys.argv[i + 1]
        if arg == '--env' and i + 1 < len(sys.argv):
            environment = sys.argv[i + 1]

    if command == 'list':
        list_profiles(account, environment)

    elif command == 'get':
        if len(sys.argv) < 3:
            print("ERROR: Profile ID required")
            print("Usage: python3 cre2_profile.py get <profile_id> --env <env>")
            sys.exit(1)
        profile_id = int(sys.argv[2])
        get_profile(profile_id, account, environment)

    elif command == 'full-config':
        if len(sys.argv) < 3:
            print("ERROR: Profile ID required")
            print("Usage: python3 cre2_profile.py full-config <profile_id> --env <env>")
            sys.exit(1)
        profile_id = int(sys.argv[2])
        full_config(profile_id, account, environment)

    elif command == 'datasources':
        if len(sys.argv) < 3:
            print("ERROR: Profile ID required")
            print("Usage: python3 cre2_profile.py datasources <profile_id> --env <env>")
            sys.exit(1)
        profile_id = int(sys.argv[2])
        get_datasources(profile_id, account, environment)

    elif command == 'test':
        if len(sys.argv) < 4:
            print("ERROR: Profile ID and Record ID required")
            print("Usage: python3 cre2_profile.py test <profile_id> <record_id> --env <env>")
            sys.exit(1)
        profile_id = int(sys.argv[2])
        record_id = int(sys.argv[3])
        test_profile(profile_id, record_id, account, environment)

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == '__main__':
    main()
