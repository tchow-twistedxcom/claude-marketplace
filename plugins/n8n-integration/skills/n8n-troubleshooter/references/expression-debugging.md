# n8n Expression Debugging Guide

Comprehensive guide to debugging and fixing n8n expressions.

## Expression Syntax Basics

### Standard Expression Format
```javascript
// Basic expression
{{ $json.fieldName }}

// With operations
{{ $json.price * 1.1 }}

// With functions
{{ $json.name.toUpperCase() }}

// Conditional
{{ $json.active ? "Yes" : "No" }}
```

### Available Variables
```yaml
$json:
  description: Current item's JSON data
  usage: "{{ $json.fieldName }}"

$input:
  description: Input data object
  usage: "{{ $input.first().json.field }}"

$node:
  description: Reference to other nodes
  usage: '{{ $node["Node Name"].json.field }}'

$now:
  description: Current date/time
  usage: "{{ $now }}"

$today:
  description: Today's date
  usage: "{{ $today }}"

$execution:
  description: Execution metadata
  usage: "{{ $execution.id }}"

$workflow:
  description: Workflow metadata
  usage: "{{ $workflow.id }}"

$env:
  description: Environment variables
  usage: "{{ $env.MY_VARIABLE }}"
  warning: "⚠️ May be blocked - see security section below"

$vars:
  description: Workflow variables
  usage: "{{ $vars.myVar }}"
```

## Common Expression Errors

### Syntax Errors

#### Missing Closing Bracket
```yaml
error: "{{ $json.data.items }"
fix: "{{ $json.data.items }}"
cause: Forgot closing }}
autofix: Yes
```

#### Missing Opening Bracket
```yaml
error: "$json.data.items }}"
fix: "{{ $json.data.items }}"
cause: Forgot opening {{
autofix: Yes
```

#### Unbalanced Brackets
```yaml
error: "{{ $json.data.items }}}"
fix: "{{ $json.data.items }}"
cause: Extra closing bracket
autofix: Yes
```

#### Invalid JavaScript
```yaml
error: "{{ $json.data items }}"
fix: "{{ $json.data.items }}"
cause: Missing dot operator
autofix: No (context dependent)
```

### Reference Errors

#### Undefined Variable
```yaml
error: "ReferenceError: xyz is not defined"
cause: Using variable that doesn't exist
fix: Use correct variable name ($json, $node, etc.)
```

#### Null Reference
```yaml
error: "TypeError: Cannot read property 'x' of null"
cause: Parent object is null
fix: Add null check or optional chaining
example:
  before: "{{ $json.user.name }}"
  after: "{{ $json.user?.name }}"
  alt: "{{ $json.user?.name ?? 'Unknown' }}"
```

#### Undefined Property
```yaml
error: "TypeError: Cannot read property 'x' of undefined"
cause: Property path doesn't exist
fix: Verify data structure, add safety checks
example:
  before: "{{ $json.data.items[0].name }}"
  after: "{{ $json.data?.items?.[0]?.name ?? '' }}"
```

### Type Errors

#### Type Mismatch
```yaml
error: "TypeError: x.toUpperCase is not a function"
cause: Value is not a string
fix: Type check or conversion
example:
  before: "{{ $json.value.toUpperCase() }}"
  after: "{{ String($json.value).toUpperCase() }}"
```

#### Array vs Object
```yaml
error: "TypeError: Cannot read property '0' of object"
cause: Expected array but got object
fix: Check data type, adjust access
example:
  object_access: "{{ $json.items.key }}"
  array_access: "{{ $json.items[0] }}"
```

## Expression Safety Patterns

### Null-Safe Access
```javascript
// Optional chaining
{{ $json.user?.profile?.name }}

// Nullish coalescing
{{ $json.value ?? "default" }}

// Combined
{{ $json.user?.name ?? "Unknown User" }}
```

### Type-Safe Operations
```javascript
// Safe string operations
{{ String($json.value || '').toUpperCase() }}

// Safe number operations
{{ Number($json.price) || 0 }}

// Safe array operations
{{ Array.isArray($json.items) ? $json.items.length : 0 }}
```

### Conditional Expressions
```javascript
// Ternary operator
{{ $json.active ? "Active" : "Inactive" }}

// Nested conditionals
{{ $json.status === "A" ? "Active" : $json.status === "P" ? "Pending" : "Unknown" }}

// Logical operators
{{ $json.name || $json.username || "Anonymous" }}
```

## n8n Built-in Functions

### Date Functions
```javascript
// Format date
{{ $json.date.toLocaleDateString() }}
{{ DateTime.fromISO($json.date).toFormat('yyyy-MM-dd') }}

// Current date
{{ $now.toISOString() }}
{{ $today }}

// Date math
{{ DateTime.now().plus({ days: 7 }).toISOString() }}
```

### String Functions
```javascript
// Common string operations
{{ $json.text.trim() }}
{{ $json.text.toLowerCase() }}
{{ $json.text.toUpperCase() }}
{{ $json.text.replace('old', 'new') }}
{{ $json.text.split(',') }}

// Template strings
{{ `Hello, ${$json.name}!` }}
```

### Array Functions
```javascript
// Array operations
{{ $json.items.length }}
{{ $json.items.map(i => i.name) }}
{{ $json.items.filter(i => i.active) }}
{{ $json.items.find(i => i.id === 123) }}
{{ $json.items.join(', ') }}
```

### Number Functions
```javascript
// Formatting
{{ $json.price.toFixed(2) }}
{{ Math.round($json.value) }}
{{ Math.floor($json.value) }}
{{ Math.ceil($json.value) }}

// Calculations
{{ $json.price * 1.1 }}
{{ Math.max(...$json.values) }}
```

