#!/usr/bin/env python3
"""
NetSuite Record Operations Executor

Perform CRUD operations on NetSuite records using the NetSuite API Gateway.
Supports multiple accounts (twistedx, dutyman) and environments (production, sandbox, sandbox2)
with OAuth authentication handled transparently by the gateway.

Multi-Account Support:
  - twistedx (twx): Twisted X account using OAuth 1.0a
  - dutyman (dm): Dutyman account using OAuth 2.0 M2M

Environment Support:
  - production (prod): Production environment
  - sandbox (sb1): Sandbox 1 environment
  - sandbox2 (sb2): Sandbox 2 environment
"""

import sys
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

# NetSuite API Gateway endpoint
GATEWAY_URL = 'http://localhost:3001/api/suiteapi'

# Account aliases
ACCOUNT_ALIASES = {
    'twx': 'twistedx',
    'twisted': 'twistedx',
    'twistedx': 'twistedx',
    'dm': 'dutyman',
    'duty': 'dutyman',
    'dutyman': 'dutyman'
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

# Default account and environment
DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox2'


def resolve_account(account: str) -> str:
    """Resolve account alias to canonical name."""
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    """Resolve environment alias to canonical name."""
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def update_record(
    record_type: str,
    record_id: int,
    fields: Dict[str, Any],
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """
    Update a NetSuite record via the API Gateway.

    Args:
        record_type: NetSuite record type (e.g., 'customrecord_twx_notification_rule')
        record_id: Internal ID of the record to update
        fields: Dictionary of field names and values to update
        account: Account to update ('twistedx'/'twx' or 'dutyman'/'dm')
        environment: 'prod'/'production', 'sb1'/'sandbox', or 'sb2'/'sandbox2'

    Returns:
        Dictionary with:
        - success: True if operation succeeded
        - recordId: Updated record ID
        - recordType: Record type
        - account: Resolved account name
        - environment: Resolved environment name
        - authType: Authentication type used (oauth1 or oauth2)
        - error: Error message if failed
    """
    # Resolve aliases
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    # Validate account
    if resolved_account not in ['twistedx', 'dutyman']:
        return {
            'success': False,
            'error': f"Invalid account: {account}. Valid options: twistedx (twx), dutyman (dm)",
            'account': resolved_account,
            'environment': resolved_env
        }

    # Validate environment
    if resolved_env not in ['production', 'sandbox', 'sandbox2']:
        return {
            'success': False,
            'error': f"Invalid environment: {environment}. Valid options: production (prod), sandbox (sb1), sandbox2 (sb2)",
            'account': resolved_account,
            'environment': resolved_env
        }

    # Build request payload for gateway
    payload = {
        'action': 'execute',
        'procedure': 'twxUpsertRecord',
        'type': record_type,
        'id': record_id,
        'fields': fields,
        'netsuiteAccount': resolved_account,
        'netsuiteEnvironment': resolved_env
    }

    try:
        # Prepare request to gateway
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            GATEWAY_URL,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Origin': 'http://localhost:3000'  # Required by gateway CORS validation
            }
        )

        # Execute request through gateway
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))

            # Gateway returns: {success, data, authType}
            return {
                'success': result.get('success', False),
                'recordId': result.get('data', {}).get('id') if result.get('success') else None,
                'recordType': record_type,
                'account': resolved_account,
                'environment': resolved_env,
                'authType': result.get('authType', 'unknown'),
                'error': result.get('error') if not result.get('success') else None
            }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            error_json = json.loads(error_body)
            error_msg = error_json.get('error', {}).get('message', error_body)
        except:
            error_msg = error_body

        return {
            'success': False,
            'error': f'HTTP {e.code}: {error_msg}',
            'account': resolved_account,
            'environment': resolved_env
        }

    except urllib.error.URLError as e:
        return {
            'success': False,
            'error': f'Gateway connection error: {str(e.reason)}. Is the gateway running at {GATEWAY_URL}?',
            'account': resolved_account,
            'environment': resolved_env
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'account': resolved_account,
            'environment': resolved_env
        }


def create_record(
    record_type: str,
    fields: Dict[str, Any],
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT
) -> Dict[str, Any]:
    """
    Create a new NetSuite record via the API Gateway.

    Args:
        record_type: NetSuite record type (e.g., 'customrecord_twx_notification_template')
        fields: Dictionary of field names and values for the new record
        account: Account to create in ('twistedx'/'twx' or 'dutyman'/'dm')
        environment: 'prod'/'production', 'sb1'/'sandbox', or 'sb2'/'sandbox2'

    Returns:
        Dictionary with:
        - success: True if operation succeeded
        - recordId: New record ID
        - recordType: Record type
        - account: Resolved account name
        - environment: Resolved environment name
        - authType: Authentication type used
        - error: Error message if failed
    """
    # For creates, don't pass an ID (or pass null/0)
    return update_record(record_type, None, fields, account, environment)


