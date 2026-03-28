---
name: airbyte-integration
description: "Manage Airbyte 2.0.1 on twistedx-docker (kind K8s cluster via abctl). Use when user asks to: trigger a sync, check sync status, update credentials, debug pipeline failures, manage streams/connections/sources, fix OOMKill or CrashLoopBackOff, rebuild custom connector images, or query Airbyte DB directly. Covers public API, web_backend internal API, DB operations, kubectl cluster management, memory/probe config, and stream configuration for SC and VC Amazon SP-API connections."
---

# Airbyte Integration

Airbyte is self-hosted via `abctl` (Kubernetes/kind) on **twistedx-docker** (Tailscale). This skill documents the API patterns needed to manage it programmatically.

## Reference Files

Load these when you need deeper coverage:

| File | When to use |
|------|------------|
| [references/db-operations.md](references/db-operations.md) | Direct DB queries, job/workload/attempt status, image tag updates, emergency cancellation |
| [references/cluster-operations.md](references/cluster-operations.md) | kubectl commands, memory patches, liveness probe tuning, loading custom images, abctl CLI |
| [references/stream-config.md](references/stream-config.md) | web_backend API, stream enable/disable, SC/VC stream lists, Snowflake verification |

## Infrastructure

| Property | Value |
|----------|-------|
| Server | `100.117.161.21` (twistedx-docker on Tailscale) |
| Port | `8100` |
| Base URL | `http://100.117.161.21:8100` |
| Airbyte Version | 2.0.1 (Helm chart 2.0.19) |
| Install method | `abctl` (kind Kubernetes cluster `airbyte-abctl`) |

> **CRITICAL**: Every API request MUST include `Host: localhost` header or nginx ingress returns 404.

## Authentication

Tokens expire per session — always get a fresh token at the start of each task.

### Step 1 — Get credentials (if not known)

```bash
ssh 100.117.161.21 "abctl local credentials"
# Returns: email, password, Client-Id, Client-Secret
```

Credentials are also stored in 1Password vault **"Twisted X AI Agent"** — check for an "Airbyte" item if added.

### Step 2 — Exchange for Bearer token

```bash
TOKEN=$(curl -s -X POST "http://100.117.161.21:8100/api/v1/applications/token" \
  -H "Content-Type: application/json" \
  -H "Host: localhost" \
  -d '{
    "client_id": "b715ca2b-a852-4389-b24e-e7fc5ea99974",
    "client_secret": "<get from abctl local credentials>",
    "grant_type": "client_credentials"
  }' | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")
```

**Note**: Client ID is `b715ca2b-a852-4389-b24e-e7fc5ea99974`. Client secret is retrieved via SSH or 1Password.

## Known IDs

| Resource | Name | ID |
|----------|------|-----|
| Workspace | Default Workspace | `85428214-e371-4d35-b66e-7ea3a7d32f27` |
| Source | Amazon SP-API - Seller Central (3P) | `ba6467b0-cd16-4814-ba4b-7fe0a7d5dea2` |
| Source | Amazon SP-API - Vendor Central (1P) | `04fc6d68-a18e-4376-a443-1581359175cd` |
| Connection | Seller Central → Snowflake | `4dff2ab4-2683-4299-8af0-dc5e938be7d3` |
| Connection | Vendor Central → Snowflake | `bfa37c64-4107-40b0-9be1-7d7108c955da` |

## API Reference

All requests use base path `/api/public/v1/` and require:
- `Authorization: Bearer $TOKEN`
- `Host: localhost`

### List Sources

```bash
curl -s "http://100.117.161.21:8100/api/public/v1/sources?workspaceIds=85428214-e371-4d35-b66e-7ea3a7d32f27" \
  -H "Authorization: Bearer $TOKEN" -H "Host: localhost"
```

### Get Source Config

```bash
curl -s "http://100.117.161.21:8100/api/public/v1/sources/<sourceId>" \
  -H "Authorization: Bearer $TOKEN" -H "Host: localhost"
```

### Update Source Credentials (e.g. rotate refresh token)

```bash
curl -s -X PATCH "http://100.117.161.21:8100/api/public/v1/sources/<sourceId>" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "configuration": {
      "sourceType": "amazon-seller-partner",
      "region": "US",
      "lwa_app_id": "<client_id>",
      "lwa_client_secret": "<client_secret>",
      "refresh_token": "<new_refresh_token>",
      "start_date": "2024-01-01T00:00:00Z",
      "account_type": "Vendor",
      "aws_environment": "PRODUCTION"
    }
  }'
```

