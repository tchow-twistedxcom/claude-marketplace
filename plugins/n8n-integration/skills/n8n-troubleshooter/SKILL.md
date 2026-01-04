---
name: n8n-troubleshooter
description: "Debug n8n workflow failures and diagnose execution issues. Use when user reports 'workflow failed', 'debug execution', 'n8n error', 'workflow not working', 'execution timeout', or needs help fixing broken automations."
version: 1.0.0
license: MIT
---

# n8n Troubleshooter

Comprehensive skill for diagnosing and resolving n8n workflow issues.

## Activation Triggers

- "workflow failed"
- "debug execution"
- "n8n error"
- "workflow not working"
- "execution timeout"
- "workflow stuck"
- "fix my workflow"
- "why did workflow fail"
- "diagnose workflow"

## Capabilities

### Failure Investigation
- Analyze failed executions
- Identify error root causes
- Trace execution flow
- Pinpoint failing nodes

### Validation Analysis
- Check workflow configuration
- Validate expressions
- Verify connections
- Assess node settings

### Fix Recommendations
- Suggest configuration changes
- Provide error resolutions
- Recommend best practices
- Apply auto-fixes when possible

## MCP Tools Available

| Tool | Purpose |
|------|---------|
| `n8n_health_check` | Check n8n instance status |
| `n8n_diagnostic` | Detailed environment diagnostics |
| `n8n_list_executions` | Find failed executions |
| `n8n_get_execution` | Analyze execution details |
| `n8n_validate_workflow` | Validate workflow configuration |
| `n8n_autofix_workflow` | Apply automatic fixes |
| `get_node_info` | Get node documentation |
| `get_property_dependencies` | Understand node dependencies |

## Troubleshooting Workflow

### Phase 1: Information Gathering

```yaml
step_1_health_check:
  tool: n8n_health_check
  purpose: Verify n8n instance is operational
  check:
    - API connectivity
    - n8n version
    - Basic functionality

step_2_identify_workflow:
  method: User provides workflow ID or name
  alternative: n8n_list_workflows to find it

step_3_get_failures:
  tool: n8n_list_executions
  params:
    workflowId: "<workflow-id>"
    status: "error"
    limit: 5
  purpose: Find recent failed executions
```

### Phase 2: Execution Analysis

```yaml
step_4_analyze_execution:
  tool: n8n_get_execution
  params:
    id: "<execution-id>"
    mode: "summary"  # Start with summary
  purpose: Get execution overview

step_5_deep_dive:
  tool: n8n_get_execution
  params:
    id: "<execution-id>"
    mode: "filtered"
    nodeNames: ["<failing-node>"]
    includeInputData: true
  purpose: Detailed failing node analysis
```

### Phase 3: Validation Check

```yaml
step_6_validate:
  tool: n8n_validate_workflow
  params:
    id: "<workflow-id>"
    options:
      profile: "strict"
      validateNodes: true
      validateConnections: true
      validateExpressions: true
  purpose: Identify configuration issues
```

### Phase 4: Resolution

```yaml
step_7_resolution:
  options:
    - Auto-fix: Use n8n_autofix_workflow
    - Manual: Provide step-by-step fix guide
    - Documentation: Reference node docs
```

## Error Categories

### Connection Errors

```yaml
ECONNREFUSED:
  symptom: Cannot connect to external service
  causes:
    - Service is down
    - Wrong URL/port
    - Firewall blocking
  diagnosis:
    - Check URL configuration
    - Verify service availability
    - Test network connectivity
  resolution:
    - Correct URL/port settings
    - Check firewall rules
    - Verify service status

ETIMEDOUT:
  symptom: Connection timed out
  causes:
    - Service too slow
    - Network issues
    - Timeout too short
  diagnosis:
    - Check service response time
    - Review timeout settings
  resolution:
    - Increase timeout value
    - Optimize service performance
    - Check network path
```

### Authentication Errors

```yaml
401_Unauthorized:
  symptom: Authentication failed
  causes:
    - Invalid credentials
    - Expired tokens
    - Wrong auth method
  diagnosis:
    - Check credential configuration
    - Verify token validity
    - Review auth settings
  resolution:
    - Update credentials in n8n
    - Refresh OAuth tokens
    - Correct authentication type

403_Forbidden:
  symptom: Access denied
  causes:
    - Insufficient permissions
    - IP not whitelisted
    - Rate limited
  diagnosis:
    - Check API permissions
    - Review IP restrictions
  resolution:
    - Request additional permissions
    - Whitelist n8n IP
    - Implement rate limiting handling
```

### Data Errors

```yaml
TypeError:
  symptom: "Cannot read property 'x' of undefined"
  causes:
    - Missing data in input
    - Wrong JSON path
    - Null values
  diagnosis:
    - Check input data structure
    - Verify expression paths
    - Review null handling
  resolution:
    - Add null checks
    - Fix JSON paths
    - Handle missing data gracefully

ValidationError:
  symptom: Data format invalid
  causes:
    - Wrong data type
    - Missing required fields
    - Invalid format
  diagnosis:
    - Check data types
    - Review required fields
    - Validate format requirements
  resolution:
    - Transform data correctly
    - Add missing fields
    - Format data properly
```

