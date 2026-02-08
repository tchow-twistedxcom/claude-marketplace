#!/usr/bin/env python3
"""
NetSuite Script Execution Log Query Tool

Query script execution logs via saved search through the SuiteAPI gateway.
Useful for debugging SuiteScripts without accessing NetSuite UI directly.

Usage:
  python3 query_execution_logs.py --script customscript_pri_qt_sl_render_query --account dm --env prod
  python3 query_execution_logs.py --level DEBUG --hours 24 --account dm --format table
  python3 query_execution_logs.py --title "DEBUG-" --hours 1 --account dm --format json
"""

import sys
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

DEFAULT_ACCOUNT = 'dutyman'
DEFAULT_ENVIRONMENT = 'production'


def resolve_account(account: str) -> str:
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def query_execution_logs(
    script_id: Optional[str] = None,
    log_level: Optional[str] = None,
    hours: int = 24,
    title: Optional[str] = None,
    limit: int = 200,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """
    Query script execution logs from NetSuite.

    Args:
        script_id: Script ID to filter by (e.g., 'customscript_pri_qt_sl_render_query')
        log_level: Log level filter: DEBUG, AUDIT, ERROR, EMERGENCY
        hours: Get logs from last N hours (default: 24)
        title: Filter logs containing this title pattern
        limit: Maximum results to return (default: 200)
        account: NetSuite account
        environment: NetSuite environment

    Returns:
        Dictionary with logs array or error
    """
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    # Validate account
    if resolved_account not in ['twistedx', 'dutyman']:
        return {'error': f"Invalid account: {account}"}

    # Validate environment
    if resolved_env not in ['production', 'sandbox', 'sandbox2']:
        return {'error': f"Invalid environment: {environment}"}

    # Build payload for executionLogsGet procedure
    payload = {
        'action': 'execute',
        'procedure': 'executionLogsGet',
        'hours': hours,
        'limit': limit,
        'netsuiteAccount': resolved_account,
        'netsuiteEnvironment': resolved_env
    }

    if script_id:
        payload['scriptId'] = script_id

    if log_level:
        payload['logLevel'] = log_level.upper()

    if title:
        payload['title'] = title

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
                # Gateway returns {success: true, data: [...logs...]}
                data = result.get('data', [])
                # Handle both array and object responses
                if isinstance(data, list):
                    logs = data
                elif isinstance(data, dict) and data.get('error'):
                    return {
                        'error': data.get('error'),
                        'account': resolved_account,
                        'environment': resolved_env
                    }
                else:
                    logs = []
                return {
                    'success': True,
                    'logs': logs,
                    'count': len(logs),
                    'account': resolved_account,
                    'environment': resolved_env
                }
            else:
                error_msg = result.get('error', 'Unknown error')
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get('message', str(error_msg))
                return {
                    'error': error_msg,
                    'account': resolved_account,
                    'environment': resolved_env
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


def format_table(logs: List[Dict[str, Any]]) -> str:
    """Format logs as ASCII table."""
    if not logs:
        return "No logs found."

    # Define columns
    columns = [
        ('Date', 'date', 10),
        ('Time', 'time', 12),
        ('Level', 'type', 10),
        ('Script', 'script', 40),
        ('Title', 'title', 50),
    ]

    # Header
    header = ' | '.join(col[0].ljust(col[2]) for col in columns)
    separator = '-+-'.join('-' * col[2] for col in columns)

    lines = [header, separator]

    for log in logs:
        row = ' | '.join(
            str(log.get(col[1], '') or '')[:col[2]].ljust(col[2])
            for col in columns
        )
        lines.append(row)

    return '\n'.join(lines)


def format_detailed(logs: List[Dict[str, Any]]) -> str:
    """Format logs with full details."""
    if not logs:
        return "No logs found."

    lines = []
    for i, log in enumerate(logs, 1):
        lines.append(f"\n{'='*80}")
        lines.append(f"Log Entry {i}")
        lines.append(f"{'='*80}")
        lines.append(f"Date:    {log.get('date', 'N/A')}")
        lines.append(f"Time:    {log.get('time', 'N/A')}")
        lines.append(f"Level:   {log.get('type', 'N/A')}")
        lines.append(f"Script:  {log.get('script', 'N/A')}")
        lines.append(f"User:    {log.get('user', 'N/A')}")
        lines.append(f"Title:   {log.get('title', 'N/A')}")
        lines.append(f"Detail:")
        detail = log.get('detail', 'N/A')
        if detail:
            # Indent detail lines
            for line in str(detail).split('\n'):
                lines.append(f"  {line}")
        else:
            lines.append("  (none)")

    return '\n'.join(lines)


def print_usage():
    print("""NetSuite Script Execution Log Query Tool

Usage: python3 query_execution_logs.py [options]

Filter Options:
  --script <id>        Script ID to filter (e.g., customscript_pri_qt_sl_render_query)
  --level <level>      Log level: DEBUG, AUDIT, ERROR, EMERGENCY
  --hours <n>          Get logs from last N hours (default: 24)
  --title <pattern>    Filter logs containing this title pattern
  --limit <n>          Maximum results (default: 200)

Connection Options:
  --account <account>  Account: dm/dutyman, twx/twistedx (default: dutyman)
  --env <environment>  Environment: prod, sb1, sb2 (default: production)

Output Options:
  --format <fmt>       Output format: table, json, detailed (default: table)

Examples:
  # Get DEBUG logs from last hour for Query Renderer
  python3 query_execution_logs.py --script customscript_pri_qt_sl_render_query --level DEBUG --hours 1 --account dm --env prod

  # Get all ERROR logs from last 24 hours
  python3 query_execution_logs.py --level ERROR --hours 24 --account dm

  # Search for specific log messages
  python3 query_execution_logs.py --title "DEBUG-USER" --hours 1 --account dm --format detailed

  # Get all recent logs as JSON
  python3 query_execution_logs.py --hours 1 --account dm --format json

Log Levels:
  DEBUG     - Detailed debugging information
  AUDIT     - Audit trail entries
  ERROR     - Error conditions
  EMERGENCY - Critical errors
""")


def main():
    if len(sys.argv) < 2 or '--help' in sys.argv or '-h' in sys.argv:
        print_usage()
        sys.exit(0)

    script_id = None
    log_level = None
    hours = 24
    title = None
    limit = 200
    account = DEFAULT_ACCOUNT
    environment = DEFAULT_ENVIRONMENT
    output_format = 'table'

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--script' and i + 1 < len(sys.argv):
            script_id = sys.argv[i + 1]
            i += 2
        elif arg == '--level' and i + 1 < len(sys.argv):
            log_level = sys.argv[i + 1]
            i += 2
        elif arg == '--hours' and i + 1 < len(sys.argv):
            hours = int(sys.argv[i + 1])
            i += 2
        elif arg == '--title' and i + 1 < len(sys.argv):
            title = sys.argv[i + 1]
            i += 2
        elif arg == '--limit' and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
            i += 2
        elif arg == '--account' and i + 1 < len(sys.argv):
            account = sys.argv[i + 1]
            i += 2
        elif arg == '--env' and i + 1 < len(sys.argv):
            environment = sys.argv[i + 1]
            i += 2
        elif arg == '--format' and i + 1 < len(sys.argv):
            output_format = sys.argv[i + 1].lower()
            i += 2
        else:
            i += 1

    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)
    print(f"Querying execution logs from {resolved_account}/{resolved_env}...", file=sys.stderr)

    result = query_execution_logs(
        script_id=script_id,
        log_level=log_level,
        hours=hours,
        title=title,
        limit=limit,
        account=account,
        environment=environment
    )

    if result.get('error'):
        print(f"ERROR: {result.get('error')}", file=sys.stderr)
        sys.exit(1)

    logs = result.get('logs', [])
    print(f"Found {len(logs)} log entries.\n", file=sys.stderr)

    if output_format == 'json':
        print(json.dumps(logs, indent=2))
    elif output_format == 'detailed':
        print(format_detailed(logs))
    else:
        print(format_table(logs))


if __name__ == '__main__':
    main()
