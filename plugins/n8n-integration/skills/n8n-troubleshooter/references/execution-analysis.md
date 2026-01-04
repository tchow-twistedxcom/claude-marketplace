# n8n Execution Analysis Guide

How to analyze workflow executions using the n8n MCP tools.

## Execution Data Modes

### Preview Mode
```yaml
mode: preview
purpose: Quick structure assessment
returns:
  - Execution metadata
  - Node list with item counts
  - No actual data
use_when:
  - Initial assessment
  - Checking execution structure
  - Finding which nodes have data

api_call:
  tool: n8n_get_execution
  params:
    id: "execution-id"
    mode: "preview"
```

### Summary Mode
```yaml
mode: summary
purpose: Data overview with samples
returns:
  - 2 data items per node
  - Basic input/output structure
  - Error information
use_when:
  - Understanding data flow
  - Identifying data format
  - Quick investigation

api_call:
  tool: n8n_get_execution
  params:
    id: "execution-id"
    mode: "summary"
```

### Filtered Mode
```yaml
mode: filtered
purpose: Focus on specific nodes
returns:
  - Data for specified nodes only
  - Configurable item limit
  - Can include input data
use_when:
  - Investigating specific node
  - Tracing data through path
  - Detailed node analysis

api_call:
  tool: n8n_get_execution
  params:
    id: "execution-id"
    mode: "filtered"
    nodeNames: ["HTTP Request", "Set"]
    itemsLimit: 5
    includeInputData: true
```

### Full Mode
```yaml
mode: full
purpose: Complete execution data
returns:
  - All data from all nodes
  - Full input and output
  - Complete error details
use_when:
  - Deep investigation required
  - Reproducing issues
  - Data verification
caution:
  - Can be very large
  - May timeout for big executions

api_call:
  tool: n8n_get_execution
  params:
    id: "execution-id"
    mode: "full"
```

## Reading Execution Data

### Execution Metadata
```yaml
fields:
  id: Unique execution identifier
  workflowId: Parent workflow ID
  finished: boolean - did it complete
  mode: How it was triggered
    - manual: UI execution
    - webhook: Webhook trigger
    - trigger: Event trigger
    - schedule: Scheduled run
  startedAt: ISO timestamp start
  stoppedAt: ISO timestamp end
  status: Current state
    - success: Completed without error
    - error: Failed with error
    - waiting: Paused/waiting
    - running: Still executing

derived:
  duration: stoppedAt - startedAt
  trigger_type: First node type
```

### Node Execution Data
```yaml
per_node_info:
  nodeName: Display name of node
  nodeType: Technical node type
  executionTime: ms to execute
  itemsCount: Number of items processed

  data:
    main: Array of output connections
      - Each connection has array of items
      - Items have json and optionally binary

  error: If node failed
    message: Error description
    description: Detailed error
    stack: Stack trace if available
```

### Data Item Structure
```yaml
item_structure:
  json: Object
    # The actual data processed
    # Structure depends on node output

  binary: Object (optional)
    # Binary data (files, images)
    # Has filename, mimeType, data

  pairedItem: Object (optional)
    # Links to source item
    # Useful for tracing
```

## Execution Analysis Patterns

### Quick Health Check
```yaml
pattern: quick_check
steps:
  1. Get execution with preview mode
  2. Check status field
  3. Look for error nodes
  4. Note item counts

interpretation:
  - status: success → Workflow completed
  - status: error → Check error nodes
  - Low item counts → Data filtering issue
  - Zero items → No data received
```

### Error Investigation
```yaml
pattern: error_trace
steps:
  1. Get execution with summary mode
  2. Find node with error
  3. Get filtered mode for error node
  4. Include input data to see what was received
  5. Analyze error message

questions:
  - What error message?
  - What input caused it?
  - Is error consistent?
  - Is it a data or config issue?
```

### Data Flow Trace
```yaml
pattern: data_trace
steps:
  1. Start with trigger node
  2. Follow connections
  3. Check data at each step
  4. Identify where data changes unexpectedly

check_points:
  - Data format at each node
  - Item count changes
  - Field additions/removals
  - Data transformations
```

### Performance Analysis
```yaml
pattern: performance
steps:
  1. Get execution with preview mode
  2. Check executionTime per node
  3. Identify slowest nodes
  4. Analyze slow node configuration

slow_node_causes:
  - Large data sets
  - External API calls
  - Complex expressions
  - Inefficient loops
```

## Common Execution Issues

### Empty Output
```yaml
symptom: Node produces no items
causes:
  - Filter removed all items
  - API returned empty
  - Expression returned null
  - Connection issue

investigation:
  - Check input data
  - Verify filter conditions
  - Test API directly
  - Check expression logic
```

### Unexpected Data
```yaml
symptom: Output data differs from expected
causes:
  - Wrong field mapping
  - Type conversion issues
  - Expression errors
  - API changes

investigation:
  - Compare expected vs actual
  - Check field names (case sensitive)
  - Verify data types
  - Review API documentation
```

### Partial Execution
```yaml
symptom: Some nodes didn't execute
causes:
  - Error stopped execution
  - Condition not met
  - No data to process
  - Disabled nodes

investigation:
  - Check error nodes
  - Review IF/Switch conditions
  - Verify upstream data
  - Check node enabled status
```

### Timeout
```yaml
symptom: Execution exceeded time limit
causes:
  - Slow external service
  - Too much data
  - Infinite loop
  - Inefficient processing

investigation:
  - Check node execution times
  - Review data volumes
  - Look for loops
  - Analyze slow operations
```

## Comparing Executions

### Success vs Failure
```yaml
comparison_approach:
  1. Get both executions (summary mode)
  2. Compare:
     - Input data differences
     - Node execution paths
     - Data transformations
  3. Identify divergence point
  4. Analyze cause of different behavior
```

### Performance Comparison
```yaml
comparison_approach:
  1. Get multiple executions
  2. Compare execution times
  3. Look for patterns:
     - Time of day effects
     - Data volume correlation
     - External service impact
```

## Execution Investigation Flow

```
Start Investigation
│
├── Get execution (preview mode)
│   └── Is status error?
│       ├── Yes → Find error node
│       │   └── Get filtered mode for error node
│       │       └── Analyze input + error
│       │
│       └── No → Is output correct?
│           ├── No → Trace data flow
│           │   └── Find where data goes wrong
│           │
│           └── Yes → Check performance
│               └── Identify slow nodes
│
└── Apply resolution
    └── Validate fix
```

## Best Practices

### Investigation Efficiency
1. Start with preview mode
2. Progressively get more detail
3. Focus on relevant nodes
4. Use filtered mode for deep dives

### Data Privacy
1. Be aware of sensitive data
2. Limit data exposure in investigations
3. Use filtered mode to minimize data
4. Consider data retention settings

### Documentation
1. Record investigation steps
2. Note root cause
3. Document resolution
4. Add to troubleshooting runbook
