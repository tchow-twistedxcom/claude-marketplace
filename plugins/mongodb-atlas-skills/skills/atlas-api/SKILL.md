---
name: atlas-api
description: MongoDB Atlas API operations for monitoring alerts, clusters, and performance metrics. Use when user mentions atlas alerts, mongodb monitoring, cluster status, atlas metrics, database alerts, check atlas, mongodb performance, slow queries, atlas api, or needs to query MongoDB Atlas Admin API.
triggers:
  keywords:
    - mongodb atlas
    - atlas alerts
    - cluster status
    - atlas metrics
    - database alerts
    - mongodb monitoring
    - atlas api
    - check atlas
    - mongodb performance
    - slow queries
    - atlas cluster
    - mongodb alerts
  contexts:
    - Checking database health or performance
    - Investigating MongoDB alerts or issues
    - Monitoring cluster state
    - Querying Atlas Admin API
---

# MongoDB Atlas API Skill

## Overview

Execute MongoDB Atlas Admin API v2 operations to monitor alerts, check cluster health, and analyze performance metrics. Uses HTTP Digest Authentication with Atlas API keys.

## Prerequisites

**Environment Variables** (required):
```bash
export ATLAS_PUBLIC_KEY="your_public_key"
export ATLAS_PRIVATE_KEY="your_private_key"
export ATLAS_PROJECT_ID="your_project_id"  # Optional - can use --project flag
```

**IP Whitelist**: Your IP must be in the Atlas API access list.

## Quick Start

```bash
# List recent alerts (last 7 days by default)
python3 scripts/atlas_api.py alerts list

# List all alerts (no date filter)
python3 scripts/atlas_api.py alerts list --all

# List alerts from last 30 days
python3 scripts/atlas_api.py alerts list --since 30

# List clusters
python3 scripts/atlas_api.py clusters list

# Get specific cluster status
python3 scripts/atlas_api.py clusters status MyCluster

# Get process metrics
python3 scripts/atlas_api.py metrics --cluster MyCluster
```

## Commands

### Alerts

```bash
# List recent alerts (last 7 days by default, includes summary)
python3 scripts/atlas_api.py alerts list [--project PROJECT_ID]

# List all alerts (no date filter)
python3 scripts/atlas_api.py alerts list --all

# List alerts from last N days
python3 scripts/atlas_api.py alerts list --since 30

# Filter by status
python3 scripts/atlas_api.py alerts list --status open
python3 scripts/atlas_api.py alerts list --status closed

# Limit number of alerts fetched
python3 scripts/atlas_api.py alerts list --limit 50

# Combine options
python3 scripts/atlas_api.py alerts list --since 14 --status open --limit 20

# Get specific alert details
python3 scripts/atlas_api.py alerts get ALERT_ID [--project PROJECT_ID]

# Acknowledge an alert (with optional comment)
python3 scripts/atlas_api.py alerts ack ALERT_ID [--comment "Investigating..."] [--project PROJECT_ID]
```

**Alert List Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--since N` | 7 | Show alerts from last N days |
| `--all` | false | Show all alerts (ignore date filter) |
| `--limit N` | 100 | Maximum alerts to fetch from API |
| `--status` | all | Filter by status: open, closed |
| `--format` | table | Output format: table, json |

**Summary Output:**
When listing alerts, a summary is displayed showing:
- Total alert count
- Open vs Closed counts
- Date range of alerts
- Top 5 alert types by frequency

### Clusters

```bash
# List all clusters in project
python3 scripts/atlas_api.py clusters list [--project PROJECT_ID]

# Get cluster details and status
python3 scripts/atlas_api.py clusters status CLUSTER_NAME [--project PROJECT_ID]
```

### Metrics

```bash
# Get cluster metrics (CPU, memory, connections)
python3 scripts/atlas_api.py metrics --cluster CLUSTER_NAME [--project PROJECT_ID] [--period PT1H]

# Available metrics: CPU, memory, connections, opcounters, disk
```

### Projects

```bash
# List all accessible projects
python3 scripts/atlas_api.py projects list
```

## Common Tasks

### Check for Recent Alerts
```bash
# Default: last 7 days with summary
python3 scripts/atlas_api.py alerts list

# Open alerts only (recent)
python3 scripts/atlas_api.py alerts list --status open

# If no recent alerts, check longer period
python3 scripts/atlas_api.py alerts list --since 30
```

### Review All Historical Alerts
```bash
# See all alerts with summary statistics
python3 scripts/atlas_api.py alerts list --all
```

### Investigate Slow Performance
```bash
# Check cluster status first
python3 scripts/atlas_api.py clusters status MyCluster

# Then check metrics
python3 scripts/atlas_api.py metrics --cluster MyCluster --period PT24H
```

### Acknowledge Alert After Investigation
```bash
python3 scripts/atlas_api.py alerts ack 507f1f77bcf86cd799439011 --comment "Resolved by scaling cluster"
```

## Output Formats

```bash
# Default: formatted table output
python3 scripts/atlas_api.py alerts list

# JSON output for scripting
python3 scripts/atlas_api.py alerts list --format json

# Quiet mode (just data, no headers)
python3 scripts/atlas_api.py alerts list --quiet
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Invalid credentials | Check API key |
| 403 Forbidden | IP not whitelisted | Add IP to Atlas access list |
| 404 Not Found | Invalid project/cluster | Verify IDs exist |

## API Reference

| Command | Endpoint | Method |
|---------|----------|--------|
| alerts list | `/groups/{groupId}/alerts` | GET |
| alerts get | `/groups/{groupId}/alerts/{alertId}` | GET |
| alerts ack | `/groups/{groupId}/alerts/{alertId}` | PATCH |
| clusters list | `/groups/{groupId}/clusters` | GET |
| clusters status | `/groups/{groupId}/clusters/{name}` | GET |
| metrics | `/groups/{groupId}/processes/{processId}/measurements` | GET |
| projects list | `/groups` | GET |

## Resources

- [Atlas Admin API v2 Documentation](https://www.mongodb.com/docs/atlas/api/atlas-admin-api-ref/)
- [API Authentication](https://www.mongodb.com/docs/atlas/api/api-authentication/)
- [Alert Types](https://www.mongodb.com/docs/atlas/reference/alert-types/)
