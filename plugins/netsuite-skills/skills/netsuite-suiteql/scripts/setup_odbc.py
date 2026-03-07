#!/usr/bin/env python3
"""
NetSuite SuiteAnalytics Connect ODBC Setup

One-time setup for NetSuite ODBC on a new machine. Reads all account and
connection details from the API gateway — no hardcoded values.

What this script does:
  1. Checks/installs unixODBC system packages (apt)
  2. Checks/installs pyodbc Python package
  3. Extracts the NetSuite ODBC driver to ~/netsuite/odbcclient/
  4. Registers the driver in ~/.odbcinst.ini
  5. Fetches account/ODBC config from the gateway API
  6. Generates DSN entries in ~/.odbc.ini for all accounts/environments
  7. Adds required env vars to ~/.bashrc

Requirements:
  - Gateway running at nsapi.twistedx.tech (or NETSUITE_GATEWAY_URL)
  - NetSuite ODBC driver zip downloaded from:
      NetSuite > Setup > Company > SuiteAnalytics Connect > Set Up SuiteAnalytics Connect
  - Certificates zip (ca3.cer, ca4.cer) from the same page

Usage:
  python3 setup_odbc.py [--driver-zip /path/to/driver.zip] [--cert-zip /path/to/certs.zip]
  python3 setup_odbc.py --check      # Check current setup status only
  python3 setup_odbc.py --dsns-only  # Regenerate DSNs from gateway (driver already installed)
"""

import sys
import os
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

GATEWAY_URL = os.environ.get('NETSUITE_GATEWAY_URL', 'https://nsapi.twistedx.tech').rstrip('/')
DRIVER_INSTALL_DIR = Path.home() / 'netsuite' / 'odbcclient'
ODBC_INI = Path.home() / '.odbc.ini'
ODBCINST_INI = Path.home() / '.odbcinst.ini'
BASHRC = Path.home() / '.bashrc'

GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
NC = '\033[0m'


def ok(msg):   print(f"{GREEN}[OK]{NC} {msg}")
def warn(msg): print(f"{YELLOW}[WARN]{NC} {msg}")
def err(msg):  print(f"{RED}[ERROR]{NC} {msg}")
def log(msg):  print(f"{BLUE}[setup]{NC} {msg}")


# ---------------------------------------------------------------------------
# Step 1: Gateway connectivity
# ---------------------------------------------------------------------------

def fetch_accounts() -> list:
    """Fetch accounts with ODBC config from the gateway API."""
    try:
        with urlopen(f"{GATEWAY_URL}/api/common/accounts", timeout=10) as resp:
            data = json.loads(resp.read().decode())
        accounts = data.get('data', {}).get('accounts', [])
        odbc_accounts = [a for a in accounts if a.get('odbc')]
        if not odbc_accounts:
            warn("No accounts with ODBC configuration found in gateway response.")
            warn("Add an 'odbc' section to each account in config/accounts.json.")
        return odbc_accounts
    except URLError as e:
        err(f"Cannot reach gateway at {GATEWAY_URL}: {e}")
        err("Ensure the gateway is running before running setup_odbc.py")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Step 2: System packages
# ---------------------------------------------------------------------------

def check_install_unixodbc():
    log("Checking unixODBC...")
    result = subprocess.run(['dpkg', '-s', 'unixodbc'], capture_output=True)
    if result.returncode == 0:
        ok("unixodbc already installed")
    else:
        log("Installing unixodbc and unixodbc-dev...")
        subprocess.run(['sudo', 'apt-get', 'install', '-y', 'unixodbc', 'unixodbc-dev'], check=True)
        ok("unixodbc installed")


def check_install_pyodbc():
    log("Checking pyodbc...")
    result = subprocess.run([sys.executable, '-c', 'import pyodbc'], capture_output=True)
    if result.returncode == 0:
        ok("pyodbc already installed")
    else:
        log("Installing pyodbc...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--user', 'pyodbc',
                        '--break-system-packages'], check=True)
        ok("pyodbc installed")


