# n8n Workflow Lifecycle

Understanding workflow states, transitions, and management patterns.

## Workflow States

### Creation State
```
Created (Inactive)
├── No executions possible
├── Can be edited freely
├── Validation not required
└── Webhook URLs not active
```

### Active State
```
Active
├── Triggers operational
├── Webhooks accepting requests
├── Scheduled triggers running
├── Executions being logged
└── Limited editing (pause recommended)
```

### Inactive State
```
Inactive
├── All triggers disabled
├── Webhooks return 404
├── No new executions
├── Existing executions continue
└── Full editing available
```

## State Transitions

### Activation Flow
```
Inactive → Active
├── Requires: Manual UI toggle
├── Cannot: Use API to activate
├── Validates: Basic structure
├── Initializes: Trigger nodes
└── Registers: Webhook endpoints
```

### Deactivation Flow
```
Active → Inactive
├── Requires: Manual UI toggle
├── Stops: New trigger events
├── Completes: In-progress executions
├── Unregisters: Webhooks
└── Preserves: Configuration
```

## Workflow Versioning

### Version Tracking
n8n internally tracks workflow versions:

```yaml
version:
  format: incrementing integer
  stored: in workflow record
  updated: on each save

history:
  available: Limited
  restore: Manual backup required
```

### Best Practices for Versioning
1. **Manual Backups**: Export JSON before major changes
2. **Git Integration**: Store workflows in version control
3. **Naming Convention**: Include version in description
4. **Change Log**: Document changes in workflow notes

## Workflow Execution Modes

### Manual Execution
```yaml
mode: manual
trigger: UI "Execute" button
scope: Full workflow or selected node
data: Uses test data or manual input
```

### Webhook Execution
```yaml
mode: webhook
trigger: HTTP request to webhook URL
scope: Full workflow
data: From HTTP request body
requires: Workflow must be active
```

### Scheduled Execution
```yaml
mode: schedule
trigger: Cron or interval trigger
scope: Full workflow
data: May include static or dynamic input
requires: Workflow must be active
```

### Triggered Execution
```yaml
mode: trigger
trigger: External event (email, file, etc.)
scope: Full workflow
data: From trigger event
requires: Workflow must be active
```

## Workflow Settings

### Execution Settings
```yaml
settings:
  executionOrder: v0|v1  # v1 recommended
  saveDataErrorExecution: all|none
  saveDataSuccessExecution: all|none
  saveExecutionProgress: true|false
  saveManualExecutions: true|false
  executionTimeout: number (seconds)
  timezone: "America/New_York"
```

### Error Handling Settings
```yaml
errorWorkflow:
  id: "error-handler-workflow-id"
  function: Called on workflow failure
  receives: Error details and context
```

## Execution Order

### v0 (Legacy)
- Breadth-first execution
- Parallel when possible
- May cause timing issues

### v1 (Recommended)
- Depth-first execution
- More predictable flow
- Better for sequential logic

## Workflow Ownership

### User Context
```yaml
ownership:
  creator: User who created
  updater: Last user to modify
  project: Project ID (enterprise)

permissions:
  via: n8n RBAC (enterprise)
  api: Uses API key owner's permissions
```

## Workflow Limits

### Per-Instance Limits
```yaml
typical_limits:
  max_nodes: Varies by plan
  max_workflows: Varies by plan
  execution_timeout: Configurable
  concurrent_executions: Plan dependent
```

### API Rate Limits
```yaml
api_limits:
  calls_per_minute: Plan dependent
  batch_operations: Not supported natively
  pagination: Required for large lists
```

## Migration Patterns

### Export Workflow
```yaml
export:
  method: n8n_get_workflow
  returns: Complete JSON
  includes:
    - Nodes and parameters
    - Connections
    - Settings
  excludes:
    - Credentials (references only)
    - Execution history
    - Active state
```

### Import Workflow
```yaml
import:
  method: n8n_create_workflow
  requires:
    - Valid JSON structure
    - Unique node IDs
    - Valid connections
  creates:
    - New workflow (inactive)
    - New workflow ID
  needs_manual:
    - Credential configuration
    - Activation
```

### Environment Migration
```yaml
dev_to_prod:
  1. Export from dev (get_workflow)
  2. Modify settings if needed:
     - Update URLs
     - Change webhook paths
     - Adjust timeouts
  3. Import to prod (create_workflow)
  4. Configure credentials manually
  5. Test in inactive state
  6. Activate manually
```

## Cleanup Patterns

### Identifying Unused Workflows
```yaml
unused_indicators:
  - No executions in 90+ days
  - Inactive status
  - No scheduled triggers
  - Orphan webhooks
```

### Safe Deletion Process
```yaml
safe_delete:
  1. Check last execution date
  2. Verify not called by other workflows
  3. Export backup JSON
  4. Confirm with owner/team
  5. Delete workflow
  6. Verify dependent systems
```

## Monitoring Workflow Health

### Health Indicators
```yaml
healthy:
  - Regular successful executions
  - No recent errors
  - Expected execution frequency
  - All nodes functioning

unhealthy:
  - Consecutive failures
  - No recent executions
  - Timeout errors
  - Missing credentials
```

### Maintenance Tasks
```yaml
regular_maintenance:
  - Review execution logs
  - Check for failed executions
  - Validate after n8n updates
  - Update deprecated nodes
  - Clean up test workflows
```
