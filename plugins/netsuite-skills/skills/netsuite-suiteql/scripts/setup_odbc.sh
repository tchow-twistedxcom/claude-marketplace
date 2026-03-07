#!/usr/bin/env bash
# setup_odbc.sh -- One-time NetSuite SuiteAnalytics Connect ODBC setup
#
# Installs and configures:
#   1. unixODBC (ODBC driver manager)
#   2. pyodbc (Python ODBC library)
#   3. NetSuite ODBC driver (DataDirect / Progress Software)
#   4. ODBC DSN entries in ~/.odbc.ini
#   5. Schema cache directories
#
# Run once per machine before using schema_refresh.py.
# Download the NetSuite ODBC driver from:
#   NetSuite > Setup > Company > SuiteAnalytics Connect > Set Up SuiteAnalytics Connect
#
# DSN naming convention: netsuite_{account}_{environment}
#   netsuite_twistedx_production
#   netsuite_twistedx_sandbox
#   netsuite_twistedx_sandbox2
#   netsuite_dutyman_production
#   netsuite_dutyman_sandbox

set -euo pipefail

DRIVER_INSTALL_DIR="/opt/netsuite/odbcclient"
ODBC_INI="$HOME/.odbc.ini"
ODBCINST_INI_USER="$HOME/.odbcinst.ini"
CACHE_ROOT="$HOME/.cache/netsuite-schema"

