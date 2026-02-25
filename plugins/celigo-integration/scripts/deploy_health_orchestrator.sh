#!/usr/bin/env bash
# deploy_health_orchestrator.sh — Deploy Phase 1 of Multi-System Health Orchestrator
#
# Reconfigures the existing Health Digest flow (PP4) from Slack posting
# to Dashboard webhook POST (B2bDashboard /api/health/ingest).
#
# Changes:
#   1. Create new "Dashboard Payload Builder" script
#   2. Create HTTP connection to B2bDashboard
#   3. Create HTTP import targeting POST /api/health/ingest
#   4. Update flow PP4 from Slack import → Dashboard import
#
# Prerequisites:
#   - celigo_config.json configured with valid API key
#   - celigo_api.py working (test: python3 celigo_api.py integrations list)
#   - B2bDashboard running with /api/health/ingest endpoint
#   - HEALTH_INGEST_API_KEY set in dashboard .env
#   - Dashboard URL accessible from Celigo (e.g., https://your-dashboard.example.com)
#
# Usage:
#   bash deploy_health_orchestrator.sh [--dry-run]
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLI="python3 ${SCRIPT_DIR}/celigo_api.py"
HOOK_FILE="${SCRIPT_DIR}/dashboard_payload_builder.js"

# Existing resource IDs (verified against live API)
FLOW_ID="698b4a31ae386aee54914746"                 # "AI Test" flow
AI_IMPORT_ID="698b4eb6adf72c4591f9685f"            # "AI Error Health Analyst" — stays
SLACK_IMPORT_ID="699c7192dbb446adf74f7216"         # "Post Health Digest to Slack" — will be replaced in PP4
BLOCK_KIT_SCRIPT_ID="699c9e947237f1bf5c4c13dc"     # block_kit_builder.js — current PP4 preMap

# New resource IDs (to be created)
DASHBOARD_SCRIPT_ID=""
DASHBOARD_CONNECTION_ID=""
DASHBOARD_IMPORT_ID=""

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "=== DRY RUN MODE — no changes will be made ==="
fi

run_cmd() {
  echo "  > $*"
  if [[ "$DRY_RUN" == "false" ]]; then
    eval "$@"
  else
    echo "  [skipped — dry run]"
  fi
}

echo ""
echo "=== Phase 1: Multi-System Health Orchestrator Deployment ==="
echo ""
echo "This script reconfigures PP4 from Slack → B2bDashboard webhook."
echo "The Slack import and connection are preserved (not deleted) for rollback."
echo ""

# ─────────────────────────────────────────────────────────────────────
# Step 1: Create the Dashboard Payload Builder script
# ─────────────────────────────────────────────────────────────────────
echo "Step 1: Create 'Dashboard Payload Builder' script..."
run_cmd "$CLI scripts create \
  --name 'Dashboard Payload Builder' \
  --function preMap \
  --code-file '${HOOK_FILE}'"

if [[ "$DRY_RUN" == "false" ]]; then
  echo ""
  echo ">>> Copy the _id from the output above and paste it here."
  read -rp "Script ID: " DASHBOARD_SCRIPT_ID
  echo "Using script ID: ${DASHBOARD_SCRIPT_ID}"
else
  DASHBOARD_SCRIPT_ID="<SCRIPT_ID_FROM_STEP_1>"
fi

# ─────────────────────────────────────────────────────────────────────
# Step 2: Create HTTP connection to B2bDashboard
# ─────────────────────────────────────────────────────────────────────
echo ""
echo "Step 2: Create HTTP connection to B2bDashboard..."
echo ""
echo ">>> Enter the B2bDashboard base URL (e.g., https://your-dashboard.example.com)"
read -rp "Dashboard URL: " DASHBOARD_URL

echo ">>> Enter the HEALTH_INGEST_API_KEY (from dashboard .env)"
read -rsp "API Key: " DASHBOARD_API_KEY
echo ""

cat > /tmp/dashboard_connection.json << CONN_EOF
{
  "type": "http",
  "name": "B2bDashboard - Health Ingest",
  "http": {
    "baseURI": "${DASHBOARD_URL}",
    "headers": [
      {
        "name": "X-API-Key",
        "value": "${DASHBOARD_API_KEY}"
      },
      {
        "name": "Content-Type",
        "value": "application/json"
      }
    ],
    "auth": {
      "type": "custom"
    },
    "mediaType": "json",
    "ping": {
      "relativeURI": "/api/health",
      "method": "GET",
      "successStatusCode": [200]
    }
  }
}
CONN_EOF

