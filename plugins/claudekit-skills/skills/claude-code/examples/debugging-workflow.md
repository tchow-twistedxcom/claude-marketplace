# Debugging Workflow Example

Complete walkthrough of debugging a complex issue using Claude Code.

---

## Scenario

**Problem**: User reports "API endpoint returns 500 error intermittently"

**Symptoms**:
- GET /api/users sometimes fails
- Error: "Cannot read property 'id' of undefined"
- Happens ~20% of requests

---

## Step 1: Understand the Problem

### Gather Context

First, reproduce and understand the issue:

```
User: "The /api/users endpoint is failing intermittently with a 500 error"

Claude: Let me investigate this issue. I'll start by understanding the error context.
```

**Tools used**: Read (for error logs), Grep (for error pattern)

```
Grep: "Cannot read property 'id' of undefined" in src/
→ Found in: src/api/users.ts:45
```

---

## Step 2: Investigate Root Cause

### Read the Affected Code

```
Read: src/api/users.ts

Found:
43│ async function getUsers(req, res) {
44│   const users = await db.users.findAll();
45│   const enriched = users.map(u => ({ ...u, name: u.profile.name }));
46│   return res.json(enriched);
47│ }
```

**Initial hypothesis**: `u.profile` is sometimes undefined

### Verify Hypothesis

```
Grep: "profile" in src/models/user.ts
→ Found: profile is an optional relation

Read: src/models/user.ts:20-30
→ Confirms: profile?: UserProfile (optional field)
```

### Use Root Cause Analyst for Deep Investigation

For complex bugs, delegate to specialized agent:

```
Task (root-cause-analyst): "Investigate why user.profile is sometimes undefined
in the getUsers API endpoint. The profile field is optional in the User model
but the code assumes it always exists."
```

Agent findings:
1. `findAll()` doesn't include profile relation by default
2. Some users have no profile (new registrations)
3. Race condition: profile created async after user

---

## Step 3: Fix the Issue

### Plan the Fix

Three options identified:
1. Add null check (quick fix)
2. Always include profile relation (proper fix)
3. Make profile non-optional (schema change)

**Chosen**: Option 2 - Include relation + null safety

### Apply the Fix

```
Edit: src/api/users.ts
old_string: const users = await db.users.findAll();
new_string: const users = await db.users.findAll({ include: ['profile'] });
```

```
Edit: src/api/users.ts
old_string: const enriched = users.map(u => ({ ...u, name: u.profile.name }));
new_string: const enriched = users.map(u => ({ ...u, name: u.profile?.name ?? 'Unknown' }));
```

---

## Step 4: Verify the Fix

### Run Tests

```
Bash: npm test -- --grep "users API"

Output:
✓ GET /api/users returns all users
✓ GET /api/users handles missing profiles
✓ GET /api/users includes profile data
3 passing (245ms)
```

### Manual Verification

```
Bash: curl http://localhost:3000/api/users | jq '.[:2]'

Output:
[
  { "id": 1, "name": "John Doe", ... },
  { "id": 2, "name": "Unknown", ... }
]
```

---

## Tool Usage Summary

| Step | Tool | Purpose |
|------|------|---------|
| Find error location | Grep | Search for error message |
| Read source code | Read | Understand implementation |
| Search related code | Grep | Find model definition |
| Deep investigation | Task (root-cause-analyst) | Complex analysis |
| Apply fix | Edit | Modify source files |
| Run tests | Bash | Verify fix works |

---

## Key Takeaways

1. **Start with symptoms**: Use Grep to find error source quickly
2. **Form hypothesis**: Read code to understand the logic
3. **Verify hypothesis**: Search for related code (models, dependencies)
4. **Use agents for complex issues**: root-cause-analyst provides systematic analysis
5. **Fix minimally**: Address the root cause, not symptoms
6. **Always verify**: Run tests and manual checks

---

## Alternative Approaches

### For Simpler Bugs
Skip the agent, use direct tools:
```
Grep → Read → Edit → Bash (test)
```

### For Complex System Issues
Use multiple agents in parallel:
```
Task (root-cause-analyst): "Investigate API errors"
Task (performance-engineer): "Check for related performance issues"
```

### When Root Cause is Unclear
Use Explore agent first:
```
Task (Explore): "How does the user profile system work in this codebase?"
```

---

*See also: [workflows.md](../references/workflows.md) for workflow patterns*
