# Review Focus Areas

Distilled from compound-engineering's ce:review persona catalog (17 personas across 4 layers).
Used to select review dimensions based on diff content for codex-review delegation.

---

## Always Applied

These dimensions apply to every review regardless of diff content.

### Correctness
- Logic errors (wrong operator, inverted condition, off-by-one)
- Null/undefined/empty handling gaps
- Edge cases not covered by the implementation
- State bugs (race conditions, stale reads, incorrect ordering)
- Error propagation failures (swallowed errors, wrong error type returned)
- Intent vs. implementation mismatch (code does not match what the name/comment implies)

### Testing
- Missing test cases for changed behavior (happy path, edge case, error path)
- Weak assertions that test implementation detail rather than observable behavior
- Tests that mock too much (no real integration path exercised)
- Test cases that exist but would not catch the bug being fixed
- Missing tests for new public functions or methods

### Maintainability
- Unnecessary coupling between unrelated modules
- Premature abstraction (DRY applied too early, wrong level)
- Dead code (unreachable branches, unused parameters, orphaned helpers)
- Naming that obscures intent (single-letter vars outside tight loops, misleading names)
- Functions doing more than one thing (mixed concerns)
- Indirection that adds complexity without value

### Project Standards
- Compliance with CLAUDE.md / AGENTS.md conventions visible in the diff
- Naming conventions from surrounding code
- Error handling patterns matching project conventions
- File organization and module structure following project patterns

---

## Conditionally Applied

Apply these only when the diff touches the relevant area.

### Security
*Apply when: auth, input handling, permissions, user data, external APIs touched*
- Auth/authz gaps (missing permission checks, wrong user context)
- Unvalidated or unsanitized user input passed to DB/shell/HTML
- Hardcoded secrets, credentials, or tokens in source
- Sensitive data exposed in logs, responses, or error messages
- Permission check ordering (auth before rate limit, etc.)
- SQL injection, XSS, command injection vectors

### Performance
*Apply when: DB queries, caching, async patterns, data transforms, pagination touched*
- N+1 queries (loop contains DB calls)
- Missing database indexes for new query patterns
- Unnecessary full-table scans or large result sets
- Cache invalidation logic gaps or thundering herd scenarios
- Unnecessary serialization/deserialization in hot paths
- Blocking I/O in async contexts

### API Contracts
*Apply when: HTTP routes, serializers, exported type signatures, versioning touched*
- Breaking changes to existing routes or response shapes
- Missing versioning for public API changes
- Serializer field mismatches (field renamed in schema but not in serializer)
- Undocumented response shape changes
- Inconsistent error response formats

### Reliability
*Apply when: error handling, retries, timeouts, background jobs, external calls touched*
- Missing error handling for external service calls (network, DB, third-party)
- Retry logic without idempotency guarantee (duplicate effects on retry)
- Missing timeouts on external calls
- Background job failure modes (no dead-letter queue, silent failures)
- Orphaned state on failure (DB row created before risky call, no cleanup on failure)
- Circuit breaker gaps for high-traffic paths

### Data Integrity
*Apply when: migrations, schema changes, backfills, data transformations touched*
- Migration reversibility (can this be rolled back?)
- Locking issues (lock timeout on large table migrations)
- Missing NOT NULL constraints on required fields
- Data loss risks (column dropped, type coercion, truncation)
- Transaction boundary gaps (related writes not in same transaction)
- Privacy compliance (PII in wrong table, missing encryption)

---

## Selection Heuristics

Use these grep patterns to decide which conditional dimensions to apply:

| Dimension | Trigger patterns in diff |
|-----------|--------------------------|
| Security | `auth`, `login`, `password`, `token`, `permission`, `role`, `user_id`, `params[`, `request.body`, `exec(`, `eval(`, `innerHTML` |
| Performance | `SELECT`, `find_by`, `where(`, `includes(`, `.all`, `cache`, `redis`, `async`, `await`, `map(`, `filter(`, `reduce(` |
| API Contracts | `routes`, `controller`, `serializer`, `schema`, `interface`, `type`, `export`, `@app.route`, `router.` |
| Reliability | `rescue`, `catch`, `try`, `retry`, `timeout`, `job`, `worker`, `queue`, `external`, `http.`, `fetch(` |
| Data Integrity | `migration`, `schema`, `add_column`, `drop_column`, `ALTER TABLE`, `backfill`, `CREATE TABLE`, `foreign_key` |
