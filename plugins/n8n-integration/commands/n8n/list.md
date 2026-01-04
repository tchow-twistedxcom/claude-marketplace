---
name: list
description: "List n8n workflows or executions with filtering options"
---

# /n8n:list - List Workflows and Executions

Quick listing of workflows and executions with filtering and pagination.

## Usage

```
/n8n:list [type] [options]
```

## Types

| Type | Description |
|------|-------------|
| `workflows` | List all workflows (default) |
| `executions` | List execution history |

## Flags

| Flag | Type | Description |
|------|------|-------------|
| `--account <id>` | both | Use specific n8n account (default: from config) |
| `--active` | workflows | Show only active workflows |
| `--inactive` | workflows | Show only inactive workflows |
| `--tags <tags>` | workflows | Filter by comma-separated tags |
| `--status <s>` | executions | Filter by status: success, error, waiting |
| `--workflow <id>` | executions | Filter executions by workflow ID |
| `--limit <n>` | both | Max results to return (default: 20) |
| `--verbose` | both | Show additional details |

## Workflow

### List Workflows (Default)

1. **Fetch Workflows**
   - Call `python3 scripts/n8n_api.py workflows list`
   - Apply filters (--active, --tags)

2. **Format Output**
   - Show ID, name, active status
   - Include tags if present
   - Show node count

3. **Pagination**
   - Use --limit flag to control result count

### List Executions

1. **Fetch Executions**
   - Call `python3 scripts/n8n_api.py executions list`
   - Apply filters (--status, --workflow)

2. **Format Output**
   - Show execution ID, workflow name, status
   - Include timestamp and duration
   - Show error summary for failed executions

## CLI Tools Used

| Script | Purpose |
|--------|---------|
| `scripts/n8n_api.py workflows list` | List workflows with filtering |
| `scripts/n8n_api.py executions list` | List executions with filtering |

### Example CLI Commands

```bash
# List all workflows
python3 scripts/n8n_api.py workflows list

# List active workflows only
python3 scripts/n8n_api.py workflows list --active true

# List failed executions
python3 scripts/n8n_api.py executions list --status error

# List executions for specific workflow
python3 scripts/n8n_api.py executions list --workflow abc123
```

## Output Format

### Workflows (Standard)
```
n8n Workflows (12 total)
================================
ID        Name                    Active   Tags
abc123    Customer Sync           ✅       [sync, production]
def456    Slack Notifier          ✅       [notifications]
ghi789    Data Cleanup            ❌       [maintenance]
jkl012    Email Parser            ✅       [email]
...

Showing 12 of 12 workflows
```

### Workflows (Verbose)
```
n8n Workflows (Detailed)
================================
abc123 - Customer Sync
  Status: Active ✅
  Tags: sync, production
  Created: 2024-01-15 09:30
  Updated: 2024-03-20 14:45
  Nodes: 8

def456 - Slack Notifier
  Status: Active ✅
  Tags: notifications
  Created: 2024-02-01 11:00
  Updated: 2024-03-18 16:20
  Nodes: 5
...
```

### Executions (Standard)
```
n8n Executions (Last 20)
================================
ID        Workflow           Status    Time
exec001   Customer Sync      ✅        2h ago
exec002   Slack Notifier     ✅        3h ago
exec003   Data Cleanup       ❌        5h ago (timeout)
exec004   Customer Sync      ✅        6h ago
...

Showing 20 executions
```

### Executions (Verbose)
```
n8n Executions (Detailed)
================================
exec001 - Customer Sync
  Status: Success ✅
  Started: 2024-03-21 10:30:15
  Duration: 2.3s
  Mode: webhook

exec003 - Data Cleanup
  Status: Failed ❌
  Started: 2024-03-21 07:15:00
  Duration: 30.0s (timeout)
  Error: ETIMEDOUT - Connection timed out
  Failed Node: HTTP Request
...
```

## MCP Tools Used

| Tool | Purpose |
|------|---------|
| `mcp__n8n__n8n_list_workflows` | Fetch workflow list with filters |
| `mcp__n8n__n8n_list_executions` | Fetch execution history |
| `mcp__n8n__n8n_get_workflow_minimal` | Get workflow details (verbose) |
| `mcp__n8n__n8n_get_execution` | Get execution details (verbose) |

## Examples

### List All Workflows
```
/n8n:list

# or explicitly
/n8n:list workflows
```

### List Active Workflows Only
```
/n8n:list workflows --active
```

### List Workflows by Tag
```
/n8n:list workflows --tags production,sync
```

### List Recent Executions
```
/n8n:list executions --limit 50
```

### List Failed Executions
```
/n8n:list executions --status error
```

### List Executions for Specific Workflow
```
/n8n:list executions --workflow abc123
```

### Detailed Workflow List
```
/n8n:list workflows --verbose
```

### List Workflows on Specific Account
```
/n8n:list workflows --account production
```

## Pagination

For large result sets, the command handles pagination automatically:

```
/n8n:list workflows --limit 100

# Output includes pagination info:
Showing 100 of 250 workflows
Use --cursor <cursor> for next page
```

## Related Commands

- `/n8n:status` - Quick health overview
- `/n8n:find` - Search for specific nodes/templates
- `/n8n:validate` - Validate a specific workflow