## Debugging Techniques

### Expression Testing
```yaml
technique: Test expressions incrementally
steps:
  1. Start with simplest form: {{ $json }}
  2. Add path step by step:
     - {{ $json.data }}
     - {{ $json.data.items }}
     - {{ $json.data.items[0] }}
  3. Identify where it breaks
```

### Data Inspection
```yaml
technique: Log expression values
steps:
  1. Add Set node before problematic node
  2. Create field with expression result
  3. Check output data
  4. Identify actual value vs expected
```

### Type Checking
```yaml
technique: Verify data types
expressions:
  type_check: "{{ typeof $json.value }}"
  is_array: "{{ Array.isArray($json.items) }}"
  is_null: "{{ $json.value === null }}"
  is_undefined: "{{ $json.value === undefined }}"
```

### Structure Exploration
```yaml
technique: Explore data structure
expressions:
  all_keys: "{{ Object.keys($json) }}"
  stringify: "{{ JSON.stringify($json) }}"
  has_property: "{{ 'fieldName' in $json }}"
```

## Expression Validation

### Using validate_workflow_expressions
```javascript
mcp__n8n__validate_workflow_expressions({
  workflow: workflowJson
})

// Returns:
// - Expression syntax errors
// - Location (node, field)
// - Suggested fixes
```

### Manual Validation Checklist
```yaml
syntax:
  □ Brackets balanced {{ }}
  □ Valid JavaScript inside
  □ Quotes properly escaped
  □ No stray characters

references:
  □ Variables exist ($json, $node, etc.)
  □ Property paths valid
  □ Node names quoted correctly
  □ Array indices valid

safety:
  □ Null checks added
  □ Type assumptions verified
  □ Default values provided
  □ Edge cases handled
```

## Common Expression Patterns

### Data Transformation
```javascript
// Rename field
{{ { newName: $json.oldName } }}

// Add calculated field
{{ { ...$json, total: $json.price * $json.quantity } }}

// Filter fields
{{ { id: $json.id, name: $json.name } }}
```

### String Building
```javascript
// Concatenation
{{ $json.firstName + ' ' + $json.lastName }}

// Template literal
{{ `Order #${$json.orderId} - ${$json.status}` }}

// Join array
{{ $json.tags.join(', ') }}
```

### Conditional Logic
```javascript
// Status mapping
{{ {'A': 'Active', 'I': 'Inactive'}[$json.status] || 'Unknown' }}

// Range check
{{ $json.score >= 90 ? 'A' : $json.score >= 80 ? 'B' : 'C' }}

// Existence check
{{ $json.email ? 'Has email' : 'No email' }}
```

### Data Aggregation
```javascript
// Sum array
{{ $json.items.reduce((sum, i) => sum + i.price, 0) }}

// Count filtered
{{ $json.items.filter(i => i.active).length }}

// Group by (complex)
{{ Object.groupBy($json.items, i => i.category) }}
```

## Quick Reference

| Issue | Symptom | Solution |
|-------|---------|----------|
| Missing }} | Parse error | Add closing brackets |
| undefined | Cannot read property | Add optional chaining |
| null | Cannot read property | Add nullish coalescing |
| Not a function | TypeError | Check data type |
| Wrong node ref | Node not found | Check node name spelling |
| Empty result | Expression returns undefined | Verify data path |
| $env empty | Security block | Use credentials store |

## Environment Variable Security

### ⚠️ $env May Be Blocked

n8n can be configured to block environment variable access in workflows:

```bash
# This setting blocks $env access (default in n8n v2.0+)
N8N_BLOCK_ENV_ACCESS_IN_NODE=true
```

### Symptoms When Blocked

```yaml
behavior:
  - $env.MY_VARIABLE returns empty/null
  - No error is thrown - fails silently!
  - Code nodes cannot access process.env
  - Expressions using $env evaluate to empty string

detection:
  test_expression: "{{ $env.PATH ? 'has access' : 'blocked' }}"
  expected_if_blocked: "" (empty string)
```

### Recommended Alternative: Credentials Store

Instead of `$env`, use n8n's built-in credentials store:

#### 1. Create Credential via API
```bash
python3 n8n_api.py credentials create \
  --name "Webhook Auth Token" \
  --type httpHeaderAuth \
  --data '{"name": "X-Webhook-Token", "value": "your-secret-value"}'
```

#### 2. Reference Credential in Node
```json
{
  "type": "n8n-nodes-base.webhook",
  "parameters": {
    "authentication": "headerAuth"
  },
  "credentials": {
    "httpHeaderAuth": {
      "id": "credential-id",
      "name": "Webhook Auth Token"
    }
  }
}
```

### Common Credential Types

| Type | Use Case | Required Fields |
|------|----------|-----------------|
| `httpHeaderAuth` | Custom header auth | `name`, `value` |
| `httpBasicAuth` | Basic HTTP auth | `user`, `password` |
| `oAuth2Api` | OAuth 2.0 flows | `clientId`, `clientSecret`, ... |
| `apiKey` | API key auth | `key` |

### Why Credentials > $env

```yaml
advantages:
  - Encrypted at rest in n8n database
  - Access controlled per workflow
  - Works regardless of N8N_BLOCK_ENV_ACCESS_IN_NODE
  - Visible in n8n UI for management
  - Can be rotated without code changes

limitations:
  - Cannot read existing environment variables
  - OAuth credentials require UI for initial authorization
  - Credential values not returned via API (security feature)
```
