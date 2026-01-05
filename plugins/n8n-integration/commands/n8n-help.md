---
name: n8n-help
description: "Show n8n plugin commands, skills, and documentation"
---

# /n8n:help - n8n Plugin Documentation

Display help for n8n plugin commands, skills, and common workflows.

## Usage

```
/n8n:help [topic]
```

## Topics

| Topic | Description |
|-------|-------------|
| (none) | Show all available commands |
| `commands` | Detailed command reference |
| `skills` | Available skills and when to use them |
| `workflows` | Common workflow patterns |
| `nodes` | Node discovery and documentation |
| `expressions` | n8n expression syntax guide |
| `ai` | AI agent workflow patterns |
| `troubleshooting` | Common issues and solutions |
| `api` | API limitations and workarounds |

## Command Reference

### Quick Commands

| Command | Description |
|---------|-------------|
| `/n8n:status` | Health check and workflow summary |
| `/n8n:list [type]` | List workflows or executions |
| `/n8n:find <query>` | Search nodes, templates, or docs |
| `/n8n:run <id>` | Trigger workflow via webhook |
| `/n8n:validate <id>` | Validate workflow configuration |

### Utility Commands

| Command | Description |
|---------|-------------|
| `/n8n:setup` | Configure n8n connection |
| `/n8n:help [topic]` | Show documentation |

## Skills Reference

### n8n-workflow-builder
**Trigger**: "create workflow", "build automation", "n8n workflow"

Build workflows from scratch or templates with guided node selection, validation, and creation.

### n8n-workflow-manager
**Trigger**: "list workflows", "update workflow", "workflow status"

Manage existing workflows: list, filter, update, delete, organize with tags.

### n8n-troubleshooter
**Trigger**: "workflow failed", "debug execution", "n8n error"

Diagnose failures with execution analysis, validation, and fix recommendations.

### n8n-integration-patterns
**Trigger**: "n8n best practices", "workflow pattern", "error handling"

Knowledge base for workflow patterns, best practices, and architecture guidance.

## Quick Start

### 1. Verify Connection
```
/n8n:setup --test
```

### 2. Check Instance Status
```
/n8n:status
```

### 3. List Your Workflows
```
/n8n:list
```

### 4. Search for Nodes
```
/n8n:find nodes slack
```

### 5. Validate a Workflow
```
/n8n:validate <workflow-id>
```

## Common Flags

| Flag | Available On | Description |
|------|--------------|-------------|
| `--account <id>` | all commands | Use specific n8n account |
| `--verbose` | status, list | Show detailed output |
| `--active` | list | Filter to active only |
| `--status <s>` | list | Filter by execution status |
| `--fix` | validate | Auto-fix common issues |
| `--examples` | find | Include usage examples |

## CLI Tools Reference

The n8n integration provides Python CLI scripts:

**Account Management** (`scripts/n8n_config.py`)
- `--list-accounts` - List all configured accounts
- `--add <id>` - Add new account
- `--remove <id>` - Remove account
- `--set-default <id>` - Set default account

**API Operations** (`scripts/n8n_api.py`)
- `workflows list` - List workflows
- `workflows get <id>` - Get workflow details
- `workflows create` - Create workflow from JSON
- `workflows update <id>` - Update workflow
- `executions list` - List executions
- `executions get <id>` - Get execution details
- `health` - Health check
- `webhook <url>` - Trigger webhook

**Authentication** (`scripts/n8n_auth.py`)
- `--test` - Test connection
- `--info` - Show config info

### Example Usage

```bash
python3 scripts/n8n_api.py workflows list
python3 scripts/n8n_api.py executions list --status error
python3 scripts/n8n_auth.py --test --account production
```

## API Limitations

| Operation | Status | Workaround |
|-----------|--------|------------|
| Direct execution | Webhook only | Add Webhook node to workflows |
| Activate/deactivate | Not via API | Manual UI toggle required |
| Credential management | Not via API | Configure in n8n UI |
| Stop execution | Not supported | Use timeout configuration |

## Getting More Help

### Detailed Topic Help
```
/n8n:help expressions    # Expression syntax guide
/n8n:help ai             # AI workflow patterns
/n8n:help troubleshooting # Common issues
```

### n8n CLI Documentation
```bash
# View CLI help
python3 scripts/n8n_api.py --help
python3 scripts/n8n_config.py --help
python3 scripts/n8n_auth.py --help
```

### Official n8n Docs
- https://docs.n8n.io/
- https://docs.n8n.io/api/

## Related Files

- `AUTHENTICATION.md` - API setup guide
- `docs/API_LIMITATIONS.md` - Detailed limitation workarounds
- `docs/WORKFLOW_EXAMPLES.md` - Example workflow recipes