run_cmd "$CLI connections create --file /tmp/dashboard_connection.json"

if [[ "$DRY_RUN" == "false" ]]; then
  echo ""
  echo ">>> Copy the _id from the output above and paste it here."
  read -rp "Connection ID: " DASHBOARD_CONNECTION_ID
  echo "Using connection ID: ${DASHBOARD_CONNECTION_ID}"
  rm -f /tmp/dashboard_connection.json
else
  DASHBOARD_CONNECTION_ID="<CONNECTION_ID_FROM_STEP_2>"
fi

# ─────────────────────────────────────────────────────────────────────
# Step 3: Create HTTP import targeting POST /api/health/ingest
# ─────────────────────────────────────────────────────────────────────
echo ""
echo "Step 3: Create HTTP import for health ingest..."

cat > /tmp/dashboard_import.json << IMP_EOF
{
  "name": "Post Health Snapshot to Dashboard",
  "_connectionId": "${DASHBOARD_CONNECTION_ID}",
  "adaptorType": "HTTPImport",
  "http": {
    "relativeURI": "/api/health/ingest",
    "method": "POST",
    "sendPostMappedData": true,
    "requestMediaType": "json",
    "successMediaType": "json"
  },
  "mapping": {
    "fields": [
      {
        "extract": "timestamp",
        "generate": "timestamp",
        "dataType": "string",
        "status": "Active"
      },
      {
        "extract": "source",
        "generate": "source",
        "dataType": "string",
        "status": "Active"
      },
      {
        "extract": "ai_summary",
        "generate": "ai_summary",
        "dataType": "string",
        "status": "Active"
      },
      {
        "extract": "systems",
        "generate": "systems",
        "dataType": "string",
        "status": "Active"
      }
    ]
  },
  "hooks": {
    "preMap": {
      "_scriptId": "${DASHBOARD_SCRIPT_ID}",
      "function": "preMap"
    }
  }
}
IMP_EOF

run_cmd "$CLI imports create --file /tmp/dashboard_import.json"

if [[ "$DRY_RUN" == "false" ]]; then
  echo ""
  echo ">>> Copy the _id from the output above and paste it here."
  read -rp "Import ID: " DASHBOARD_IMPORT_ID
  echo "Using import ID: ${DASHBOARD_IMPORT_ID}"
  rm -f /tmp/dashboard_import.json
else
  DASHBOARD_IMPORT_ID="<IMPORT_ID_FROM_STEP_3>"
fi

# ─────────────────────────────────────────────────────────────────────
# Step 4: Update flow PP4 from Slack import → Dashboard import
# ─────────────────────────────────────────────────────────────────────
echo ""
echo "Step 4: Update flow PP4 to use Dashboard import..."
echo ""
echo "IMPORTANT: This uses the full-replace PUT pattern."
echo "You must first fetch the current flow, then update the pageProcessors array."
echo ""
echo "Manual steps (fetch-merge-PUT pattern):"
echo ""
echo "  1. Fetch the current flow:"
echo "     $CLI flows get ${FLOW_ID} > /tmp/current_flow.json"
echo ""
echo "  2. In the pageProcessors array, find the last PP (index 4)."
echo "     Replace its _importId from ${SLACK_IMPORT_ID} to ${DASHBOARD_IMPORT_ID}"
echo ""
echo "  3. Update the flow:"
echo "     $CLI flows update ${FLOW_ID} --file /tmp/current_flow.json"
echo ""
echo "  4. Test the flow:"
echo "     $CLI flows run ${FLOW_ID}"
echo ""
echo "=== Deployment script complete ==="
echo ""
echo "Summary of created resources:"
echo "  Script: ${DASHBOARD_SCRIPT_ID} (Dashboard Payload Builder)"
echo "  Connection: ${DASHBOARD_CONNECTION_ID} (B2bDashboard - Health Ingest)"
echo "  Import: ${DASHBOARD_IMPORT_ID} (Post Health Snapshot to Dashboard)"
echo ""
echo "Rollback: To revert PP4 back to Slack, change the last PP's _importId"
echo "back to ${SLACK_IMPORT_ID} using the same fetch-merge-PUT pattern."
