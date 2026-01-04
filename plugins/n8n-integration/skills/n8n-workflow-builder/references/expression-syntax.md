# n8n Expression Syntax Guide

Complete reference for n8n expressions in workflow building.

## Expression Basics

### Syntax Format
```javascript
// Standard expression
{{ expression }}

// Examples
{{ $json.fieldName }}
{{ $json.price * 1.1 }}
{{ $json.name.toUpperCase() }}
```

### When Expressions Are Evaluated
```yaml
evaluation:
  timing: At node execution
  context: Current item data
  scope: Per item (not batch)
```

## Available Variables

### $json - Current Item Data
```javascript
// Access current item's JSON data
{{ $json.fieldName }}
{{ $json.nested.property }}
{{ $json.array[0].field }}

// Full object
{{ $json }}
```

### $input - Input Data Object
```javascript
// First item from input
{{ $input.first().json.field }}

// Last item from input
{{ $input.last().json.field }}

// All items
{{ $input.all() }}

// Item at specific index
{{ $input.item(0).json.field }}
```

### $node - Reference Other Nodes
```javascript
// Access data from named node
{{ $node["Node Name"].json.field }}

// From first item of node output
{{ $node["HTTP Request"].first().json.data }}

// All items from node
{{ $node["Set"].all() }}

// Item count from node
{{ $node["Set"].all().length }}
```

### $execution - Execution Metadata
```javascript
// Execution ID
{{ $execution.id }}

// Execution mode
{{ $execution.mode }}

// Resume URL (for wait node)
{{ $execution.resumeUrl }}
```

### $workflow - Workflow Metadata
```javascript
// Workflow ID
{{ $workflow.id }}

// Workflow name
{{ $workflow.name }}

// Workflow active status
{{ $workflow.active }}
```

### $now / $today - Date/Time
```javascript
// Current date/time (Luxon DateTime)
{{ $now }}
{{ $now.toISO() }}
{{ $now.toFormat('yyyy-MM-dd') }}

// Today's date
{{ $today }}
{{ $today.toISODate() }}
```

### $env - Environment Variables
```javascript
// Access environment variable
{{ $env.MY_API_KEY }}
{{ $env.DATABASE_URL }}
```

### $vars - Workflow Variables
```javascript
// Access workflow variable
{{ $vars.myVariable }}
```

## Data Access Patterns

### Object Access
```javascript
// Dot notation
{{ $json.user.profile.name }}

// Bracket notation (for special characters)
{{ $json["field-name"] }}
{{ $json.data["special.key"] }}

// Dynamic property
{{ $json[$json.keyName] }}
```

### Array Access
```javascript
// By index
{{ $json.items[0] }}
{{ $json.items[2].name }}

// Last item
{{ $json.items.at(-1) }}

// Array operations
{{ $json.items.length }}
{{ $json.items.map(i => i.name) }}
{{ $json.items.filter(i => i.active) }}
```

### Null-Safe Access
```javascript
// Optional chaining
{{ $json.user?.profile?.name }}

// Nullish coalescing
{{ $json.value ?? "default" }}

// Combined
{{ $json.user?.name ?? "Unknown" }}

// Logical OR (also handles empty string, 0)
{{ $json.name || "Default Name" }}
```

## String Operations

### Basic Operations
```javascript
// Concatenation
{{ $json.firstName + ' ' + $json.lastName }}

// Template literal
{{ `Hello, ${$json.name}!` }}

// Case conversion
{{ $json.text.toUpperCase() }}
{{ $json.text.toLowerCase() }}

// Trim whitespace
{{ $json.text.trim() }}
```

### String Methods
```javascript
// Replace
{{ $json.text.replace('old', 'new') }}
{{ $json.text.replaceAll('old', 'new') }}

// Split
{{ $json.text.split(',') }}

// Substring
{{ $json.text.substring(0, 10) }}
{{ $json.text.slice(-5) }}

// Includes
{{ $json.text.includes('search') }}

// Length
{{ $json.text.length }}
```

### Formatting
```javascript
// Pad
{{ String($json.id).padStart(5, '0') }}

// Join array to string
{{ $json.tags.join(', ') }}

// JSON stringify
{{ JSON.stringify($json.data) }}
```

## Number Operations

### Basic Math
```javascript
// Arithmetic
{{ $json.price * 1.1 }}
{{ $json.total / $json.count }}
{{ $json.value + 100 }}
{{ $json.amount - $json.discount }}

// Modulo
{{ $json.index % 2 }}
```

### Number Methods
```javascript
// Fixed decimals
{{ $json.price.toFixed(2) }}

// Rounding
{{ Math.round($json.value) }}
{{ Math.floor($json.value) }}
{{ Math.ceil($json.value) }}

// Min/Max
{{ Math.max($json.a, $json.b) }}
{{ Math.min(...$json.values) }}

// Parse from string
{{ Number($json.stringValue) }}
{{ parseInt($json.text) }}
{{ parseFloat($json.text) }}
```

