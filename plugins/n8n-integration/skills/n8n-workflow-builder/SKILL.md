---
name: n8n-workflow-builder
description: "Build n8n workflows from scratch or templates with guided node selection and validation. Use when user asks to 'create workflow', 'build automation', 'n8n workflow', 'automate process', 'create AI agent workflow', or needs help designing new n8n automations."
version: 1.0.0
license: MIT
---

# n8n Workflow Builder

Advanced skill for creating n8n workflows through intelligent node selection, template adaptation, and structured workflow composition.

## Activation Triggers

- "create workflow"
- "build automation"
- "n8n workflow"
- "automate process"
- "create AI agent"
- "build integration"
- "workflow from template"
- "connect [service] to [service]"

## Capabilities

### Workflow Creation
- Build workflows from scratch
- Adapt templates for requirements
- Select optimal nodes for tasks
- Configure node parameters

### Node Discovery
- Search nodes by functionality
- Get node documentation
- Understand node dependencies
- Select appropriate triggers

### AI Workflow Building
- Create AI agent workflows
- Connect AI tools to nodes
- Configure LLM nodes
- Build agentic patterns

### Validation & Deployment
- Validate before creation
- Create workflow via API
- Provide activation instructions

## CLI Tools Available

| Script | Purpose |
|--------|---------|
| `scripts/n8n_api.py workflows list` | List existing workflows |
| `scripts/n8n_api.py workflows get` | Get workflow structure |
| `scripts/n8n_api.py workflows create` | Create new workflow |
| `scripts/n8n_api.py workflows update` | Update workflow |
| `scripts/n8n_api.py health` | Check n8n instance |

### Example CLI Commands

```bash
# List workflows to see patterns
python3 scripts/n8n_api.py workflows list

# Get workflow JSON for reference
python3 scripts/n8n_api.py workflows get <id> --json > workflow.json

# Create workflow from JSON file
python3 scripts/n8n_api.py workflows create --file workflow.json

# Add a node to existing workflow
python3 scripts/n8n_api.py workflows add-node <id> --node-json '{"type": "n8n-nodes-base.set"}'
```

### API Limitations