### List Connections

```bash
curl -s "http://100.117.161.21:8100/api/public/v1/connections?workspaceIds=85428214-e371-4d35-b66e-7ea3a7d32f27" \
  -H "Authorization: Bearer $TOKEN" -H "Host: localhost"
```

### Trigger a Sync

```bash
curl -s -X POST "http://100.117.161.21:8100/api/public/v1/jobs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Host: localhost" \
  -H "Content-Type: application/json" \
  -d '{"connectionId": "<connectionId>", "jobType": "sync"}'
```

Returns `409` with `"A sync is already running"` if one is in progress — that's normal.

### Check Job / Sync Status

```bash
# List recent jobs for a connection
curl -s "http://100.117.161.21:8100/api/public/v1/jobs?connectionId=<connectionId>&limit=5" \
  -H "Authorization: Bearer $TOKEN" -H "Host: localhost" | \
  python3 -c "import json,sys; [print(j['jobId'], j['status'], j.get('startTime','')) for j in json.load(sys.stdin).get('data',[])]"
```

Job statuses: `running`, `succeeded`, `failed`, `cancelled`, `pending`

### Health Check

```bash
curl -s -H "Host: localhost" "http://100.117.161.21:8100/api/v1/health"
# Returns: {"available": true}
```

## Amazon SP-API Source Config Reference

The Amazon sources use `sourceType: amazon-seller-partner` with these fields:

| Field | Seller Central | Vendor Central |
|-------|---------------|----------------|
| `account_type` | `Seller` | `Vendor` |
| `lwa_app_id` | `amzn1.application-oa2-client.f05eaeced30b4e188f97fa71c61e9a82` | same |
| `lwa_client_secret` | from 1Password "Amazon SP-API" | same |
| `refresh_token` | `seller_refresh_token` from 1Password | `vendor_refresh_token` from 1Password |
| `start_date` | `2025-12-10T00:00:00Z` | `2025-12-10T00:00:00Z` |
| `region` | `US` | `US` |
| `aws_environment` | `PRODUCTION` | `PRODUCTION` |

> **⚠️ PATCHING SOURCES — CRITICAL**: When doing a PATCH via public API, the GET response returns masked values (`**********`) for secret fields. Sending those masked values back in a PATCH will **overwrite and destroy** the real credentials. Always fetch secrets fresh from 1Password and send the real values. See the 1password skill for the safe subprocess pattern.

## Custom Connector Image History

### Current: `5.6.0-vc-fix5` (as of 2026-03-11)

**All fixes from vc-fix4 PLUS GET_VENDOR_SALES_REPORT cursor fix.**

**Changes in vc-fix5 (manifest patch via Python):**

1. **`GET_VENDOR_SALES_REPORT`: Added `DatetimeBasedCursor` with `step: P3M`** — The stream previously sent ONE request for the full date range (e.g., 26 months), which caused Amazon to return `AsyncJobStatus.FAILED`. Now splits into 3-month quarterly slices. Cursor field: `endDate`. After first run, state: `{"endDate": "2026-02-28T00:00:00Z"}` (truly incremental on subsequent runs).
   - `dataStartTime`: `{{ stream_slice.cursor_slice.start_time[:7] ~ '-01T00:00:00Z' }}` (snaps to month start)
   - `dataEndTime`: `{{ stream_slice.cursor_slice.end_time }}`

**vc-fix4 fixes preserved** (see vc-fix4 section below).

---

### Previous: `5.6.0-vc-fix4` (superseded 2026-03-11)

**All fixes from vc-fix3 PLUS performance/backfill optimizations.**

**Changes in vc-fix4 (applied via Python to manifest):**

1. **`step: P1D` → `P30D`** — `GET_SALES_AND_TRAFFIC_REPORT` and `GET_SALES_AND_TRAFFIC_REPORT_BY_DATE` had hardcoded P1D step causing 730+ API calls for 2 years. Changed to P30D (~26 calls).

2. **`step: P7D` → `P30D`** — `VendorOrders`/`VendorOrdersStatus`/`VendorDirectFulfillmentShipping` had P7D step. Changed to P30D.

3. **`P730D` → `P1000D`** (86 occurrences) — All `start_datetime` Jinja expressions capped lookback at 730 days (~Mar 2024). Extended to 1000 days to allow Jan 2024 start.

4. **`start_date` fallback in `replication_start_date`** (43 occurrences) — Manifest uses `config.get('replication_start_date', ...)` but Airbyte API stores field as `start_date`. Added fallback: `config.get('start_date', config.get('replication_start_date', ...))`.

