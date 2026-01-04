---
name: n8n-workflow-manager
description: "Manage n8n workflows: list, filter, update, delete, organize with tags. Use when user asks to 'list workflows', 'update workflow', 'workflow status', 'organize workflows', 'tag workflows', or needs to manage existing n8n automations."
version: 1.0.0
license: MIT
---

# n8n Workflow Manager

Comprehensive skill for managing existing n8n workflows through the n8n MCP server.

## Activation Triggers

- "list my workflows"
- "show workflow status"
- "update workflow settings"
- "organize workflows with tags"
- "delete old workflows"
- "find workflows by tag"
- "workflow inventory"
- "modify workflow"

## Capabilities

### Workflow CRUD Operations
- List all workflows with filtering
- Get workflow details and structure
- Update workflow configurations
- Delete workflows safely
- Organize with tags

### Workflow Analysis
- View workflow structure
- Analyze node composition
- Check active/inactive status
- Review execution history

### Batch Operations
- Filter by status (active/inactive)
- Filter by tags
- Bulk tag management
- Workflow inventory reports

## MCP Tools Available

| Tool | Operation | Usage |
|------|-----------|-------|
| `n8n_list_workflows` | List | Get workflow inventory |
| `n8n_get_workflow` | Read | Full workflow JSON |
| `n8n_get_workflow_details` | Read | Details with metadata |
| `n8n_get_workflow_structure` | Read | Nodes and connections only |
| `n8n_get_workflow_minimal` | Read | ID, name, status only |
| `n8n_update_full_workflow` | Update | Complete workflow replacement |
| `n8n_update_partial_workflow` | Update | Incremental changes |
| `n8n_delete_workflow` | Delete | Remove workflow |
| `n8n_validate_workflow` | Validate | Check configuration |
| `n8n_autofix_workflow` | Fix | Auto-repair issues |

## Workflow Patterns

### List and Filter Workflows

```yaml
operation: list_workflows
steps:
  1. Call n8n_list_workflows with filters:
     - active: true/false (optional)
     - tags: ["tag1", "tag2"] (optional)
     - limit: number (default 100)

  2. Format results:
     - Group by status (active/inactive)
     - Show tags
     - Include last updated timestamp

  3. Handle pagination:
     - Check hasMore flag
     - Use cursor for next page
```

### Get Workflow Details

```yaml
operation: get_workflow
modes:
  minimal:
    tool: n8n_get_workflow_minimal
    returns: id, name, active, tags
    use_when: Quick status check

  structure:
    tool: n8n_get_workflow_structure
    returns: nodes, connections (no params)
    use_when: Understanding flow logic

  details:
    tool: n8n_get_workflow_details
    returns: metadata, version, stats
    use_when: Full analysis needed

  full:
    tool: n8n_get_workflow
    returns: Complete JSON
    use_when: Modification or backup
```

### Update Workflow (Partial)

```yaml
operation: partial_update
tool: n8n_update_partial_workflow
operations_types:
  - addNode: Add new node
  - removeNode: Remove node
  - updateNode: Modify node params
  - moveNode: Change position
  - enableNode: Enable node
  - disableNode: Disable node
  - addConnection: Connect nodes
  - removeConnection: Disconnect nodes
  - updateSettings: Workflow settings
  - updateName: Rename workflow
  - addTag: Add tag
  - removeTag: Remove tag

example:
  id: "workflow-id"
  operations:
    - type: "updateName"
      name: "New Workflow Name"
    - type: "addTag"
      tag: "production"
    - type: "updateSettings"
      settings:
        executionOrder: "v1"
        timezone: "America/New_York"
```

### Delete Workflow

```yaml
operation: delete_workflow
steps:
  1. Verify workflow exists:
     - Call n8n_get_workflow_minimal
     - Confirm ID and name

  2. Check for dependencies:
     - Review if called by other workflows
     - Check for active webhooks

  3. Recommend backup:
     - Get full workflow JSON
     - Suggest saving before delete

  4. Execute deletion:
     - Call n8n_delete_workflow
     - This action is PERMANENT

  5. Confirm removal:
     - Verify workflow no longer exists
```

## Tag Management

### Adding Tags

```yaml
add_tag:
  tool: n8n_update_partial_workflow
  operation:
    type: "addTag"
    tag: "tag-name"

  notes:
    - Tags are case-sensitive
    - Create new tags by using them
    - No separate tag management API
```

### Removing Tags

```yaml
remove_tag:
  tool: n8n_update_partial_workflow
  operation:
    type: "removeTag"
    tag: "tag-name"
```

### Filtering by Tags

```yaml
filter_by_tags:
  tool: n8n_list_workflows
  params:
    tags: ["production", "sync"]

  notes:
    - Exact match only
    - Multiple tags = AND logic
```

## Validation and Fix

### Validate Before Changes

```yaml
validate_workflow:
  tool: n8n_validate_workflow
  params:
    id: "workflow-id"
    options:
      profile: "runtime"  # or strict, ai-friendly, minimal
      validateNodes: true
      validateConnections: true
      validateExpressions: true

  interpret_results:
    errors: Must fix before activation
    warnings: Review but can proceed
    suggestions: Best practice improvements
```

### Auto-Fix Common Issues

```yaml
autofix_workflow:
  tool: n8n_autofix_workflow
  params:
    id: "workflow-id"
    applyFixes: false  # Preview first
    confidenceThreshold: "medium"
    fixTypes:
      - expression-format
      - typeversion-correction
      - error-output-config
      - webhook-missing-path

  workflow:
    1. Preview with applyFixes: false
    2. Review proposed changes
    3. Apply with applyFixes: true
    4. Re-validate to confirm
```

## Error Handling

### Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| 404 Not Found | Invalid workflow ID | Verify ID with list |
| 409 Conflict | Concurrent modification | Retry with fresh data |
| 422 Unprocessable | Invalid update data | Check operation format |
| 500 Server Error | n8n internal error | Check n8n logs |

### Safe Update Pattern

```yaml
safe_update:
  1. Get current state:
     tool: n8n_get_workflow

  2. Validate planned changes:
     tool: validate_workflow (locally)

  3. Apply changes:
     tool: n8n_update_partial_workflow
     params:
       validateOnly: true  # Dry run first

  4. If validation passes:
     tool: n8n_update_partial_workflow
     params:
       validateOnly: false  # Apply for real

  5. Verify result:
     tool: n8n_get_workflow_minimal
```

## Best Practices

### Before Modifications
1. Always get current workflow state first
2. Use partial updates over full replacements
3. Validate changes before applying
4. Consider creating backup

### Tag Organization
- Use consistent naming conventions
- Consider environment tags: dev, staging, production
- Use category tags: sync, notification, data-processing
- Include owner/team tags for large organizations

### Workflow Naming
- Use descriptive names
- Include purpose: "Customer Data Sync"
- Consider prefixes for grouping
- Avoid special characters

## Limitations

### Cannot Do via API
- Activate/deactivate workflows (manual UI only)
- Execute workflows directly (webhook only)
- Manage credentials
- Stop running executions

### Workarounds
- **Activation**: Document requirement for manual activation
- **Execution**: Ensure webhook nodes exist for triggering
- **Credentials**: Provide credential setup instructions

## Related Skills

- `n8n-workflow-builder` - Create new workflows
- `n8n-troubleshooter` - Debug workflow issues
- `n8n-integration-patterns` - Best practices

## Reference Files

- `@workflow-lifecycle.md` - Workflow states and transitions
- `@validation-guide.md` - Validation rules and profiles
- `@autofix-patterns.md` - Auto-fix capabilities
