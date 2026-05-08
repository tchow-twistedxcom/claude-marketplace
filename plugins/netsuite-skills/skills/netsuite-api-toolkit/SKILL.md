---
name: netsuite-api-toolkit
description: Debug and validate API gateway routing, TypeScript type contracts, and environment configuration. Use this skill when debugging API issues, type mismatches, environment routing problems, or when you need to inspect request/response data. Triggers include "API issue", "type mismatch", "wrong environment", "gateway debug", "contract validation", "inspect request", or "generate types".
---

# NetSuite API Toolkit

## Overview

A unified toolkit for debugging and validating the NetSuite API Gateway and frontend-backend contracts. This skill helps prevent and diagnose issues like:
- **Environment routing problems** - Requests going to wrong NetSuite environment
- **Type mismatches** - TypeScript interfaces not matching actual API responses
- **Configuration errors** - Missing or invalid OAuth/app configurations
- **Request tracing** - Understanding what's being sent/received

## Sub-Commands

| Command | Script | Purpose |
|---------|--------|---------|
| `test-environments` | `test_environments.py` | Test all 3 environments in parallel |
| `validate-config` | `validate_config.py` | Validate gateway config files |
| `inspect-requests` | `inspect_request.py` | Log and trace API requests |
| `validate-types` | `validate_types.py` | Compare TS interfaces to API responses |
| `generate-types` | `generate_types.py` | Auto-generate TS types from API |

## Gateway URL & Authentication

**Production gateway (always available):** `https://nsapi.twistedx.tech`
**Local dev gateway:** `http://localhost:3001` (requires Docker — see below)

All requests to the production gateway require an API key sent as `X-API-Key`:

```bash
curl -X POST "https://nsapi.twistedx.tech/api/suiteapi" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $NETSUITE_API_KEY" \
  -d '{"netsuiteEnvironment":"sandbox2","action":"taskCreate","procedure":"taskCreate", ...}'
```

The Python skill scripts read the key automatically from `NETSUITE_API_KEY` env var. Local dev without an API key falls back to `Origin` header instead.

## Triggering Scheduled Scripts via `taskCreate`

Use the `suiteapi` app's `taskCreate` procedure to trigger a scheduled script on demand.

**⚠️ Common mistakes that each produce a different error:**

| Mistake | Error |
|---------|-------|
| Wrong host (`gateway.twistedx.io`) | `curl: (6) Could not resolve host` |
| Wrong app ID (`netsuite`, `twx`) | `{"error":"App not found"}` |
| Missing `action` field | `{"error":"Action parameter is required"}` |
| `action` present but no `procedure` | `{"error":"MISSING_PROCEDURE"}` |
| `taskType`/`scriptId` nested inside `"params":{}` | `{"error":"taskType and scriptId are required"}` |

**Correct format — ALL of these fields required at the top level:**

```bash
curl -X POST "https://nsapi.twistedx.tech/api/suiteapi" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $NETSUITE_API_KEY" \
  -d '{
    "netsuiteEnvironment": "sandbox2",
    "action": "taskCreate",
    "procedure": "taskCreate",
    "taskType": "SCHEDULED_SCRIPT",
    "scriptId": "customscript_pri_containertouch_sc",
    "deploymentId": "customdeploy_pri_containertouch_sc"
  }'
```

Key rules:
- `action` AND `procedure` are both required (they are the same value: `"taskCreate"`)
- `taskType`, `scriptId`, `deploymentId` go at the **top level**, NOT inside a `"params"` key
- `netsuiteEnvironment` values: `"sandbox"` (SB1), `"sandbox2"` (SB2), `"production"`

**Look up deployment IDs before triggering:**
```bash
python3 ~/.../netsuite-script-deployments/scripts/list_deployments.py \
  --script customscript_pri_containertouch_sc --env sb2
```

## Prerequisites

**Production gateway** is always available — no local setup needed for most tasks.

**Local dev gateway** (optional, for offline development):
```bash
cd ~/NetSuiteApiGateway
docker compose up -d
# Verify:
curl http://localhost:3001/health
```

## Quick Start

### Test Environment Routing
```bash
# Test all environments
python3 scripts/test_environments.py

# Test specific environment
python3 scripts/test_environments.py --env sandbox2

# Test specific app
python3 scripts/test_environments.py --app homepage
```

### Validate Configuration
```bash
# Validate all configs
python3 scripts/validate_config.py

# Validate specific config
python3 scripts/validate_config.py --config oauth2.json
```

### Inspect API Requests
```bash
# Capture a request/response
python3 scripts/inspect_request.py --app homepage --action getOperationsStatus --env sandbox2

# Generate curl command
python3 scripts/inspect_request.py --app homepage --action getConfig --env prod --curl
```

### Validate TypeScript Types
```bash
# Compare types to API response
python3 scripts/validate_types.py --types-file src/types/operations.ts --app homepage --action getOperationsStatus
```

### Generate TypeScript Types
```bash
# Generate types from API response
python3 scripts/generate_types.py --app homepage --action getOperationsStatus --output src/types/operations.generated.ts
```

## Environment Routing

The gateway selects NetSuite environment using this priority:

| Priority | Source | Example |
|----------|--------|---------|
| 1 (Highest) | Request Body | `{"netsuiteEnvironment": "sandbox2"}` |
| 2 | Query Parameter | `?netsuiteEnvironment=sandbox2` |
| 3 | HTTP Header | `X-NetSuite-Environment: sandbox2` |
| 4 (Lowest) | Default | `NETSUITE_ENVIRONMENT` env var |

**Valid environments:** `production`, `sandbox`, `sandbox2`

## Common Issues

### Wrong Environment
**Symptom:** API returns data from production when sandbox2 expected
**Diagnosis:**
```bash
python3 scripts/test_environments.py --app homepage
```
**Fix:** Ensure frontend sends `X-NetSuite-Environment` header or body parameter

### Type Mismatch
**Symptom:** `Cannot read properties of undefined` errors in frontend
**Diagnosis:**
```bash
python3 scripts/validate_types.py --types-file src/types/operations.ts --app homepage --action getOperationsStatus
```
**Fix:** Update TypeScript types to match actual API response structure

### Configuration Error
**Symptom:** 401 or 500 errors for specific environments
**Diagnosis:**
```bash
python3 scripts/validate_config.py
```
**Fix:** Ensure OAuth credentials exist for all environments in `config/oauth.json` or `config/oauth2.json`

## Templates

### React Error Boundary
Copy `templates/error_boundary.tsx` to catch runtime errors gracefully:
```tsx
<ErrorBoundary fallbackTitle="Component Name">
  <YourComponent />
</ErrorBoundary>
```

### Type Guard
Copy `templates/type_guard.ts` pattern for runtime type validation:
```typescript
function isOperationsStatus(obj: unknown): obj is OperationsStatus {
  return obj !== null && typeof obj === 'object' && 'autoFulfillment' in obj;
}
```

## Documentation

- `docs/environment-routing.md` - How environment selection works
- `docs/api-contracts.md` - Type/contract patterns and best practices
