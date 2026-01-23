#!/usr/bin/env python3
"""
NetSuite CRE 2.0 Document Renderer

Render CRE 2.0 templates for NetSuite records.
Note: Full rendering requires the CRE2 engine running in NetSuite.
This script provides debugging and data inspection capabilities.

Commands:
  render <profile_id> <record_id>  Render document (via NetSuite)
  preview <profile_id> <record_id> Open preview instructions
  debug <profile_id> <record_id>   Show data that would be passed to template
"""

import sys
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List

# NetSuite API Gateway endpoint
GATEWAY_URL = 'http://localhost:3001/api/suiteapi'

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

DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox'


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
    resolved_env = resolve_environment(environment)

    payload = {
        'action': 'queryRun',
        'procedure': 'queryRun',
        'query': query,
        'params': params or [],
        'returnAllRows': True,
        'netsuiteAccount': account,
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

    except Exception as e:
        return {'error': str(e), 'records': [], 'count': 0}


def get_profile_info(profile_id: int, environment: str) -> Optional[Dict]:
    """Get profile configuration."""
    query = """
    SELECT
        ID,
        Name,
        BUILTIN.DF(custrecord_pri_cre2_rectype) AS RecordType,
        custrecord_pri_cre2_gen_file_tmpl_doc AS Template,
        custrecord_pri_cre2_send_email AS SendEmail
    FROM customrecord_pri_cre2_profile
    WHERE ID = ?
    """
    results = execute_query(query, params=[profile_id], environment=environment)

    if results.get('error') or results['count'] == 0:
        return None

    return results['records'][0]


def debug_render(profile_id: int, record_id: int, environment: str = DEFAULT_ENVIRONMENT) -> None:
    """Show data that would be passed to the template."""
    print(f"Debugging data for profile {profile_id}, record {record_id}")
    print(f"Environment: {resolve_environment(environment)}\n")

    # Get profile info
    profile = get_profile_info(profile_id, environment)
    if not profile:
        print(f"ERROR: Profile {profile_id} not found")
        return

    record_type = profile.get('recordtype', '').lower()
    print(f"Profile: {profile.get('name', '')}")
    print(f"Record Type: {record_type}")
    print(f"Template: {profile.get('template', '')}")
    print()

    # Get record data based on record type
    if record_type == 'customer':
        print("=" * 60)
        print("RECORD DATA (record.*)")
        print("=" * 60)

        record_query = """
        SELECT
            ID, entityid, companyname, email, phone,
            BUILTIN.DF(terms) AS terms,
            creditlimit,
            defaultbillingaddress, defaultshippingaddress
        FROM customer
        WHERE ID = ?
        """
        record_results = execute_query(record_query, params=[record_id], environment=environment)

        if record_results.get('error'):
            print(f"Error: {record_results['error']}")
        elif record_results['count'] > 0:
            print(json.dumps(record_results['records'][0], indent=2))
        else:
            print(f"Customer {record_id} not found")

        # Sample transaction data
        print("\n" + "=" * 60)
        print("TRANSACTION DATA (tran.rows) - Sample")
        print("=" * 60)

        tran_query = """
        SELECT
            T.ID, T.TranID, T.TranDate, T.DueDate,
            BUILTIN.DF(T.Type) AS Type,
            T.ForeignTotal AS Amount,
            T.ForeignAmountUnpaid AS OpenBalance
        FROM Transaction T
        WHERE T.Entity = ?
          AND T.Type IN ('CustInvc', 'CustCred', 'CustPymt')
        ORDER BY T.TranDate DESC
        FETCH FIRST 5 ROWS ONLY
        """
        tran_results = execute_query(tran_query, params=[record_id], environment=environment)

        if tran_results.get('error'):
            print(f"Error: {tran_results['error']}")
        elif tran_results['count'] > 0:
            for tran in tran_results['records']:
                print(json.dumps(tran, indent=2))
        else:
            print("No transactions found for this customer")

    elif record_type == 'transaction':
        print("=" * 60)
        print("TRANSACTION DATA")
        print("=" * 60)

        tran_query = """
        SELECT
            T.ID, T.TranID, T.TranDate, T.DueDate,
            BUILTIN.DF(T.Entity) AS Customer,
            BUILTIN.DF(T.Type) AS Type,
            BUILTIN.DF(T.Status) AS Status,
            T.ForeignTotal AS Amount
        FROM Transaction T
        WHERE T.ID = ?
        """
        tran_results = execute_query(tran_query, params=[record_id], environment=environment)

        if tran_results.get('error'):
            print(f"Error: {tran_results['error']}")
        elif tran_results['count'] > 0:
            print(json.dumps(tran_results['records'][0], indent=2))
        else:
            print(f"Transaction {record_id} not found")

        # Get line items
        print("\n" + "=" * 60)
        print("LINE ITEMS")
        print("=" * 60)

        lines_query = """
        SELECT
            TL.Line,
            BUILTIN.DF(TL.Item) AS Item,
            TL.Quantity,
            TL.Rate,
            TL.ForeignAmount AS Amount
        FROM TransactionLine TL
        WHERE TL.Transaction = ?
          AND TL.mainline = 'F'
          AND TL.Item IS NOT NULL
        ORDER BY TL.Line
        """
        lines_results = execute_query(lines_query, params=[record_id], environment=environment)

        if lines_results.get('error'):
            print(f"Error: {lines_results['error']}")
        elif lines_results['count'] > 0:
            for line in lines_results['records']:
                print(json.dumps(line, indent=2))
        else:
            print("No line items found")

    elif 'edi' in record_type.lower():
        print("=" * 60)
        print("EDI TRANSACTION DATA")
        print("=" * 60)

        edi_query = """
        SELECT
            id, name,
            custrecord_twx_edi_history_json AS edi_json
        FROM customrecord_twx_edi_history
        WHERE id = ?
        """
        edi_results = execute_query(edi_query, params=[record_id], environment=environment)

        if edi_results.get('error'):
            print(f"Error: {edi_results['error']}")
        elif edi_results['count'] > 0:
            record = edi_results['records'][0]
            print(f"Record ID: {record.get('id')}")
            print(f"Name: {record.get('name')}")
            print()
            edi_json = record.get('edi_json')
            if edi_json:
                try:
                    parsed = json.loads(edi_json)
                    print("=" * 60)
                    print("PARSED EDI DATA (available as OVERRIDE.edi.*)")
                    print("=" * 60)
                    print(json.dumps(parsed, indent=2)[:2000])
                    if len(json.dumps(parsed)) > 2000:
                        print("... [truncated]")
                except:
                    print("EDI JSON: Unable to parse")
            else:
                print("No EDI JSON data found")
        else:
            print(f"EDI History record {record_id} not found")

    else:
        print(f"Debug not implemented for record type: {record_type}")
        print("Generic record query...")

        generic_query = f"SELECT * FROM {record_type} WHERE id = ?"
        results = execute_query(generic_query, params=[record_id], environment=environment)

        if results.get('error'):
            print(f"Error: {results['error']}")
        elif results['count'] > 0:
            print(json.dumps(results['records'][0], indent=2))


def render_document(profile_id: int, record_id: int, environment: str = DEFAULT_ENVIRONMENT) -> None:
    """
    Instructions to render a document.
    Note: Actual rendering requires the CRE2 engine in NetSuite.
    """
    profile = get_profile_info(profile_id, environment)
    if not profile:
        print(f"ERROR: Profile {profile_id} not found")
        return

    env_name = resolve_environment(environment)
    base_url = {
        'production': 'https://system.netsuite.com',
        'sandbox': 'https://system.sandbox.netsuite.com',
        'sandbox2': 'https://system.sandbox2.netsuite.com'
    }.get(env_name, 'https://system.netsuite.com')

    print(f"CRE 2.0 Document Rendering")
    print("=" * 60)
    print(f"Profile: {profile.get('name', '')} (ID: {profile_id})")
    print(f"Record ID: {record_id}")
    print(f"Template File: {profile.get('template', '')}")
    print(f"Send Email: {'Yes' if profile.get('sendemail') == 'T' else 'No'}")
    print(f"Environment: {env_name}")
    print()
    print("To render this document in NetSuite:")
    print()
    print("Option 1: Via CRE2 Profile UI")
    print("-" * 40)
    print("1. Navigate to: Customization > Printing & Branding > CRE2 Profiles")
    print(f"2. Open profile ID {profile_id}")
    print("3. Click Test/Preview button")
    print(f"4. Enter record ID: {record_id}")
    print()
    print("Option 2: Via SuiteScript")
    print("-" * 40)
    print("```javascript")
    print("define(['/.bundle/369503/CRE2/PRI_CRE2_Engine'], (creEngine) => {")
    print(f"    const CRE2 = creEngine.createCRE2Engine({profile_id});")
    print(f"    CRE2.Load({{ recordId: {record_id} }});")
    print("    CRE2.TranslateAndSendQuietly();")
    print("    const fileId = CRE2.getGeneratedFileId();")
    print("    log.debug('Generated file', fileId);")
    print("});")
    print("```")


def preview_document(profile_id: int, record_id: int, environment: str = DEFAULT_ENVIRONMENT) -> None:
    """Show preview instructions."""
    render_document(profile_id, record_id, environment)


def print_usage():
    """Print usage information."""
    print("""CRE 2.0 Document Renderer

Usage: python3 cre2_render.py <command> <profile_id> <record_id> [options]

Commands:
  render <profile_id> <record_id>   Show how to render document
  preview <profile_id> <record_id>  Same as render (alias)
  debug <profile_id> <record_id>    Show data passed to template

Options:
  --env <environment>    Environment: prod, sb1, sb2 (default: sb1)

Examples:
  python3 cre2_render.py debug 15 12345 --env sb1
  python3 cre2_render.py render 15 12345 --env sb1
  python3 cre2_render.py preview 15 12345 --env sb1

Note: Full rendering requires the CRE2 engine in NetSuite.
      The 'debug' command shows data that would be available to the template.
""")


def main():
    """CLI interface."""
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help', 'help']:
        print_usage()
        sys.exit(0)

    command = sys.argv[1]
    environment = DEFAULT_ENVIRONMENT

    # Parse --env flag
    for i, arg in enumerate(sys.argv):
        if arg == '--env' and i + 1 < len(sys.argv):
            environment = sys.argv[i + 1]

    if command in ['render', 'preview']:
        if len(sys.argv) < 4:
            print("ERROR: Profile ID and Record ID required")
            print("Usage: python3 cre2_render.py render <profile_id> <record_id> --env <env>")
            sys.exit(1)
        profile_id = int(sys.argv[2])
        record_id = int(sys.argv[3])
        render_document(profile_id, record_id, environment)

    elif command == 'debug':
        if len(sys.argv) < 4:
            print("ERROR: Profile ID and Record ID required")
            print("Usage: python3 cre2_render.py debug <profile_id> <record_id> --env <env>")
            sys.exit(1)
        profile_id = int(sys.argv[2])
        record_id = int(sys.argv[3])
        debug_render(profile_id, record_id, environment)

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == '__main__':
    main()
