# n8n Workflow Examples

Ready-to-use workflow patterns and examples for common integration scenarios.

## Quick Start Examples

### 1. Simple Webhook to Slack

Receive webhook, send message to Slack.

```json
{
  "name": "Webhook to Slack",
  "nodes": [
    {
      "id": "webhook-1",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [100, 300],
      "parameters": {
        "httpMethod": "POST",
        "path": "notify-slack"
      },
      "webhookId": "notify-slack-webhook"
    },
    {
      "id": "slack-1",
      "name": "Slack",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 2.2,
      "position": [300, 300],
      "parameters": {
        "resource": "message",
        "operation": "post",
        "channel": "{{ $json.channel || 'general' }}",
        "text": "{{ $json.message }}"
      }
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{ "node": "Slack", "type": "main", "index": 0 }]]
    }
  }
}
```

**Usage**:
```bash
curl -X POST https://n8n.example.com/webhook/notify-slack \
  -H "Content-Type: application/json" \
  -d '{"channel": "#alerts", "message": "Hello from webhook!"}'
```

### 2. Scheduled Data Sync

Sync data from API to database on schedule.

```json
{
  "name": "Daily Data Sync",
  "nodes": [
    {
      "id": "schedule-1",
      "name": "Schedule",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [100, 300],
      "parameters": {
        "rule": {
          "interval": [{ "field": "cronExpression", "expression": "0 6 * * *" }]
        }
      }
    },
    {
      "id": "http-1",
      "name": "Fetch Data",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [300, 300],
      "parameters": {
        "method": "GET",
        "url": "https://api.example.com/data",
        "options": {
          "pagination": {
            "paginationMode": "off"
          }
        }
      }
    },
    {
      "id": "postgres-1",
      "name": "Upsert to DB",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.4,
      "position": [500, 300],
      "parameters": {
        "operation": "upsert",
        "table": "synced_data",
        "columns": "id, name, updated_at",
        "conflictColumns": "id"
      }
    }
  ],
  "connections": {
    "Schedule": {
      "main": [[{ "node": "Fetch Data", "type": "main", "index": 0 }]]
    },
    "Fetch Data": {
      "main": [[{ "node": "Upsert to DB", "type": "main", "index": 0 }]]
    }
  }
}
```

### 3. Form Handler with Validation

Process form submissions with validation.

```json
{
  "name": "Form Handler",
  "nodes": [
    {
      "id": "webhook-1",
      "name": "Form Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [100, 300],
      "parameters": {
        "httpMethod": "POST",
        "path": "submit-form",
        "responseMode": "responseNode"
      }
    },
    {
      "id": "code-1",
      "name": "Validate",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [300, 300],
      "parameters": {
        "jsCode": "const errors = [];\n\nif (!$json.email?.includes('@')) {\n  errors.push('Invalid email');\n}\n\nif (!$json.name?.trim()) {\n  errors.push('Name required');\n}\n\nreturn [{ json: { ...item.json, valid: errors.length === 0, errors } }];"
      }
    },
    {
      "id": "if-1",
      "name": "Is Valid?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [500, 300],
      "parameters": {
        "conditions": {
          "boolean": [{ "value1": "={{ $json.valid }}", "value2": true }]
        }
      }
    },
    {
      "id": "respond-success",
      "name": "Success Response",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [700, 200],
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ { success: true, message: 'Form submitted' } }}"
      }
    },
    {
      "id": "respond-error",
      "name": "Error Response",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [700, 400],
      "parameters": {
        "respondWith": "json",
        "responseCode": 400,
        "responseBody": "={{ { success: false, errors: $json.errors } }}"
      }
    }
  ],
  "connections": {
    "Form Webhook": {
      "main": [[{ "node": "Validate", "type": "main", "index": 0 }]]
    },
    "Validate": {
      "main": [[{ "node": "Is Valid?", "type": "main", "index": 0 }]]
    },
    "Is Valid?": {
      "main": [
        [{ "node": "Success Response", "type": "main", "index": 0 }],
        [{ "node": "Error Response", "type": "main", "index": 0 }]
      ]
    }
  }
}
```

## Integration Patterns

### CRM to Email Marketing Sync

Sync contacts from CRM to email platform.

