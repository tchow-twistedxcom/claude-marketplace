# n8n Workflow Auto-Fix Patterns

Automated repair capabilities, confidence levels, and fix application patterns.

## Auto-Fix Overview

The `n8n_autofix_workflow` tool can automatically repair common workflow issues with varying confidence levels.

### Supported Fix Types

| Fix Type | Description | Confidence |
|----------|-------------|------------|
| `expression-format` | Fix expression syntax | High |
| `typeversion-correction` | Update node versions | Medium |
| `error-output-config` | Configure error outputs | High |
| `node-type-correction` | Fix node type references | Medium |
| `webhook-missing-path` | Add missing webhook paths | High |

## Expression Format Fixes

### Missing Closing Brackets
```yaml
issue: "{{ $json.data.items }"
fix: "{{ $json.data.items }}"
confidence: high
detection: Unbalanced brackets
```

### Missing Opening Brackets
```yaml
issue: "$json.data.items }}"
fix: "{{ $json.data.items }}"
confidence: high
detection: Orphan closing brackets
```

### Double Bracket Issues
```yaml
issue: "{{{{ $json.data }}}}"
fix: "{{ $json.data }}"
confidence: medium
detection: Extra brackets detected
```

### Whitespace Normalization
```yaml
issue: "{{$json.data}}"
fix: "{{ $json.data }}"
confidence: high
note: Adds standard spacing
```

## TypeVersion Corrections

### Outdated Version Detection
```yaml
detection:
  method: Compare against current node registry
  checks:
    - Node type exists
    - Version is below current
    - Migration path available

fix_process:
  1. Identify current recommended version
  2. Check compatibility
  3. Update typeVersion field
  4. May update related parameters
```

### Common Version Updates
```yaml
examples:
  httpRequest:
    old: 3
    current: 4.2
    confidence: medium
    notes: Parameter structure may differ

  slack:
    old: 1
    current: 2.2
    confidence: medium
    notes: Auth configuration changes

  code:
    old: 1
    current: 2
    confidence: high
    notes: Minor syntax updates
```

### Version Update Risks
```yaml
low_risk:
  - Minor version bumps
  - No parameter changes
  - Same authentication
  confidence: high

medium_risk:
  - Major version bumps
  - Some parameter renames
  - Same functionality
  confidence: medium

high_risk:
  - Breaking changes
  - New required parameters
  - Changed behavior
  confidence: low (manual recommended)
```

## Error Output Configuration

### Missing Error Output
```yaml
issue: Node has no error handling output configured
fix:
  action: Add onError configuration
  default:
    onError: continueErrorOutput
  confidence: high
```

### Error Handler Pattern
```yaml
recommended_config:
  onError: continueErrorOutput

  benefits:
    - Workflow continues on node failure
    - Error data available for handling
    - Prevents complete workflow failure

  alternatives:
    continueRegularOutput: Ignore errors
    stopWorkflow: Halt on error
```

## Node Type Corrections

### Type Reference Fixes
```yaml
detection:
  - Node type not found in registry
  - Partial match with known types
  - Package prefix missing

examples:
  wrong: "slack"
  correct: "n8n-nodes-base.slack"
  confidence: medium

  wrong: "nodes-base.slac"
  correct: "n8n-nodes-base.slack"
  confidence: medium (typo detection)
```

### Package Prefix Normalization
```yaml
core_nodes:
  prefix: "n8n-nodes-base"
  example: "n8n-nodes-base.httpRequest"

langchain_nodes:
  prefix: "@n8n/n8n-nodes-langchain"
  example: "@n8n/n8n-nodes-langchain.openAi"

community_nodes:
  prefix: varies
  detection: Check installed packages
```

## Webhook Path Fixes

### Missing Path Detection
```yaml
issue: Webhook node has no path configured
detection:
  - path field empty or missing
  - httpMethod configured but no path

fix:
  action: Generate unique path
  format: "webhook-{uuid}"
  confidence: high
```

### Path Uniqueness
```yaml
generation:
  method: UUID-based
  ensures: No collision with existing webhooks
  format: "webhook-abc123-def456"
```

## Using Auto-Fix

### Preview Mode (Recommended First)
```javascript
mcp__n8n__n8n_autofix_workflow({
  id: "workflow-id",
  applyFixes: false,  // Preview only
  confidenceThreshold: "medium",
  fixTypes: [
    "expression-format",
    "typeversion-correction",
    "error-output-config"
  ]
})

// Returns proposed fixes without applying
```

### Apply Fixes
```javascript
mcp__n8n__n8n_autofix_workflow({
  id: "workflow-id",
  applyFixes: true,  // Apply changes
  confidenceThreshold: "high",  // Only high-confidence fixes
  maxFixes: 50
})
```

### Confidence Thresholds

| Threshold | Applies |
|-----------|---------|
| `high` | Only obvious, safe fixes |
| `medium` | Reasonable fixes with some risk |
| `low` | All detected fixes (review carefully) |

## Auto-Fix Workflow

### Recommended Process
```yaml
step_1_preview:
  action: Run with applyFixes: false
  review: Examine proposed changes
  decision: Proceed or adjust parameters

step_2_apply:
  action: Run with applyFixes: true
  monitor: Check for success/failure

step_3_validate:
  action: Run n8n_validate_workflow
  verify: All issues resolved
  check: No new issues introduced

step_4_test:
  action: Manual test execution
  verify: Workflow behaves correctly
```

### Handling Partial Fixes
```yaml
scenario: Some fixes applied, some failed

response:
  1. Note successfully applied fixes
  2. Identify failed fixes
  3. Manual resolution for failed items
  4. Re-validate after manual fixes
```

## Cannot Auto-Fix

### Manual Intervention Required

| Issue | Reason | Manual Action |
|-------|--------|---------------|
| Missing credentials | Security | Configure in n8n UI |
| Invalid URLs | Context-dependent | Provide correct URL |
| Missing required params | Unknown values | Configure settings |
| Logic errors | Requires understanding | Review and correct |
| Complex expressions | Semantic issues | Rewrite expression |

### Referral Pattern
```yaml
when_cannot_fix:
  message: "Cannot auto-fix: [issue description]"
  guidance:
    - What the issue is
    - Why it can't be automated
    - Steps for manual resolution
    - Related documentation
```

## Fix Result Interpretation

### Success Response
```yaml
result:
  status: "success"
  fixesApplied: 3
  fixes:
    - type: "expression-format"
      node: "Set"
      before: "{{ $json.name }"
      after: "{{ $json.name }}"
    - type: "typeversion-correction"
      node: "HTTP Request"
      before: 3
      after: 4.2
```

### Partial Success
```yaml
result:
  status: "partial"
  fixesApplied: 2
  fixesFailed: 1
  applied:
    - [successful fixes]
  failed:
    - type: "node-type-correction"
      node: "Unknown"
      reason: "Node type not found in registry"
```

### Failure Response
```yaml
result:
  status: "failed"
  reason: "Workflow validation failed after fixes"
  rollback: true  # Changes reverted
  recommendation: "Manual review required"
```

## Best Practices

### Before Auto-Fix
1. Back up workflow JSON
2. Review current validation errors
3. Understand what will be changed
4. Use preview mode first

### After Auto-Fix
1. Validate the fixed workflow
2. Test execution manually
3. Verify expected behavior
4. Document changes made

### When to Avoid Auto-Fix
- Critical production workflows
- Complex business logic
- Recent major n8n updates
- Unknown workflow purpose
