---
name: find
description: "Search n8n nodes, templates, or documentation by keyword"
---

# /n8n:find - Search n8n Resources

Search for nodes, templates, or documentation by keyword.

## Usage

```
/n8n:find <type> <query> [options]
```

## Types

| Type | Description |
|------|-------------|
| `nodes` | Search available n8n nodes |
| `templates` | Search workflow templates |
| `docs` | Search node documentation |
| `ai` | List AI-capable nodes |

## Flags

| Flag | Description |
|------|-------------|
| `--account <id>` | Use specific n8n account (default: from config) |
| `--examples` | Include usage examples (nodes/templates) |
| `--limit <n>` | Max results to return (default: 10) |
| `--category <c>` | Filter nodes by category: trigger, transform, output, input, AI |
| `--task <t>` | Filter templates by task type |

## Workflow

### Search Nodes

1. **Execute Search**
   - Call `mcp__n8n__search_nodes` with query
   - Optionally include examples with `includeExamples: true`

2. **Format Results**
   - Show node name, package, description
   - Include example configurations if requested

### Search Templates

1. **Execute Search**
   - Call `mcp__n8n__search_templates` with query
   - Or use `mcp__n8n__get_templates_for_task` for task-based search

2. **Format Results**
   - Show template ID, name, description
   - Include node count and popularity

### Search Documentation

1. **Execute Search**
   - Call `mcp__n8n__get_node_documentation` for specific node
   - Or `mcp__n8n__search_node_properties` for property search

2. **Format Results**
   - Show documentation content
   - Include authentication requirements
   - List available operations

### List AI Nodes

1. **Execute List**
   - Call `mcp__n8n__list_ai_tools`

2. **Format Results**
   - Show AI-capable nodes
   - Include usage context

## Output Format

### Node Search Results
```
n8n Node Search: "slack"
================================
Found 5 matching nodes:

1. Slack (n8n-nodes-base.slack)
   Send messages, manage channels, users
   Categories: Communication, Output

2. Slack Trigger (n8n-nodes-base.slackTrigger)
   Trigger on Slack events
   Categories: Communication, Trigger

3. Slack Credential Test
   Test Slack API credentials
   Categories: Utility
...
```

### Node Search with Examples
```
n8n Node Search: "http" --examples
================================
1. HTTP Request (n8n-nodes-base.httpRequest)
   Make HTTP requests to any URL

   Example Configuration:
   {
     "method": "POST",
     "url": "https://api.example.com/data",
     "authentication": "genericCredentialType",
     "sendBody": true,
     "bodyParameters": {
       "parameters": [{"name": "key", "value": "value"}]
     }
   }
...
```

### Template Search Results
```
n8n Template Search: "slack notification"
================================
Found 15 matching templates:

1. Slack Alert on Error (ID: 1234)
   Views: 5,432 | Nodes: 4
   Send Slack alerts when workflows fail

2. Daily Slack Report (ID: 2345)
   Views: 3,211 | Nodes: 6
   Generate and send daily reports to Slack

3. GitHub PR to Slack (ID: 3456)
   Views: 2,890 | Nodes: 5
   Notify Slack channel on new PRs
...
```

### AI Nodes List
```
n8n AI-Capable Nodes
================================
263 nodes can be used as AI tools

Popular AI Tool Nodes:
1. HTTP Request - Make API calls for AI agents
2. Code - Execute JavaScript/Python
3. Google Sheets - Read/write spreadsheets
4. Slack - Send messages
5. Database nodes - Query data
...

Note: ANY node can be AI tool! Connect to AI Agent's tool port.
```

## MCP Tools Used

| Tool | Purpose |
|------|---------|
| `mcp__n8n__search_nodes` | Search nodes by keyword |
| `mcp__n8n__list_nodes` | List nodes by category |
| `mcp__n8n__get_node_essentials` | Get node summary with examples |
| `mcp__n8n__get_node_documentation` | Get full node documentation |
| `mcp__n8n__search_templates` | Search templates by keyword |
| `mcp__n8n__get_templates_for_task` | Get templates by task type |
| `mcp__n8n__list_ai_tools` | List AI-capable nodes |
| `mcp__n8n__search_node_properties` | Search node properties |

## Examples

### Search for Nodes
```
/n8n:find nodes slack

# With examples
/n8n:find nodes http --examples
```

### Search by Category
```
/n8n:find nodes webhook --category trigger
```

### Search Templates
```
/n8n:find templates "email automation"

# By task type
/n8n:find templates --task ai_automation
```

### Task Types for Templates
```
ai_automation     - AI and LLM workflows
data_sync         - Data synchronization
webhook_processing - Webhook handlers
email_automation  - Email workflows
slack_integration - Slack workflows
data_transformation - Data processing
file_processing   - File handling
scheduling        - Scheduled tasks
api_integration   - API connections
database_operations - Database workflows
```

### Get Node Documentation
```
/n8n:find docs slack

# Search for specific property
/n8n:find docs httpRequest --property authentication
```

### List AI Nodes
```
/n8n:find ai

# All nodes can be AI tools - this shows optimized ones
```

## Advanced Usage

### Find Trigger Nodes
```
/n8n:find nodes "" --category trigger --limit 20
```

### Find Templates with Specific Nodes
For finding templates that use specific nodes, use the skill `n8n-workflow-builder` which can search templates by node type.

## Related Commands

- `/n8n:list` - List workflows and executions
- `/n8n:validate` - Validate workflow configuration
- `/n8n:help nodes` - Node usage documentation