## Date/Time Operations

### Luxon DateTime (n8n built-in)
```javascript
// Parse ISO string
{{ DateTime.fromISO($json.date) }}

// Format date
{{ DateTime.fromISO($json.date).toFormat('yyyy-MM-dd') }}
{{ DateTime.fromISO($json.date).toFormat('MMMM d, yyyy') }}

// Date math
{{ DateTime.now().plus({ days: 7 }) }}
{{ DateTime.now().minus({ hours: 2 }) }}

// Compare dates
{{ DateTime.fromISO($json.date) > DateTime.now() }}
```

### Date Formatting Options
```javascript
// ISO format
{{ $now.toISO() }}

// Custom formats
{{ $now.toFormat('yyyy-MM-dd') }}          // 2024-03-21
{{ $now.toFormat('dd/MM/yyyy') }}          // 21/03/2024
{{ $now.toFormat('MMMM d, yyyy') }}        // March 21, 2024
{{ $now.toFormat('HH:mm:ss') }}            // 14:30:45
{{ $now.toFormat('yyyy-MM-dd HH:mm:ss') }} // 2024-03-21 14:30:45
```

### Date Parts
```javascript
{{ $now.year }}
{{ $now.month }}
{{ $now.day }}
{{ $now.hour }}
{{ $now.minute }}
{{ $now.weekday }}
```

## Array Operations

### Transformation
```javascript
// Map
{{ $json.items.map(item => item.name) }}
{{ $json.items.map(item => ({ id: item.id, title: item.name })) }}

// Filter
{{ $json.items.filter(item => item.active) }}
{{ $json.items.filter(item => item.amount > 100) }}

// Find
{{ $json.items.find(item => item.id === 123) }}

// Reduce
{{ $json.items.reduce((sum, item) => sum + item.amount, 0) }}

// Flat
{{ $json.nestedArrays.flat() }}
```

### Array Methods
```javascript
// Sort
{{ $json.items.sort((a, b) => a.name.localeCompare(b.name)) }}
{{ $json.items.sort((a, b) => b.amount - a.amount) }}

// Reverse
{{ $json.items.reverse() }}

// Slice
{{ $json.items.slice(0, 5) }}

// Includes
{{ $json.tags.includes('important') }}

// Every/Some
{{ $json.items.every(i => i.valid) }}
{{ $json.items.some(i => i.error) }}
```

## Conditional Logic

### Ternary Operator
```javascript
// Simple condition
{{ $json.status === 'active' ? 'Yes' : 'No' }}

// Nested conditions
{{ $json.score >= 90 ? 'A' : $json.score >= 80 ? 'B' : 'C' }}
```

### Logical Operators
```javascript
// AND
{{ $json.a && $json.b }}

// OR
{{ $json.a || $json.b }}

// NOT
{{ !$json.value }}

// Nullish coalescing
{{ $json.value ?? 'default' }}
```

### Object Lookup
```javascript
// Map status codes
{{ { 'A': 'Active', 'I': 'Inactive', 'P': 'Pending' }[$json.status] }}

// With default
{{ { 'A': 'Active', 'I': 'Inactive' }[$json.status] ?? 'Unknown' }}
```

## Object Operations

### Create Objects
```javascript
// Inline object
{{ { name: $json.name, email: $json.email } }}

// Spread operator
{{ { ...$json, processed: true } }}

// Computed properties
{{ { [$json.keyName]: $json.value } }}
```

### Object Methods
```javascript
// Get keys
{{ Object.keys($json) }}

// Get values
{{ Object.values($json) }}

// Get entries
{{ Object.entries($json) }}

// Has property
{{ 'fieldName' in $json }}
{{ Object.hasOwn($json, 'field') }}
```

## Common Patterns

### Data Transformation
```javascript
// Rename fields
{{ { newName: $json.oldName, anotherField: $json.original } }}

// Add field
{{ { ...$json, newField: 'value' } }}

// Remove field (spread without)
{{ (({ removeThis, ...rest }) => rest)($json) }}

// Conditional field
{{ $json.include ? { field: $json.value } : {} }}
```

### String Building
```javascript
// URL building
{{ `https://api.example.com/${$json.resource}/${$json.id}` }}

// Email template
{{ `Dear ${$json.name},\n\nYour order #${$json.orderId} has been confirmed.` }}
```

### Aggregation
```javascript
// Sum
{{ $json.items.reduce((sum, i) => sum + i.price, 0) }}

// Average
{{ $json.values.reduce((a, b) => a + b, 0) / $json.values.length }}

// Group by
{{ Object.groupBy($json.items, item => item.category) }}
```

## Expression Debugging Tips

```javascript
// Check type
{{ typeof $json.value }}

// Check if array
{{ Array.isArray($json.value) }}

// Stringify for inspection
{{ JSON.stringify($json, null, 2) }}

// Log all keys
{{ Object.keys($json) }}
```
