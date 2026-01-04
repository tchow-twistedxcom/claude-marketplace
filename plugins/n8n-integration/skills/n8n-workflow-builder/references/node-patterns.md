# n8n Node Configuration Patterns

Common node configurations for building workflows.

## HTTP Request Node

### Basic GET Request
```json
{
  "id": "http-get-1",
  "name": "Fetch Data",
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4.2,
  "position": [400, 300],
  "parameters": {
    "method": "GET",
    "url": "https://api.example.com/data",
    "authentication": "genericCredentialType",
    "genericAuthType": "httpHeaderAuth"
  }
}
```

### POST with JSON Body
```json
{
  "id": "http-post-1",
  "name": "Send Data",
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4.2,
  "position": [600, 300],
  "parameters": {
    "method": "POST",
    "url": "https://api.example.com/submit",
    "sendBody": true,
    "specifyBody": "json",
    "jsonBody": "={{ $json }}",
    "options": {
      "response": {
        "response": {
          "responseFormat": "json"
        }
      }
    }
  }
}
```

### With Custom Headers
```json
{
  "parameters": {
    "method": "GET",
    "url": "https://api.example.com/data",
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        {
          "name": "X-API-Key",
          "value": "={{ $env.API_KEY }}"
        },
        {
          "name": "Content-Type",
          "value": "application/json"
        }
      ]
    }
  }
}
```

### With Query Parameters
```json
{
  "parameters": {
    "method": "GET",
    "url": "https://api.example.com/search",
    "sendQuery": true,
    "queryParameters": {
      "parameters": [
        {
          "name": "q",
          "value": "={{ $json.searchTerm }}"
        },
        {
          "name": "limit",
          "value": "100"
        }
      ]
    }
  }
}
```

## Set Node

### Manual Mode - Set Fields
```json
{
  "id": "set-1",
  "name": "Prepare Data",
  "type": "n8n-nodes-base.set",
  "typeVersion": 3.4,
  "position": [500, 300],
  "parameters": {
    "mode": "manual",
    "duplicateItem": false,
    "assignments": {
      "assignments": [
        {
          "id": "field1",
          "name": "outputField",
          "value": "={{ $json.inputField }}",
          "type": "string"
        },
        {
          "id": "field2",
          "name": "timestamp",
          "value": "={{ $now.toISOString() }}",
          "type": "string"
        }
      ]
    }
  }
}
```

### Raw Mode - Full JSON
```json
{
  "parameters": {
    "mode": "raw",
    "jsonOutput": "={{ JSON.stringify({ id: $json.id, name: $json.name, processed: true }) }}"
  }
}
```

## IF Node

### Simple Condition
```json
{
  "id": "if-1",
  "name": "Check Status",
  "type": "n8n-nodes-base.if",
  "typeVersion": 2.1,
  "position": [600, 300],
  "parameters": {
    "conditions": {
      "options": {
        "caseSensitive": true,
        "leftValue": "",
        "typeValidation": "strict"
      },
      "conditions": [
        {
          "id": "condition1",
          "leftValue": "={{ $json.status }}",
          "rightValue": "active",
          "operator": {
            "type": "string",
            "operation": "equals"
          }
        }
      ],
      "combinator": "and"
    }
  }
}
```

### Multiple Conditions (AND)
```json
{
  "parameters": {
    "conditions": {
      "conditions": [
        {
          "leftValue": "={{ $json.status }}",
          "rightValue": "active",
          "operator": {
            "type": "string",
            "operation": "equals"
          }
        },
        {
          "leftValue": "={{ $json.amount }}",
          "rightValue": "100",
          "operator": {
            "type": "number",
            "operation": "gte"
          }
        }
      ],
      "combinator": "and"
    }
  }
}
```

## Switch Node

### Multiple Outputs
```json
{
  "id": "switch-1",
  "name": "Route by Type",
  "type": "n8n-nodes-base.switch",
  "typeVersion": 3.2,
  "position": [600, 300],
  "parameters": {
    "mode": "rules",
    "rules": {
      "rules": [
        {
          "id": "rule1",
          "output": 0,
          "conditions": {
            "conditions": [
              {
                "leftValue": "={{ $json.type }}",
                "rightValue": "order",
                "operator": {
                  "type": "string",
                  "operation": "equals"
                }
              }
            ]
          }
        },
        {
          "id": "rule2",
          "output": 1,
          "conditions": {
            "conditions": [
              {
                "leftValue": "={{ $json.type }}",
                "rightValue": "refund",
                "operator": {
                  "type": "string",
                  "operation": "equals"
                }
              }
            ]
          }
        }
      ]
    },
    "fallbackOutput": 2
  }
}
```

