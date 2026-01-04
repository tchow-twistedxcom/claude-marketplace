# n8n Trigger Nodes Reference

Complete guide to trigger nodes for workflow entry points.

## Trigger Categories

### Manual Triggers
- **Manual Trigger** - UI button execution
- **Execute Workflow** - Called by other workflows

### HTTP Triggers
- **Webhook** - HTTP endpoint
- **Webhook Trigger** - Alternative webhook

### Scheduled Triggers
- **Schedule Trigger** - Cron/interval execution
- **Cron** - Cron expression based

### Event Triggers
- **Application-specific triggers** (Slack, GitHub, etc.)
- **Polling triggers** - Check for changes

## Webhook Node

### Basic Configuration
```json
{
  "id": "webhook-1",
  "name": "Webhook",
  "type": "n8n-nodes-base.webhook",
  "typeVersion": 2,
  "position": [100, 300],
  "parameters": {
    "httpMethod": "POST",
    "path": "my-webhook",
    "options": {}
  },
  "webhookId": "unique-webhook-id"
}
```

### HTTP Methods
```yaml
methods:
  GET: Read/query data
  POST: Create/submit data
  PUT: Update/replace data
  PATCH: Partial update
  DELETE: Remove data
  HEAD: Headers only
```

### Response Modes
```json
{
  "parameters": {
    "responseMode": "onReceived"
  }
}
// Options:
// "onReceived" - Respond immediately
// "lastNode" - Respond after last node
// "responseNode" - Use Respond to Webhook node
```

### Webhook Authentication
```json
{
  "parameters": {
    "authentication": "basicAuth",
    "options": {
      "rawBody": true
    }
  },
  "credentials": {
    "httpBasicAuth": {
      "id": "credential-id",
      "name": "Webhook Auth"
    }
  }
}
```

### Custom Headers Response
```json
{
  "parameters": {
    "options": {
      "responseHeaders": {
        "entries": [
          {
            "name": "X-Custom-Header",
            "value": "custom-value"
          }
        ]
      }
    }
  }
}
```

### Webhook URLs
```yaml
production:
  format: "https://your-n8n.com/webhook/<path>"
  requires: Workflow active

test:
  format: "https://your-n8n.com/webhook-test/<path>"
  requires: Nothing, always available

path_options:
  static: "my-endpoint"
  uuid: "abc123-def456-..."
  custom: "customers/create"
```

## Schedule Trigger

### Cron Expression
```json
{
  "id": "schedule-1",
  "name": "Schedule Trigger",
  "type": "n8n-nodes-base.scheduleTrigger",
  "typeVersion": 1.2,
  "position": [100, 300],
  "parameters": {
    "rule": {
      "interval": [
        {
          "field": "cronExpression",
          "expression": "0 9 * * *"
        }
      ]
    }
  }
}
```

### Common Cron Patterns
```yaml
cron_expressions:
  "0 * * * *": Every hour at minute 0
  "*/15 * * * *": Every 15 minutes
  "0 9 * * *": Daily at 9 AM
  "0 9 * * 1-5": Weekdays at 9 AM
  "0 0 * * 0": Weekly on Sunday midnight
  "0 0 1 * *": Monthly on 1st at midnight

cron_format: "minute hour day-of-month month day-of-week"
```

### Interval Mode
```json
{
  "parameters": {
    "rule": {
      "interval": [
        {
          "field": "minutes",
          "minutesInterval": 30
        }
      ]
    }
  }
}
```

### Hours Mode
```json
{
  "parameters": {
    "rule": {
      "interval": [
        {
          "field": "hours",
          "hoursInterval": 2,
          "triggerAtMinute": 0
        }
      ]
    }
  }
}
```

## Manual Trigger

### Basic Setup
```json
{
  "id": "manual-1",
  "name": "When clicking Test workflow",
  "type": "n8n-nodes-base.manualTrigger",
  "typeVersion": 1,
  "position": [100, 300],
  "parameters": {}
}
```

### Use Cases
```yaml
use_cases:
  - Testing workflow logic
  - On-demand execution
  - Admin operations
  - Development/debugging
```

## Error Trigger

### Error Handler Setup
```json
{
  "id": "error-1",
  "name": "Error Trigger",
  "type": "n8n-nodes-base.errorTrigger",
  "typeVersion": 1,
  "position": [100, 500],
  "parameters": {}
}
```

### Available Error Data
```javascript
// Error information available
{{ $json.execution.id }}
{{ $json.execution.url }}
{{ $json.execution.error.message }}
{{ $json.execution.error.node.name }}
{{ $json.workflow.id }}
{{ $json.workflow.name }}
```

### Error Handling Workflow
```yaml
pattern:
  nodes:
    - Error Trigger
    - Format Error Message
    - Send Notification (Slack/Email)
    - Log to Database

  purpose:
    - Centralized error handling
    - Notifications on failures
    - Error logging and tracking
```

## Application Triggers

### Slack Trigger
```json
{
  "id": "slack-trigger-1",
  "name": "Slack Trigger",
  "type": "n8n-nodes-base.slackTrigger",
  "typeVersion": 1,
  "position": [100, 300],
  "parameters": {
    "events": ["message"],
    "channel": "general"
  }
}
```

### GitHub Trigger
```json
{
  "id": "github-trigger-1",
  "name": "GitHub Trigger",
  "type": "n8n-nodes-base.githubTrigger",
  "typeVersion": 1,
  "position": [100, 300],
  "parameters": {
    "owner": "username",
    "repository": "repo-name",
    "events": ["push", "pull_request"]
  }
}
```

### Generic Polling Pattern
```yaml
polling_triggers:
  concept: Check for changes periodically

  examples:
    - Email IMAP: Check for new emails
    - RSS: Check for new items
    - Database: Check for new records

  configuration:
    pollInterval: Check frequency
    filters: What to look for
```

## Trigger Selection Guide

### Use Webhook When
```yaml
scenarios:
  - External system sends data
  - API endpoint needed
  - Real-time processing required
  - Third-party integrations calling n8n
```

### Use Schedule When
```yaml
scenarios:
  - Periodic data sync
  - Scheduled reports
  - Batch processing
  - Maintenance tasks
  - Regular API polling
```

### Use App Trigger When
```yaml
scenarios:
  - Native integration available
  - Event-driven workflows
  - Real-time app events
  - Simplified authentication
```

### Use Error Trigger When
```yaml
scenarios:
  - Centralized error handling
  - Failure notifications
  - Error logging
  - Retry orchestration
```

## Trigger Best Practices

### Webhook Security
```yaml
recommendations:
  - Use authentication
  - Validate input data
  - Implement rate limiting
  - Use HTTPS only
  - Unique webhook paths
```

### Schedule Optimization
```yaml
recommendations:
  - Avoid overlapping executions
  - Consider timezone
  - Use appropriate intervals
  - Handle long-running tasks
  - Implement idempotency
```

### Error Handling
```yaml
recommendations:
  - Always have error handling
  - Log execution details
  - Notify on critical failures
  - Implement retry logic
  - Set appropriate timeouts
```

## Trigger Positioning
```yaml
layout:
  trigger_position: [100, 300]
  first_node: [300, 300]

  notes:
    - Trigger always leftmost
    - Single trigger per workflow
    - Clear flow direction left to right
```
