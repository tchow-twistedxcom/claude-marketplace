#!/usr/bin/env python3
"""
Add data sources to CRE2 profiles that are missing them.
"""

import sys
import json
import urllib.request
import time

GATEWAY_URL = 'http://localhost:3001/api/suiteapi'

DATA_SOURCE_QUERY = """SELECT h.id, h.name, h.custrecord_twx_edi_history_json AS edi_json, h.custrecord_twx_eth_edi_tp AS trading_partner, h.custrecord_twx_edi_type AS doc_type, h.custrecord_twx_edi_history_status AS status, h.created AS created_date, tp.custrecord_twx_edi_tp_logo AS tp_logo_id, tp.name AS tp_name FROM customrecord_twx_edi_history h LEFT JOIN customrecord_twx_edi_tp tp ON h.custrecord_twx_eth_edi_tp = tp.id WHERE h.id = ${record.id}"""


def execute_query(query, account='twistedx', environment='sandbox2'):
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
    with urllib.request.urlopen(req, timeout=60) as response:
        result = json.loads(response.read().decode('utf-8'))
        return result.get('data', {}).get('records', [])


def create_data_source(profile_id, account='twistedx', environment='sandbox2'):
    payload = {
        'action': 'execute',
        'procedure': 'twxUpsertRecord',
        'type': 'customrecord_pri_cre2_query',
        'id': 0,
        'fields': {
            'name': 'edi',
            'custrecord_pri_cre2q_parent': profile_id,
            'custrecord_pri_cre2q_query': DATA_SOURCE_QUERY,
            'custrecord_pri_cre2q_paged': False,
            'custrecord_pri_cre2q_single_record_json': False
        },
        'netsuiteAccount': account,
        'netsuiteEnvironment': environment
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
                return {'success': True, 'id': result.get('data', {}).get('id')}
            return {'success': False, 'error': result.get('error', 'Unknown')}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def main():
    account = 'twistedx'
    environment = 'sandbox2'

    # Get profiles with data sources
    with_ds = set(
        r['profile_id'] for r in execute_query(
            "SELECT DISTINCT custrecord_pri_cre2q_parent as profile_id FROM customrecord_pri_cre2_query",
            account, environment
        )
    )

    # Get all EDI profiles
    profiles = execute_query(
        "SELECT id, name FROM customrecord_pri_cre2_profile WHERE name LIKE 'TWX-EDI-%' AND isinactive = 'F' ORDER BY name",
        account, environment
    )

    # Find profiles without data sources
    missing = [(p['id'], p['name']) for p in profiles if p['id'] not in with_ds]

    print(f"Profiles missing data sources: {len(missing)}")
    print()

    if not missing:
        print("All profiles have data sources!")
        return

    created = 0
    failed = 0

    for i, (pid, pname) in enumerate(missing, 1):
        result = create_data_source(pid, account, environment)
        if result.get('success'):
            print(f"  ✓ {pname} → DS ID: {result.get('id')}")
            created += 1
        else:
            print(f"  ✗ {pname} → Error: {result.get('error')}")
            failed += 1

        time.sleep(0.15)

        if i % 20 == 0:
            print(f"\n  Progress: {i}/{len(missing)} ({100*i//len(missing)}%)\n")

    print("\n" + "=" * 60)
    print(f"Created: {created}")
    print(f"Failed: {failed}")
    print("=" * 60)


if __name__ == '__main__':
    main()
