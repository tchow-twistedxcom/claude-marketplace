# Research & Exploration Example

Complete walkthrough of exploring an unfamiliar codebase using Claude Code.

---

## Scenario

**Request**: "I just joined a new project. Help me understand how the codebase is organized and how the main features work."

**Context**:
- Large TypeScript project
- No prior knowledge of architecture
- Need to understand before making changes

---

## Step 1: Initial Exploration

### Get High-Level Overview

Start with the Explore agent for broad discovery:

```
User: "Help me understand this codebase structure"

Task (Explore): "Analyze the overall structure of this codebase. Identify:
1. Directory organization
2. Main entry points
3. Core modules/features
4. Technology stack"
```

Explore agent findings:
```
Directory Structure:
├── src/
│   ├── api/          # REST API routes
│   ├── services/     # Business logic
│   ├── models/       # Database models
│   ├── utils/        # Shared utilities
│   └── index.ts      # Entry point
├── tests/
├── docs/
└── config/

Tech Stack:
- Node.js + TypeScript
- Express.js (API framework)
- PostgreSQL (database)
- Prisma (ORM)
- Jest (testing)
```

---

## Step 2: Understand Key Components

### Find Main Features

```
Glob: src/api/**/*.ts
→ Found 12 route files

Read: src/api/index.ts (parallel with below)
Read: src/index.ts
```

Identified main API domains:
- `/api/users` - User management
- `/api/products` - Product catalog
- `/api/orders` - Order processing
- `/api/auth` - Authentication

### Deep Dive into Core Feature

Pick the most important feature to understand in detail:

```
Task (Explore): "Trace how an order is processed from API request to database.
Include validation, business logic, and data persistence steps."
```

Order processing flow discovered:
```
1. POST /api/orders
   └─ src/api/orders.ts:createOrder()
      └─ src/services/orderService.ts:create()
         ├─ Validate cart items
         ├─ Check inventory
         ├─ Calculate totals
         └─ src/models/order.ts (Prisma)
            └─ Database transaction
```

---

## Step 3: Understand Patterns

### Find Coding Patterns

```
Grep: "async function" in src/services/ -A 5
→ Shows service method patterns

Grep: "router\.(get|post|put|delete)" in src/api/
→ Shows API route patterns
```

Identified patterns:
- Services use async/await with try-catch
- API routes follow RESTful conventions
- Validation uses Zod schemas
- Errors handled by middleware

### Read Pattern Examples

```
Read: src/services/orderService.ts (lines 1-50)
Read: src/api/orders.ts (lines 1-50)
Read: src/middleware/errorHandler.ts
```

---

## Step 4: Map Dependencies

### Find How Components Connect

```
Task (Explore): "Map the dependencies between services. Which services
call other services? What are the shared utilities?"
```

Dependency map:
```
orderService
├─ uses: userService (get user data)
├─ uses: productService (check inventory)
├─ uses: paymentService (process payment)
└─ uses: emailService (send confirmation)

All services use:
├─ src/utils/logger.ts
├─ src/utils/errors.ts
└─ src/utils/validators.ts
```

### Understand Database Schema

```
Read: prisma/schema.prisma

Key models:
- User (1:N Orders, 1:1 Profile)
- Product (N:M Orders via OrderItem)
- Order (1:N OrderItems, N:1 User)
```

---

## Step 5: Identify Entry Points

### Find Where to Start

```
Grep: "TODO|FIXME|HACK" in src/
→ Found 3 TODOs in orderService (potential improvement areas)

Read: docs/CONTRIBUTING.md
→ Found development guidelines and conventions
```

### Understand Test Structure

```
Glob: tests/**/*.test.ts
→ Found 24 test files

Read: tests/services/orderService.test.ts (lines 1-30)
→ Shows how to test services
```

---

## Step 6: Create Summary

### Document Findings

Based on exploration, create mental model:

```
CODEBASE SUMMARY
================

Architecture: Layered (API → Service → Model)

Key Directories:
- src/api/      : Express routes, request handling
- src/services/ : Business logic, orchestration
- src/models/   : Prisma models, database layer
- src/utils/    : Shared helpers, logging, errors

Main Features:
1. User Management - CRUD, profiles, auth
2. Product Catalog - Inventory, categories
3. Order Processing - Cart, checkout, payments

Patterns:
- Async services with try-catch
- Zod validation schemas
- Centralized error handling
- Prisma for database operations

Entry Points for New Work:
- Add feature: Create route → service → model
- Fix bug: Start at API, trace through service
- Add test: Mirror structure in tests/
```

---

## Tool Usage Summary

| Step | Tool | Purpose |
|------|------|---------|
| Broad overview | Task (Explore) | Initial discovery |
| Find files | Glob | Directory scanning |
| Read code | Read (parallel) | Understand implementation |
| Search patterns | Grep | Find conventions |
| Deep analysis | Task (Explore) | Trace feature flows |
| Documentation | Read | Check existing docs |

---

## Key Takeaways

1. **Start broad**: Use Explore agent for initial overview
2. **Go deep selectively**: Pick one feature to trace end-to-end
3. **Find patterns**: Grep for common code patterns
4. **Map dependencies**: Understand how components connect
5. **Read existing docs**: Check CONTRIBUTING.md, README, etc.
6. **Create mental model**: Summarize for future reference

---

## Alternative Approaches

### For Smaller Codebases
Skip agents, use direct tools:
```
Glob → Read → Grep → Read
```

### For Specific Questions
Use targeted exploration:
```
Task (Explore): "How does authentication work in this codebase?"
```

### For Complex Architecture
Use feature-dev:code-explorer:
```
Task (feature-dev:code-explorer): "Analyze the payment processing
architecture, including external integrations and error handling"
```

---

## Common Exploration Queries

```
# Overall structure
"What is the directory structure and main components?"

# Specific feature
"How does [feature X] work from request to response?"

# Patterns
"What patterns are used for [validation/error handling/logging]?"

# Dependencies
"What external services/APIs does this integrate with?"

# Testing
"How are tests organized and what's the testing strategy?"

# Configuration
"Where is configuration stored and how is it loaded?"
```

---

*See also: [workflows.md](../references/workflows.md) for workflow patterns*
