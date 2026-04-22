---
title: "Railway SKIPPED gateway deploy + Redis 503 after adding schema-cron/railway.toml"
date: 2026-04-18
category: docs/solutions/runtime-errors
module: netsuite-api-gateway
problem_type: runtime_error
component: tooling
severity: high
symptoms:
  - All GET and POST requests to /api/common/schema/* returned 401 "API key is required" — the same error as the catch-all auth middleware, indicating schema routes were never reached
  - railway deployment list showed latest deploy as SKIPPED; gateway was running April 7 pre-schema-routes build
  - schema-cron service build failed with "Could not find root directory: schema-cron"
  - After forced redeploy, schema endpoints returned 503 "Redis not available" despite REDIS_ENABLED=true being set
  - railway variables showed no REDIS_URL — Redis service had never been provisioned
root_cause: incomplete_setup
resolution_type: environment_setup
tags:
  - railway
  - express
  - redis
  - deployment
  - schema-cache
  - github-app
  - monorepo
related_components:
  - netsuite-suiteql
  - schema-cron
---

# Railway SKIPPED gateway deploy + Redis 503 after adding schema-cron/railway.toml

## Problem

After merging PR #23 (which added `routes/schema.js` schema cache endpoints and `schema-cron/railway.toml` for a planned cron service), all `/api/common/schema/*` requests returned 401. The schema routes were mounted correctly in Express before the auth middleware, but Railway had silently skipped the deployment — the gateway was still serving April 7 code. After forcing a deploy, the routes returned 503 because the Railway Redis service was never provisioned despite `REDIS_ENABLED=true` being set.

## Symptoms

- `GET /api/common/schema/twistedx/sandbox2/_meta` → `401 "API key is required"` (same error as the `/api/:appId` auth catch-all — not a schema route error)
- `railway deployment list` → latest deployment status `SKIPPED`, last SUCCESS was April 7
- Railway CI error: "Could not find root directory: schema-cron" from a phantom schema-cron service build
- After forced redeploy: `GET /api/common/schema/twistedx/sandbox2/invalid` → `400 "Unknown resource"` ✓ but `GET /_meta` → `503 "Redis not available"`
- `railway variables | grep -i redis` → only `REDIS_ENABLED=true`, no `REDIS_URL`

## What Didn't Work

**GitHub push deploys while `schema-cron/railway.toml` was in the repo.** Railway's GitHub App detected the new file and attempted to auto-build a `schema-cron` service with root=`schema-cron`. That build failed (ODBC driver files are gitignored). Railway cascaded this failure and marked the gateway deployment SKIPPED. Every subsequent commit push continued to SKIP silently.

**`railway add --database redis`.** In non-interactive/terminal mode this command hangs — outputs `> What do you need? Database` and exits without provisioning anything. Not suitable for scripted use.

**`railway deployment redeploy --yes` before deploying new code.** This replays the last *successful* build (April 7 code), not the current filesystem. Running this before `railway up` just re-runs the stale image and does not pick up the new schema routes.

*(session history)* Redis on this gateway was always a Docker-compose service — never a Railway addon across all prior sessions through March 2026. This means the gap (`REDIS_ENABLED=true` but no `REDIS_URL`) was a systematic configuration oversight, not a regression from a working state.

## Solution

### Step 1 — Remove conflicting Railway config and force-deploy new code

```bash
# Remove the file causing Railway to attempt an unbuildable schema-cron service
git rm schema-cron/railway.toml
git commit -m "fix: remove schema-cron railway.toml causing gateway deployment skip"
git push origin main

# Deploy directly via CLI, bypassing GitHub integration
cd ~/NetSuiteApiGateway
railway up --detach

# Verify schema routes are now reachable (expect 400, not 401)
curl https://nsapi.twistedx.tech/api/common/schema/twistedx/sandbox2/invalid_resource
# → 400 {"error": {"message": "Unknown resource 'invalid_resource'..."}}
```

### Step 2 — Provision Redis and link to gateway

```bash
# Provision Redis (railway add --database redis hangs; use template instead)
railway deploy --template redis

# Switch back to the gateway service
railway service netsuite-gateway

# Link Redis using Railway's variable reference syntax (expands at runtime)
railway variable --set "REDIS_URL=\${{Redis.REDIS_URL}}"

# Generate and set admin token for schema POST endpoints
railway variable --set "SCHEMA_ADMIN_TOKEN=$(openssl rand -hex 32)"

# Redeploy gateway to pick up new env vars
railway deployment redeploy --yes

# Verify Redis is connected
curl https://nsapi.twistedx.tech/health/detailed
# → "cache": {"type": "redis", "status": "healthy"}
```

### Step 3 — Seed schema data from local ODBC cache

Upload cached ODBC schema files via direct POST to the schema endpoints:

```bash
TOKEN=<SCHEMA_ADMIN_TOKEN>
BASE=https://nsapi.twistedx.tech
CACHE=~/.cache/netsuite-schema

for account in twistedx; do
  for env in production sandbox sandbox2; do
    for resource in tables columns fkeys; do
      f="$CACHE/$account/$env/$resource.json"
      [ -f "$f" ] && curl -s -o /dev/null -w "$account/$env/$resource: %{http_code}\n" \
        -X POST "$BASE/api/common/schema/$account/$env/$resource" \
        -H "Content-Type: application/json" \
        -H "X-Schema-Admin-Token: $TOKEN" \
        --data-binary "@$f"
    done
  done
done
# → twistedx/production/tables: 200  (×9)
```

Then populate custom records and custom fields via SuiteQL for each environment:

```bash
cd plugins/netsuite-skills/skills/netsuite-suiteql
SCHEMA_ADMIN_TOKEN=$TOKEN NETSUITE_GATEWAY_URL=$BASE \
  python3 scripts/schema_lookup.py refresh-custom --account twistedx --env production --upload
# repeat for sandbox, sandbox2
```

### Step 4 — Verify zero-setup sync

```bash
rm -rf ~/.cache/netsuite-schema/twistedx/sandbox2/
NETSUITE_GATEWAY_URL=$BASE python3 scripts/schema_lookup.py sync --account twistedx --env sandbox2
# → tables 2155 records, columns 31786, fkeys 19097, custom_records 630, custom_fields 4927
```

## Why This Works

**Deployment skip:** Railway's GitHub App scans every `railway.toml` in a repo and attempts to build a service for each one. `schema-cron/railway.toml` told Railway to build a service with root=`schema-cron/`, but the Dockerfile's `COPY odbc-driver/` references gitignored files. Railway's pre-build validation failed and cascaded the failure to the gateway deployment, marking it SKIPPED. Removing the file eliminates the phantom service configuration. `railway up --detach` deploys directly from the local filesystem, bypassing the GitHub App entirely.

**Redis provisioning:** `railway deploy --template redis` creates a managed Redis instance as a proper Railway service with its own `REDIS_URL` variable. The `${{Redis.REDIS_URL}}` reference syntax injects the internal private network URL at runtime. Without this reference, `REDIS_ENABLED=true` is inert — the gateway has no URL to connect to and falls back to in-memory cache.

*(session history)* Railway env vars for this gateway have previously diverged from what the deployed code actually reads — `API_KEY_REQUIRED=true` was set in Railway before the code even read that var. The same pattern applied here: `REDIS_ENABLED=true` implied intent without wiring.

## Prevention

**Don't commit `railway.toml` for services that can't build yet.** If a planned service depends on gitignored files (like ODBC drivers), keep its `railway.toml` out of the repo until the Dockerfile and all dependencies are in place. A `railway.toml.example` or a doc reference is sufficient.

**Provision Railway add-ons before merging dependent code.** Before merging code that requires Redis (or any Railway-managed service), create the service in Railway and set the linked variable (`${{ServiceName.VAR}}`). This ensures the env var is present on first deploy.

**Use `railway variable --set "VAR=\${{Service.VAR}}"` not hardcoded URLs.** Railway variable references automatically track service reprovisioning. Hardcoded connection strings go stale.

**When Railway shows SKIPPED, check for phantom services.** `railway deployment list` SKIPPED status (not FAILED) indicates a build cascade rather than a gateway-specific error. Check all `railway.toml` files in the repo and verify Railway isn't trying to build a service you didn't intend to deploy yet.

**`railway add --database <type>` hangs in non-interactive mode.** Use `railway deploy --template <type>` instead for non-interactive provisioning.

## Related Issues

- PR #23 (NetSuiteApiGateway): feat(schema) — gateway-hosted schema cache + Railway cron service
- Schema-cron ODBC driver distribution: needs resolution before restoring `schema-cron/railway.toml` and deploying the weekly refresh service