def format_result(result: Dict[str, Any]) -> str:
    """
    Format operation result for display.

    Args:
        result: Operation result dictionary

    Returns:
        Formatted string
    """
    if result.get('error'):
        return f"ERROR: {result['error']}"

    account = result.get('account', 'unknown')
    env = result.get('environment', 'unknown')
    auth_type = result.get('authType', 'unknown')
    record_id = result.get('recordId')
    record_type = result.get('recordType', 'unknown')

    header = f"[{account}/{env}] ({auth_type})"

    if result.get('success'):
        return f"{header}\n✅ Successfully updated {record_type} (ID: {record_id})"
    else:
        return f"{header}\n❌ Operation failed: {result.get('error', 'Unknown error')}"


def print_usage():
    """Print usage information."""
    print("""NetSuite Record Operations Executor

Usage: python3 update_record.py <record_type> <record_id> [options]
       python3 update_record.py <record_type> --create [options]

Arguments:
  record_type            NetSuite record type (e.g., 'customrecord_twx_notification_rule')
  record_id              Internal ID of record to update (omit for --create)

Options:
  --field <name=value>   Set field value (use multiple times for multiple fields)
                         For JSON values, use single quotes around value:
                         --field conditions='{"status":"Processing Error"}'

  --account <account>    Account to operate on (default: twistedx)
                         Aliases: twistedx (twx), dutyman (dm)

  --env <environment>    Environment to use (default: sandbox2)
                         Aliases: production (prod), sandbox (sb1), sandbox2 (sb2)

  --create               Create new record instead of updating existing one

  --json                 Output result as JSON

Examples:
  # Update notification rule RULE-0002 in sandbox2
  python3 update_record.py customrecord_twx_notification_rule 2 \\
    --field custrecord_twx_rule_conditions='{"status":"Processing Error"}' \\
    --field custrecord_twx_rule_template=1 \\
    --env sb2

  # Create new notification template
  python3 update_record.py customrecord_twx_notification_template --create \\
    --field name="Test Template" \\
    --field custrecord_twx_template_subject="Test Subject" \\
    --field custrecord_twx_template_body="Test Body" \\
    --env sb2

  # Update record in production
  python3 update_record.py customrecord_twx_notification_rule 5 \\
    --field custrecord_twx_rule_active=false \\
    --account twx --env prod

  # Update with JSON output for scripting
  python3 update_record.py customrecord_twx_notification_rule 2 \\
    --field custrecord_twx_rule_template=1 \\
    --json

Accounts:
  twistedx (twx)  - Twisted X (OAuth 1.0a) - Environments: production, sandbox, sandbox2
  dutyman (dm)    - Dutyman (OAuth 2.0 M2M) - Environments: production, sandbox

Note: The NetSuite API Gateway must be running at http://localhost:3001
      Run 'docker compose up -d' in ~/NetSuiteApiGateway if needed
""")


def main():
    """CLI interface for record operations."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    # Check for help
    if sys.argv[1] in ['-h', '--help', 'help']:
        print_usage()
        sys.exit(0)

    # Parse arguments
    record_type = sys.argv[1]
    record_id = None
    fields = {}
    account = DEFAULT_ACCOUNT
    environment = DEFAULT_ENVIRONMENT
    is_create = False
    json_output = False

    # Determine if this is a create or update
    if '--create' in sys.argv:
        is_create = True
        i = 2
    else:
        if len(sys.argv) < 3 or sys.argv[2].startswith('--'):
            print("ERROR: record_id required (or use --create for new record)")
            print_usage()
            sys.exit(1)
        try:
            record_id = int(sys.argv[2])
        except ValueError:
            print(f"ERROR: record_id must be a number, got: {sys.argv[2]}")
            sys.exit(1)
        i = 3

    # Parse options
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--field' and i + 1 < len(sys.argv):
            field_spec = sys.argv[i + 1]
            if '=' not in field_spec:
                print(f"ERROR: --field requires format 'name=value', got: {field_spec}")
                sys.exit(1)
            name, value = field_spec.split('=', 1)
            # Try to parse as JSON for complex types
            try:
                fields[name] = json.loads(value)
            except json.JSONDecodeError:
                # If not JSON, treat as string/number
                try:
                    # Try to parse as number
                    if '.' in value:
                        fields[name] = float(value)
                    else:
                        fields[name] = int(value)
                except ValueError:
                    # Keep as string
                    fields[name] = value
            i += 2
        elif arg == '--account' and i + 1 < len(sys.argv):
            account = sys.argv[i + 1]
            i += 2
        elif arg == '--env' and i + 1 < len(sys.argv):
            environment = sys.argv[i + 1]
            i += 2
        elif arg == '--create':
            is_create = True
            i += 1
        elif arg == '--json':
            json_output = True
            i += 1
        else:
            print(f"ERROR: Unknown argument: {arg}")
            print_usage()
            sys.exit(1)

    if not fields:
        print("ERROR: At least one --field required")
        print_usage()
        sys.exit(1)

    # Show what we're doing
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)
    operation = "Creating" if is_create else f"Updating ID {record_id}"
    print(f"{operation} {record_type} in {resolved_account}/{resolved_env}...\n")

    # Execute operation
    if is_create:
        result = create_record(record_type, fields, account, environment)
    else:
        result = update_record(record_type, record_id, fields, account, environment)

    # Format and print result
    if json_output:
        print(json.dumps(result, indent=2))
    else:
        output = format_result(result)
        print(output)

    # Exit with error code if operation failed
    if not result.get('success'):
        sys.exit(1)


if __name__ == '__main__':
    main()
