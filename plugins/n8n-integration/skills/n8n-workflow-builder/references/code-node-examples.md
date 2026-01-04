# n8n Code Node Examples

Common patterns and examples for the Code node.

## Code Node Basics

### Node Configuration
```json
{
  "id": "code-1",
  "name": "Code",
  "type": "n8n-nodes-base.code",
  "typeVersion": 2,
  "position": [500, 300],
  "parameters": {
    "jsCode": "// Your JavaScript code here\nreturn items;"
  }
}
```

### Required Return Format
```javascript
// Must return an array of items
// Each item must have a json property
return items.map(item => ({
  json: {
    // your data here
  }
}));

// Or create new items
return [
  { json: { field1: "value1" } },
  { json: { field2: "value2" } }
];
```

## Data Transformation

### Transform All Items
```javascript
// Transform each item
return items.map(item => ({
  json: {
    id: item.json.id,
    fullName: `${item.json.firstName} ${item.json.lastName}`,
    email: item.json.email.toLowerCase(),
    createdAt: new Date().toISOString()
  }
}));
```

### Filter Items
```javascript
// Filter items based on condition
return items.filter(item =>
  item.json.status === 'active' &&
  item.json.amount > 100
);
```

### Add Calculated Fields
```javascript
// Add new fields to existing data
return items.map(item => ({
  json: {
    ...item.json,
    total: item.json.price * item.json.quantity,
    taxAmount: item.json.price * item.json.quantity * 0.1,
    processed: true
  }
}));
```

### Rename Fields
```javascript
// Rename fields for API compatibility
return items.map(item => ({
  json: {
    user_id: item.json.userId,
    user_name: item.json.userName,
    user_email: item.json.userEmail
  }
}));
```

## Array Operations

### Flatten Nested Array
```javascript
// Flatten nested items into separate items
const results = [];
for (const item of items) {
  for (const child of item.json.children) {
    results.push({
      json: {
        parentId: item.json.id,
        ...child
      }
    });
  }
}
return results;
```

### Group Items
```javascript
// Group items by a field
const grouped = {};
for (const item of items) {
  const key = item.json.category;
  if (!grouped[key]) {
    grouped[key] = [];
  }
  grouped[key].push(item.json);
}

return Object.entries(grouped).map(([category, items]) => ({
  json: { category, items, count: items.length }
}));
```

### Aggregate Data
```javascript
// Calculate aggregations
const sum = items.reduce((acc, item) => acc + item.json.amount, 0);
const count = items.length;
const avg = sum / count;
const max = Math.max(...items.map(i => i.json.amount));
const min = Math.min(...items.map(i => i.json.amount));

return [{
  json: { sum, count, avg, max, min }
}];
```

### Sort Items
```javascript
// Sort items by field
const sorted = [...items].sort((a, b) =>
  a.json.name.localeCompare(b.json.name)
);
return sorted;

// Sort by number descending
const sortedByAmount = [...items].sort((a, b) =>
  b.json.amount - a.json.amount
);
return sortedByAmount;
```

### Remove Duplicates
```javascript
// Remove duplicates by field
const seen = new Set();
return items.filter(item => {
  const key = item.json.email;
  if (seen.has(key)) return false;
  seen.add(key);
  return true;
});
```

## String Processing

### Parse JSON String
```javascript
// Parse JSON from string field
return items.map(item => ({
  json: {
    ...item.json,
    parsedData: JSON.parse(item.json.jsonString)
  }
}));
```

### Format Strings
```javascript
// Format strings
return items.map(item => ({
  json: {
    ...item.json,
    slug: item.json.title.toLowerCase().replace(/\s+/g, '-'),
    truncated: item.json.description.slice(0, 100) + '...',
    cleaned: item.json.text.trim().replace(/\n/g, ' ')
  }
}));
```

### Extract from String
```javascript
// Extract data from string using regex
const emailRegex = /[\w.-]+@[\w.-]+\.\w+/g;

return items.map(item => {
  const emails = item.json.text.match(emailRegex) || [];
  return {
    json: {
      ...item.json,
      extractedEmails: emails
    }
  };
});
```

## Date Operations