**vc-fix3 fixes preserved:**
- VendorCheck stream in `check:` block (replaces Orders — 3P-only, always 403 for Vendor accounts)
- `dataStartTime`/`dataEndTime` Jinja expressions for vendor sales and inventory
- `reportOptions` with `distributorView: MANUFACTURING`, `sellingProgram: RETAIL`
- `dataEndTime` formula that excludes incomplete current month

**Custom image details:**

| Property | Value |
|----------|-------|
| Image tag | `airbyte/source-amazon-seller-partner:5.6.0-vc-fix5` |
| SC actor_definition_version ID | `0f0aa1a3-ccf4-4927-8fde-2c87ec572b2d` (actor_def `e55879a8`) |
| VC actor_definition_version ID | `cde0f46c-a3ab-4662-ae1f-7938c69059cb` (actor_def `ec291512`) |
| Base image | `airbyte/source-amazon-seller-partner:5.6.0` |
| Manifest location (in image) | `/airbyte/integration_code/source_declarative_manifest/manifest.yaml` |

> **CRITICAL**: SC and VC use DIFFERENT actor_definitions! SC uses `e55879a8` ("Amazon Seller Partner" standard); VC uses `ec291512` ("Amazon SP-API - Vendor Fixed" custom). Both have separate `actor_definition_version` rows that must be updated when changing images.

> **CRITICAL**: Airbyte runs in a kind K8s cluster inside Docker container `airbyte-abctl-control-plane`. The kind cluster has its OWN containerd instance — images must be loaded into the KIND container's containerd, NOT the host's. Use `docker exec -i airbyte-abctl-control-plane ctr ...`, not `sudo ctr ...`.

**How to rebuild if needed:**

```bash
# On twistedx-docker
cd /tmp
# 1. Extract manifest from running image
docker run --rm --entrypoint cat airbyte/source-amazon-seller-partner:5.6.0-vc-fix4 \
  /airbyte/integration_code/source_declarative_manifest/manifest.yaml > manifest.yaml

# 2. Edit manifest (or apply Python fixes — see fix4 changes above)

# 3. Build and load into KIND container's containerd (NOT host!)
cat > Dockerfile << 'EOF'
FROM airbyte/source-amazon-seller-partner:5.6.0
COPY manifest.yaml /airbyte/integration_code/source_declarative_manifest/manifest.yaml
EOF
docker build -t airbyte/source-amazon-seller-partner:5.6.0-vc-fix5 .
docker save airbyte/source-amazon-seller-partner:5.6.0-vc-fix5 | \
  docker exec -i airbyte-abctl-control-plane ctr -n k8s.io images import -

# 4. Update DB for BOTH SC and VC actor_definition_versions
docker exec airbyte-abctl-control-plane kubectl exec -n airbyte-abctl airbyte-db-0 -- \
  psql -U airbyte -d db-airbyte -c \
  "UPDATE actor_definition_version SET docker_image_tag='5.6.0-vc-fix5' WHERE id IN ('0f0aa1a3-ccf4-4927-8fde-2c87ec572b2d','cde0f46c-a3ab-4662-ae1f-7938c69059cb');"
```

**Vendor stream date logic (in manifest):**

```yaml
# Sales: startDate = first day of config start_month, endDate = last day of prev complete month
dataStartTime: "{{ config.get('start_date', (now_utc() - duration('P90D')).strftime('%Y-%m-%dT00:00:00Z'))[:7] ~ '-01T00:00:00Z' }}"
dataEndTime: "{{ (now_utc() - duration('P' ~ now_utc().day ~ 'D')).strftime('%Y-%m-%dT23:59:59Z') }}"
reportOptions: {reportPeriod: MONTH, distributorView: MANUFACTURING, sellingProgram: RETAIL}

# Inventory: 22-day window ending 8 days ago (data available with ~7-8 day lag)
dataStartTime: "{{ (now_utc() - duration('P22D')).strftime('%Y-%m-%dT00:00:00Z') }}"
dataEndTime: "{{ (now_utc() - duration('P8D')).strftime('%Y-%m-%dT23:59:59Z') }}"
reportOptions: {reportPeriod: DAY, distributorView: MANUFACTURING, sellingProgram: RETAIL}
```

**Snowflake permissions note:** Tables in both `SELLER_DATA` and `VENDOR_DATA` must be owned by `AIRBYTE_ROLE` (not ACCOUNTADMIN). If jobs fail with "Insufficient privileges to operate on table":

