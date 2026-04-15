---
name: codex-lfg
description: "Full autonomous engineering workflow with Codex delegation for BOTH work and review phases. Plan locally, delegate implementation and review to Codex. Use when you want to lfg with codex, run the full pipeline with codex, or want codex to do both the work and review."
argument-hint: "[feature description or plan path]"
disable-model-invocation: true
---

# Codex LFG — Full Engineering Pipeline with Codex Delegation

CRITICAL: You MUST execute every step below IN ORDER. Do NOT skip any required step. Do NOT jump ahead to coding or implementation. The plan phase (step 1) MUST be completed and verified BEFORE any work begins. Violating this order produces bad output.

This pipeline is the Codex-delegation variant of `/lfg`. It delegates the implementation and review phases to Codex while retaining local control of planning, todo resolution, and browser testing.

**Token economics:** Implementation + review tokens run on the Codex model, freeing the orchestrating Claude Code context for orchestration and decision-making.

---

## Pipeline

### Step 1: Plan

Run:
```
/ce:plan $ARGUMENTS
```

**GATE — STOP.** Verify that `ce:plan` produced a plan file in `docs/plans/`. If no plan file was created:
- If `ce:plan` reported the task is non-software and cannot be processed in pipeline mode, stop the pipeline and inform the user that codex-lfg requires software tasks.
- Otherwise, run `/ce:plan $ARGUMENTS` again.

Do NOT proceed to step 2 until a written plan exists.

**Record the plan file path.** It is passed to the review step.

---

### Step 2: Work (Codex Delegated)

Run:
```
/ce:work-beta delegate:codex
```

This delegates code implementation to Codex via `codex exec`. The work-beta skill handles:
- Pre-delegation checks (availability, consent, environment guard)
- Batching and prompt construction
- Background execution with polling
- Rollback on failure
- Fallback to standard `ce:work` if Codex is unavailable

**GATE — STOP.** Verify that implementation work was performed -- files were created or modified beyond the plan file itself. Do NOT proceed to step 3 if no code changes were made.

---

### Step 3: Review (Codex Delegated)

Run:
```
/codex-workflows:codex-review mode:autofix plan:<plan-path-from-step-1>
```

This delegates code review to Codex. The codex-review skill handles:
- Pre-delegation checks (availability, consent, environment guard)
- Scope detection from diff
- Background execution via `codex exec`
- Structured findings with applied safe_auto fixes
- Fallback to `/ce:review mode:autofix plan:<plan-path>` if Codex is unavailable

Pass the plan file path from step 1 so the review can verify requirements completeness.

---

### Step 4: Todo Resolution

Run:
```
/compound-engineering:todo-resolve
```

Resolves any todos created by the review step.

---

### Step 5: Browser Tests

Run:
```
/compound-engineering:test-browser
```

Runs browser tests on pages affected by the changes.

---

### Step 6: Complete

Output:
```
<promise>DONE</promise>
```

---

## Fallback Behavior

Both Codex delegation steps degrade gracefully if Codex is unavailable:
- **Step 2:** `ce:work-beta` falls back to standard `ce:work` automatically
- **Step 3:** `codex-review` falls back to `/ce:review mode:autofix plan:<path>` automatically

The pipeline always completes even without Codex. The delegation is a performance optimization, not a hard dependency.

---

## Differences from Upstream `/lfg`

| | Upstream `lfg` | `codex-lfg` |
|---|---|---|
| Implementation | `/ce:work` | `/ce:work-beta delegate:codex` |
| Review | `/ce:review mode:autofix` | `/codex-workflows:codex-review mode:autofix` |
| Fallback | None | Both Codex steps fall back to standard skills |
| ralph-loop | Step 1 (if available) | Not included (optional, can be added manually before invoking) |

---

Start with step 1 now. Remember: plan FIRST, then work. Never skip the plan.