### Format Dates
```javascript
// Format dates using Luxon (built-in)
const { DateTime } = require('luxon');

return items.map(item => ({
  json: {
    ...item.json,
    formattedDate: DateTime.fromISO(item.json.date).toFormat('MMMM d, yyyy'),
    dayOfWeek: DateTime.fromISO(item.json.date).weekdayLong
  }
}));
```

### Date Calculations
```javascript
const { DateTime } = require('luxon');

return items.map(item => {
  const date = DateTime.fromISO(item.json.date);
  const now = DateTime.now();

  return {
    json: {
      ...item.json,
      daysAgo: Math.floor(now.diff(date, 'days').days),
      isExpired: date < now,
      nextWeek: date.plus({ weeks: 1 }).toISO()
    }
  };
});
```

## API Data Processing

### Build API Payload
```javascript
// Prepare data for API call
return [{
  json: {
    method: 'POST',
    url: 'https://api.example.com/data',
    body: {
      records: items.map(item => ({
        id: item.json.id,
        name: item.json.name
      }))
    }
  }
}];
```

### Parse API Response
```javascript
// Parse and normalize API response
const response = items[0].json;

return response.data.items.map(item => ({
  json: {
    id: item.id,
    name: item.attributes.name,
    createdAt: item.attributes.created_at,
    tags: item.relationships.tags.map(t => t.name)
  }
}));
```

## Error Handling

### Try-Catch Pattern
```javascript
return items.map(item => {
  try {
    // Risky operation
    const data = JSON.parse(item.json.jsonString);
    return {
      json: { ...item.json, parsed: data, success: true }
    };
  } catch (error) {
    return {
      json: {
        ...item.json,
        success: false,
        error: error.message
      }
    };
  }
});
```

### Validation
```javascript
// Validate and filter valid items
const validItems = [];
const invalidItems = [];

for (const item of items) {
  const errors = [];

  if (!item.json.email?.includes('@')) {
    errors.push('Invalid email');
  }
  if (!item.json.name?.trim()) {
    errors.push('Name required');
  }

  if (errors.length === 0) {
    validItems.push(item);
  } else {
    invalidItems.push({
      json: { ...item.json, errors }
    });
  }
}

// Return valid items to main output
// Could use second output for invalid
return validItems;
```

## Multi-Item Operations

### Combine Items
```javascript
// Combine all items into single summary
return [{
  json: {
    totalItems: items.length,
    totalAmount: items.reduce((sum, i) => sum + i.json.amount, 0),
    items: items.map(i => i.json)
  }
}];
```

### Split Single Item to Multiple
```javascript
// Split one item into multiple
const item = items[0].json;
return item.products.map(product => ({
  json: {
    orderId: item.orderId,
    customerName: item.customerName,
    product: product
  }
}));
```

## Accessing Previous Nodes

### Access Specific Node Data
```javascript
// Access data from a specific node
const httpData = $node["HTTP Request"].json;
const setData = $node["Set Node Name"].json;

return [{
  json: {
    fromHttp: httpData.response,
    fromSet: setData.customField
  }
}];
```

## Common Utility Functions

### UUID Generation
```javascript
// Generate UUIDs for items
const { randomUUID } = require('crypto');

return items.map(item => ({
  json: {
    ...item.json,
    uuid: randomUUID()
  }
}));
```

### Hashing
```javascript
// Hash sensitive data
const crypto = require('crypto');

return items.map(item => ({
  json: {
    ...item.json,
    hashedEmail: crypto
      .createHash('sha256')
      .update(item.json.email)
      .digest('hex')
  }
}));
```

### Delay Processing
```javascript
// Add delay (use cautiously)
await new Promise(resolve => setTimeout(resolve, 1000));

return items;
```

## Best Practices

```yaml
guidelines:
  - Always return array of items
  - Each item needs json property
  - Use try-catch for error handling
  - Keep code focused and simple
  - Use comments for complex logic
  - Test with sample data first

performance:
  - Avoid blocking operations
  - Use const/let, not var
  - Minimize external calls
  - Process in batches if needed

debugging:
  - Use console.log for debugging
  - Check execution data in n8n
  - Test expressions separately
```
