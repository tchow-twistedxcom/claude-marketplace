---
name: netsuite-script-deployments
description: List and analyze NetSuite script deployments - find active/inactive scripts by record type or script type. Use this skill when you need to check which scripts are deployed for a record type, verify if a script is active, or find all deployments of a specific type. Triggers include "list deployments", "find active scripts", "check script deployment", or any script deployment queries.
---

# NetSuite Script Deployments Skill

## Overview

Query and analyze NetSuite script deployments via the NetSuite API Gateway. This skill helps identify active vs inactive script deployments before making modifications - critical for avoiding the mistake of editing inactive scripts.

**Authentication is handled automatically** by the NetSuite API Gateway using OAuth 1.0a.

**Use this skill when:**
- Checking which scripts are deployed for a specific record type
- Verifying if a script deployment is active before editing
- Finding all deployments of a specific script type (User Event, RESTlet, etc.)
- Auditing script deployments across the system

## Prerequisites

**NetSuite API Gateway** must be running:
```bash
cd ~/NetSuiteApiGateway
docker compose up -d
```

Verify gateway is running:
```bash
curl http://localhost:3001/health
```

## List Deployments

### By Record Type

```bash
# List all scripts for inventory items
python3 scripts/list_deployments.py --record-type inventoryitem --env prod

# List only ACTIVE scripts for inventory items
python3 scripts/list_deployments.py --record-type inventoryitem --active-only --env prod

# List scripts for sales orders
python3 scripts/list_deployments.py --record-type salesorder --env prod
```

### By Script Type

```bash
# List all User Event deployments
python3 scripts/list_deployments.py --script-type userevent --env prod

# List all RESTlet deployments
python3 scripts/list_deployments.py --script-type restlet --env prod

# List all Scheduled Script deployments
python3 scripts/list_deployments.py --script-type scheduled --env prod
```

### By Script ID Pattern

```bash
# Find all TWX scripts
python3 scripts/list_deployments.py --script-id "customscript_twx%" --env prod

# Find specific script deployments
python3 scripts/list_deployments.py --script-id "customscript_inventory_part_ue" --env prod
```

### Combined Filters

```bash
# Active User Event scripts for inventory items
python3 scripts/list_deployments.py --record-type inventoryitem --script-type ue --active-only --env prod

# All RESTlets for TWX
python3 scripts/list_deployments.py --script-type rl --script-id "customscript_twx%" --env prod
```

## Options

| Option | Description | Required |
|--------|-------------|----------|
| `--record-type` | Filter by record type (e.g., inventoryitem) | No |
| `--script-type` | Filter by script type (see aliases below) | No |
| `--script-id` | Filter by script ID (supports % wildcards) | No |
| `--active-only` | Only show deployed (active) scripts | No |
| `--account` | Account (default: twistedx) | No |
| `--env` | Environment: prod, sb1, sb2 (default: sb2) | No |
| `--limit` | Max results (default: 100) | No |
| `--format` | Output: table, json (default: table) | No |

## Script Type Aliases

Use short aliases for convenience:

| Alias | Full Name | Script Type |
|-------|-----------|-------------|
| `ue` | `userevent` | User Event |
| `cl` | `client` | Client Script |
| `sl` | `suitelet` | Suitelet |
| `rl` | `restlet` | RESTlet |
| `ss` | `scheduled` | Scheduled Script |
| `mr` | `mapreduce` | Map/Reduce |
| `mu` | `massupdate` | Mass Update |
| `wfa` | `workflow` | Workflow Action |

## Output Fields

- `deployment_id` - Script deployment ID (e.g., customdeploy_twx_ue_inventory)
- `script_id` - Script ID (e.g., customscript_twx_inventory_ue)
- `script_type` - Type of script (USEREVENT, RESTLET, etc.)
- `record_type` - Record type the script is deployed to
- `deployed` - Yes/No - whether the deployment is active
- `status` - Deployment status

## Quick Reference

```bash
# List all deployments for a record type
python3 scripts/list_deployments.py --record-type inventoryitem --env prod

# List only active deployments
python3 scripts/list_deployments.py --record-type inventoryitem --active-only --env prod

# List all RESTlets
python3 scripts/list_deployments.py --script-type rl --env prod

# Find scripts by ID pattern
python3 scripts/list_deployments.py --script-id "customscript_twx%" --env prod

# Output as JSON
python3 scripts/list_deployments.py --record-type salesorder --format json --env prod
```

## Common Use Cases

### Before Modifying a Script

**Critical:** Always check if a script is active before editing!

```bash
# Check which inventory item UE scripts are active
python3 scripts/list_deployments.py --record-type inventoryitem --script-type ue --active-only --env prod

# Output might show:
# customdeploy_inventorypart_ue  customscript_inventorypart_ue  USEREVENT  inventoryitem  Yes  Released
# ^^^^^ This is the ACTIVE one to modify

# vs inactive ones:
# customdeploy_twx_ue2_prices    customscript_twx_ue2_prices    USEREVENT  inventoryitem  No   Testing
# ^^^^^ This is INACTIVE - do NOT modify
```

### Audit All RESTlets

```bash
# List all RESTlet deployments
python3 scripts/list_deployments.py --script-type restlet --env prod

# Find active RESTlets only
python3 scripts/list_deployments.py --script-type restlet --active-only --env prod
```

### Find All Scripts for a Record Type

```bash
# See all scripts that run on sales orders
python3 scripts/list_deployments.py --record-type salesorder --env prod

# Filter to just User Events and Client Scripts
python3 scripts/list_deployments.py --record-type salesorder --script-type ue --env prod
python3 scripts/list_deployments.py --record-type salesorder --script-type cl --env prod
```

### Compare Sandbox vs Production

```bash
# List active inventory scripts in production
python3 scripts/list_deployments.py --record-type inventoryitem --active-only --env prod

# Compare to sandbox
python3 scripts/list_deployments.py --record-type inventoryitem --active-only --env sb2
```

## Error Handling

### Common Errors

**No deployments found:**
```
Found 0 deployment(s)
No deployments found.
```
→ Check the record type spelling or try without filters

**Gateway not running:**
```
ERROR: Gateway connection error: Connection refused
```
→ Start the gateway: `cd ~/NetSuiteApiGateway && docker compose up -d`

## Why This Matters

Editing the wrong script is a common mistake that wastes time. For example:

- `TWX_UE2_beforeSubmit_prices.js` - **INACTIVE** (isdeployed = F)
- `inventoryPartUserEvent.js` - **ACTIVE** (isdeployed = T)

If you modify the inactive script, your changes will have no effect! Always use `--active-only` to verify which script is actually running.

## Resources

### scripts/list_deployments.py
List NetSuite script deployments:
- Filter by record type, script type, or active status
- Script type aliases (ue, rl, sl, etc.)
- Identifies active vs inactive deployments
- Essential for verifying correct script targets
