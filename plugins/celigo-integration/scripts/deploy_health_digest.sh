#!/usr/bin/env bash
# deploy_health_digest.sh — Deploy the Celigo Health Digest feature
#
# Executes Phases 2-4 of the plan:
#   Phase 2: Create script + attach to export + update pageSize
#   Phase 3: Update AI Agent import (model + prompt + mappings)
#   Phase 4: Simplify FTP CSV import mappings
#
# Prerequisites:
#   - celigo_config.json configured with valid API key
#   - celigo_api.py working (test: python3 celigo_api.py integrations list)
#
# Usage:
#   bash deploy_health_digest.sh [--dry-run]
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLI="python3 ${SCRIPT_DIR}/celigo_api.py"
HOOK_FILE="${SCRIPT_DIR}/health_digest_hook.js"

# Resource IDs (verified against live API 2026-02-19)
EXPORT_ID="698b4a2e1abec9665997a07b"   # "Get all jobs with errors" — HTTPExport
AI_IMPORT_ID="698b4eb6adf72c4591f9685f" # "AI Error Health Analyst" — aiAgent
FTP_IMPORT_ID="699605c7783ea4efe70cc4ff" # "Write Error Summary to CSV" — FTPImport
FLOW_ID="698b4a31ae386aee54914746"       # "AI Test" flow

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
echo "Step 2b: Attach script to export + increase pageSize to 100..."
# Update export: attach hook AND change relativeURI pageSize from 10 to 100
# (reduces State API calls by 90% — from ~100 pages to ~10)
run_cmd "$CLI exports update ${EXPORT_ID} \
  --data '{\"hooks\":{\"preSavePage\":{\"_scriptId\":\"${SCRIPT_ID}\"}},\"http\":{\"relativeURI\":\"/v1/jobs?pageSize=100\"}}'"

echo ""
echo "=== Phase 3: Update AI Agent Import ==="
echo ""

# NOTE: Verified field structure is aiAgent.openai (NOT assistantMetadata)
echo "Step 3: Update model to gpt-4.1-mini + new executive digest prompt..."
run_cmd "$CLI imports update ${AI_IMPORT_ID} \
  --file /dev/stdin" <<'JSONEOF'
{
  "aiAgent": {
    "openai": {
      "model": "gpt-4.1-mini",
      "instructions": "You are a Celigo integration health monitor. You receive a JSON summary of recent job execution data across all integrations.\n\nWrite a concise executive health digest (2-3 short paragraphs) covering:\n1. Overall health status (healthy/warning/critical) based on the error rate percentage\n2. Key issues: which flows have the most errors, and how many\n3. One recommended action\n\nFormat for Slack readability. Use plain text, no markdown headers or bullet lists.\nStart with a status indicator: \"HEALTHY\" if error rate <5%, \"WARNING\" if 5-15%, \"CRITICAL\" if >15%.\nInclude the time range and total job count.\nKeep it under 500 characters.",
      "maxOutputTokens": 600
    }
  }
}
JSONEOF

echo ""
echo "=== Phase 4: Simplify FTP CSV Import ==="
echo ""

# NOTE: Verified field is 'mappings' (array), not 'mapping.fields'
echo "Step 4: Update mappings to 2 columns (aiSummary + timestamp)..."
run_cmd "$CLI imports update ${FTP_IMPORT_ID} \
  --data '{\"mappings\":[{\"extract\":\"$.aiSummary\",\"generate\":\"aiSummary\",\"dataType\":\"string\"},{\"extract\":\"$.generatedAt\",\"generate\":\"timestamp\",\"dataType\":\"string\"}]}'"

echo ""
echo "=== Deployment complete ==="
echo ""
echo "Next steps (Phase 5 — Test and Verify):"
echo "  1. Run the flow:  $CLI flows run ${FLOW_ID}"
echo "  2. Monitor job:   $CLI flows jobs-latest ${FLOW_ID}"
echo "  3. Check errors:  $CLI errors list --flow ${FLOW_ID} --import ${AI_IMPORT_ID}"
echo "  4. Verify FTP CSV has 1 row with aiSummary + timestamp"
echo ""