```python
# Fix: grant ownership on ALL tables + future tables (as ACCOUNTADMIN)
import snowflake.connector, subprocess, os

pw = subprocess.run(["op", "item", "get", "Snowflake - Admin (tchowtwistedxcom)",
    "--vault", "Twisted X AI Agent", "--fields", "password", "--reveal"],
    capture_output=True, text=True, env={**os.environ}).stdout.strip()
conn = snowflake.connector.connect(account="qgmygkf-vr21666", user="tchowtwistedxcom",
    password=pw, database="AIRBYTE_RAW", role="ACCOUNTADMIN", warehouse="AIRBYTE_WAREHOUSE")
cur = conn.cursor()
for schema in ("SELLER_DATA", "VENDOR_DATA"):
    cur.execute(f"SHOW TABLES IN SCHEMA AIRBYTE_RAW.{schema}")
    for row in cur.fetchall():
        cur.execute(f'GRANT OWNERSHIP ON TABLE AIRBYTE_RAW.{schema}."{row[1]}" TO ROLE AIRBYTE_ROLE COPY CURRENT GRANTS')
    cur.execute(f"GRANT ALL PRIVILEGES ON FUTURE TABLES IN SCHEMA AIRBYTE_RAW.{schema} TO ROLE AIRBYTE_ROLE")
    cur.execute(f"GRANT CREATE TABLE ON SCHEMA AIRBYTE_RAW.{schema} TO ROLE AIRBYTE_ROLE")
conn.commit()
```

Admin credentials: `Snowflake - Admin (tchowtwistedxcom)` in vault `Twisted X AI Agent`.

## Active Connection Config (as of 2026-03-11)

| Connection | Streams | Schedule | Status |
|-----------|---------|----------|--------|
| SC → Snowflake | ALL streams enabled | 2:00 AM UTC daily | ✅ Running |
| VC → Snowflake | 9 streams enabled | 4:00 AM UTC daily | ✅ Job 75 succeeded — first clean run |

### VC Disabled Streams (permanently unavailable for Twisted X)
- `GET_VENDOR_FORECASTING_FRESH_REPORT` — Amazon Fresh program, not available for shoe brands
- `GET_BRAND_ANALYTICS_ALTERNATE_PURCHASE_REPORT` — not available for this vendor account
- `GET_BRAND_ANALYTICS_ITEM_COMPARISON_REPORT` — not available for this vendor account

**Source config:** Both sources PATCH'd with `start_date=2024-01-01T00:00:00Z` AND `replication_start_date=2024-01-01T00:00:00Z` (manifest reads `replication_start_date` but API stores as `start_date`; fix4 manifest handles both).

**1Password item**: `Amazon SP-API` in vault `Twisted X AI Agent`

```bash
# Retrieve credentials from 1Password
op item get "Amazon SP-API" --vault "Twisted X AI Agent" \
  --fields lwa_client_id,lwa_client_secret,seller_refresh_token,vendor_refresh_token --reveal
```

## Snowflake Destination Config

Data lands in `AIRBYTE_RAW` database:
- Seller Central streams → schema `SELLER_DATA`
- Vendor Central streams → schema `VENDOR_DATA`
- Verification SQL: `/home/tchow/InfrastructureDashboard/docs/snowflake-amazon-verification-dashboard.sql`

## Common Workflows

### Rotate VC refresh token end-to-end

1. Get new token from Vendor Central → Settings → Account Info → Developer Access
2. Verify it works: `python3 spapi_api.py --profile vendor reports create --type GET_VENDOR_SALES_REPORT`
3. Update 1Password: `op item edit "Amazon SP-API" --vault "Twisted X AI Agent" "vendor_refresh_token=<new>"`
4. Update Airbyte source via PATCH API (see above)
5. Trigger sync: POST to `/api/public/v1/jobs` with VC connection ID
6. Verify in Snowflake: check `VENDOR_DATA` table row counts

### Debug empty Snowflake tables

1. Check `INFORMATION_SCHEMA.TABLES` for row counts and `LAST_ALTERED` timestamps
2. If `LAST_ALTERED ≈ CREATED` (within seconds) → table was schema-only, never received data
3. If `LAST_ALTERED` is hours/days after `CREATED` → data did sync
4. Check `_AIRBYTE_META` on populated tables for `sync_id` and `changes`
5. Root causes: wrong account type (MerchantAccountId vs VendorAccountId), missing API permissions, report generation timeout

### Fix source container OOMKill (memory too low)