```json
{
  "name": "CRM to Email Sync",
  "nodes": [
    {
      "id": "schedule-1",
      "name": "Hourly Sync",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [100, 300],
      "parameters": {
        "rule": {
          "interval": [{ "field": "hours", "hoursInterval": 1 }]
        }
      }
    },
    {
      "id": "crm-1",
      "name": "Get New Contacts",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [300, 300],
      "parameters": {
        "method": "GET",
        "url": "https://crm.example.com/api/contacts",
        "qs": {
          "modified_since": "={{ $now.minus({hours: 1}).toISO() }}"
        }
      }
    },
    {
      "id": "transform-1",
      "name": "Transform Data",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [500, 300],
      "parameters": {
        "jsCode": "return items.map(item => ({\n  json: {\n    email: item.json.email,\n    firstName: item.json.first_name,\n    lastName: item.json.last_name,\n    tags: item.json.status === 'customer' ? ['customer'] : ['lead']\n  }\n}));"
      }
    },
    {
      "id": "batch-1",
      "name": "Batch 50",
      "type": "n8n-nodes-base.splitInBatches",
      "typeVersion": 3,
      "position": [700, 300],
      "parameters": {
        "batchSize": 50
      }
    },
    {
      "id": "email-1",
      "name": "Upsert to Email Platform",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [900, 300],
      "parameters": {
        "method": "POST",
        "url": "https://email.example.com/api/subscribers/batch",
        "body": "={{ $json }}"
      }
    }
  ],
  "connections": {
    "Hourly Sync": {
      "main": [[{ "node": "Get New Contacts", "type": "main", "index": 0 }]]
    },
    "Get New Contacts": {
      "main": [[{ "node": "Transform Data", "type": "main", "index": 0 }]]
    },
    "Transform Data": {
      "main": [[{ "node": "Batch 50", "type": "main", "index": 0 }]]
    },
    "Batch 50": {
      "main": [
        [{ "node": "Upsert to Email Platform", "type": "main", "index": 0 }],
        []
      ]
    },
    "Upsert to Email Platform": {
      "main": [[{ "node": "Batch 50", "type": "main", "index": 0 }]]
    }
  }
}
```

### Order Processing Pipeline

Process incoming orders with validation and notifications.

```json
{
  "name": "Order Processing",
  "nodes": [
    {
      "id": "webhook-1",
      "name": "Order Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [100, 300],
      "parameters": {
        "httpMethod": "POST",
        "path": "new-order"
      }
    },
    {
      "id": "validate-1",
      "name": "Validate Order",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [300, 300],
      "parameters": {
        "jsCode": "const order = $json;\nconst errors = [];\n\nif (!order.items?.length) errors.push('No items');\nif (!order.customer?.email) errors.push('No customer email');\nif (!order.total || order.total <= 0) errors.push('Invalid total');\n\nreturn [{ json: { ...order, isValid: errors.length === 0, validationErrors: errors } }];"
      }
    },
    {
      "id": "if-valid",
      "name": "Is Valid?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [500, 300],
      "parameters": {
        "conditions": {
          "boolean": [{ "value1": "={{ $json.isValid }}", "value2": true }]
        }
      }
    },
    {
      "id": "save-order",
      "name": "Save to Database",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.4,
      "position": [700, 200],
      "parameters": {
        "operation": "insert",
        "table": "orders"
      }
    },
    {
      "id": "notify-customer",
      "name": "Email Confirmation",
      "type": "n8n-nodes-base.emailSend",
      "typeVersion": 2.1,
      "position": [900, 200],
      "parameters": {
        "toEmail": "={{ $json.customer.email }}",
        "subject": "Order Confirmed #{{ $json.orderId }}",
        "text": "Thank you for your order!"
      }
    },
    {
      "id": "notify-slack",
      "name": "Notify Team",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 2.2,
      "position": [900, 300],
      "parameters": {
        "channel": "#orders",
        "text": "New order #{{ $json.orderId }} - ${{ $json.total }}"
      }
    },
    {
      "id": "log-error",
      "name": "Log Invalid Order",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.4,
      "position": [700, 400],
      "parameters": {
        "operation": "insert",
        "table": "order_errors"
      }
    }
  ],
  "connections": {
    "Order Webhook": {
      "main": [[{ "node": "Validate Order", "type": "main", "index": 0 }]]
    },
    "Validate Order": {
      "main": [[{ "node": "Is Valid?", "type": "main", "index": 0 }]]
    },
    "Is Valid?": {
      "main": [
        [{ "node": "Save to Database", "type": "main", "index": 0 }],
        [{ "node": "Log Invalid Order", "type": "main", "index": 0 }]
      ]
    },
    "Save to Database": {
      "main": [
        [
          { "node": "Email Confirmation", "type": "main", "index": 0 },
          { "node": "Notify Team", "type": "main", "index": 0 }
        ]
      ]
    }
  }
}
```

