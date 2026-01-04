# n8n Node Diagnostics Guide

Per-node troubleshooting patterns and diagnostic techniques.

## Node Diagnostic Approach

### Standard Diagnostic Flow
```yaml
1. Identify failing node:
   - Check execution data
   - Find node with error

2. Analyze configuration:
   - tool: get_node_info
   - Review required parameters
   - Check credentials

3. Check input data:
   - Review upstream output
   - Verify data format
   - Check for null values

4. Validate settings:
   - tool: validate_node_operation
   - Check dependencies
   - Review property visibility

5. Apply fix:
   - Configuration change
   - Data transformation
   - Error handling
```

## HTTP Request Node

### Common Issues
```yaml
request_formation:
  - Wrong URL format
  - Missing path parameters
  - Query string errors
  - Body not JSON serializable

authentication:
  - Credentials not set
  - Token expired
  - Wrong auth type
  - Header misconfigured

response_handling:
  - Content-Type not JSON
  - Binary data not handled
  - Pagination not implemented
  - Error responses not caught
```

### Diagnostic Checklist
```yaml
configuration:
  □ URL is complete and valid
  □ Method matches API requirement
  □ Authentication configured
  □ Headers include Content-Type
  □ Body format matches Content-Type

data:
  □ Path parameters resolved
  □ Query parameters encoded
  □ Body serializable to JSON
  □ Response format expected

error_handling:
  □ Error responses handled
  □ Timeout appropriate
  □ Retry configured if needed
```

### Useful Properties
```yaml
get_property_dependencies:
  nodeType: "nodes-base.httpRequest"
  query: "authentication"
  # Shows auth-dependent fields

key_settings:
  - method: GET|POST|PUT|DELETE|etc
  - url: Target endpoint
  - authentication: Auth type
  - sendBody: Enable request body
  - responseFormat: Expected response
```

## Webhook Node

### Common Issues
```yaml
configuration:
  - Path not unique
  - Method mismatch
  - Auth not configured
  - Response mode wrong

activation:
  - Workflow not active (404)
  - Wrong URL (test vs production)
  - Path changed after save

response:
  - Timeout on long workflows
  - Wrong response format
  - Headers not set
```

### Diagnostic Checklist
```yaml
setup:
  □ Unique webhook path
  □ Correct HTTP method
  □ Authentication if needed
  □ Response mode appropriate

testing:
  □ Workflow is active
  □ Using production URL (not test)
  □ Client timeout sufficient
  □ Response data configured
```

## Code Node

### Common Issues
```yaml
javascript:
  - Syntax errors
  - Undefined variables
  - Wrong return format
  - Async issues

python:
  - Indentation errors
  - Import failures
  - Type mismatches
  - Memory limits

data_handling:
  - Not returning items array
  - Missing json property
  - Binary data issues
```

### Diagnostic Checklist
```yaml
code_quality:
  □ Syntax valid
  □ All variables defined
  □ Returns correct structure
  □ Handles errors

n8n_integration:
  □ Accesses $input correctly
  □ Returns items array
  □ Each item has json property
  □ Binary data handled properly
```

### Return Format
```javascript
// Correct return format
return items.map(item => ({
  json: {
    // your data here
    processedField: item.json.originalField
  }
}));

// For new items
return [
  { json: { field1: "value1" } },
  { json: { field2: "value2" } }
];
```

## Set Node

### Common Issues
```yaml
configuration:
  - Wrong operation mode
  - Field names incorrect
  - Expression errors
  - Type mismatches

modes:
  manual: Set specific values
  expression: Compute values
  raw: JSON structure
```

### Diagnostic Checklist
```yaml
setup:
  □ Correct mode selected
  □ Field names match expected
  □ Expressions valid
  □ Types compatible

output:
  □ Required fields present
  □ Unnecessary fields removed
  □ Data structure correct
```

## IF Node

### Common Issues
```yaml
conditions:
  - Wrong comparison operator
  - Type mismatch in comparison
  - Null value handling
  - Complex condition logic

paths:
  - Wrong output connected
  - Both paths needed
  - Empty output handling
```

### Diagnostic Checklist
```yaml
condition_setup:
  □ Left value exists
  □ Operator appropriate
  □ Right value correct type
  □ Null handling considered

routing:
  □ True path connected
  □ False path connected (if needed)
  □ Both paths handle data
```

## Loop/SplitInBatches Node

### Common Issues
```yaml
configuration:
  - Batch size too large
  - Memory exhaustion
  - Infinite loop potential

handling:
  - Items not merged after loop
  - Lost data between iterations
  - Order not preserved
```

### Diagnostic Checklist
```yaml
setup:
  □ Batch size appropriate
  □ Loop terminates
  □ Data merged correctly

performance:
  □ Batch size optimized
  □ Memory usage acceptable
  □ Execution time reasonable
```

## Merge Node

### Common Issues
```yaml
configuration:
  - Wrong merge mode
  - Key field mismatch
  - Missing data on one branch

modes:
  append: Combine all items
  combine: Match by position
  merge_by_field: Match by field value
  multiplex: Cartesian product
```

### Diagnostic Checklist
```yaml
setup:
  □ Correct mode for use case
  □ All inputs connected
  □ Key fields exist and match

output:
  □ Expected item count
  □ Data combined correctly
  □ No data lost
```

## Database Nodes

### Common Issues
```yaml
connection:
  - Wrong credentials
  - Connection timeout
  - SSL/TLS issues

query:
  - SQL syntax errors
  - Permission denied
  - Query timeout

data:
  - Type conversion issues
  - Encoding problems
  - Null handling
```

### Diagnostic Checklist
```yaml
connection:
  □ Credentials correct
  □ Host/port reachable
  □ SSL configured properly

query:
  □ SQL syntax valid
  □ Tables/columns exist
  □ Permissions granted
  □ Query optimized
```

## AI/LLM Nodes

### Common Issues
```yaml
configuration:
  - API key not set
  - Model not available
  - Rate limit exceeded

prompts:
  - Prompt too long
  - Format not supported
  - Tokens exceeded

responses:
  - Parsing failures
  - Unexpected format
  - Empty responses
```

### Diagnostic Checklist
```yaml
setup:
  □ API key configured
  □ Model selected
  □ Rate limits understood

execution:
  □ Prompt within limits
  □ Response parsed correctly
  □ Errors handled gracefully
```

## General Diagnostics

### Using get_node_info
```yaml
purpose: Understand node requirements
tool: mcp__n8n__get_node_info
params:
  nodeType: "nodes-base.httpRequest"

returns:
  - All properties
  - Operations
  - Default values
  - Required fields
```

### Using validate_node_operation
```yaml
purpose: Check node configuration
tool: mcp__n8n__validate_node_operation
params:
  nodeType: "nodes-base.slack"
  config:
    resource: "channel"
    operation: "create"
  profile: "runtime"

returns:
  - Validation errors
  - Missing fields
  - Suggestions
```

### Using get_property_dependencies
```yaml
purpose: Understand conditional fields
tool: mcp__n8n__get_property_dependencies
params:
  nodeType: "nodes-base.httpRequest"
  config:
    sendBody: true

returns:
  - Visible properties based on config
  - Required fields for current settings
```

## Node Category Quick Reference

| Category | Common Issues | First Check |
|----------|--------------|-------------|
| HTTP | Auth, URL, timeout | Credentials, URL format |
| Webhook | Not active, path | Active status, URL |
| Database | Connection, query | Credentials, SQL |
| Code | Syntax, return format | Code validity |
| Transform | Expression, field names | Data path |
| Logic | Condition, routing | Input data |
| AI | API key, limits | Credentials |