# ---------------------------------------------------------------------------
# Step 3: Driver extraction
# ---------------------------------------------------------------------------

def find_driver_lib() -> Path | None:
    """Find ivoa27.so in the install directory."""
    matches = list(DRIVER_INSTALL_DIR.rglob('ivoa27.so'))
    return matches[0] if matches else None


def extract_driver(driver_zip: Path):
    log(f"Extracting driver to {DRIVER_INSTALL_DIR}...")
    DRIVER_INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(driver_zip) as zf:
        zf.extractall(DRIVER_INSTALL_DIR)
    lib = find_driver_lib()
    if not lib:
        err(f"ivoa27.so not found after extraction. Contents: {list(DRIVER_INSTALL_DIR.iterdir())}")
        sys.exit(1)
    ok(f"Driver extracted: {lib}")


def extract_certs(cert_zip: Path):
    cert_dir = DRIVER_INSTALL_DIR / 'cert'
    cert_dir.mkdir(parents=True, exist_ok=True)
    log(f"Extracting certificates to {cert_dir}...")
    with zipfile.ZipFile(cert_zip) as zf:
        zf.extractall(cert_dir)
    certs = list(cert_dir.glob('*.cer'))
    if not certs:
        warn("No .cer files found in cert zip.")
    else:
        ok(f"Certificates: {[c.name for c in certs]}")


# ---------------------------------------------------------------------------
# Step 4: Register driver in ~/.odbcinst.ini
# ---------------------------------------------------------------------------

def register_driver(driver_lib: Path):
    log("Registering ODBC driver in ~/.odbcinst.ini...")
    content = ODBCINST_INI.read_text() if ODBCINST_INI.exists() else ''
    if '[NetSuite]' in content:
        ok("NetSuite driver already registered in ~/.odbcinst.ini")
        return

    entry = f"""
[NetSuite]
Description=NetSuite SuiteAnalytics Connect ODBC Driver
Driver={driver_lib}
Setup={driver_lib}
UsageCount=1
"""
    with open(ODBCINST_INI, 'a') as f:
        f.write(entry)
    ok(f"Driver registered in {ODBCINST_INI}")


# ---------------------------------------------------------------------------
# Step 5: Configure DSNs from gateway accounts
# ---------------------------------------------------------------------------

def derive_odbc_host(base_host: str, account_id: str, env_id: str) -> str:
    """
    Derive the per-environment ODBC host from the base host.
    sandbox  → {accountId}-sb1.connect.api.netsuite.com
    sandbox2 → {accountId}-sb2.connect.api.netsuite.com
    production → base_host unchanged
    """
    if env_id == 'sandbox':
        return base_host.replace(account_id, f"{account_id}-sb1")
    elif env_id == 'sandbox2':
        return base_host.replace(account_id, f"{account_id}-sb2")
    return base_host


def configure_dsns(accounts: list):
    log(f"Configuring DSNs in {ODBC_INI}...")

    # Find cert paths
    cert_dir = DRIVER_INSTALL_DIR / 'cert'
    ca3 = cert_dir / 'ca3.cer'
    ca4 = cert_dir / 'ca4.cer'
    trust_store = f"{ca3},{ca4}" if ca3.exists() and ca4.exists() else ''
    if not trust_store:
        warn("ca3.cer / ca4.cer not found. TLS verification may fail.")

    # Read existing DSNs
    existing = ODBC_INI.read_text() if ODBC_INI.exists() else ''
    dsns_written = []

    for account in accounts:
        acct_id = account['id']
        odbc_cfg = account['odbc']
        base_host = odbc_cfg.get('serviceHost', '')
        port = odbc_cfg.get('port', 1708)
        role_id = odbc_cfg.get('roleId', '')
        ns_account_id = account.get('accountId', '')

        for env in account.get('environments', []):
            env_id = env['id']
            dsn = f"netsuite_{acct_id}_{env_id}"

            if f"[{dsn}]" in existing:
                ok(f"  DSN already exists: {dsn} (skipping)")
                continue

            host = derive_odbc_host(base_host, ns_account_id, env_id)
            trust_line = f"\nTrustStore={trust_store}" if trust_store else ''
            entry = f"""
[{dsn}]
Driver=NetSuite
Description=NetSuite {account.get('name', acct_id)} ({env.get('name', env_id)})
Host={host}
Port={port}
ServerDataSource=NetSuite2.com
Encrypted=1
AllowSinglePacketLogout=1{trust_line}
CustomProperties=AccountID={ns_account_id};RoleID={role_id}
"""
            with open(ODBC_INI, 'a') as f:
                f.write(entry)
            ok(f"  Configured: {dsn}  →  {host}")
            dsns_written.append(dsn)

    if dsns_written:
        ok(f"DSNs written to {ODBC_INI}")
    else:
        ok("All DSNs already configured")