## AI Agent Examples

### Customer Support Bot

AI agent with knowledge base and ticket creation.

```json
{
  "name": "Support Bot",
  "nodes": [
    {
      "id": "webhook-1",
      "name": "Chat Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [100, 300],
      "parameters": {
        "httpMethod": "POST",
        "path": "support-chat",
        "responseMode": "responseNode"
      }
    },
    {
      "id": "agent-1",
      "name": "Support Agent",
      "type": "@n8n/n8n-nodes-langchain.agent",
      "typeVersion": 1.6,
      "position": [400, 300],
      "parameters": {
        "promptType": "define",
        "text": "={{ $json.message }}",
        "options": {
          "systemMessage": "You are a helpful customer support agent. Answer questions based on the knowledge base. If you cannot help, offer to create a support ticket."
        }
      }
    },
    {
      "id": "llm-1",
      "name": "OpenAI",
      "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
      "typeVersion": 1,
      "position": [400, 500],
      "parameters": {
        "model": "gpt-4",
        "options": {
          "temperature": 0.7
        }
      }
    },
    {
      "id": "memory-1",
      "name": "Memory",
      "type": "@n8n/n8n-nodes-langchain.memoryBufferWindow",
      "typeVersion": 1.2,
      "position": [400, 100],
      "parameters": {
        "sessionIdType": "customKey",
        "sessionKey": "={{ $json.sessionId }}",
        "contextWindowLength": 10
      }
    },
    {
      "id": "respond-1",
      "name": "Send Response",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [700, 300],
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ { response: $json.output, sessionId: $json.sessionId } }}"
      }
    }
  ],
  "connections": {
    "Chat Webhook": {
      "main": [[{ "node": "Support Agent", "type": "main", "index": 0 }]]
    },
    "OpenAI": {
      "ai_languageModel": [[{ "node": "Support Agent", "type": "ai_languageModel", "index": 0 }]]
    },
    "Memory": {
      "ai_memory": [[{ "node": "Support Agent", "type": "ai_memory", "index": 0 }]]
    },
    "Support Agent": {
      "main": [[{ "node": "Send Response", "type": "main", "index": 0 }]]
    }
  }
}
```

### Data Extraction Agent

AI agent that extracts structured data from documents.

```json
{
  "name": "Document Extractor",
  "nodes": [
    {
      "id": "webhook-1",
      "name": "Document Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [100, 300],
      "parameters": {
        "httpMethod": "POST",
        "path": "extract-data"
      }
    },
    {
      "id": "agent-1",
      "name": "Extractor Agent",
      "type": "@n8n/n8n-nodes-langchain.agent",
      "typeVersion": 1.6,
      "position": [400, 300],
      "parameters": {
        "promptType": "define",
        "text": "Extract the following information from this document:\n{{ $json.document }}\n\nExtract: company name, date, total amount, line items"
      }
    },
    {
      "id": "llm-1",
      "name": "OpenAI",
      "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
      "typeVersion": 1,
      "position": [400, 500],
      "parameters": {
        "model": "gpt-4",
        "options": {
          "temperature": 0
        }
      }
    },
    {
      "id": "parser-1",
      "name": "Structured Output",
      "type": "@n8n/n8n-nodes-langchain.outputParserStructured",
      "typeVersion": 1,
      "position": [600, 500],
      "parameters": {
        "schemaType": "manual",
        "inputSchema": {
          "type": "object",
          "properties": {
            "companyName": { "type": "string" },
            "date": { "type": "string" },
            "totalAmount": { "type": "number" },
            "lineItems": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "description": { "type": "string" },
                  "quantity": { "type": "number" },
                  "price": { "type": "number" }
                }
              }
            }
          }
        }
      }
    }
  ],
  "connections": {
    "Document Webhook": {
      "main": [[{ "node": "Extractor Agent", "type": "main", "index": 0 }]]
    },
    "OpenAI": {
      "ai_languageModel": [[{ "node": "Extractor Agent", "type": "ai_languageModel", "index": 0 }]]
    },
    "Structured Output": {
      "ai_outputParser": [[{ "node": "Extractor Agent", "type": "ai_outputParser", "index": 0 }]]
    }
  }
}
```