# TwistedX account ID (from accounts.json)
TWX_ACCOUNT_ID="4138030"
# Dutyman account ID
DM_ACCOUNT_ID="8055418"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() { echo -e "${BLUE}[setup]${NC} $*"; }
ok()  { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err() { echo -e "${RED}[ERROR]${NC} $*"; }

check_or_install() {
    local pkg="$1"
    if dpkg -s "$pkg" &>/dev/null; then
        ok "$pkg already installed"
    else
        log "Installing $pkg..."
        sudo apt-get install -y "$pkg"
        ok "$pkg installed"
    fi
}

# ============================================================
# Step 1: Prerequisites
# ============================================================

echo ""
echo "============================================================"
echo "  NetSuite SuiteAnalytics Connect ODBC Setup"
echo "============================================================"
echo ""

log "Step 1: Checking prerequisites..."

# Check OS
if ! command -v apt-get &>/dev/null; then
    err "This script requires apt-get (Debian/Ubuntu). Adjust for your OS."
    exit 1
fi

check_or_install unixodbc
check_or_install unixodbc-dev  # Required for pyodbc compilation

# ============================================================
# Step 2: Install pyodbc
# ============================================================

log "Step 2: Installing pyodbc..."
if python3 -c "import pyodbc" &>/dev/null; then
    ok "pyodbc already installed"
else
    pip3 install --user pyodbc
    ok "pyodbc installed"
fi

# ============================================================
# Step 3: NetSuite ODBC Driver
# ============================================================

log "Step 3: NetSuite ODBC driver..."
echo ""
echo "  Download the driver from NetSuite:"
echo "  1. Log in to NetSuite"
echo "  2. Go to Setup > Company > SuiteAnalytics Connect"
echo "  3. Click 'Set Up SuiteAnalytics Connect'"
echo "  4. Download the Linux 64-bit ODBC driver zip"
echo ""

if [[ -f "$DRIVER_INSTALL_DIR/lib64/ivoa27.so" ]]; then
    ok "NetSuite ODBC driver already installed at $DRIVER_INSTALL_DIR"
else
    while true; do
        read -rp "  Path to downloaded driver zip (or 'skip' to skip): " DRIVER_ZIP
        if [[ "$DRIVER_ZIP" == "skip" ]]; then
            warn "Skipping driver installation. You will need to install it manually."
            warn "Expected driver library: $DRIVER_INSTALL_DIR/lib64/ivoa27.so"
            break
        fi
        if [[ ! -f "$DRIVER_ZIP" ]]; then
            err "File not found: $DRIVER_ZIP"
            continue
        fi

        log "Extracting driver to $DRIVER_INSTALL_DIR..."
        sudo mkdir -p "$DRIVER_INSTALL_DIR"
        sudo unzip -o "$DRIVER_ZIP" -d "$DRIVER_INSTALL_DIR"

        # Find the .so file (may be in a subdirectory)
        SO_FILE=$(find "$DRIVER_INSTALL_DIR" -name "ivoa27.so" 2>/dev/null | head -1)
        if [[ -z "$SO_FILE" ]]; then
            SO_FILE=$(find "$DRIVER_INSTALL_DIR" -name "*.so" 2>/dev/null | head -1)
        fi

        if [[ -z "$SO_FILE" ]]; then
            err "Could not find ODBC driver .so file in extracted archive."
            echo "Contents of $DRIVER_INSTALL_DIR:"
            ls -la "$DRIVER_INSTALL_DIR"/ 2>/dev/null || true
            continue
        fi

        ok "Driver library: $SO_FILE"
        DRIVER_INSTALL_DIR="$(dirname "$(dirname "$SO_FILE")")"
        break
    done
fi

DRIVER_LIB=$(find "$DRIVER_INSTALL_DIR" -name "ivoa27.so" 2>/dev/null | head -1 || echo "")

# ============================================================
# Step 4: Register ODBC Driver
# ============================================================

log "Step 4: Registering ODBC driver..."

if [[ -n "$DRIVER_LIB" ]]; then
    DRIVER_DIR="$(dirname "$DRIVER_LIB")"

    # Check if already registered
    if odbcinst -q -d -n "NetSuite" &>/dev/null; then
        ok "NetSuite ODBC driver already registered"
    else
        # Register in user odbcinst.ini (no root needed)
        cat >> "$ODBCINST_INI_USER" << EOF

[NetSuite]
Description=NetSuite SuiteAnalytics Connect ODBC Driver
Driver=$DRIVER_LIB
Setup=$DRIVER_LIB
UsageCount=1
EOF
        ok "NetSuite driver registered in $ODBCINST_INI_USER"
    fi

    # Find SSL certificates
    CERT_DIR="$DRIVER_INSTALL_DIR/cert"
    if [[ ! -d "$CERT_DIR" ]]; then
        CERT_DIR=$(find "$DRIVER_INSTALL_DIR" -name "ca*.cer" 2>/dev/null | head -1 | xargs -I{} dirname {} 2>/dev/null || echo "")
    fi

    if [[ -d "$CERT_DIR" ]]; then
        ok "Certificates found at $CERT_DIR"
        TRUST_STORE="$CERT_DIR/ca3.cer,$CERT_DIR/ca4.cer"
    else
        warn "Certificate directory not found. TLS verification may fail."
        TRUST_STORE=""
    fi
else
    warn "Driver library not found — skipping driver registration."
    warn "Edit $ODBCINST_INI_USER manually to register your driver."
    TRUST_STORE=""
fi

# ============================================================
# Step 5: Configure DSNs
# ============================================================

log "Step 5: Configuring DSNs in $ODBC_INI..."
echo ""
echo "  You need the following from your NetSuite SuiteAnalytics Connect page:"
echo "    - ServiceHost (e.g., 4138030.connect.api.netsuite.com)"
echo "    - Port (usually 1708)"
echo "    - Role ID (your NetSuite role for ODBC access)"
echo ""

# Check if DSNs already exist
EXISTING_DSNS=$(grep -c '^\[netsuite_' "$ODBC_INI" 2>/dev/null || echo 0)
if [[ "$EXISTING_DSNS" -gt 0 ]]; then
    echo "  Found $EXISTING_DSNS existing netsuite_* DSN(s) in $ODBC_INI"
    read -rp "  Re-configure DSNs? [y/N]: " RECONFIG
    if [[ ! "$RECONFIG" =~ ^[Yy] ]]; then
        log "Keeping existing DSNs"
    else
        EXISTING_DSNS=0
    fi
fi

if [[ "$EXISTING_DSNS" -eq 0 ]]; then
    echo ""

    configure_dsns() {
        local ACCT="$1"
        local ACCT_ID="$2"
        shift 2
        local ENVS=("$@")

        echo "  --- Configure $ACCT (Account ID: $ACCT_ID) ---"
        read -rp "  ServiceHost for $ACCT (e.g., ${ACCT_ID}.connect.api.netsuite.com): " SVC_HOST
        read -rp "  Port [1708]: " PORT
        PORT="${PORT:-1708}"
        read -rp "  Role ID for $ACCT: " ROLE_ID

        for ENV in "${ENVS[@]}"; do
            DSN="netsuite_${ACCT}_${ENV}"
            # Adjust host for sandbox environments
            case "$ENV" in
                sandbox)  HOST="${SVC_HOST//$ACCT_ID/${ACCT_ID}-sb1}" ;;
                sandbox2) HOST="${SVC_HOST//$ACCT_ID/${ACCT_ID}-sb2}" ;;
                *)        HOST="$SVC_HOST" ;;
            esac
            # NetSuite ODBC hosts are often: {accountid}.connect.api.netsuite.com or {accountid}-sb1.connect.api.netsuite.com

            cat >> "$ODBC_INI" << EOF

