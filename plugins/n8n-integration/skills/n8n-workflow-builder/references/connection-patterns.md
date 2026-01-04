# n8n Connection Patterns

Workflow connection structures and routing patterns.

## Connection Basics

### Simple Linear Connection
```json
{
  "Webhook": {
    "main": [
      [
        {
          "node": "Set",
          "type": "main",
          "index": 0
        }
      ]
    ]
  },
  "Set": {
    "main": [
      [
        {
          "node": "HTTP Request",
          "type": "main",
          "index": 0
        }
      ]
    ]
  }
}
```

### Connection Structure Explained
```yaml
structure:
  "<Source Node Name>":
    main:                    # Output type
      - connection_set_0:    # First output
        - node: "Target"     # Target node name
          type: "main"       # Input type on target
          index: 0           # Input index

output_types:
  main: Standard data output
  ai_tool: AI tool connections
  ai_memory: Memory connections
  ai_outputParser: Parser connections
```

## Branching Patterns

### IF Node Branches (True/False)
```json
{
  "IF": {
    "main": [
      [
        {
          "node": "True Path",
          "type": "main",
          "index": 0
        }
      ],
      [
        {
          "node": "False Path",
          "type": "main",
          "index": 0
        }
      ]
    ]
  }
}
```

### Switch Node Multiple Outputs
```json
{
  "Switch": {
    "main": [
      [
        {
          "node": "Route A",
          "type": "main",
          "index": 0
        }
      ],
      [
        {
          "node": "Route B",
          "type": "main",
          "index": 0
        }
      ],
      [
        {
          "node": "Route C",
          "type": "main",
          "index": 0
        }
      ],
      [
        {
          "node": "Default Route",
          "type": "main",
          "index": 0
        }
      ]
    ]
  }
}
```

## Merging Patterns

### Merge Two Branches
```json
{
  "True Path": {
    "main": [
      [
        {
          "node": "Merge",
          "type": "main",
          "index": 0
        }
      ]
    ]
  },
  "False Path": {
    "main": [
      [
        {
          "node": "Merge",
          "type": "main",
          "index": 1
        }
      ]
    ]
  }
}
```

### Multi-Input Merge
```json
{
  "Source A": {
    "main": [[{ "node": "Merge", "type": "main", "index": 0 }]]
  },
  "Source B": {
    "main": [[{ "node": "Merge", "type": "main", "index": 1 }]]
  },
  "Source C": {
    "main": [[{ "node": "Merge", "type": "main", "index": 2 }]]
  }
}
```

## Parallel Execution

### Fan-Out Pattern
```json
{
  "Trigger": {
    "main": [
      [
        { "node": "Path A", "type": "main", "index": 0 },
        { "node": "Path B", "type": "main", "index": 0 },
        { "node": "Path C", "type": "main", "index": 0 }
      ]
    ]
  }
}
```

### Fan-In Pattern
```json
{
  "Path A": {
    "main": [[{ "node": "Merge", "type": "main", "index": 0 }]]
  },
  "Path B": {
    "main": [[{ "node": "Merge", "type": "main", "index": 1 }]]
  },
  "Path C": {
    "main": [[{ "node": "Merge", "type": "main", "index": 2 }]]
  }
}
```

## Loop Patterns

### Split In Batches Loop
```json
{
  "Split In Batches": {
    "main": [
      [
        {
          "node": "Process Item",
          "type": "main",
          "index": 0
        }
      ],
      [
        {
          "node": "After Loop",
          "type": "main",
          "index": 0
        }
      ]
    ]
  },
  "Process Item": {
    "main": [
      [
        {
          "node": "Split In Batches",
          "type": "main",
          "index": 0
        }
      ]
    ]
  }
}
```

## Error Handling Connections

### Node with Error Output
```json
{
  "HTTP Request": {
    "main": [
      [
        {
          "node": "Success Handler",
          "type": "main",
          "index": 0
        }
      ],
      [
        {
          "node": "Error Handler",
          "type": "main",
          "index": 0
        }
      ]
    ]
  }
}
```

### Error Trigger Pattern
```json
{
  "Error Trigger": {
    "main": [
      [
        {
          "node": "Log Error",
          "type": "main",
          "index": 0
        }
      ]
    ]
  }
}
```

## AI Agent Connections

### AI Agent with Tools
```json
{
  "AI Agent": {
    "ai_tool": [
      [
        {
          "node": "HTTP Request Tool",
          "type": "ai_tool",
          "index": 0
        }
      ]
    ],
    "ai_memory": [
      [
        {
          "node": "Buffer Memory",
          "type": "ai_memory",
          "index": 0
        }
      ]
    ],
    "main": [
      [
        {
          "node": "Output",
          "type": "main",
          "index": 0
        }
      ]
    ]
  }
}
```

### Tool Node Connection
```json
{
  "Tool Node": {
    "ai_tool": [
      [
        {
          "node": "AI Agent",
          "type": "ai_tool",
          "index": 0
        }
      ]
    ]
  }
}
```

## Complete Workflow Examples

### Simple Webhook Workflow
```json
{
  "Webhook": {
    "main": [[{ "node": "Process Data", "type": "main", "index": 0 }]]
  },
  "Process Data": {
    "main": [[{ "node": "Respond to Webhook", "type": "main", "index": 0 }]]
  }
}
```

### Conditional Processing
```json
{
  "Webhook": {
    "main": [[{ "node": "IF", "type": "main", "index": 0 }]]
  },
  "IF": {
    "main": [
      [{ "node": "Process Valid", "type": "main", "index": 0 }],
      [{ "node": "Handle Invalid", "type": "main", "index": 0 }]
    ]
  },
  "Process Valid": {
    "main": [[{ "node": "Merge", "type": "main", "index": 0 }]]
  },
  "Handle Invalid": {
    "main": [[{ "node": "Merge", "type": "main", "index": 1 }]]
  },
  "Merge": {
    "main": [[{ "node": "Respond", "type": "main", "index": 0 }]]
  }
}
```

### Multi-Service Integration
```json
{
  "Webhook": {
    "main": [[{ "node": "Get Customer", "type": "main", "index": 0 }]]
  },
  "Get Customer": {
    "main": [[
      { "node": "Update CRM", "type": "main", "index": 0 },
      { "node": "Send Email", "type": "main", "index": 0 },
      { "node": "Log Activity", "type": "main", "index": 0 }
    ]]
  },
  "Update CRM": {
    "main": [[{ "node": "Merge Results", "type": "main", "index": 0 }]]
  },
  "Send Email": {
    "main": [[{ "node": "Merge Results", "type": "main", "index": 1 }]]
  },
  "Log Activity": {
    "main": [[{ "node": "Merge Results", "type": "main", "index": 2 }]]
  },
  "Merge Results": {
    "main": [[{ "node": "Respond", "type": "main", "index": 0 }]]
  }
}
```

## Connection Validation Rules

### Must Have
```yaml
requirements:
  - At least one trigger node
  - All nodes connected (no orphans)
  - Valid node names in connections
  - Correct input indices

avoid:
  - Self-referencing (except loops)
  - Circular dependencies (except designed loops)
  - Missing target nodes
```

### Index Guidelines
```yaml
input_indices:
  single_input: Always 0
  merge_inputs: 0, 1, 2... for each source
  conditional_output: 0=true, 1=false for IF
  switch_output: 0, 1, 2... per case, last=fallback
```
