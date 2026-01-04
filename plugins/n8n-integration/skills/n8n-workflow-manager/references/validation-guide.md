# n8n Workflow Validation Guide

Comprehensive guide to workflow validation profiles, rules, and resolution patterns.

## Validation Profiles

### Minimal Profile
```yaml
profile: minimal
purpose: Quick checks for required fields only
checks:
  - Required node fields present
  - Basic connection validity
  - Trigger node exists
skips:
  - Expression validation
  - Type version checks
  - Best practice warnings
use_when:
  - Quick health check
  - Draft workflows
  - Development iteration
```

### Runtime Profile (Default)
```yaml
profile: runtime
purpose: Catches issues that would fail during execution
checks:
  - All minimal checks
  - Expression syntax
  - Connection type compatibility
  - Credential references valid
  - Node configuration complete
skips:
  - Style/formatting issues
  - Optimization suggestions
use_when:
  - Pre-activation validation
  - After modifications
  - Standard validation
```

### AI-Friendly Profile
```yaml
profile: ai-friendly
purpose: Optimized for AI agent tool usage
checks:
  - All runtime checks
  - AI tool connection validation
  - Parameter completeness for AI
  - Input/output schema validation
skips:
  - Manual interaction requirements
  - UI-specific settings
use_when:
  - AI agent workflows
  - Tool-connected nodes
  - Automated execution paths
```

### Strict Profile
```yaml
profile: strict
purpose: Maximum validation including best practices
checks:
  - All previous checks
  - Best practice compliance
  - Naming conventions
  - Error handling presence
  - Documentation completeness
includes:
  - Style warnings
  - Performance suggestions
  - Security recommendations
use_when:
  - Production deployment
  - Code review
  - Compliance requirements
```

## Validation Categories

### Node Validation
```yaml
node_checks:
  required_fields:
    - Node has valid type
    - Node has unique ID
    - Required parameters set
    - typeVersion is valid

  configuration:
    - Operation is valid for resource
    - Parameters match operation
    - Credentials referenced correctly

  compatibility:
    - Node type exists
    - Version supported
    - No deprecated features (warning)
```

### Connection Validation
```yaml
connection_checks:
  structure:
    - No orphan nodes (warning)
    - All connections have valid endpoints
    - No self-referencing connections

  flow:
    - At least one trigger node
    - No unreachable nodes
    - Circular dependencies handled

  types:
    - Output types match input requirements
    - AI tool connections valid
    - Error outputs configured
```

### Expression Validation
```yaml
expression_checks:
  syntax:
    - Brackets balanced {{ }}
    - Valid JavaScript in expressions
    - No undefined variables

  references:
    - $json paths exist
    - $node references valid
    - Function calls valid

  security:
    - No eval() usage
    - No dangerous functions
    - Input sanitization (warning)
```

## Common Validation Errors

### Node Errors

#### Missing Required Field
```yaml
error: "Missing required field: url"
severity: error
node_type: httpRequest
cause: URL not configured
fix:
  manual: Configure URL in node settings
  cannot_autofix: true
```

#### Invalid Credential Reference
```yaml
error: "Credential not found: slack_oauth2"
severity: error
cause: Credential deleted or renamed
fix:
  manual: Update credential in node settings
  cannot_autofix: true
```

#### Deprecated Node Version
```yaml
error: "typeVersion 3 is deprecated"
severity: warning
cause: Outdated node version
fix:
  autofix: Update typeVersion to current
  confidence: high
```

### Connection Errors

#### Orphan Node
```yaml
error: "Node 'Set' has no connections"
severity: warning
cause: Node not connected to workflow
fix:
  options:
    - Connect to appropriate node
    - Remove if unused
  cannot_autofix: true
```

#### Invalid Connection Type
```yaml
error: "Cannot connect 'main' output to 'ai_tool' input"
severity: error
cause: Incompatible connection types
fix:
  manual: Review connection configuration
  cannot_autofix: true
```

#### Missing Trigger
```yaml
error: "Workflow has no trigger node"
severity: error
cause: No entry point defined
fix:
  manual: Add trigger node (Webhook, Schedule, etc.)
  cannot_autofix: true
```

### Expression Errors

#### Syntax Error
```yaml
error: "Invalid expression: {{ $json.data.items }"
severity: error
cause: Missing closing bracket
fix:
  autofix: Add missing }}
  confidence: high
```

#### Undefined Variable
```yaml
error: "Variable $json.user.name may be undefined"
severity: warning
cause: Path may not exist at runtime
fix:
  options:
    - Add null check
    - Ensure upstream provides data
  autofix: Can wrap in optional chaining
```

#### Invalid Function
```yaml
error: "Function 'customFunc' is not defined"
severity: error
cause: Using unavailable function
fix:
  manual: Use n8n built-in functions
  cannot_autofix: true
```

## Validation API Usage

### Full Workflow Validation
```javascript
// Validate workflow by ID
mcp__n8n__n8n_validate_workflow({
  id: "workflow-id",
  options: {
    profile: "runtime",
    validateNodes: true,
    validateConnections: true,
    validateExpressions: true
  }
})
```

### Validate Workflow JSON
```javascript
// Validate workflow structure directly
mcp__n8n__validate_workflow({
  workflow: workflowJson,
  options: {
    profile: "strict",
    validateConnections: true,
    validateExpressions: true,
    validateNodes: true
  }
})
```

### Validate Connections Only
```javascript
// Quick connection check
mcp__n8n__validate_workflow_connections({
  workflow: workflowJson
})
```

### Validate Expressions Only
```javascript
// Check expression syntax
mcp__n8n__validate_workflow_expressions({
  workflow: workflowJson
})
```

### Validate Single Node
```javascript
// Check node configuration
mcp__n8n__validate_node_operation({
  nodeType: "nodes-base.httpRequest",
  config: {
    method: "POST",
    url: "https://api.example.com"
  },
  profile: "ai-friendly"
})
```

## Interpreting Results

### Result Structure
```yaml
validation_result:
  valid: boolean
  errors: array
    - message: string
    - severity: error|warning
    - node: string (optional)
    - field: string (optional)
    - suggestion: string (optional)
  warnings: array
  suggestions: array
```

### Severity Levels

| Level | Meaning | Action |
|-------|---------|--------|
| error | Workflow will fail | Must fix |
| warning | May cause issues | Review |
| suggestion | Best practice | Consider |

### Decision Flow
```
Validation Result
├── Errors present?
│   ├── Yes → Cannot activate safely
│   │   └── Review and fix each error
│   └── No → Proceed to warnings
├── Warnings present?
│   ├── Critical warnings → Review before activation
│   └── Minor warnings → Document and proceed
└── Suggestions?
    └── Consider for improvement
```

## Pre-Activation Checklist

### Required Checks
- [ ] No validation errors
- [ ] All required fields configured
- [ ] Credentials properly set up
- [ ] Webhook paths are unique
- [ ] Trigger nodes configured

### Recommended Checks
- [ ] Error handling in place
- [ ] Timeout values appropriate
- [ ] Test execution successful
- [ ] Output data format correct
- [ ] No deprecated nodes

### Optional Checks
- [ ] Naming conventions followed
- [ ] Documentation complete
- [ ] Tags assigned
- [ ] Owner identified
