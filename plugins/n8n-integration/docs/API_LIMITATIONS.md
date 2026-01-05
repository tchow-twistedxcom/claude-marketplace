# n8n API Capabilities and Limitations

This document describes the capabilities and limitations of the n8n REST API (v1).

## API Capability Summary

### Available Operations

| Category | Operations | Description |
|----------|------------|-------------|
| Workflow CRUD | Create, read, update, delete, list | Full workflow management |
| Workflow Activation | Activate, deactivate | POST /workflows/{id}/activate, /deactivate |
| Validation | Validate, auto-fix | Check workflows, expressions, connections |
| Node Discovery | Search, list, get info | Find nodes, templates, documentation |
| Execution | List, get, delete, retry | Monitor and manage executions |
| Credentials | Create, delete, list, schema | Manage credentials via API |
| Tags | CRUD | Organize workflows with tags |
| Utility | Health check, webhooks | Diagnostics and triggering |

### API Feature Matrix

| Feature | API Support | Endpoint | Notes |
|---------|-------------|----------|-------|
| Workflow Activation | ✅ Yes | POST /workflows/{id}/activate | Activates workflow for triggers |
| Workflow Deactivation | ✅ Yes | POST /workflows/{id}/deactivate | Stops active triggers |
| Credential Create | ✅ Yes | POST /credentials | Create new credentials |
| Credential Delete | ✅ Yes | DELETE /credentials/{id} | Remove credentials |
| Credential Schema | ✅ Yes | GET /credentials/schema/{type} | Get field schema for type |
| Credential Update | ❌ No | — | Delete and recreate instead |
| Credential Read Data | ❌ No | — | Sensitive data never returned |
| Direct Execution | ❌ No | — | Use webhook trigger instead |
| Stop Execution | ❌ No | — | Rely on timeouts |
| Bulk Import/Export | ❌ No | — | One workflow at a time |

### Limitations Summary

| Feature | Limitation | Workaround |
|---------|------------|------------|
| Direct Execution | Cannot execute workflows directly | Add webhook trigger, call webhook URL |
| Stop Executions | Cannot stop running executions | Set appropriate timeouts, use circuit breakers |
| Credential Update | No update endpoint | Delete and recreate credential |
| Version History | No built-in versioning | Export workflow JSON to git before changes |

## Detailed API Usage

### 1. Workflow Activation

**Available**: ✅ Yes - Use POST /workflows/{id}/activate and /deactivate

**Python Example**:
```python
from n8n_api import N8nClient, WorkflowsAPI

client = N8nClient()
api = WorkflowsAPI(client)

# Activate workflow
result = api.activate("workflow-id")
print(f"Activated: {result.get('active')}")

# Deactivate workflow
result = api.deactivate("workflow-id")
print(f"Deactivated: {not result.get('active')}")
```

**CLI Example**:
```bash
# Activate
python3 n8n_api.py workflows activate <workflow-id>

# Deactivate
python3 n8n_api.py workflows deactivate <workflow-id>
```

**Note**: Activation is automatically triggered when updating an active workflow via PUT.

### 2. Workflow Execution

**Limitation**: Cannot programmatically execute workflows on demand.

**Impact**: Only webhook-triggered workflows can be executed via API.

**Workaround**:
```yaml
approach_1: "Use Webhook Trigger"
  - Add Webhook node to workflow
  - Call webhook URL to trigger execution
  - Works only when workflow is active

approach_2: "Use Schedule Trigger"
  - Add Schedule Trigger for automatic execution
  - Cannot trigger on-demand

approach_3: "Execute Workflow Node"
  - Create a webhook-triggered wrapper workflow
  - Use "Execute Workflow" node to run target workflow
```

**Example Wrapper Workflow**:
```json
{
  "nodes": [
    {
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "path": "run-workflow",
        "httpMethod": "POST"
      }
    },
    {
      "name": "Execute Workflow",
      "type": "n8n-nodes-base.executeWorkflow",
      "parameters": {
        "workflowId": "={{ $json.workflowId }}"
      }
    }
  ]
}
```

### 3. Credential Management

**Available**: ✅ Create, Delete, Schema - Use POST/DELETE /credentials

> **Note**: GET /credentials (list) may return 405 on some n8n installations
> due to security restrictions. Create, delete, and schema endpoints are
> always available.

**Python Example**:
```python
from n8n_api import N8nClient, CredentialsAPI

client = N8nClient()
api = CredentialsAPI(client)

# List all credentials (without sensitive data)
creds = api.list()

# Create a new credential
result = api.create(
    name="Webhook Auth Token",
    type="httpHeaderAuth",
    data={
        "name": "X-Webhook-Token",
        "value": "your-secret-token"
    }
)
print(f"Created credential ID: {result.get('id')}")

# Get schema for a credential type
schema = api.get_schema("httpHeaderAuth")

# Delete a credential
api.delete("credential-id")
```

**CLI Example**:
```bash
# List credentials
python3 n8n_api.py credentials list

# Create credential
python3 n8n_api.py credentials create \
  --name "Webhook Auth Token" \
  --type httpHeaderAuth \
  --data '{"name": "X-Webhook-Token", "value": "secret123"}'

# Delete credential
python3 n8n_api.py credentials delete <credential-id>
```

**Common Credential Types**:
| Type | Description | Required Fields |
|------|-------------|-----------------|
| `httpHeaderAuth` | Custom header authentication | `name`, `value` |
| `httpBasicAuth` | Basic HTTP authentication | `user`, `password` |
| `oAuth2Api` | OAuth 2.0 flow | `clientId`, `clientSecret`, etc. |
| `apiKey` | API key authentication | `key` |