# ---------------------------------------------------------------------------
# Step 6: Environment variables in ~/.bashrc
# ---------------------------------------------------------------------------

def update_bashrc():
    log("Checking ~/.bashrc environment variables...")
    content = BASHRC.read_text() if BASHRC.exists() else ''

    additions = []
    lib64 = DRIVER_INSTALL_DIR / 'lib64'

    if 'netsuite/odbcclient/lib64' not in content:
        additions.append(f'export LD_LIBRARY_PATH="{lib64}:$LD_LIBRARY_PATH"')
    if 'OASDK_ODBC_HOME' not in content:
        additions.append(f'export OASDK_ODBC_HOME="{lib64}"')
    if 'ODBCINI' not in content:
        additions.append(f'export ODBCINI="$HOME/.odbc.ini"')
    if 'ODBCSYSINI' not in content:
        additions.append(f'export ODBCSYSINI="$HOME"')

    if additions:
        with open(BASHRC, 'a') as f:
            f.write('\n# NetSuite ODBC\n')
            f.write('\n'.join(additions) + '\n')
        ok(f"Added to ~/.bashrc:\n  " + '\n  '.join(additions))
    else:
        ok("~/.bashrc already has all required env vars")

    # Apply to current process
    os.environ['LD_LIBRARY_PATH'] = f"{lib64}:{os.environ.get('LD_LIBRARY_PATH', '')}"
    os.environ['OASDK_ODBC_HOME'] = str(lib64)
    os.environ['ODBCINI'] = str(ODBC_INI)
    os.environ['ODBCSYSINI'] = str(Path.home())


# ---------------------------------------------------------------------------
# Status check
# ---------------------------------------------------------------------------

