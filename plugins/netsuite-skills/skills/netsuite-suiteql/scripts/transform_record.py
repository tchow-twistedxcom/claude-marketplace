#!/usr/bin/env python3
"""
NetSuite Record Transform Executor

Drive record.transform workflows (SO→IF, SO→Invoice, PO→ItemReceipt, etc.) via the
NetSuite API Gateway's twxTransformRecord procedure.  Mirrors update_record.py auth
and gateway patterns; pass --dry-run to inspect the assembled payload before firing.

Multi-Account Support:
  - twistedx (twx): Twisted X account using OAuth 1.0a
  - dutyman (dm): Dutyman account using OAuth 2.0 M2M

Environment Support:
  - production (prod): Production environment
  - sandbox (sb1): Sandbox 1 environment
  - sandbox2 (sb2): Sandbox 2 environment (default)
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.error
from typing import Any, Dict, Optional, Tuple

# NetSuite API Gateway endpoint — override with NETSUITE_GATEWAY_URL env var
_gw_base = os.environ.get('NETSUITE_GATEWAY_URL', 'https://nsapi.twistedx.tech').rstrip('/')
GATEWAY_URL = f'{_gw_base}/api/suiteapi'

# Account aliases — identical to update_record.py
ACCOUNT_ALIASES = {
    'twx': 'twistedx',
    'twisted': 'twistedx',
    'twistedx': 'twistedx',
    'dm': 'dutyman',
    'duty': 'dutyman',
    'dutyman': 'dutyman',
}

# Environment aliases — identical to update_record.py
ENV_ALIASES = {
    'prod': 'production',
    'production': 'production',
    'sb1': 'sandbox',
    'sandbox': 'sandbox',
    'sandbox1': 'sandbox',
    'sb2': 'sandbox2',
    'sandbox2': 'sandbox2',
}

DEFAULT_ACCOUNT = 'twistedx'
DEFAULT_ENVIRONMENT = 'sandbox2'


def resolve_account(account: str) -> str:
    return ACCOUNT_ALIASES.get(account.lower(), account.lower())


def resolve_environment(environment: str) -> str:
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def parse_json_arg(value: Optional[str], flag_name: str) -> Optional[Any]:
    """Parse a JSON string argument; exits with an error message on bad JSON."""
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        print(f"ERROR: {flag_name} is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)


def transform_record(
    from_type: str,
    from_id: int,
    to_type: str,
    account: str = DEFAULT_ACCOUNT,
    environment: str = DEFAULT_ENVIRONMENT,
    is_dynamic: bool = True,
    default_values: Optional[Dict[str, Any]] = None,
    fields: Optional[Dict[str, Any]] = None,
    line_updates: Optional[Dict[str, Any]] = None,
    sublists: Optional[Dict[str, Any]] = None,
    subrecords: Optional[Dict[str, Any]] = None,
    save: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], str, str]:
    """
    Build the twxTransformRecord gateway payload.

    Returns:
        (payload dict, resolved_account, resolved_env)
    """
    resolved_account = resolve_account(account)
    resolved_env = resolve_environment(environment)

    payload: Dict[str, Any] = {
        'action': 'execute',
        'procedure': 'twxTransformRecord',
        'netsuiteAccount': resolved_account,
        'netsuiteEnvironment': resolved_env,
        'fromType': from_type,
        'fromId': from_id,
        'toType': to_type,
        'isDynamic': is_dynamic,
    }
    if default_values is not None:
        payload['defaultValues'] = default_values
    if fields is not None:
        payload['fields'] = fields
    if line_updates is not None:
        payload['lineUpdates'] = line_updates
    if sublists is not None:
        payload['sublists'] = sublists
    if subrecords is not None:
        payload['subrecords'] = subrecords
    if save is not None:
        payload['save'] = save

    return payload, resolved_account, resolved_env


def call_gateway(payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST payload to the gateway and return the parsed JSON response."""
    data = json.dumps(payload).encode('utf-8')
    _api_key = os.environ.get('NETSUITE_API_KEY', '')
    req = urllib.request.Request(
        GATEWAY_URL,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            **({'X-API-Key': _api_key} if _api_key else {'Origin': _gw_base}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            return json.loads(error_body)
        except json.JSONDecodeError:
            return {'success': False, 'error': error_body}
    except urllib.error.URLError as e:
        return {
            'success': False,
            'error': f'Gateway connection error: {e.reason}. Is the gateway running at {GATEWAY_URL}?',
        }
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {e}'}


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='transform_record.py',
        description='Drive NetSuite record.transform workflows via twxTransformRecord.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # SO → Item Fulfillment (shipstatus A, all lines receive at location 1)
  python3 transform_record.py \\
    --from-type salesorder --from-id 24017329 --to-type itemfulfillment \\
    --fields '{"shipstatus":"A"}' \\
    --line-updates '{"item":[{"matchAll":true,"fields":{"itemreceive":true,"location":1}}]}'

  # SO → Invoice
  python3 transform_record.py \\
    --from-type salesorder --from-id 24017329 --to-type invoice

  # PO → Item Receipt
  python3 transform_record.py \\
    --from-type purchaseorder --from-id 99999 --to-type itemreceipt

  # Dry-run — print payload without calling the API
  python3 transform_record.py \\
    --from-type salesorder --from-id 24017329 --to-type itemfulfillment --dry-run

  # Production transform
  python3 transform_record.py \\
    --from-type salesorder --from-id 24017329 --to-type invoice \\
    --environment production

Accounts:
  twistedx (twx)  — OAuth 1.0a  — prod, sb1, sb2
  dutyman  (dm)   — OAuth 2.0 M2M — prod, sb1 only

Gateway URL: https://nsapi.twistedx.tech  (override: NETSUITE_GATEWAY_URL env var)
API Key auth: set NETSUITE_API_KEY env var (falls back to Origin header if unset)
""",
    )

    # Required arguments
    req_grp = parser.add_argument_group('required')
    req_grp.add_argument('--from-type', required=True, metavar='TYPE',
                         help='Source record type (e.g. salesorder, purchaseorder)')
    req_grp.add_argument('--from-id', required=True, type=int, metavar='ID',
                         help='Source record internal ID')
    req_grp.add_argument('--to-type', required=True, metavar='TYPE',
                         help='Target record type (e.g. itemfulfillment, invoice, itemreceipt)')

    # Account / environment
    parser.add_argument('--account', default=DEFAULT_ACCOUNT, metavar='ACCOUNT',
                        help=f'Account alias (default: {DEFAULT_ACCOUNT}). Aliases: twx, dm')
    parser.add_argument('--environment', '--env', default=DEFAULT_ENVIRONMENT, metavar='ENV',
                        help=f'Environment (default: {DEFAULT_ENVIRONMENT}). Aliases: prod, sb1, sb2')
    parser.add_argument('--gateway-url', default=None, metavar='URL',
                        help='Override gateway base URL (also: NETSUITE_GATEWAY_URL env var)')

    # Transform options
    parser.add_argument('--is-dynamic', default=True, type=lambda x: x.lower() != 'false',
                        metavar='BOOL', help='Dynamic mode (default: true)')
    parser.add_argument('--default-values', default=None, metavar='JSON',
                        help='JSON object passed to record.transform at sourcing time '
                             '(e.g. \'{"inventorylocation":1}\')')
    parser.add_argument('--fields', default=None, metavar='JSON',
                        help='JSON object of post-transform field values '
                             '(e.g. \'{"shipstatus":"A","memo":"test"}\')')
    parser.add_argument('--line-updates', default=None, metavar='JSON',
                        help='JSON object for mutating existing sublist lines. Use for static '
                             'sublists (e.g. IF item sublist). '
                             'Format: {"sublistId":[{"matchAll":true,"fields":{...}}]}')
    parser.add_argument('--sublists', default=None, metavar='JSON',
                        help='JSON object for adding new lines to non-static sublists '
                             '(selectNewLine path). Do NOT use for the IF item sublist.')
    parser.add_argument('--subrecords', default=None, metavar='JSON',
                        help='JSON object for subrecord field values '
                             '(e.g. \'{"shippingaddress":{"addr1":"123 Main"}}\')')
    parser.add_argument('--save', default=None, metavar='JSON',
                        help='JSON object to override record.save() options '
                             '(default: {"enableSourcing":true,"ignoreMandatoryFields":true})')

    parser.add_argument('--idempotency-key', default=None, metavar='KEY',
                        help='Unique key forwarded in payload for dedup auditing. '
                             'record.transform is non-idempotent — use a stable key (e.g. '
                             'uuid4 or SO-id+toType) so retried calls can be identified. '
                             'The gateway does not enforce dedup; this is for audit/logging.')

    # Output
    parser.add_argument('--dry-run', action='store_true',
                        help='Print the assembled payload and exit without calling the API')
    parser.add_argument('--json', dest='json_output', action='store_true',
                        help='Output result as JSON')

    args = parser.parse_args()

    # Override gateway URL if provided
    global _gw_base, GATEWAY_URL
    if args.gateway_url:
        _gw_base = args.gateway_url.rstrip('/')
        GATEWAY_URL = f'{_gw_base}/api/suiteapi'

    # Parse JSON arguments
    default_values = parse_json_arg(args.default_values, '--default-values')
    fields         = parse_json_arg(args.fields, '--fields')
    line_updates   = parse_json_arg(args.line_updates, '--line-updates')
    sublists       = parse_json_arg(args.sublists, '--sublists')
    subrecords     = parse_json_arg(args.subrecords, '--subrecords')
    save           = parse_json_arg(args.save, '--save')

    # Build payload
    payload, resolved_account, resolved_env = transform_record(
        from_type=args.from_type,
        from_id=args.from_id,
        to_type=args.to_type,
        account=args.account,
        environment=args.environment,
        is_dynamic=args.is_dynamic,
        default_values=default_values,
        fields=fields,
        line_updates=line_updates,
        sublists=sublists,
        subrecords=subrecords,
        save=save,
    )

    if args.idempotency_key:
        payload['idempotencyKey'] = args.idempotency_key

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        sys.exit(0)

    print(f"Transforming {args.from_type} {args.from_id} → {args.to_type} "
          f"in {resolved_account}/{resolved_env}...\n", file=sys.stderr)

    result = call_gateway(payload)

    if args.json_output:
        out = sys.stdout if result.get('success') else sys.stderr
        print(json.dumps(result, indent=2), file=out)
    else:
        if result.get('success'):
            data = result.get('data', result)
            record_id = data.get('id') if isinstance(data, dict) else data
            print(f"✅ {args.from_type} {args.from_id} → {args.to_type} "
                  f"created: id={record_id}")
        else:
            error_msg = result.get('error') or result.get('message') or json.dumps(result)
            print(f"❌ Transform failed: {error_msg}", file=sys.stderr)

    if not result.get('success'):
        sys.exit(1)


if __name__ == '__main__':
    main()
