#!/bin/bash

# NetSuite Certificate Generator
# Generates self-signed X.509 certificates for NetSuite TBA authentication

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Display usage
usage() {
  cat << EOF
NetSuite Certificate Generator

Usage: $0 <authid> [output-directory]

Arguments:
  authid            Unique identifier for the certificate (e.g., myapp-sb1)
  output-directory  Directory to save certificate files (default: ./keys)

Examples:
  $0 myapp-sb1
  $0 myapp-prod /secure/keys

Output:
  <authid>.pem  - Private key (keep secure!)
  <authid>.crt  - Certificate (upload to NetSuite)

EOF
  exit 1
}

# Check arguments
if [ $# -lt 1 ]; then
  usage
fi

AUTH_ID="$1"
OUTPUT_DIR="${2:-./keys}"

# Validate authId format
if [[ ! "$AUTH_ID" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo -e "${RED}Error: authId must contain only letters, numbers, underscores, and hyphens${NC}"
  exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# File paths
PRIVATE_KEY="$OUTPUT_DIR/$AUTH_ID.pem"
CERTIFICATE="$OUTPUT_DIR/$AUTH_ID.crt"

# Check if files already exist
if [ -f "$PRIVATE_KEY" ] || [ -f "$CERTIFICATE" ]; then
  echo -e "${YELLOW}Warning: Certificate files already exist for '$AUTH_ID'${NC}"
  read -p "Overwrite? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
  fi
fi

echo -e "${GREEN}Generating certificate for authId: $AUTH_ID${NC}"
echo

# Generate private key
echo "📝 Generating private key..."
openssl genrsa -out "$PRIVATE_KEY" 2048

# Set secure permissions on private key
chmod 600 "$PRIVATE_KEY"

# Generate self-signed certificate
echo "🔐 Generating self-signed certificate..."
openssl req -new -x509 -key "$PRIVATE_KEY" -out "$CERTIFICATE" -days 3650 \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=$AUTH_ID"

echo
echo -e "${GREEN}✅ Certificate generated successfully!${NC}"
echo
echo "📁 Files created:"
echo "  Private Key:  $PRIVATE_KEY"
echo "  Certificate:  $CERTIFICATE"
echo
echo -e "${YELLOW}⚠️  IMPORTANT SECURITY NOTES:${NC}"
echo "  1. Keep the private key (.pem) file SECURE and PRIVATE"
echo "  2. Never commit the private key to version control"
echo "  3. Add to .gitignore: *.pem"
echo "  4. Private key permissions: $(ls -l "$PRIVATE_KEY" | awk '{print $1}')"
echo
echo -e "${GREEN}📤 Next Steps:${NC}"
echo "  1. Upload the certificate (.crt) to NetSuite:"
echo "     Setup > Company > Setup Tasks > Manage Certificates"
echo
echo "  2. Note the Certificate ID from NetSuite"
echo
echo "  3. Update your configuration:"
echo "     Option A: Environment variable"
echo "       export TWX_SDF_${AUTH_ID^^}_CERT_ID=\"cert-id-from-netsuite\""
echo "       export TWX_SDF_${AUTH_ID^^}_PRIVATE_KEY_PATH=\"$PRIVATE_KEY\""
echo
echo "     Option B: twx-sdf.config.json"
cat << JSON
       {
         "environments": {
           "$AUTH_ID": {
             "accountId": "YOUR_ACCOUNT_ID",
             "authId": "$AUTH_ID",
             "certificateId": "cert-id-from-netsuite",
             "privateKeyPath": "$PRIVATE_KEY"
           }
         }
       }
JSON
echo
echo "  4. Test deployment:"
echo "     npx twx-deploy deploy $AUTH_ID --dry-run"
echo
echo -e "${GREEN}Done!${NC}"
