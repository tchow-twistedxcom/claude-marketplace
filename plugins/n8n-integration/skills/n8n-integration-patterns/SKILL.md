# n8n Integration Patterns

---
name: n8n-integration-patterns
description: "Best practices and patterns for n8n workflows: webhook design, data synchronization, error handling, rate limiting, and performance optimization"
version: 1.0.0
license: MIT
---

## Purpose

Provide architectural patterns, best practices, and implementation guidance for building robust n8n workflows. This skill focuses on design patterns rather than individual node configuration.

## Activation Triggers

- "n8n best practices"
- "workflow pattern"
- "integration pattern"
- "n8n architecture"
- "webhook design"
- "data sync pattern"
- "error handling pattern"
- "rate limiting"
- "performance optimization"
- "robust workflow"
- "production workflow"

## Pattern Categories

```yaml
categories:
  webhook_patterns:
    description: "HTTP endpoint design and security"
    reference: "references/webhook-patterns.md"
    topics:
      - Authentication strategies
      - Request validation
      - Response handling
      - Webhook security

  data_sync_patterns:
    description: "Data synchronization between systems"
    reference: "references/data-sync-patterns.md"
    topics:
      - Full sync vs incremental
      - Change detection
      - Conflict resolution
      - Batch processing

  error_handling:
    description: "Graceful failure and recovery"
    reference: "references/error-handling.md"
    topics:
      - Error classification
      - Retry strategies
      - Fallback patterns
      - Dead letter queues

  rate_limiting:
    description: "API quota management"
    reference: "references/rate-limiting.md"
    topics:
      - Throttling patterns
      - Backoff strategies
      - Queue management
      - Quota tracking

  performance:
    description: "Workflow optimization"
    reference: "references/performance-optimization.md"
    topics:
      - Parallel processing
      - Memory management
      - Execution time reduction
      - Batch optimization
```

## Workflow Consultation Process

### Phase 1: Requirements Analysis
```yaml
questions:
  - What systems are being integrated?
  - What is the data volume and frequency?
  - What are the error tolerance requirements?
  - Are there rate limiting constraints?
  - What is the expected latency?
```

### Phase 2: Pattern Selection
```yaml
selection_criteria:
  webhook_patterns:
    when:
      - External systems calling n8n
      - API endpoint requirements
      - Real-time event processing

  data_sync_patterns:
    when:
      - Bidirectional data flow
      - Regular synchronization needs
      - Multiple data sources

  error_handling:
    when:
      - Critical data workflows
      - Unreliable external APIs
      - Production environments

  rate_limiting:
    when:
      - Third-party API integrations
      - High-volume workflows
      - Quota-constrained APIs

  performance:
    when:
      - Large data volumes
      - Time-sensitive operations
      - Resource constraints
```

### Phase 3: Pattern Application
```yaml
implementation:
  1. Select appropriate pattern from reference
  2. Adapt to specific requirements
  3. Build workflow with pattern principles
  4. Add error handling and monitoring
  5. Validate and optimize
```

## Common Integration Architectures

### Hub-and-Spoke Pattern
```yaml
pattern: hub_and_spoke
description: "Central n8n hub connecting multiple spokes"
structure:
  hub: n8n instance
  spokes:
    - CRM (Salesforce, HubSpot)
    - ERP (NetSuite, SAP)
    - Marketing (Mailchimp, Klaviyo)
    - Support (Zendesk, Freshdesk)
use_case: "Enterprise data orchestration"
```

### Event-Driven Pattern
```yaml
pattern: event_driven
description: "React to events from multiple sources"
components:
  - Webhook triggers
  - Message queues
  - Event routers
  - Event handlers
use_case: "Real-time integrations"
```

### Batch Processing Pattern
```yaml
pattern: batch_processing
description: "Process large volumes on schedule"
components:
  - Schedule trigger
  - Pagination handling
  - Batch splitting
  - Result aggregation
use_case: "Data warehousing, reporting"
```

### Saga Pattern
```yaml
pattern: saga
description: "Distributed transactions with compensation"
components:
  - Transaction steps
  - Compensation handlers
  - State tracking
  - Rollback logic
use_case: "Multi-system updates requiring consistency"
```

## Tool Usage

### Pattern Research
```yaml
templates:
  tool: search_templates
  params:
    query: "<pattern type>"
  purpose: "Find real-world pattern implementations"

documentation:
  tool: get_node_documentation
  params:
    nodeType: "<relevant node>"
  purpose: "Understand node capabilities for pattern"
```

### Pattern Validation
```yaml
validation:
  tool: validate_workflow
  params:
    workflow: "<workflow JSON>"
  purpose: "Verify pattern implementation"
```

## Best Practices Summary

### Design Principles
```yaml
principles:
  idempotency:
    description: "Same input always produces same result"
    implementation: "Use unique IDs, check before create"

  resilience:
    description: "Handle failures gracefully"
    implementation: "Retries, fallbacks, circuit breakers"

  observability:
    description: "Know what's happening"
    implementation: "Logging, monitoring, alerting"

  scalability:
    description: "Handle growth"
    implementation: "Pagination, batching, async processing"
```

### Anti-Patterns to Avoid
```yaml
anti_patterns:
  tight_coupling:
    problem: "Direct dependencies between workflows"
    solution: "Use webhooks or queues for loose coupling"

  no_error_handling:
    problem: "Workflows fail silently"
    solution: "Always implement error branches"

  hardcoded_values:
    problem: "Configuration in workflow logic"
    solution: "Use environment variables and workflow variables"

  monolithic_workflows:
    problem: "One massive workflow doing everything"
    solution: "Break into focused sub-workflows"

  no_validation:
    problem: "Processing invalid data"
    solution: "Validate inputs before processing"
```

## Integration with Other Skills

```yaml
workflow_builder:
  provides: "Node configurations and connections"
  receives: "Pattern requirements"

workflow_manager:
  provides: "Deployment and lifecycle management"
  receives: "Pattern-based workflows"

troubleshooter:
  provides: "Debugging and diagnostics"
  receives: "Pattern failure scenarios"
```

## Output Format

When applying patterns, provide:

```markdown
## Pattern Recommendation

**Selected Pattern**: [Pattern name]

**Rationale**: [Why this pattern fits the requirements]

**Key Components**:
- [Component 1]: [Purpose]
- [Component 2]: [Purpose]

**Implementation Considerations**:
- [Consideration 1]
- [Consideration 2]

**Workflow Structure**:
[High-level node flow]

**Error Handling**:
[Error handling approach]

**Monitoring**:
[What to monitor]
```