def check_status(accounts: list):
    print("\nODBC Setup Status")
    print("=" * 50)

    # Driver
    lib = find_driver_lib()
    print(f"Driver (ivoa27.so):   {'✓ ' + str(lib) if lib else '✗ Not found'}")

    # Certs
    cert_dir = DRIVER_INSTALL_DIR / 'cert'
    ca3 = (cert_dir / 'ca3.cer').exists()
    ca4 = (cert_dir / 'ca4.cer').exists()
    print(f"Certificates:         {'✓ ca3.cer + ca4.cer' if ca3 and ca4 else '✗ Missing'}")

    # odbcinst.ini
    odbcinst = ODBCINST_INI.read_text() if ODBCINST_INI.exists() else ''
    print(f"Driver registered:    {'✓' if '[NetSuite]' in odbcinst else '✗ Not in ~/.odbcinst.ini'}")

    # DSNs
    existing = ODBC_INI.read_text() if ODBC_INI.exists() else ''
    for account in accounts:
        for env in account.get('environments', []):
            dsn = f"netsuite_{account['id']}_{env['id']}"
            status = '✓' if f'[{dsn}]' in existing else '✗ Missing'
            print(f"DSN {dsn:<40} {status}")

    # env vars
    has_ld = 'netsuite/odbcclient/lib64' in BASHRC.read_text() if BASHRC.exists() else False
    print(f"~/.bashrc env vars:   {'✓' if has_ld else '✗ LD_LIBRARY_PATH not set'}")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    argv = sys.argv[1:]

    if '--help' in argv or '-h' in argv:
        print(__doc__)
        sys.exit(0)

    # Parse args
    driver_zip = None
    cert_zip = None
    check_only = '--check' in argv
    dsns_only = '--dsns-only' in argv

    i = 0
    while i < len(argv):
        if argv[i] == '--driver-zip' and i + 1 < len(argv):
            driver_zip = Path(argv[i + 1])
            i += 2
        elif argv[i] == '--cert-zip' and i + 1 < len(argv):
            cert_zip = Path(argv[i + 1])
            i += 2
        else:
            i += 1

    print()
    print("=" * 60)
    print("  NetSuite SuiteAnalytics Connect ODBC Setup")
    print("=" * 60)
    print()

    log(f"Fetching account config from gateway: {GATEWAY_URL}")
    accounts = fetch_accounts()
    ok(f"Found {len(accounts)} account(s) with ODBC config: {[a['id'] for a in accounts]}")
    print()

    if check_only:
        check_status(accounts)
        sys.exit(0)

    if not dsns_only:
        # Step 1: System packages
        check_install_unixodbc()
        check_install_pyodbc()
        print()

        # Step 2: Driver extraction
        lib = find_driver_lib()
        if lib:
            ok(f"NetSuite ODBC driver already installed: {lib}")
        else:
            if not driver_zip:
                print("  Download the NetSuite ODBC driver (Linux 64-bit) from:")
                print("  NetSuite > Setup > Company > SuiteAnalytics Connect")
                print()
                driver_zip_str = input("  Path to driver zip (or 'skip'): ").strip()
                if driver_zip_str.lower() == 'skip':
                    warn("Skipping driver installation.")
                else:
                    driver_zip = Path(driver_zip_str)

            if driver_zip:
                if not driver_zip.exists():
                    err(f"File not found: {driver_zip}")
                    sys.exit(1)
                extract_driver(driver_zip)

        # Step 3: Certificates
        cert_dir = DRIVER_INSTALL_DIR / 'cert'
        ca3 = cert_dir / 'ca3.cer'
        if ca3.exists():
            ok(f"Certificates already present in {cert_dir}")
        else:
            # Check if certs were included in driver zip
            bundled = list(DRIVER_INSTALL_DIR.rglob('ca3.cer'))
            if bundled:
                bundled_dir = bundled[0].parent
                if bundled_dir != cert_dir:
                    cert_dir.mkdir(parents=True, exist_ok=True)
                    for cer in bundled_dir.glob('*.cer'):
                        shutil.copy(cer, cert_dir / cer.name)
                ok(f"Certificates found in driver package: {[c.name for c in cert_dir.glob('*.cer')]}")
            elif cert_zip:
                extract_certs(cert_zip)
            else:
                print()
                print("  Certificate authority certs (ca3.cer, ca4.cer) are needed for TLS.")
                print("  Download 'Certificate Authority Certificates' from the same NetSuite page.")
                cert_zip_str = input("  Path to certs zip (or 'skip'): ").strip()
                if cert_zip_str.lower() != 'skip':
                    extract_certs(Path(cert_zip_str))

        # Step 4: Register driver
        lib = find_driver_lib()
        if lib:
            register_driver(lib)
        else:
            warn("Driver library not found — skipping driver registration.")

        print()

    # Step 5: Configure DSNs
    configure_dsns(accounts)
    print()

    # Step 6: ~/.bashrc
    update_bashrc()
    print()

    # Final status
    check_status(accounts)

    print("=" * 60)
    print("  Setup Complete!")
    print("=" * 60)
    print()
    print("  Next steps:")
    print()
    print("  1. Reload shell env (or open a new terminal):")
    print("     source ~/.bashrc")
    print()
    print("  2. Set ODBC credentials and refresh schema:")
    print("     export NETSUITE_ODBC_USER='your@email.com'")
    print("     export NETSUITE_ODBC_PASSWORD='yourpassword'")
    print("     python3 schema_refresh.py --all-accounts --all-environments")
    print()
    print("  3. Verify schema cache:")
    print("     python3 schema_lookup.py status")
    print()


if __name__ == '__main__':
    main()
