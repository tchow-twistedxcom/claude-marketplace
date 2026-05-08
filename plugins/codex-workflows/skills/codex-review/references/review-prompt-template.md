# Review Prompt Templates

Use these templates to build the review instruction file at
`.context/codex-workflows/codex-review/<run-id>/review-instructions.md`.

Substitute `{PLACEHOLDERS}` with actual values before writing.

---

## Template: report-only Mode

Piped to `codex review` stdin via `- <` flag.

```xml
<review-focus>
Review the diff for the following dimensions. For each finding, be specific:
include the file name, line number, a short issue title (≤10 words), why it
matters (impact, not description), and a suggested fix only if it is clear and
correct.

{FOCUS_AREAS_LIST}
</review-focus>

<requirements>
{PLAN_REQUIREMENTS_IF_AVAILABLE}
</requirements>

<format>
Present findings grouped by severity:

**P0 — Blockers** (data loss, security holes, breaking changes)
**P1 — High** (bugs that will surface in normal use)
**P2 — Medium** (degraded behavior, poor test coverage)
**P3 — Low** (style, naming, minor improvements)

For each finding:
  File: <path>:<line>
  Issue: <title>
  Why: <impact>
  Fix: <suggested fix or "needs design decision">

End with a one-line verdict:
  > **Ready to merge** | **Ready with fixes** | **Needs work**
  > <one sentence rationale>
</format>
```

---

## Template: autofix Mode

Piped to `codex exec` stdin via `- <` flag.

```xml
<task>
Review the code changes below and produce a structured review report.

For each issue found:
1. Classify severity (P0=blocker, P1=high, P2=medium, P3=low)
2. Classify autofix_class:
   - safe_auto: local, deterministic fix (rename, add null check, add missing test)
   - gated_auto: concrete fix that changes behavior or contracts (needs human approval)
   - manual: requires design decision or context unavailable in the diff
   - advisory: report-only, no code change needed
3. For safe_auto findings: apply the fix directly to the file
4. For all other findings: report without touching the files

{FOCUS_AREAS_LIST}
</task>

<diff>
{DIFF_CONTENT}
</diff>

<requirements>
{PLAN_REQUIREMENTS_IF_AVAILABLE}
</requirements>

<constraints>
- Do NOT run git commit, git push, or create PRs -- the orchestrating agent handles all git operations
- Apply ONLY safe_auto fixes -- leave gated_auto, manual, and advisory findings untouched
- Restrict all file modifications to the repository root
- If you discover mid-execution that a safe_auto fix requires changes outside the diff scope, downgrade it to gated_auto and report without fixing
- Resolve the task fully before stopping
</constraints>

<output_contract>
Report your result via the --output-schema mechanism. Fill in every field:
- status: "completed" ONLY if the review is thorough AND all safe_auto fixes were applied (or there were none)
  "partial" if you could not review all files
  "failed" if no meaningful review was produced
- findings: array of all findings (including applied safe_auto fixes)
- files_modified: array of files you changed (empty if report-only or no safe_auto fixes)
- summary: one-paragraph description of the overall code quality and key concerns
- testing_gaps: array of missing tests or weak coverage found
- residual_risks: array of concerns that require human attention (gated_auto, manual items)
</output_contract>
```

---

## Focus Areas Rendering

When building `{FOCUS_AREAS_LIST}`, format selected areas as:

```
Focus areas for this review:

ALWAYS APPLY:
- Correctness: logic errors, off-by-one errors, null/undefined handling, edge cases,
  incorrect error propagation, state bugs
- Testing: coverage gaps (missing happy path, edge case, or error path tests), weak
  assertions (testing implementation detail rather than behavior), brittle tests
- Maintainability: unnecessary coupling, premature abstraction, dead code, naming that
  obscures intent, functions doing more than one thing
- Project standards: compliance with CLAUDE.md / AGENTS.md conventions visible in the diff

CONDITIONALLY APPLIED (include only if selected):
- Security: auth/authz gaps, unvalidated user input, hardcoded secrets, exposed sensitive
  data, permission check ordering
- Performance: N+1 queries, missing indexes, unnecessary full-table scans, cache
  invalidation logic, unnecessary serialization in hot paths
- API contracts: breaking changes to routes or type signatures, missing versioning,
  serializer mismatches, undocumented response shape changes
- Reliability: missing error handling for external calls, retry logic correctness,
  timeout gaps, background job failure modes, orphaned state on failure
- Data integrity: migration safety (reversibility, locking), constraint gaps, transaction
  boundaries, privacy compliance
```

---

## Plan Requirements Rendering

If a `plan:` path was provided and the file was read successfully, use:

```
Requirements from plan document (<plan-path>):
<bullet list of key requirements and acceptance criteria from the plan>

Verify that the changes satisfy all stated requirements. Flag any requirements
that appear unimplemented or partially implemented.
```

If no plan path was provided, use:

```
No plan document provided. Review for general correctness and quality.
```
