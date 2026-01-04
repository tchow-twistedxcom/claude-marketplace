---
name: status
description: "Check n8n instance health and display workflow summary"
---

# /n8n:status - n8n Health Check

Quick health check showing n8n connectivity, active workflows, and recent execution status.

## Usage

```
/n8n:status [--verbose] [--account <id>]
```

## Flags

| Flag | Description |
|------|-------------|
| `--verbose` | Show detailed metrics, API response times, version info |
| `--account <id>` | Use specific account (default: from config) |

## Workflow

1. **Health Check**
   - Call `mcp__n8n__n8n_health_check`
   - Report API connectivity and n8n version

2. **Workflow Summary**
   - Call `mcp__n8n__n8n_list_workflows`
   - Count active vs inactive workflows

3. **Recent Failures** (if any)
   - Call `mcp__n8n__n8n_list_executions` with status: "error"
   - Show last 5 failed executions

4. **Running Executions**
   - Check for currently running executions
   - Report count and duration

## Output Format

### Standard Output
```
n8n Status Report [local]
================================
API Connection: Healthy (http://localhost:5679)
Workflows: 12 active / 5 inactive
Recent Failures: 2 in last 24h
   Customer Sync - 3h ago (timeout)
   Slack Notifier - 8h ago (auth error)
Running: 1 execution in progress
```

### Verbose Output (--verbose)
```
n8n Status Report (Detailed)
================================
API:
  URL: http://localhost:5679/api/v1
  Status: Connected
  Latency: 45ms
  Version: 2.19.6
  Latest Available: 2.31.5
  Update Available: Yes

Workflows:
  Total: 17
  Active: 12
  Inactive: 5

Node Database:
  Total Nodes: 537
  AI-Capable: 263
  Triggers: 104
  Documentation Coverage: 88%

Recent Executions (last 24h):
  Success: 145
  Failed: 2
  Running: 1

Failed Executions:
  1. Customer Sync (abc123)
     - Time: 3 hours ago
     - Error: ETIMEDOUT after 30000ms
     - Node: HTTP Request
  2. Slack Notifier (def456)
     - Time: 8 hours ago
     - Error: invalid_auth
     - Node: Slack
```

## MCP Tools Used

| Tool | Purpose |
|------|---------|
| `mcp__n8n__n8n_health_check` | API connectivity and version |
| `mcp__n8n__n8n_list_workflows` | Workflow inventory |
| `mcp__n8n__n8n_list_executions` | Execution history and failures |
| `mcp__n8n__get_database_statistics` | Node inventory (verbose mode) |

## Examples

### Quick Check
```
/n8n:status

# Fast overview of n8n health
```

### Detailed Status
```
/n8n:status --verbose

# Full metrics including node stats, version info
```

### Scripting
Use the status check to verify n8n before running workflows:
```
/n8n:status
/n8n:run my-workflow
```

## Troubleshooting

### "API Connection: Failed"

Run setup to diagnose:
```
/n8n:setup --diagnose
```

### "Recent Failures" showing issues

Debug the failed workflow:
```
/n8n:validate <workflow-id>
```

Or get execution details:
```
Use mcp__n8n__n8n_get_execution with the execution ID
```

## Related Commands

- `/n8n:setup` - Configure connection
- `/n8n:list` - Full workflow listing
- `/n8n:validate` - Check specific workflow
