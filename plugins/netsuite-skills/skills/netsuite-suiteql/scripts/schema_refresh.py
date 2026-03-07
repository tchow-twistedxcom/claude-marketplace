#!/usr/bin/env python3
"""
NetSuite SuiteQL Schema Refresh (ODBC)

Connects to NetSuite SuiteAnalytics Connect via ODBC and dumps full schema
(OA_TABLES, OA_COLUMNS, OA_FKEYS) to JSON cache files.

Requires:
  - pyodbc installed: pip3 install --user pyodbc
  - NetSuite ODBC driver installed (see setup_odbc.py)
  - DSNs configured in ~/.odbc.ini (run: python3 setup_odbc.py)
  - Credentials via env vars NETSUITE_ODBC_USER + NETSUITE_ODBC_PASSWORD
    or prompts if not set

Accounts and environments are read dynamically from the API gateway.
Set NETSUITE_GATEWAY_URL to override (default: https://nsapi.twistedx.tech).

Cache location: ~/.cache/netsuite-schema/{account}/{environment}/

Usage:
  python3 schema_refresh.py [--account twx] [--env sb2]
  python3 schema_refresh.py --all-accounts --all-environments
  python3 schema_refresh.py --status
"""

import sys
import os
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from urllib.request import urlopen
from urllib.error import URLError

# Cache root
CACHE_ROOT = os.path.expanduser('~/.cache/netsuite-schema')

# Gateway URL (override via env var)
GATEWAY_URL = os.environ.get('NETSUITE_GATEWAY_URL', 'https://nsapi.twistedx.tech').rstrip('/')

# Environment aliases — universal NetSuite conventions, not account-specific
ENV_ALIASES = {
    'prod': 'production',
    'production': 'production',
    'sb1': 'sandbox',
    'sandbox': 'sandbox',
    'sandbox1': 'sandbox',
    'sb2': 'sandbox2',
    'sandbox2': 'sandbox2'
}

# Module-level cache for accounts config (fetched once per run)
_accounts_config: Optional[Dict] = None


def fetch_accounts_config() -> Dict:
    """
    Fetch accounts configuration from the API gateway.
    Returns dict with 'accounts', 'account_aliases', 'default_account', 'default_environment'.
    Falls back to empty config on error.
    """
    global _accounts_config
    if _accounts_config is not None:
        return _accounts_config

    try:
        with urlopen(f"{GATEWAY_URL}/api/common/accounts", timeout=10) as resp:
            data = json.loads(resp.read().decode())
        raw_accounts = data.get('data', {}).get('accounts', [])

        accounts = {}
        account_aliases = {}
        for acct in raw_accounts:
            aid = acct['id']
            accounts[aid] = {
                'name': acct.get('name', aid),
                'accountId': acct.get('accountId', ''),
                'odbc': acct.get('odbc') or {},
                'environments': [e['id'] for e in acct.get('environments', [])]
            }
            for alias in acct.get('aliases', []):
                account_aliases[alias] = aid

        _accounts_config = {
            'accounts': accounts,
            'account_aliases': account_aliases,
            'default_account': data.get('data', {}).get('defaultAccount', ''),
            'default_environment': data.get('data', {}).get('defaultEnvironment', '')
        }
    except (URLError, Exception) as e:
        print(f"  WARNING: Could not reach gateway at {GATEWAY_URL}: {e}")
        print("  Set NETSUITE_GATEWAY_URL or ensure the gateway is running.")
        _accounts_config = {
            'accounts': {},
            'account_aliases': {},
            'default_account': '',
            'default_environment': ''
        }

    return _accounts_config


def resolve_account(account: str) -> str:
    cfg = fetch_accounts_config()
    normalized = account.lower()
    # Try direct match first, then aliases
    if normalized in cfg['accounts']:
        return normalized
    return cfg['account_aliases'].get(normalized, normalized)


def resolve_environment(environment: str) -> str:
    return ENV_ALIASES.get(environment.lower(), environment.lower())


def get_default_account() -> str:
    return fetch_accounts_config()['default_account']


def get_default_environment() -> str:
    return fetch_accounts_config()['default_environment']


def get_account_environments(account: str) -> List[str]:
    cfg = fetch_accounts_config()
    return cfg['accounts'].get(account, {}).get('environments', [])


def get_all_account_environments() -> List[Tuple[str, str]]:
    cfg = fetch_accounts_config()
    pairs = []
    for acct, info in cfg['accounts'].items():
        for env in info.get('environments', []):
            pairs.append((acct, env))
    return pairs