**Note**: The n8n REST API does not provide:
- Node search endpoints (use n8n UI node palette or official docs)
- Template search (browse https://n8n.io/workflows/)
- Node documentation lookup (see https://docs.n8n.io/integrations/builtin/)

For node discovery, use:
1. **n8n UI**: Node palette in workflow editor
2. **Official Docs**: https://docs.n8n.io/integrations/builtin/
3. **Templates**: https://n8n.io/workflows/

## Workflow Building Process

### Phase 1: Requirements Gathering

```yaml
understand_needs:
  questions:
    - What should the workflow accomplish?
    - What triggers the workflow? (webhook, schedule, event)
    - What services/APIs are involved?
    - What transformations are needed?
    - What's the expected output?
    - Any error handling requirements?

  categorize:
    trigger_type: manual|webhook|schedule|event
    complexity: simple|moderate|complex
    integrations: list of services
    ai_required: boolean
```

### Phase 2: Template Search

```yaml
find_templates:
  tool: search_templates
  params:
    query: "relevant keywords"

  alternative:
    tool: get_templates_for_task
    params:
      task: ai_automation|data_sync|webhook_processing|etc

  evaluate:
    - Relevance to requirements
    - Node count and complexity
    - Popularity (views)
    - Adaptability
```

### Phase 3: Node Selection

```yaml
identify_nodes:
  1. Trigger Node:
     - Webhook for API endpoints
     - Schedule Trigger for cron jobs
     - Service trigger for events

  2. Processing Nodes:
     tool: search_nodes
     params:
       query: "service or function name"
       includeExamples: true

  3. Output Nodes:
     - HTTP Request for API calls
     - Service nodes for integrations
     - Set node for data formatting

  4. Utility Nodes:
     - IF for conditions
     - Switch for routing
     - Merge for combining data
     - Code for custom logic
```

### Phase 4: Workflow Composition

```yaml
build_structure:
  1. Create node array:
     - Assign unique IDs
     - Set positions (visual layout)
     - Configure parameters

  2. Define connections:
     - Map output to input
     - Handle multiple outputs
     - Connect error paths

  3. Configure settings:
     - executionOrder: "v1"
     - timezone
     - error handling

  4. Validate composition:
     tool: validate_workflow
     params:
       workflow: composedWorkflow
```

### Phase 5: Creation & Activation

```yaml
create_workflow:
  # IMPORTANT: Do NOT include 'active' in POST body — it is read-only
  tool: n8n_create_workflow
  params:
    name: "Workflow Name"
    nodes: [nodeArray]
    connections: {connectionMap}
    settings: {workflowSettings}

  post_creation:
    - Workflow created inactive
    - Activate via API: POST /api/v1/workflows/{id}/activate
    - Or via CLI: python3 scripts/n8n_api.py workflows activate <id>
    - Share webhook URL if applicable
```

#### Activation via CLI
```bash
# Create workflow (returns workflow ID)
WF_ID=$(python3 scripts/n8n_api.py workflows create --file workflow.json --json | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Activate immediately after creation
python3 scripts/n8n_api.py workflows activate $WF_ID

# Verify active status
python3 scripts/n8n_api.py workflows get $WF_ID --json | python3 -c "import sys,json; d=json.load(sys.stdin); print('active:', d.get('active'))"
```

## Node Structure Reference

### Basic Node Structure
```json
{
  "id": "unique-uuid",
  "name": "Display Name",
  "type": "n8n-nodes-base.nodeType",
  "typeVersion": 1,
  "position": [x, y],
  "parameters": {
    "param1": "value1",
    "param2": "{{ $json.field }}"
  }
}
```

### Connection Structure
```json
{
  "Source Node Name": {
    "main": [
      [
        {
          "node": "Target Node Name",
          "type": "main",
          "index": 0
        }
      ]
    ]
  }
}
```

### Workflow Settings
```json
{
  "executionOrder": "v1",
  "saveDataErrorExecution": "all",
  "saveDataSuccessExecution": "all",
  "saveExecutionProgress": true,
  "timezone": "America/New_York"
}
```

## Common Workflow Patterns

### Webhook to API
```yaml
pattern: webhook_to_api
nodes:
  1. Webhook (trigger)
  2. Set (prepare data)
  3. HTTP Request (call API)
  4. Respond to Webhook

use_case: API endpoint that processes and forwards
```

### Scheduled Data Sync
```yaml
pattern: scheduled_sync
nodes:
  1. Schedule Trigger
  2. HTTP Request (fetch data)
  3. IF (check for changes)
  4. Database (update records)

use_case: Periodic data synchronization
```

### AI Processing
```yaml
pattern: ai_processing
nodes:
  1. Trigger (webhook/schedule)
  2. Data preparation
  3. OpenAI/LLM node
  4. Output handling

use_case: AI-powered data processing
```

### Multi-Step Integration
```yaml
pattern: multi_step
nodes:
  1. Trigger
  2. Fetch from Source A
  3. Transform data
  4. Send to Destination B
  5. Send to Destination C
  6. Log results

use_case: Complex integrations
```

## AI Agent Workflows

### AI Agent Structure
```yaml
ai_agent_workflow:
  components:
    agent_node:
      type: "@n8n/n8n-nodes-langchain.agent"
      connects_to: tools, memory, output_parser

    tool_nodes:
      - Any node can be a tool
      - Connect to agent's tool port
      - Configured for AI invocation

    memory_node:
      - Window Buffer Memory
      - Chat Memory
      - Custom memory

    output_parser:
      - Structured output
      - Custom parsing

  tools_note: |
    ANY n8n node can be used as an AI tool!
    Connect any node to the AI Agent's tool port.
    For community nodes, set N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true
```

### Getting AI Tool Info
```yaml
get_ai_info:
  tool: get_node_as_tool_info
  params:
    nodeType: "nodes-base.httpRequest"

  returns:
    - How to configure as AI tool
    - Required parameters
    - Usage examples
```

## Validation Before Creation

### Pre-Creation Checks
```yaml
validate:
  tool: validate_workflow
  params:
    workflow: builtWorkflow
    options:
      validateNodes: true
      validateConnections: true
      validateExpressions: true

  handle_errors:
    - Fix identified issues
    - Re-validate
    - Proceed when clean
```

### Node Configuration Check
```yaml
validate_node:
  tool: validate_node_operation
  params:
    nodeType: "nodes-base.httpRequest"
    config:
      method: "POST"
      url: "https://api.example.com"
    profile: "runtime"

  ensures:
    - Required fields present
    - Valid configuration
    - Correct parameter types
```

## Template Adaptation

### Using Templates
```yaml
template_workflow:
  1. Find template:
     tool: search_templates
     params:
       query: "slack notification"

  2. Get template:
     tool: get_template
     params:
       templateId: 1234
       mode: "full"

  3. Adapt:
     - Modify parameters
     - Add/remove nodes
     - Update connections
     - Customize for requirements

  4. Create:
     tool: n8n_create_workflow
     params:
       name: "Customized Workflow"
       nodes: adaptedNodes
       connections: adaptedConnections
```

## Post-Creation Steps

### Activation Requirements
```yaml
activation:
  note: |
    Workflows are created INACTIVE.
    Activate via REST API — no manual UI step needed.

  api_method: POST /api/v1/workflows/{id}/activate
  cli_method: python3 scripts/n8n_api.py workflows activate <id>

  important:
    - 'active' field is READ-ONLY in POST/PUT body — setting it there is silently ignored
    - Must call the /activate endpoint separately after creation
    - Deactivate with: POST /api/v1/workflows/{id}/deactivate

  verify:
    - GET /api/v1/workflows/{id} → check "active": true
```

### Webhook URL Retrieval
```yaml
webhook_url:
  production: https://your-n8n.com/webhook/<path>
  test: https://your-n8n.com/webhook-test/<path>

  note: |
    Production URL only works when workflow is active.
    Test URL works for manual testing.
```

## MCP Server Trigger (Expose Workflows as MCP Tools)

Use the MCP Server Trigger to expose n8n workflows as tools callable by Claude Desktop or any MCP client.

### Node Structure
```json
{
  "id": "<uuid>",
  "name": "MCP Server Trigger",
  "type": "@n8n/n8n-nodes-langchain.mcpTrigger",
  "typeVersion": 1,
  "position": [0, 0],
  "webhookId": "<uuid>",
  "parameters": {
    "authentication": "none",
    "path": "my-tool-path"
  }
}
```

**Required parameters** (only these two exist on this node):
- `path` (string, required) — unique path for the MCP endpoint (e.g. `celigo-list-errors`)
- `authentication` — `"none"` or `"basicAuth"`

**DO NOT** include `toolDescription`, `inputSchema`, or other parameters — they don't exist and will cause "Missing or invalid required parameters" errors.

### Workflow Settings for MCP
```json
{
  "executionOrder": "v1",
  "availableInMCP": true
}
```

`availableInMCP: true` is required in workflow settings for the workflow to be exposed via the n8n MCP server endpoint.

### Critical Architecture — Tools Connect INTO the Trigger

**WRONG** (webhook-style, doesn't work):
```
MCP Server Trigger → HTTP Request → Code → Respond to Webhook
```

**CORRECT** (tool-based, required by n8n):
```
toolHttpRequest/toolCode → [ai_tool output] → MCP Server Trigger [ai_tool input]
```

The MCP Server Trigger has:
- **Input**: `ai_tool` connection type — accepts tool nodes
- **Output**: none

Each tool node connected to the trigger is exposed as a separate MCP tool. When an MCP client calls `tools/list`, it gets back the connected tools.

### MCP Tool Pattern (Correct)
```yaml
mcp_tool_workflow:
  Nodes:
    1. toolHttpRequest or toolCode (position: [-200, 0])
       - Outputs via ai_tool connection type
    2. MCP Server Trigger (path: "my-tool-name")
       - Has ai_tool INPUT (not output)

  Connections:
    "Tool Node Name":
      ai_tool: [[{node: "MCP Server Trigger", type: "ai_tool", index: 0}]]

  Settings:
    availableInMCP: true  # required
    executionOrder: "v1"

  SSE Endpoint (typeVersion 1):
    GET  /mcp/{path}/sse       → SSE setup (persistent connection)
    POST /mcp/{path}/messages  → send MCP messages (with ?sessionId=)
```

### toolHttpRequest — Correct Header Configuration

**WRONG** (uses `headerParameters.parameters` — wrong field, creates empty toolParameter):
```json
{
  "sendHeaders": true,
  "headerParameters": {"parameters": [{"name": "Authorization", "value": "Bearer ..."}]}
}
```

**CORRECT** (use `specifyHeaders: "json"` with `jsonHeaders`):
```json
{
  "sendHeaders": true,
  "specifyHeaders": "json",
  "jsonHeaders": "{\"Authorization\": \"Bearer YOUR_API_KEY\"}"
}
```

**Why**: `headerParameters` is for the regular HTTP Request node. `toolHttpRequest` uses `parametersHeaders.values` (keypair) or `jsonHeaders` (json). The default `parametersHeaders` has `{values: [{name: ""}]}` which creates a spurious empty-string toolParameter and causes ZodErrors when the tool is called.

### Creating an MCP Tool Workflow via API
```python
import uuid, json

api_key = "your_api_key"
tool_id = str(uuid.uuid4())
trigger_id = str(uuid.uuid4())

workflow = {
    "name": "My MCP Tool",
    "settings": {"executionOrder": "v1", "availableInMCP": True},
    "nodes": [
        {
            "id": tool_id,
            "name": "My Tool",
            "type": "@n8n/n8n-nodes-langchain.toolHttpRequest",
            "typeVersion": 1.1,
            "position": [-200, 0],
            "parameters": {
                "toolDescription": "What this tool does. No input parameters needed.",
                "method": "GET",
                "url": "https://api.example.com/endpoint",
                "sendHeaders": True,
                "specifyHeaders": "json",
                "jsonHeaders": json.dumps({"Authorization": f"Bearer {api_key}"})
            }
        },
        {
            "id": trigger_id,
            "name": "MCP Server Trigger",
            "type": "@n8n/n8n-nodes-langchain.mcpTrigger",
            "typeVersion": 1,
            "position": [0, 0],
            "webhookId": str(uuid.uuid4()),
            "parameters": {"authentication": "none", "path": "my-tool-path"}
        }
    ],
    "connections": {
        "My Tool": {
            "ai_tool": [[{"node": "MCP Server Trigger", "type": "ai_tool", "index": 0}]]
        }
    }
}

# Create (no 'active' in body)
result = n8n_api("POST", "/workflows", workflow)
wf_id = result["id"]

# Activate separately
n8n_api("POST", f"/workflows/{wf_id}/activate")
```

### Claude Desktop MCP Config
```json
{
  "mcpServers": {
    "n8n": {
      "command": "npx",
      "args": ["n8n-mcp"],
      "env": {
        "N8N_API_URL": "https://your-n8n.com",
        "N8N_API_KEY": "your-api-key",
        "MCP_MODE": "stdio"
      }
    }
  }
}
```

## Best Practices

### Workflow Design
1. Start with clear trigger
2. Handle errors gracefully
3. Include logging for debugging
4. Use meaningful node names
5. Position nodes for readability

### Node Selection
1. Use native nodes when available
2. Check node version compatibility
3. Consider rate limits
4. Plan for data volume

### Testing
1. Test with sample data first
2. Validate all paths
3. Check error handling
4. Verify output format

## Reference Files

- `@node-patterns.md` - Common node configurations
- `@connection-patterns.md` - Workflow structure patterns
- `@ai-agent-patterns.md` - AI workflow building
- `@expression-syntax.md` - n8n expression guide
- `@trigger-nodes.md` - Trigger node options
- `@code-node-examples.md` - Code node patterns
