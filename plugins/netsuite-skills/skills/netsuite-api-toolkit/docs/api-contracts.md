# API Contract Patterns

Best practices for maintaining type safety between frontend TypeScript and backend API responses.

## The Problem

TypeScript types are compile-time only. If API responses don't match your interfaces, you get runtime errors:

```typescript
// types.ts
interface User {
  id: string;
  firstName: string;  // Expected
  lastName: string;
}

// API actually returns:
{
  "id": "123",
  "first_name": "John",  // snake_case, not camelCase!
  "last_name": "Doe"
}

// Runtime crash:
console.log(user.firstName);  // undefined!
```

## Solution 1: Type Guards

Add runtime validation before using data:

```typescript
function isUser(obj: unknown): obj is User {
  return (
    obj !== null &&
    typeof obj === 'object' &&
    'id' in obj &&
    'firstName' in obj &&
    'lastName' in obj
  );
}

// Usage
const data = await fetchUser();
if (isUser(data)) {
  console.log(data.firstName);  // Safe!
} else {
  console.error('Invalid user data:', data);
}
```

## Solution 2: Zod Schemas

Use Zod for declarative validation with automatic type inference:

```typescript
import { z } from 'zod';

const UserSchema = z.object({
  id: z.string(),
  firstName: z.string(),
  lastName: z.string()
});

type User = z.infer<typeof UserSchema>;

// Usage
const result = UserSchema.safeParse(data);
if (result.success) {
  console.log(result.data.firstName);  // Typed and validated!
} else {
  console.error('Validation errors:', result.error.issues);
}
```

## Solution 3: Generate Types from API

Use `generate_types.py` to create TypeScript types from actual API responses:

```bash
# Generate types from live API
python3 generate_types.py --app homepage --action getOperationsStatus

# Output to file
python3 generate_types.py --app homepage --action getOperationsStatus \
  --output src/types/operations.generated.ts

# Include Zod schemas
python3 generate_types.py --app homepage --action getOperationsStatus --zod
```

## Solution 4: Validate Types Against API

Use `validate_types.py` to compare existing types with API responses:

```bash
# Validate types file
python3 validate_types.py \
  --types-file src/types/operations.ts \
  --app homepage \
  --action getOperationsStatus

# Example output:
# ⚠️  Fields in API but NOT in TypeScript (2):
#    + newField: string  (sample: "value")
#    + anotherField: number  (sample: 42)
# ❌ Type mismatches (1):
#    ≠ status: TS expects 'boolean', API returns 'string'
```

## Recommended Workflow

### Development Phase

1. **Fetch sample response**:
   ```bash
   python3 inspect_request.py --app homepage --action getOperationsStatus
   ```

2. **Generate initial types**:
   ```bash
   python3 generate_types.py --app homepage --action getOperationsStatus \
     --output src/types/operations.generated.ts
   ```

3. **Add type guards**:
   Use the `type_guard.ts` template to create runtime validation.

### Maintenance Phase

1. **Validate periodically**:
   ```bash
   # Add to CI/CD pipeline
   python3 validate_types.py \
     --types-file src/types/operations.ts \
     --app homepage \
     --action getOperationsStatus
   ```

2. **Regenerate when API changes**:
   ```bash
   python3 generate_types.py --app homepage --action getOperationsStatus \
     --output src/types/operations.generated.ts
   ```

## Common Type Mismatches

### 1. Case Sensitivity

**Problem**: API uses snake_case, TypeScript uses camelCase.

**Solution**: Transform at API boundary:
```typescript
function transformUser(raw: RawUser): User {
  return {
    id: raw.id,
    firstName: raw.first_name,
    lastName: raw.last_name
  };
}
```

### 2. Nested Arrays vs Objects

**Problem**: TypeScript expects object, API returns array.

```typescript
// TypeScript
interface Category {
  name: string;
  items: Item[];  // Flat array
}

// API returns
{
  "name": "Orders",
  "items": {  // Object with nested arrays!
    "pending": [...],
    "completed": [...]
  }
}
```

**Solution**: Flatten in transformer:
```typescript
function transformCategory(raw: RawCategory): Category {
  const allItems = [
    ...raw.items.pending,
    ...raw.items.completed
  ];
  return {
    name: raw.name,
    items: allItems
  };
}
```

### 3. Optional vs Required Fields

**Problem**: Field sometimes missing in API response.

**Solution**: Mark as optional in TypeScript:
```typescript
interface Job {
  id: string;
  status: string;
  lastRunTime?: string;  // Optional - not always present
  nextRunTime?: string;
}
```

### 4. Union Types

**Problem**: Field can be multiple types.

**Solution**: Use union types:
```typescript
interface ApiResponse {
  data: string | number | null;  // Can be any of these
  count: number | string;  // API sometimes returns "0" instead of 0
}
```

## Error Boundary Integration

Always wrap components that consume API data with Error Boundaries:

```tsx
import ErrorBoundary from './ErrorBoundary';

function App() {
  return (
    <ErrorBoundary fallbackTitle="Operations Dashboard">
      <OperationsDashboard />
    </ErrorBoundary>
  );
}
```

This prevents type mismatches from crashing the entire application.

## Checklist

- [ ] Generate types from actual API responses
- [ ] Add type guards for runtime validation
- [ ] Validate types against API in CI/CD
- [ ] Wrap API-consuming components with Error Boundaries
- [ ] Transform API responses at boundary (case conversion, flattening)
- [ ] Mark optional fields correctly
- [ ] Use union types for polymorphic fields