def get_cache_dir(account: str, environment: str) -> str:
    return os.path.join(CACHE_ROOT, account, environment)


def save_cache(cache_dir: str, filename: str, data: Dict[str, Any]) -> None:
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"    Saved {path} ({os.path.getsize(path) // 1024}KB)")


def load_cache(cache_dir: str, filename: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(cache_dir, filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def get_dsn_name(account: str, environment: str) -> str:
    """Derive ODBC DSN name from account + environment."""
    return f"netsuite_{account}_{environment}"


def parse_oa_userdata(oa_userdata: Optional[str]) -> Dict[str, Any]:
    """
    Parse the 16-position oa_userdata metadata string from OA_TABLES/OA_COLUMNS.

    Position 1: C=Custom, S=Standard
    Position 2: V=Visible, H=Hidden
    Position 3: M=has Last Modified Date, -=no
    Position 4: D=hard Delete available, -=no
    Positions 17+: required feature name (after | delimiter at position 17)
    """
    if not oa_userdata or len(oa_userdata) < 4:
        return {'is_custom': False, 'is_hidden': False, 'has_last_modified': False,
                'has_hard_delete': False, 'required_features': []}

    result = {
        'is_custom': oa_userdata[0] == 'C',
        'is_hidden': oa_userdata[1] == 'H',
        'has_last_modified': oa_userdata[2] == 'M',
        'has_hard_delete': len(oa_userdata) > 3 and oa_userdata[3] == 'D',
        'required_features': []
    }

    # Feature name starts after position 17 (| delimiter)
    if len(oa_userdata) > 17 and oa_userdata[16] == '|':
        feature = oa_userdata[17:].strip()
        if feature:
            result['required_features'] = [feature]

    return result


def get_odbc_credentials(account: str, environment: str) -> Tuple[str, str]:
    """Get ODBC credentials from env vars or prompt."""
    user = os.environ.get('NETSUITE_ODBC_USER', '')
    password = os.environ.get('NETSUITE_ODBC_PASSWORD', '')

    if not user:
        print(f"  NETSUITE_ODBC_USER not set. Enter credentials for {account}/{environment}:")
        user = input("  ODBC Username (NetSuite email): ").strip()

    if not password:
        import getpass
        password = getpass.getpass(f"  ODBC Password for {user}: ")

    return user, password


def refresh_account_environment(account: str, environment: str,
                                 user: str = '', password: str = '',
                                 tables_only: bool = False,
                                 columns_only: bool = False,
                                 fkeys_only: bool = False) -> Dict[str, Any]:
    """
    Connect to NetSuite via ODBC and refresh schema cache for one account/environment.
    Returns stats dict.
    """
    try:
        import pyodbc
    except ImportError:
        return {'error': 'pyodbc not installed. Run: pip3 install --user pyodbc\nThen install ODBC driver: python3 setup_odbc.py'}

    dsn = get_dsn_name(account, environment)
    if not user or not password:
        user, password = get_odbc_credentials(account, environment)

    cache_dir = get_cache_dir(account, environment)
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    print(f"\n  Connecting to DSN: {dsn}")
    try:
        conn = pyodbc.connect(f"DSN={dsn};UID={user};PWD={password}", timeout=30)
    except pyodbc.Error as e:
        return {'error': f"ODBC connection failed for {dsn}: {e}\nVerify DSN in ~/.odbc.ini and credentials."}

    cursor = conn.cursor()
    stats = {'account': account, 'environment': environment, 'dsn': dsn}

    try:
        # ---------------------------------------------------------------
        # OA_TABLES
        # ---------------------------------------------------------------
        if not columns_only and not fkeys_only:
            print("    Querying OA_TABLES...")
            cursor.execute("""
                SELECT table_name, table_type, table_owner, oa_userdata, remarks
                FROM oa_tables
                ORDER BY table_name
            """)
            tables = []
            for row in cursor.fetchall():
                ud = parse_oa_userdata(row.oa_userdata)
                tables.append({
                    'table_name': row.table_name or '',
                    'table_type': row.table_type or '',
                    'table_owner': row.table_owner or '',
                    'is_custom': ud['is_custom'],
                    'is_hidden': ud['is_hidden'],
                    'has_last_modified': ud['has_last_modified'],
                    'has_hard_delete': ud['has_hard_delete'],
                    'required_features': ud['required_features'],
                    'description': row.remarks or ''
                })

            save_cache(cache_dir, 'tables.json', {
                '_source': 'odbc',
                '_refreshed_at': ts,
                '_account': account,
                '_environment': environment,
                '_record_count': len(tables),
                'tables': tables
            })
            stats['tables_count'] = len(tables)
            print(f"    {len(tables)} tables found")

        # ---------------------------------------------------------------
        # OA_COLUMNS
        # ---------------------------------------------------------------
        if not tables_only and not fkeys_only:
            print("    Querying OA_COLUMNS (may take 30-90 seconds)...")
            cursor.execute("""
                SELECT table_name, column_name, data_type, type_name,
                       oa_length, oa_precision, oa_scale, remarks
                FROM oa_columns
                ORDER BY table_name, column_name
            """)

            columns_grouped: Dict[str, List[Dict]] = {}
            total_cols = 0
            for row in cursor.fetchall():
                tname = row.table_name or ''
                if tname not in columns_grouped:
                    columns_grouped[tname] = []
                columns_grouped[tname].append({
                    'column_name': row.column_name or '',
                    'data_type': _odbc_type_name(row.data_type),
                    'type_name': row.type_name or '',
                    'length': row.oa_length,
                    'precision': row.oa_precision,
                    'scale': row.oa_scale,
                    'description': row.remarks or ''
                })
                total_cols += 1

            save_cache(cache_dir, 'columns.json', {
                '_source': 'odbc',
                '_refreshed_at': ts,
                '_account': account,
                '_environment': environment,
                '_record_count': total_cols,
                'columns': columns_grouped
            })
            stats['columns_count'] = total_cols
            print(f"    {total_cols} columns across {len(columns_grouped)} tables")

        # ---------------------------------------------------------------
        # OA_FKEYS
        # ---------------------------------------------------------------
        if not tables_only and not columns_only:
            print("    Querying OA_FKEYS...")
            try:
                cursor.execute("""
                    SELECT pktable_name, pkcolumn_name, fktable_name, fkcolumn_name,
                           key_seq, fk_name, pk_name
                    FROM oa_fkeys
                """)
                foreign_keys = []
                primary_keys = []
                for row in cursor.fetchall():
                    if row.fktable_name:
                        foreign_keys.append({
                            'pk_table': row.pktable_name or '',
                            'pk_column': row.pkcolumn_name or '',
                            'fk_table': row.fktable_name or '',
                            'fk_column': row.fkcolumn_name or '',
                            'key_seq': row.key_seq,
                            'fk_name': row.fk_name or '',
                            'pk_name': row.pk_name or ''
                        })
                    else:
                        primary_keys.append({
                            'table_name': row.pktable_name or '',
                            'column_name': row.pkcolumn_name or '',
                            'pk_name': row.pk_name or '',
                            'key_seq': row.key_seq
                        })

                save_cache(cache_dir, 'fkeys.json', {
                    '_source': 'odbc',
                    '_refreshed_at': ts,
                    '_account': account,
                    '_environment': environment,
                    '_record_count': len(foreign_keys) + len(primary_keys),
                    'foreign_keys': foreign_keys,
                    'primary_keys': primary_keys
                })
                stats['fkeys_count'] = len(foreign_keys)
                stats['primary_keys_count'] = len(primary_keys)
                print(f"    {len(foreign_keys)} foreign keys, {len(primary_keys)} primary keys")
            except pyodbc.Error as e:
                print(f"    WARNING: OA_FKEYS query failed: {e}")
                stats['fkeys_error'] = str(e)

    finally:
        cursor.close()
        conn.close()

    # Update metadata
    metadata = load_cache(cache_dir, '_metadata.json') or {'account': account, 'environment': environment}
    odbc_refresh = {'timestamp': ts}
    if 'tables_count' in stats:
        odbc_refresh['tables_count'] = stats['tables_count']
    if 'columns_count' in stats:
        odbc_refresh['columns_count'] = stats['columns_count']
    if 'fkeys_count' in stats:
        odbc_refresh['fkeys_count'] = stats['fkeys_count']
    metadata['odbc_refresh'] = odbc_refresh
    save_cache(cache_dir, '_metadata.json', metadata)

    stats['success'] = True
    return stats


def _odbc_type_name(data_type: Optional[int]) -> str:
    """Convert ODBC data_type integer to human-readable name."""
    if data_type is None:
        return ''
    type_map = {
        -11: 'GUID', -10: 'WLONGVARCHAR', -9: 'WVARCHAR', -8: 'WCHAR',
        -7: 'BIT', -6: 'TINYINT', -5: 'BIGINT', -4: 'LONGVARBINARY',
        -3: 'VARBINARY', -2: 'BINARY', -1: 'LONGVARCHAR', 1: 'CHAR',
        2: 'NUMERIC', 3: 'DECIMAL', 4: 'INTEGER', 5: 'SMALLINT',
        6: 'FLOAT', 7: 'REAL', 8: 'DOUBLE', 9: 'DATE', 10: 'TIME',
        11: 'TIMESTAMP', 12: 'VARCHAR', 91: 'DATE', 92: 'TIME', 93: 'TIMESTAMP'
    }
    return type_map.get(data_type, str(data_type))


def show_status() -> None:
    """Show status of all cache directories."""
    print(f"Schema cache root: {CACHE_ROOT}\n")
    pairs = get_all_account_environments()
    if not pairs:
        print("  No accounts found. Is the gateway running?")
        return
    for account, env in pairs:
        cache_dir = get_cache_dir(account, env)
        files = ['tables.json', 'columns.json', 'fkeys.json', 'custom_records.json', 'custom_fields.json']
        print(f"[{account}/{env}]")
        for fname in files:
            path = os.path.join(cache_dir, fname)
            if os.path.exists(path):
                import time
                age = (time.time() - os.path.getmtime(path)) / 86400
                size = os.path.getsize(path) // 1024
                warn = ' ⚠️' if age > 90 else ''
                print(f"  {fname:<30} {age:.1f}d old, {size}KB{warn}")
            else:
                print(f"  {fname:<30} NOT PRESENT")
        print()


def main():
    argv = sys.argv[1:]

    if '--help' in argv or '-h' in argv:
        print(__doc__)
        sys.exit(0)

    if '--status' in argv:
        show_status()
        sys.exit(0)

    all_accounts = '--all-accounts' in argv
    all_environments = '--all-environments' in argv
    tables_only = '--tables-only' in argv
    columns_only = '--columns-only' in argv
    fkeys_only = '--fkeys-only' in argv

    # Parse account and environment
    default_account = get_default_account()
    default_environment = get_default_environment()
    account = default_account
    environment = default_environment

    i = 0
    while i < len(argv):
        if argv[i] == '--account' and i + 1 < len(argv):
            account = resolve_account(argv[i + 1])
            i += 2
        elif argv[i] == '--env' and i + 1 < len(argv):
            environment = resolve_environment(argv[i + 1])
            i += 2
        else:
            i += 1

    # Check pyodbc availability early
    try:
        import pyodbc
    except ImportError:
        print("ERROR: pyodbc is not installed.")
        print("Install it: pip3 install --user pyodbc")
        print("Then set up the ODBC driver: python3 setup_odbc.py")
        sys.exit(1)

    # Get credentials once for all refreshes
    user = os.environ.get('NETSUITE_ODBC_USER', '')
    password = os.environ.get('NETSUITE_ODBC_PASSWORD', '')
    if not user or not password:
        print("ODBC credentials (set NETSUITE_ODBC_USER + NETSUITE_ODBC_PASSWORD env vars to avoid prompts):")
        import getpass
        if not user:
            user = input("ODBC Username (NetSuite email): ").strip()
        if not password:
            password = getpass.getpass(f"ODBC Password for {user}: ")

    # Build list of (account, environment) pairs to refresh
    pairs = []
    if all_accounts and all_environments:
        pairs = get_all_account_environments()
    elif all_accounts:
        for acct in fetch_accounts_config()['accounts']:
            if environment in get_account_environments(acct):
                pairs.append((acct, environment))
    elif all_environments:
        for env in get_account_environments(account):
            pairs.append((account, env))
    else:
        envs = get_account_environments(account)
        if environment not in envs:
            print(f"ERROR: {account} does not support {environment}")
            print(f"Valid environments for {account}: {envs}")
            sys.exit(1)
        pairs.append((account, environment))

    if not pairs:
        print("ERROR: No accounts found. Is the gateway running?")
        print(f"Gateway URL: {GATEWAY_URL}")
        sys.exit(1)

    print(f"Refreshing {len(pairs)} account/environment combination(s)...")

    errors = []
    for acct, env in pairs:
        print(f"\n{'='*60}")
        print(f"Account: {acct}, Environment: {env}")
        print('='*60)
        stats = refresh_account_environment(
            acct, env, user=user, password=password,
            tables_only=tables_only,
            columns_only=columns_only,
            fkeys_only=fkeys_only
        )
        if stats.get('error'):
            print(f"  ERROR: {stats['error']}")
            errors.append(f"{acct}/{env}: {stats['error']}")
        else:
            print(f"  ✓ Success")

    print(f"\n{'='*60}")
    print(f"Refresh complete: {len(pairs) - len(errors)}/{len(pairs)} succeeded")
    if errors:
        print("Errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