## Error Handling Examples

### Workflow with Full Error Handling

```json
{
  "name": "Robust API Integration",
  "nodes": [
    {
      "id": "schedule-1",
      "name": "Schedule",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [100, 300],
      "parameters": {
        "rule": {
          "interval": [{ "field": "minutes", "minutesInterval": 15 }]
        }
      }
    },
    {
      "id": "http-1",
      "name": "API Call",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [300, 300],
      "parameters": {
        "method": "GET",
        "url": "https://api.example.com/data",
        "options": {
          "timeout": 30000
        }
      },
      "onError": "continueErrorOutput"
    },
    {
      "id": "if-success",
      "name": "Check Success",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [500, 200],
      "parameters": {
        "conditions": {
          "number": [{ "value1": "={{ $json.statusCode || 200 }}", "operation": "smaller", "value2": 400 }]
        }
      }
    },
    {
      "id": "process-1",
      "name": "Process Data",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [700, 100],
      "parameters": {
        "jsCode": "// Process successful response\nreturn items;"
      }
    },
    {
      "id": "retry-logic",
      "name": "Retry Logic",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [700, 300],
      "parameters": {
        "jsCode": "const retryCount = ($json.retryCount || 0) + 1;\nconst maxRetries = 3;\nconst shouldRetry = retryCount < maxRetries && $json.statusCode >= 500;\n\nreturn [{ json: { shouldRetry, retryCount, error: $json.error } }];"
      }
    },
    {
      "id": "if-retry",
      "name": "Should Retry?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [900, 300],
      "parameters": {
        "conditions": {
          "boolean": [{ "value1": "={{ $json.shouldRetry }}", "value2": true }]
        }
      }
    },
    {
      "id": "wait-1",
      "name": "Backoff Wait",
      "type": "n8n-nodes-base.wait",
      "typeVersion": 1.1,
      "position": [1100, 200],
      "parameters": {
        "amount": "={{ Math.pow(2, $json.retryCount) * 1000 }}",
        "unit": "milliseconds"
      }
    },
    {
      "id": "alert-1",
      "name": "Alert on Failure",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 2.2,
      "position": [1100, 400],
      "parameters": {
        "channel": "#alerts",
        "text": "API Integration Failed after 3 retries: {{ $json.error }}"
      }
    }
  ],
  "connections": {
    "Schedule": {
      "main": [[{ "node": "API Call", "type": "main", "index": 0 }]]
    },
    "API Call": {
      "main": [
        [{ "node": "Check Success", "type": "main", "index": 0 }],
        [{ "node": "Retry Logic", "type": "main", "index": 0 }]
      ]
    },
    "Check Success": {
      "main": [
        [{ "node": "Process Data", "type": "main", "index": 0 }],
        [{ "node": "Retry Logic", "type": "main", "index": 0 }]
      ]
    },
    "Retry Logic": {
      "main": [[{ "node": "Should Retry?", "type": "main", "index": 0 }]]
    },
    "Should Retry?": {
      "main": [
        [{ "node": "Backoff Wait", "type": "main", "index": 0 }],
        [{ "node": "Alert on Failure", "type": "main", "index": 0 }]
      ]
    },
    "Backoff Wait": {
      "main": [[{ "node": "API Call", "type": "main", "index": 0 }]]
    }
  }
}
```

## Usage Tips

### Creating Workflows from Examples

1. Copy the JSON example
2. Use `n8n_create_workflow` tool
3. Update node parameters for your use case
4. Configure required credentials
5. Validate with `n8n_validate_workflow`
6. Activate workflow manually in UI

### Customizing Examples

```yaml
common_customizations:
  - Update webhook paths
  - Change API URLs and endpoints
  - Modify Slack channels
  - Adjust schedule intervals
  - Update database tables/columns
  - Change validation rules
  - Customize error messages
```

### Testing Workflows

```yaml
testing_approach:
  1. Create workflow with Manual Trigger
  2. Test with sample data in UI
  3. Replace trigger with production trigger
  4. Test end-to-end with webhook
  5. Monitor executions for errors
  6. Activate for production use
```
