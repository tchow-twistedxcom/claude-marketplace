---
name: n8n-run
description: "Trigger an n8n workflow via webhook"
---

# /n8n:run - Trigger Workflow via Webhook

Execute an n8n workflow by triggering its webhook endpoint.

## Usage

```
/n8n:run <webhook-url|workflow-id> [options]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `webhook-url` | Full webhook URL from n8n workflow |
| `workflow-id` | Workflow ID (requires webhook path lookup) |

## Flags

| Flag | Description |
|------|-------------|
| `--account <id>` | Use specific n8n account (default: from config) |
| `--data <json>` | JSON data to send with request |
| `--file <path>` | Read data from JSON file |
| `--method <m>` | HTTP method: GET, POST, PUT, DELETE (default: POST) |
| `--headers <json>` | Additional HTTP headers as JSON |
| `--no-wait` | Don't wait for workflow completion |
| `--timeout <ms>` | Response timeout in milliseconds |

## Important Limitations

### Webhook Required
**n8n API does not support direct workflow execution.** All workflows must have a Webhook node configured to be triggered externally.

### Workflow Must Be Active
Workflows must be **manually activated** in the n8n UI before they can receive webhook requests. The API cannot activate workflows.

## Workflow

1. **Validate Input**
   - Parse webhook URL or look up workflow
   - Validate URL format

2. **Prepare Request**
   - Set HTTP method (default: POST)
   - Parse data payload if provided
   - Add custom headers if specified

3. **Execute Webhook**
   - Call `python3 scripts/n8n_api.py webhook <url>`
   - Handle response or timeout

4. **Report Results**
   - Show execution status
   - Display response data
   - Report any errors

## Output Format

### Successful Execution
```
Workflow Triggered Successfully
================================
Webhook: https://n8n.example.com/webhook/abc-123
Method: POST
Status: 200 OK

Response:
{
  "success": true,
  "processed": 5,
  "message": "Data synced successfully"
}

Execution Time: 2.3s
```

### Execution with Data
```
Triggering Workflow...
================================
URL: https://n8n.example.com/webhook/customer-sync
Method: POST
Data: {"customerId": "12345", "action": "update"}

Response (200 OK):
{
  "status": "updated",
  "customerId": "12345",
  "timestamp": "2024-03-21T10:30:00Z"
}
```

### Error Response
```
Workflow Execution Failed
================================
Webhook: https://n8n.example.com/webhook/abc-123
Status: 500 Internal Server Error

Error:
{
  "message": "Database connection timeout",
  "node": "PostgreSQL"
}

Troubleshooting:
- Check workflow configuration with /n8n:validate <workflow-id>
- Review execution logs in n8n UI
- Verify database credentials
```

### Workflow Not Active
```
Cannot Trigger Workflow
================================
The webhook endpoint returned 404.

Possible causes:
1. Workflow is not active (activate in n8n UI)
2. Webhook path is incorrect
3. Webhook node configuration changed

To activate:
1. Open n8n UI
2. Navigate to the workflow
3. Toggle the Active switch to ON
```

## CLI Tools Used

| Script | Purpose |
|--------|---------|
| `scripts/n8n_api.py webhook` | Trigger webhook URL |
| `scripts/n8n_api.py workflows get` | Look up workflow details |
| `scripts/n8n_api.py workflows list` | Find workflow by name |

### Example CLI Commands

```bash
# Trigger webhook with POST
python3 scripts/n8n_api.py webhook https://n8n.example.com/webhook/abc-123

# Trigger with JSON data
python3 scripts/n8n_api.py webhook https://n8n.example.com/webhook/abc-123 --data '{"key": "value"}'

# GET request
python3 scripts/n8n_api.py webhook https://n8n.example.com/webhook/status --method GET

# With custom headers
python3 scripts/n8n_api.py webhook https://n8n.example.com/webhook/api --headers '{"X-API-Key": "secret"}'
```

## Examples

### Basic Webhook Trigger
```
/n8n:run https://n8n.example.com/webhook/abc-123
```

### Trigger with JSON Data
```
/n8n:run https://n8n.example.com/webhook/customer-sync --data '{"customerId": "12345"}'
```

### Trigger with Data from File
```
/n8n:run https://n8n.example.com/webhook/import --file ./data.json
```

### GET Request
```
/n8n:run https://n8n.example.com/webhook/status --method GET
```

### With Custom Headers
```
/n8n:run https://n8n.example.com/webhook/api --headers '{"X-API-Key": "secret"}'
```

### Fire and Forget (No Wait)
```
/n8n:run https://n8n.example.com/webhook/batch --no-wait
```

### Extended Timeout
```
/n8n:run https://n8n.example.com/webhook/long-process --timeout 60000
```

### Run on Specific Account
```
/n8n:run my-workflow --account production
```

## Setting Up Webhooks

### Creating a Webhook-Triggered Workflow

1. **Add Webhook Node**
   - Add "Webhook" as the first node
   - Configure HTTP Method (GET/POST)
   - Copy the webhook URL

2. **Configure Response**
   - Set response mode (immediately or when last node finishes)
   - Configure response data

3. **Activate Workflow**
   - Toggle the workflow to Active in n8n UI
   - Test with a sample request

### Webhook URL Format
```
Production: https://your-n8n.com/webhook/<webhook-id>
Test: https://your-n8n.com/webhook-test/<webhook-id>
```

### Common Webhook Patterns

**Respond Immediately**
- Best for async processing
- Returns acknowledgment quickly
- Process continues in background

**Respond After Completion**
- Best for sync operations
- Returns actual results
- Client waits for completion

## Troubleshooting

### 404 Not Found
- Workflow not active → Activate in n8n UI
- Wrong webhook path → Check webhook node configuration
- Typo in URL → Verify URL from n8n

### 500 Internal Server Error
- Node error → Check n8n execution logs
- Credentials invalid → Update credentials in n8n
- External service down → Check connected services

### Timeout
- Workflow too slow → Optimize workflow or increase timeout
- External dependency → Check network/service availability

## Related Commands

- `/n8n:list workflows` - Find workflows
- `/n8n:validate` - Validate workflow before running
- `/n8n:status` - Check n8n health