**Limitations**:
- Cannot update credentials (delete and recreate instead)
- Sensitive data (passwords, secrets) never returned in API responses
- OAuth credentials require UI flow for initial authorization

### 4. Execution Control

**Limitation**: Cannot stop or retry running executions.

**Impact**: Long-running or stuck executions must complete or timeout.

**Workaround**:
```yaml
prevention:
  - Set appropriate execution timeouts
  - Implement circuit breakers in workflows
  - Use execution limits in workflow settings

monitoring:
  - Track execution durations
  - Alert on unusually long executions
  - Review execution logs regularly

workflow_settings:
  executionTimeout: 300  # 5 minutes max
  saveDataErrorExecution: "all"
  saveDataSuccessExecution: "all"
```

### 5. Bulk Operations

**Limitation**: No batch operations for workflows or executions.

**Impact**: Must process workflows one at a time.

**Workaround**:
```javascript
// Iterate through workflows
const workflowIds = ['id1', 'id2', 'id3'];

for (const id of workflowIds) {
  // Process each workflow
  await processWorkflow(id);
  // Add delay to avoid rate limiting
  await sleep(100);
}
```

### 6. Workflow Versioning

**Limitation**: No built-in version history via API.

**Impact**: Cannot rollback to previous workflow versions.

**Workaround**:
```yaml
manual_versioning:
  - Export workflow JSON before changes
  - Store versions in Git repository
  - Use naming convention: workflow_v1, workflow_v2

backup_process:
  1. Get workflow via n8n_get_workflow
  2. Save JSON to version control
  3. Tag with version number
  4. Update workflow
  5. Verify changes
```

**Backup Script Pattern**:
```javascript
// Before updating, backup current version
const backup = {
  timestamp: new Date().toISOString(),
  workflowId: workflow.id,
  workflowName: workflow.name,
  version: `v${Date.now()}`,
  workflow: workflow
};

// Store backup (database, file, git)
await storeBackup(backup);
```

## API Error Codes

### Common Errors and Handling

| Error Code | Description | Recommended Action |
|------------|-------------|-------------------|
| 401 | Unauthorized | Check API key validity |
| 403 | Forbidden | Verify API key permissions |
| 404 | Not Found | Verify workflow/execution ID exists |
| 422 | Validation Error | Check workflow JSON structure |
| 429 | Rate Limited | Implement backoff and retry |
| 500 | Server Error | Retry with exponential backoff |

### Error Handling Pattern
```javascript
const response = await n8nApiCall(request);

switch (response.status) {
  case 401:
    throw new Error('Invalid API key. Please verify your N8N_API_KEY.');

  case 403:
    throw new Error('API key lacks required permissions.');

  case 404:
    throw new Error(`Resource not found: ${request.resourceId}`);

  case 422:
    const errors = response.body.errors;
    throw new Error(`Validation failed: ${JSON.stringify(errors)}`);

  case 429:
    const retryAfter = response.headers['retry-after'] || 60;
    throw new Error(`Rate limited. Retry after ${retryAfter} seconds.`);

  case 500:
    throw new Error('n8n server error. Please try again later.');

  default:
    if (response.status >= 400) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
}
```

## Feature Request Workarounds

### Desired: Execute Workflow on Demand
```yaml
current_limitation: "No direct execution API"
workaround:
  option_1:
    description: "Webhook wrapper"
    setup:
      - Create webhook-triggered workflow
      - Call webhook to execute
    limitation: "Requires workflow to be active"

  option_2:
    description: "Manual trigger in UI"
    setup:
      - Add Manual Trigger node
      - User clicks 'Execute' in UI
    limitation: "Not automatable"
```

### Desired: Clone Workflow
```yaml
current_limitation: "No clone API endpoint"
workaround:
  process:
    1. Get workflow via n8n_get_workflow
    2. Modify JSON (new name, remove IDs)
    3. Create new workflow via n8n_create_workflow

code_example:
  const original = await getWorkflow(id);
  const clone = {
    ...original,
    name: `${original.name} (Copy)`,
    id: undefined,  # Let n8n generate new ID
  };
  await createWorkflow(clone);
```

### Desired: Workflow Templates
```yaml
current_limitation: "Templates are read-only"
workaround:
  process:
    1. Get template via get_template
    2. Modify for specific use case
    3. Create as new workflow
    4. Configure credentials manually
```

## Best Practices

### Working Within Limitations

```yaml
workflow_design:
  - Always include Webhook trigger for external execution
  - Document required credentials in workflow notes
  - Use meaningful naming for nodes and workflows
  - Add error handling for all external calls

deployment_process:
  - Create workflow via API
  - Validate workflow via API
  - Provide user with activation instructions
  - Document credential requirements
  - Test with manual execution first

maintenance:
  - Monitor executions via API
  - Review error executions regularly
  - Update workflows incrementally
  - Keep backup of workflow JSON
```

### Automation Boundaries

```yaml
fully_automatable:
  - Workflow creation and updates
  - Workflow validation and auto-fix
  - Workflow activation/deactivation
  - Credential creation and deletion
  - Execution monitoring
  - Node and template discovery
  - Health checks and diagnostics

requires_manual_step:
  - Direct workflow execution (without webhook)
  - Stopping running executions
  - Credential update (delete and recreate instead)
  - OAuth credential initial authorization
```

## Future API Enhancements

The following features may be added in future n8n API versions:

- Direct execution endpoint (without webhook trigger)
- Execution control (stop running executions)
- Credential update endpoint (currently must delete and recreate)
- Bulk operations (import/export multiple workflows)
- Workflow versioning (built-in version history)

Check n8n release notes for API updates: https://docs.n8n.io/release-notes/