**Symptom**: Source container exits with code 137 (OOMKilled) during large streams.

**Root cause**: The server pod (`airbyte-abctl-server`) creates jobs with `SyncResourceRequirements.source` baked in at job creation time. If the server hasn't been restarted after a ConfigMap change, it uses stale env vars.

**ConfigMap** `airbyte-abctl-airbyte-env` controls memory:
```
JOB_MAIN_CONTAINER_MEMORY_LIMIT: 4Gi
JOB_MAIN_CONTAINER_MEMORY_REQUEST: 2Gi
REPLICATION_ORCHESTRATOR_MEMORY_LIMIT: 4Gi
CONNECTOR_SPECIFIC_RESOURCE_DEFAULTS_ENABLED: "false"
```

**Fix**: After updating ConfigMap, restart the server pod:
```bash
ssh 100.117.161.21 "docker exec airbyte-abctl-control-plane kubectl rollout restart deployment/airbyte-abctl-server -n airbyte-abctl"
```

New jobs will then have 4Gi source limits. Verify:
```bash
kubectl get pod replication-job-<N>-attempt-0 -o jsonpath='{.spec.containers[*].resources}'
```

### Fix workload-launcher CrashLoopBackOff

**Symptom**: Launcher crashes repeatedly with exit code 143 (liveness probe timeout). Replication pods never start.

**Root cause**: The MUTEX stage (`EnforceMutexStage`) tries to delete old replication pods with the same connection ID (from previous failed/error jobs). If old pods are stuck (Error/Completed with no cleanup), the K8s API call blocks the launcher threads, causing liveness probe timeout.

**Fix**: Force-delete the stale replication pods:
```bash
# List stuck pods
kubectl get pods -n airbyte-abctl | grep replication

# Force delete
kubectl delete pod -n airbyte-abctl replication-job-<N>-attempt-0 --force
```

The launcher will then unblock, proceed past MUTEX → ARCHITECTURE → LAUNCH stages, and create new replication pods.

### Fix all Airbyte pods crashing (missing memory limits / BestEffort QoS)

**Symptom**: Multiple pods crash-looping — worker OOMKilled (exit 137), workload-api-server and workload-launcher crashing (exit 143 / liveness probe failure). Syncs fail with `No successful heartbeat in the last 600s; exiting` in orchestrator logs.

**Root cause**: Airbyte pods deployed with no resource limits (`{}`). Worker has no JVM heap limit and grows unbounded → kernel OOM kills it. Workload-api-server JVM GC pauses cause liveness probe port 8085 to stop responding → SIGTERM.

**Fix**: Patch all deployments to add memory limits:
```bash
# Worker (Temporal workflows)
kubectl patch deployment -n airbyte-abctl airbyte-abctl-worker --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/resources","value":{"requests":{"memory":"1Gi","cpu":"100m"},"limits":{"memory":"2Gi","cpu":"2"}}}]'

# Workload API server (heartbeat handler)
kubectl patch deployment -n airbyte-abctl airbyte-abctl-workload-api-server --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/resources","value":{"requests":{"memory":"512Mi","cpu":"100m"},"limits":{"memory":"1Gi","cpu":"1"}}}]'

# Workload launcher (pod creator)
kubectl patch deployment -n airbyte-abctl airbyte-abctl-workload-launcher --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/resources","value":{"requests":{"memory":"512Mi","cpu":"100m"},"limits":{"memory":"2Gi","cpu":"2"}}}]'

# Server (job creator)
kubectl patch deployment -n airbyte-abctl airbyte-abctl-server --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/resources","value":{"requests":{"memory":"512Mi","cpu":"100m"},"limits":{"memory":"2Gi","cpu":"2"}}}]'

# Wait for rollouts
kubectl rollout status deployment/airbyte-abctl-worker -n airbyte-abctl
kubectl rollout status deployment/airbyte-abctl-workload-api-server -n airbyte-abctl
kubectl rollout status deployment/airbyte-abctl-workload-launcher -n airbyte-abctl
kubectl rollout status deployment/airbyte-abctl-server -n airbyte-abctl
```

> **Note**: These patches are NOT persisted across `abctl local install` re-installs. Re-apply after upgrades.
> **Note**: The `abctl` prefix needed only when calling from outside the cluster. Remove for commands inside the control plane container.

### Get abctl credentials via Portainer

Airbyte runs on environment ID `2` (Docker-SSC) in Portainer. The kind container is `airbyte-abctl-control-plane` — port 80 maps to host port 8100.
