#!/usr/bin/env python3
"""
NetSuite Script Deployment Lister

List script deployments by record type, script type, or active status.

Usage:
  python3 list_deployments.py --record-type inventoryitem --env prod
  python3 list_deployments.py --script-type USEREVENT --env prod
  python3 list_deployments.py --record-type inventoryitem --active-only --env sb2
"""

import sys
import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List

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

# Script type mappings
SCRIPT_TYPES = {
    'userevent': 'USEREVENT',
    'ue': 'USEREVENT',
    'client': 'CLIENT',
    'cl': 'CLIENT',
    'suitelet': 'SUITELET',
    'sl': 'SUITELET',
    'restlet': 'RESTLET',
    'rl': 'RESTLET',
    'scheduled': 'SCHEDULED',
    'ss': 'SCHEDULED',
    'mapreduce': 'MAPREDUCE',
    'mr': 'MAPREDUCE',
    'workflow': 'WORKFLOWACTION',
    'wfa': 'WORKFLOWACTION',
    'massupdate': 'MASSUPDATE',
    'mu': 'MASSUPDATE',
    'portlet': 'PORTLET',
    'bundleinstallation': 'BUNDLEINSTALLATION'
}

DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox2'


def resolve_account(account: str) -> str:
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def resolve_script_type(script_type: str) -> str:
    return SCRIPT_TYPES.get(script_type.lower(), script_type.upper())


def query_run(query: str, account: str, environment: str) -> Dict[str, Any]:
    """Execute a SuiteQL query via the gateway."""
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    payload = {
        'action': 'execute',
        'procedure': 'queryRun',
        'query': query,
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

            if result.get('success'):
                return {
                    'success': True,
                    'records': result.get('data', {}).get('records', [])
                }
            else:
                return {
                    'error': result.get('error', {}).get('message', 'Unknown error')
                }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            error_json = json.loads(error_body)
            error_msg = error_json.get('error', {}).get('message', error_body)
        except:
            error_msg = error_body
        return {'error': f'HTTP {e.code}: {error_msg}'}

    except urllib.error.URLError as e:
        return {'error': f'Gateway connection error: {str(e.reason)}'}

    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}


def list_deployments(
    record_type: Optional[str] = None,
    script_type: Optional[str] = None,
    active_only: bool = False,
    script_id: Optional[str] = None,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT,
    limit: int = 100
) -> Dict[str, Any]:
    """
    List script deployments from NetSuite.

    Args:
        record_type: Filter by record type (e.g., inventoryitem, salesorder)
        script_type: Filter by script type (e.g., USEREVENT, CLIENT)
        active_only: Only show deployed (active) scripts
        script_id: Filter by script ID pattern
        account: NetSuite account
        environment: NetSuite environment
        limit: Maximum results to return

    Returns:
        Dictionary with deployments or error
    """
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    # Validate account
    if resolved_account not in ['twistedx', 'dutyman']:
        return {'error': f"Invalid account: {account}"}

    # Validate environment
    if resolved_env not in ['production', 'sandbox', 'sandbox2']:
        return {'error': f"Invalid environment: {environment}"}

    # Build query - joining scriptdeployment with script
    query = """
        SELECT
            sd.scriptid AS deployment_id,
            sd.title AS deployment_title,
            sd.isdeployed,
            sd.status,
            sd.recordtype,
            s.scriptid AS script_id,
            s.name AS script_name,
            s.scripttype,
            s.scriptfile
        FROM scriptdeployment sd
        INNER JOIN script s ON sd.script = s.id
        WHERE 1=1
    """

    conditions = []

    if record_type:
        conditions.append(f"LOWER(sd.recordtype) = '{record_type.lower()}'")

    if script_type:
        resolved_type = resolve_script_type(script_type)
        conditions.append(f"s.scripttype = '{resolved_type}'")

    if active_only:
        conditions.append("sd.isdeployed = 'T'")

    if script_id:
        if '%' in script_id:
            conditions.append(f"s.scriptid LIKE '{script_id}'")
        else:
            conditions.append(f"s.scriptid = '{script_id}'")

    if conditions:
        query += " AND " + " AND ".join(conditions)

    query += f" ORDER BY sd.recordtype, s.scripttype, s.scriptid FETCH FIRST {limit} ROWS ONLY"

    result = query_run(query, account, environment)

    if result.get('error'):
        return result

    deployments = result.get('records', [])
    return {
        'success': True,
        'count': len(deployments),
        'deployments': deployments,
        'account': resolved_account,
        'environment': resolved_env
    }