### Execution Errors

```yaml
Timeout:
  symptom: Execution exceeded time limit
  causes:
    - Long-running operations
    - Infinite loops
    - Large data sets
  diagnosis:
    - Check execution duration
    - Review loop configurations
    - Analyze data volume
  resolution:
    - Increase timeout
    - Add pagination
    - Optimize data processing

MemoryLimit:
  symptom: Out of memory
  causes:
    - Large data in memory
    - Memory leaks
    - Too many parallel operations
  diagnosis:
    - Check data sizes
    - Review parallel execution
  resolution:
    - Process data in chunks
    - Reduce parallelization
    - Clear intermediate data
```

## Diagnostic Patterns

### Quick Diagnosis
```yaml
quick_check:
  1. n8n_health_check → Is n8n running?
  2. n8n_list_executions(status: error) → Any recent failures?
  3. n8n_validate_workflow → Configuration issues?
```

### Deep Diagnosis
```yaml
deep_dive:
  1. All quick checks
  2. n8n_get_execution(mode: full) → Full execution data
  3. Trace data flow through nodes
  4. Check each node's input/output
  5. Identify where data goes wrong
```

### Expression Diagnosis
```yaml
expression_debug:
  1. n8n_validate_workflow → Find expression errors
  2. Check expression syntax:
     - Balanced brackets {{ }}
     - Valid JavaScript
     - Correct variable references
  3. Verify data availability:
     - $json paths exist
     - Previous node outputs correct
```

## Resolution Patterns

### Auto-Fix Path
```yaml
when_applicable:
  - Expression format errors
  - TypeVersion issues
  - Error output configuration
  - Webhook path problems

process:
  1. n8n_autofix_workflow(applyFixes: false) → Preview
  2. Review proposed changes
  3. n8n_autofix_workflow(applyFixes: true) → Apply
  4. n8n_validate_workflow → Verify fix
```

### Manual Fix Path
```yaml
when_required:
  - Missing credentials
  - Invalid URLs
  - Business logic errors
  - Complex configurations

process:
  1. Identify exact issue
  2. Provide step-by-step instructions
  3. Reference relevant documentation
  4. Suggest testing approach
```

## Execution Analysis

### Execution Modes
```yaml
preview:
  use: First look at execution
  returns: Structure and counts only
  fast: Yes

summary:
  use: Understanding what happened
  returns: 2 samples per node
  shows: Data flow overview

filtered:
  use: Focus on specific nodes
  params:
    nodeNames: ["Node1", "Node2"]
    includeInputData: true
  returns: Targeted data

full:
  use: Complete investigation
  returns: All data
  caution: Can be large
```

### Reading Execution Data
```yaml
key_information:
  - startedAt: When execution began
  - stoppedAt: When it ended
  - status: success/error/waiting
  - mode: manual/webhook/trigger

per_node:
  - executionTime: How long node took
  - data: Input and output items
  - error: If node failed
```

## Common Fixes

### Fix Expression Errors
```yaml
problem: Invalid expression syntax
example: "{{ $json.data }"
fix: "{{ $json.data }}"
tool: n8n_autofix_workflow(fixTypes: ["expression-format"])
```

### Fix Missing Webhooks
```yaml
problem: Webhook not responding
checks:
  - Is workflow active? (Manual check in UI)
  - Is webhook path configured?
  - Is HTTP method correct?
fix:
  - Auto-fix can add missing path
  - Manual activation required in UI
```

### Fix Credential Issues
```yaml
problem: 401/403 errors
cannot_auto_fix: true
guidance:
  1. Navigate to n8n UI
  2. Go to workflow settings
  3. Click on the failing node
  4. Update credential configuration
  5. Test with manual execution
```

### Fix Timeout Issues
```yaml
problem: ETIMEDOUT errors
options:
  workflow_level:
    - Update settings.executionTimeout
  node_level:
    - Increase node-specific timeout
  optimization:
    - Add pagination
    - Process in smaller batches
```

## Best Practices

### Preventive Measures
1. Add error handling nodes
2. Validate input data early
3. Use appropriate timeouts
4. Implement retry logic
5. Log important steps

### Investigation Order
1. Start with most recent failure
2. Check if issue is consistent
3. Compare with successful executions
4. Isolate the failing component
5. Test fixes in isolation

### Documentation
- Record common failure patterns
- Document resolution steps
- Track recurring issues
- Maintain troubleshooting runbook

## Reference Files

- `@common-errors.md` - Error catalog with solutions
- `@execution-analysis.md` - Execution data interpretation
- `@connection-debugging.md` - Network and connection issues
- `@node-diagnostics.md` - Per-node troubleshooting
- `@expression-debugging.md` - Expression error fixes