## Merge Node

### Append Items
```json
{
  "id": "merge-1",
  "name": "Combine Results",
  "type": "n8n-nodes-base.merge",
  "typeVersion": 3,
  "position": [800, 300],
  "parameters": {
    "mode": "append"
  }
}
```

### Merge by Field
```json
{
  "parameters": {
    "mode": "combine",
    "mergeByFields": {
      "values": [
        {
          "field1": "id",
          "field2": "customerId"
        }
      ]
    },
    "joinMode": "enrichInput1"
  }
}
```

## Loop/Split In Batches

### Process in Batches
```json
{
  "id": "batch-1",
  "name": "Process Batches",
  "type": "n8n-nodes-base.splitInBatches",
  "typeVersion": 3,
  "position": [500, 300],
  "parameters": {
    "batchSize": 10,
    "options": {}
  }
}
```

## Wait Node

### Wait Duration
```json
{
  "id": "wait-1",
  "name": "Wait 5 Seconds",
  "type": "n8n-nodes-base.wait",
  "typeVersion": 1.1,
  "position": [600, 300],
  "parameters": {
    "resume": "timeInterval",
    "amount": 5,
    "unit": "seconds"
  }
}
```

## Error Handling Nodes

### Error Trigger
```json
{
  "id": "error-trigger-1",
  "name": "On Error",
  "type": "n8n-nodes-base.errorTrigger",
  "typeVersion": 1,
  "position": [100, 500],
  "parameters": {}
}
```

### Stop and Error
```json
{
  "id": "stop-1",
  "name": "Stop Workflow",
  "type": "n8n-nodes-base.stopAndError",
  "typeVersion": 1,
  "position": [800, 500],
  "parameters": {
    "errorMessage": "Processing failed: {{ $json.error }}"
  }
}
```

## Common Integrations

### Slack Message
```json
{
  "id": "slack-1",
  "name": "Send Slack Message",
  "type": "n8n-nodes-base.slack",
  "typeVersion": 2.2,
  "position": [700, 300],
  "parameters": {
    "resource": "message",
    "operation": "post",
    "channel": {
      "mode": "name",
      "value": "#notifications"
    },
    "messageType": "text",
    "text": "={{ $json.message }}"
  },
  "credentials": {
    "slackApi": {
      "id": "credential-id",
      "name": "Slack account"
    }
  }
}
```

### Google Sheets Append
```json
{
  "id": "sheets-1",
  "name": "Add to Sheet",
  "type": "n8n-nodes-base.googleSheets",
  "typeVersion": 4.4,
  "position": [700, 300],
  "parameters": {
    "operation": "appendOrUpdate",
    "documentId": {
      "mode": "list",
      "value": "spreadsheet-id"
    },
    "sheetName": {
      "mode": "list",
      "value": "Sheet1"
    },
    "columns": {
      "mappingMode": "autoMapInputData",
      "value": {}
    }
  }
}
```

### Database Query
```json
{
  "id": "postgres-1",
  "name": "Query Database",
  "type": "n8n-nodes-base.postgres",
  "typeVersion": 2.4,
  "position": [500, 300],
  "parameters": {
    "operation": "executeQuery",
    "query": "SELECT * FROM users WHERE status = 'active'"
  }
}
```

## Node Positioning Guidelines

```yaml
layout_patterns:
  horizontal_flow:
    trigger: [100, 300]
    step1: [300, 300]
    step2: [500, 300]
    step3: [700, 300]
    output: [900, 300]

  branching:
    trigger: [100, 300]
    decision: [300, 300]
    branch_a: [500, 200]
    branch_b: [500, 400]
    merge: [700, 300]

  parallel:
    trigger: [100, 300]
    split: [300, 300]
    path_a: [500, 200]
    path_b: [500, 400]
    merge: [700, 300]

spacing:
  horizontal: 200
  vertical: 100-200
```