[$DSN]
Driver=NetSuite
Description=NetSuite $ACCT ($ENV)
Host=$HOST
Port=$PORT
ServerDataSource=NetSuite2.com
Encrypted=1
AllowSinglePacketLogout=1
${TRUST_STORE:+TrustStore=$TRUST_STORE}
CustomProperties=AccountID=$ACCT_ID;RoleID=$ROLE_ID
EOF
            ok "  DSN configured: $DSN (Host: $HOST)"
        done
        echo ""
    }

    echo ""
    echo "  Configure TwistedX account:"
    configure_dsns "twistedx" "$TWX_ACCOUNT_ID" "production" "sandbox" "sandbox2"

    echo "  Configure Dutyman account:"
    configure_dsns "dutyman" "$DM_ACCOUNT_ID" "production" "sandbox"

    ok "DSN configuration written to $ODBC_INI"
fi

# ============================================================
# Step 6: Test Connections
# ============================================================

log "Step 6: Testing ODBC connections..."
echo ""

test_connection() {
    local DSN="$1"
    local USER="$2"
    local PASS="$3"

    if python3 -c "
import pyodbc, sys
try:
    conn = pyodbc.connect('DSN=$DSN;UID=$USER;PWD=$PASS', timeout=15)
    cur = conn.cursor()
    cur.execute('SELECT table_name FROM oa_tables WHERE ROWNUM <= 1')
    row = cur.fetchone()
    conn.close()
    print('OK: Connected, got table:', row[0] if row else '(none)')
except Exception as e:
    print('FAIL:', str(e))
    sys.exit(1)
" 2>&1; then
        return 0
    else
        return 1
    fi
}

echo "  Enter credentials to test connections:"
read -rp "  ODBC Username (NetSuite email): " TEST_USER
read -rsp "  ODBC Password: " TEST_PASS
echo ""

TEST_DSNS=("netsuite_twistedx_sandbox2" "netsuite_dutyman_sandbox")
for DSN in "${TEST_DSNS[@]}"; do
    echo -n "  Testing $DSN... "
    if test_connection "$DSN" "$TEST_USER" "$TEST_PASS"; then
        ok "OK"
    else
        err "FAILED (check host/port/credentials in $ODBC_INI)"
    fi
done

# ============================================================
# Step 7: Create Cache Directories
# ============================================================

log "Step 7: Creating cache directories..."

ACCOUNTS=("twistedx" "dutyman")
TWX_ENVS=("production" "sandbox" "sandbox2")
DM_ENVS=("production" "sandbox")

for ACCT in "${ACCOUNTS[@]}"; do
    if [[ "$ACCT" == "twistedx" ]]; then
        ENVS=("${TWX_ENVS[@]}")
    else
        ENVS=("${DM_ENVS[@]}")
    fi
    for ENV in "${ENVS[@]}"; do
        DIR="$CACHE_ROOT/$ACCT/$ENV"
        mkdir -p "$DIR"
        ok "  $DIR"
    done
done

# ============================================================
# Summary
# ============================================================

echo ""
echo "============================================================"
echo "  Setup Complete!"
echo "============================================================"
echo ""
echo "  Next steps:"
echo ""
echo "  1. Refresh full ODBC schema (run when schema changes):"
echo "     export NETSUITE_ODBC_USER='your@email.com'"
echo "     export NETSUITE_ODBC_PASSWORD='yourpassword'"
echo "     python3 schema_refresh.py --all-accounts --all-environments"
echo ""
echo "  2. Refresh custom records (no ODBC needed, run anytime):"
echo "     python3 schema_lookup.py refresh-custom --account twx --env sb2"
echo ""
echo "  3. Verify everything is working:"
echo "     python3 schema_lookup.py status"
echo "     python3 schema_lookup.py describe Transaction --env sb2"
echo ""
echo "  TIP: Set NETSUITE_ODBC_USER and NETSUITE_ODBC_PASSWORD in ~/.bashrc"
echo "  to avoid repeated credential prompts."
echo ""
