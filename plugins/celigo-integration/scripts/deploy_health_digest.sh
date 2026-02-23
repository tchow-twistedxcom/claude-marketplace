#!/usr/bin/env bash
# deploy_health_digest.sh — Deploy the Celigo Health Digest feature
#
# Executes setup for:
#   Phase 2: Create script + attach to export + update pageSize
#   Phase 3: Update AI Agent import (model + prompt + mappings)
#   Phase 4: Configure Slack import for digest posting
#
# Prerequisites:
#   - celigo_config.json configured with valid API key
#   - celigo_api.py working (test: python3 celigo_api.py integrations list)
#   - Slack bot token with chat:write scope
#   - Slack channel ID for digest posting
#
# Usage:
#   bash deploy_health_digest.sh [--dry-run]
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLI="python3 ${SCRIPT_DIR}/celigo_api.py"
HOOK_FILE="${SCRIPT_DIR}/health_digest_hook.js"

# Resource IDs (verified against live API 2026-02-23)
EXPORT_ID="698b4a2e1abec9665997a07b"          # "Get all jobs with errors" — HTTPExport
AI_IMPORT_ID="698b4eb6adf72c4591f9685f"       # "AI Error Health Analyst" — aiAgent
SLACK_IMPORT_ID="699c7192dbb446adf74f7216"    # "Post Health Digest to Slack" — HTTP POST
SLACK_CONNECTION_ID="699c7191783ea4efe724fe21" # "Slack - Health Digest Bot" — HTTP connection
FLOW_ID="698b4a31ae386aee54914746"            # "AI Test" flow

# Flow pipeline: Export → AI Agent (responseMapping: _text→aiSummary) → Slack (aiSummary→text)

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
echo "=== Phase 2: Create and deploy preSavePage hook ==="
echo ""

echo "Step 2a: Create script via API..."
run_cmd "$CLI scripts create \
  --name 'Health Digest Accumulator' \
  --function preSavePage \
  --code-file '${HOOK_FILE}'"

if [[ "$DRY_RUN" == "false" ]]; then
  echo ""
  echo ">>> Copy the _id from the output above and paste it here."
  echo ">>> (It will be used to attach the script to the export.)"
  read -rp "Script ID: " SCRIPT_ID
else
  SCRIPT_ID="<SCRIPT_ID>"
fi

echo ""
echo "Step 2b: Attach script to export + configure for full data fetch..."
# No formType: "assistant" — export fetches all jobs without delta tracking.
# pageSize=2000 ensures all jobs (API max 1001) arrive in single page.
run_cmd "$CLI exports update ${EXPORT_ID} \
  --data '{\"hooks\":{\"preSavePage\":{\"_scriptId\":\"${SCRIPT_ID}\",\"function\":\"preSavePage\"}},\"http\":{\"relativeURI\":\"/v1/jobs\",\"method\":\"GET\",\"requestMediaType\":\"json\",\"successMediaType\":\"json\",\"errorMediaType\":\"json\",\"isRest\":true,\"response\":{\"twoDArray\":{\"doNotNormalize\":false,\"hasHeader\":false}}},\"pageSize\":2000}'"

echo ""
echo "=== Phase 3: Update AI Agent Import ==="
echo ""

# NOTE: The AI Agent prompt contains:
#   - Explicit field definitions (totalFlowRuns, totalErrors, etc.)
#   - CST timezone conversion instruction
#   - Static "CURRENT OPEN ERRORS" section (refresh via CLI before updating)
#   - Flow ID→Name mapping (107+ flows)
#   - maxOutputTokens: 1000, model: gpt-4.1-mini
#
# The prompt is managed via:
#   $CLI imports update ${AI_IMPORT_ID} --file /tmp/ai_agent_update.json
#
# To generate a fresh prompt with current open errors and flow mappings,
# use the celigo_api.py health-digest generate command and update manually.

echo "Step 3: Update AI Agent import with prompt file..."
echo "  NOTE: Prepare /tmp/ai_agent_update.json with the full prompt first."
echo "  The prompt must include flow name mapping, CST instruction, and open errors."
run_cmd "$CLI imports update ${AI_IMPORT_ID} --file /tmp/ai_agent_update.json"

echo ""
echo "=== Phase 4: Configure Slack Import ==="
echo ""

# Slack import uses sendPostMappedData (not body template) to avoid JSON escaping issues.
# Mappings:
#   hardCodedValue "thomas-test-notifications" → channel
#   $.aiSummary → text
echo "Step 4: Verify Slack import configuration..."
echo "  Import: ${SLACK_IMPORT_ID}"
echo "  Connection: ${SLACK_CONNECTION_ID}"
echo "  Endpoint: POST /chat.postMessage"
echo "  Channel: thomas-test-notifications"
run_cmd "$CLI imports get ${SLACK_IMPORT_ID} -f json | python3 -c 'import sys,json; d=json.load(sys.stdin); print(\"OK\" if d.get(\"name\") else \"MISSING\")'"

echo ""
echo "=== Deployment complete ==="
echo ""
echo "Next steps (Test and Verify):"
echo "  1. Run the flow:  $CLI flows run ${FLOW_ID}"
echo "  2. Monitor job:   $CLI flows jobs-latest ${FLOW_ID}"
echo "  3. Check errors:  $CLI errors list --flow ${FLOW_ID} --import ${AI_IMPORT_ID}"
echo "  4. Verify Slack message in #thomas-test-notifications"
echo ""
echo "To update open errors in the AI prompt:"
echo "  1. Fetch current errors:  $CLI errors integration-summary <integration_id>"
echo "  2. Update prompt file:    Edit /tmp/ai_agent_update.json"
echo "  3. Push to Celigo:        $CLI imports update ${AI_IMPORT_ID} --file /tmp/ai_agent_update.json"
echo ""