def print_usage():
    print("""NetSuite Script Deployment Lister

Usage: python3 list_deployments.py [options]

Filter Options:
  --record-type <type>   Filter by record type (e.g., inventoryitem, salesorder)
  --script-type <type>   Filter by script type (e.g., USEREVENT, CLIENT, RESTLET)
  --script-id <id>       Filter by script ID (supports % wildcards)
  --active-only          Only show deployed (active) scripts

Options:
  --account <account>    Account (default: twistedx)
  --env <environment>    Environment (default: sandbox2)
  --limit <n>            Max results (default: 100)
  --format <format>      Output format: table, json (default: table)

Script Type Aliases:
  userevent, ue          User Event scripts
  client, cl             Client scripts
  suitelet, sl           Suitelets
  restlet, rl            RESTlets
  scheduled, ss          Scheduled scripts
  mapreduce, mr          Map/Reduce scripts
  massupdate, mu         Mass Update scripts

Examples:
  # List all active user event scripts for inventory items
  python3 list_deployments.py --record-type inventoryitem --script-type ue --active-only --env prod

  # List all deployments for a record type
  python3 list_deployments.py --record-type salesorder --env prod

  # List all RESTlet deployments
  python3 list_deployments.py --script-type restlet --env prod

  # Find specific script deployments
  python3 list_deployments.py --script-id "customscript_twx%" --env prod

  # Output as JSON
  python3 list_deployments.py --record-type inventoryitem --format json --env prod
""")


def print_table(deployments: List[Dict]):
    """Print deployments in table format."""
    if not deployments:
        print("No deployments found.")
        return

    # Calculate column widths
    cols = {
        'deployment_id': max(max(len(str(d.get('deployment_id', ''))) for d in deployments), 13),
        'script_id': max(max(len(str(d.get('script_id', ''))) for d in deployments), 10),
        'script_type': max(max(len(str(d.get('scripttype', ''))) for d in deployments), 11),
        'record_type': max(max(len(str(d.get('recordtype', ''))) for d in deployments), 11),
        'deployed': 8,
        'status': max(max(len(str(d.get('status', ''))) for d in deployments), 8)
    }

    # Limit widths
    cols['deployment_id'] = min(cols['deployment_id'], 35)
    cols['script_id'] = min(cols['script_id'], 30)
    cols['record_type'] = min(cols['record_type'], 20)

    # Print header
    header = (
        f"{'Deployment ID':<{cols['deployment_id']}}  "
        f"{'Script ID':<{cols['script_id']}}  "
        f"{'Script Type':<{cols['script_type']}}  "
        f"{'Record Type':<{cols['record_type']}}  "
        f"{'Deployed':<{cols['deployed']}}  "
        f"{'Status':<{cols['status']}}"
    )
    print(header)
    print("-" * len(header))

    # Print rows
    for d in deployments:
        deployment_id = str(d.get('deployment_id', ''))[:35]
        script_id = str(d.get('script_id', ''))[:30]
        script_type = str(d.get('scripttype', ''))
        record_type = str(d.get('recordtype', ''))[:20]
        deployed = 'Yes' if d.get('isdeployed') == 'T' else 'No'
        status = str(d.get('status', ''))

        print(
            f"{deployment_id:<{cols['deployment_id']}}  "
            f"{script_id:<{cols['script_id']}}  "
            f"{script_type:<{cols['script_type']}}  "
            f"{record_type:<{cols['record_type']}}  "
            f"{deployed:<{cols['deployed']}}  "
            f"{status:<{cols['status']}}"
        )


def main():
    if len(sys.argv) < 2 or '--help' in sys.argv or '-h' in sys.argv:
        print_usage()
        sys.exit(0)

    record_type = None
    script_type = None
    script_id = None
    active_only = False
    account = DEFAULT_ACCOUNT
    environment = DEFAULT_ENVIRONMENT
    limit = 100
    output_format = 'table'

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--record-type' and i + 1 < len(sys.argv):
            record_type = sys.argv[i + 1]
            i += 2
        elif arg == '--script-type' and i + 1 < len(sys.argv):
            script_type = sys.argv[i + 1]
            i += 2
        elif arg == '--script-id' and i + 1 < len(sys.argv):
            script_id = sys.argv[i + 1]
            i += 2
        elif arg == '--active-only':
            active_only = True
            i += 1
        elif arg == '--account' and i + 1 < len(sys.argv):
            account = sys.argv[i + 1]
            i += 2
        elif arg == '--env' and i + 1 < len(sys.argv):
            environment = sys.argv[i + 1]
            i += 2
        elif arg == '--limit' and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
            i += 2
        elif arg == '--format' and i + 1 < len(sys.argv):
            output_format = sys.argv[i + 1].lower()
            i += 2
        else:
            i += 1

    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    filters = []
    if record_type:
        filters.append(f"record_type={record_type}")
    if script_type:
        filters.append(f"script_type={resolve_script_type(script_type)}")
    if active_only:
        filters.append("active_only")
    if script_id:
        filters.append(f"script_id={script_id}")

    filter_str = ', '.join(filters) if filters else 'all'
    print(f"Searching deployments in {resolved_account}/{resolved_env} ({filter_str})...")

    result = list_deployments(
        record_type=record_type,
        script_type=script_type,
        active_only=active_only,
        script_id=script_id,
        account=account,
        environment=environment,
        limit=limit
    )

    if result.get('error'):
        print(f"ERROR: {result.get('error')}")
        sys.exit(1)

    deployments = result.get('deployments', [])
    print(f"Found {len(deployments)} deployment(s)\n")

    if output_format == 'json':
        print(json.dumps(result, indent=2))
    else:
        print_table(deployments)


if __name__ == '__main__':
    main()
