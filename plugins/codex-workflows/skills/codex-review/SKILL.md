---
name: codex-review
description: "Delegate code review to Codex CLI. Use when you want Codex to do the PR review, code review, or want to run review with codex. Supports report-only (default) and autofix modes. Reuses compound-engineering scope detection pattern."
argument-hint: "[mode:autofix] [mode:report-only] [plan:<path>] [base:<ref>]"
disable-model-invocation: true
---

# Codex Review

Delegate code review to the Codex CLI. Uses `codex review` for fast, read-only analysis and `codex exec` with structured output for autofix mode. Extends compound-engineering's Codex delegation pattern to the review phase.

## Input Arguments

<input_arguments> #$ARGUMENTS </input_arguments>

## Argument Parsing

Parse `$ARGUMENTS` for the following optional tokens. Strip each recognized token before interpreting the remainder.

| Token | Example | Effect |
|-------|---------|--------|
| `mode:autofix` | `mode:autofix` | Use `codex exec` with structured findings; apply safe_auto fixes |
| `mode:report-only` | `mode:report-only` | Use `codex review` read-only (default) |
| `base:<ref>` | `base:origin/main` | Skip scope detection, use as diff base |
| `plan:<path>` | `plan:docs/plans/foo.md` | Load plan for requirements verification context |

**Default mode:** `report-only`. Codex delegation is inherently non-interactive -- no "interactive" mode.

**Fuzzy activation:** Also recognize "review with codex", "codex review", "delegate review to codex" as equivalent to the default invocation.

### Settings Resolution Chain

**Config (pre-resolved):**
!`cat "$(git rev-parse --show-toplevel 2>/dev/null)/.compound-engineering/config.local.yaml" 2>/dev/null || cat "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)")/.compound-engineering/config.local.yaml" 2>/dev/null || echo '__NO_CONFIG__'`

If the block above contains YAML, extract values for keys below. If it shows `__NO_CONFIG__`, all settings fall through to defaults.

Config keys:
- `review_delegate` -- `codex` or default `false`
- `review_delegate_consent` -- `true` or default `false`
- `review_delegate_model` -- Codex model (default `gpt-5.4`)
- `review_delegate_effort` -- `minimal`, `low`, `medium`, `high` (default), or `xhigh`
- `review_delegate_decision` -- `auto` (default) or `ask`
- `work_delegate_sandbox` -- reuse: `yolo` (default) or `full-auto` (for autofix mode)

Resolution chain (highest to lowest priority):
1. Argument flag (if present)
2. Config file values
3. Hard defaults

Store resolved state:
- `review_mode` -- `report-only` or `autofix`
- `review_delegate_active` -- boolean (from config or argument)
- `review_model` -- string (default `gpt-5.4`)
- `review_effort` -- string (default `high`)
- `review_consent` -- boolean (from config)
- `sandbox_mode` -- `yolo` or `full-auto` (from `work_delegate_sandbox`, used by autofix)

---

## Execution Workflow

Read `references/codex-review-workflow.md` for the complete delegation workflow including pre-checks, mode-specific execution, result processing, and fallback handling.

### Phase 0: Pre-Delegation Checks

Run the checks in `references/codex-review-workflow.md` (Pre-Delegation Checks section). If any check fails, fall back to `/ce:review mode:<review_mode>` with any `plan:` argument passed through.

### Phase 1: Scope Detection

**If `base:` argument provided:** Use that ref directly. Skip `resolve-base.sh`.

**Otherwise:** Run `references/resolve-base.sh` to determine the merge-base. The script outputs `BASE:<sha>` on success or `ERROR:<message>` on failure.

```bash
bash references/resolve-base.sh
```

If the script outputs `ERROR:`, ask the user to provide a `base:<ref>` argument and stop.

Compute scope from the resolved base:
```bash
# Changed files
git diff --name-only "$BASE"

# Full diff (for prompt context)
git diff "$BASE"
```

### Phase 2: Build Review Prompt

Read `references/focus-areas.md` and select applicable focus areas based on the diff content:

- **Always apply:** correctness, testing, maintainability, project standards
- **Apply if diff touches auth/input/permissions:** security
- **Apply if diff touches DB queries/cache/async:** performance
- **Apply if diff touches routes/type signatures:** api-contracts
- **Apply if diff touches error handling/retries/timeouts:** reliability
- **Apply if diff touches migrations/schema:** data-integrity

Load `references/review-prompt-template.md` and build the prompt using:
- Selected focus areas
- Diff content (for autofix mode -- include the full diff in the prompt)
- Plan requirements (if `plan:` argument provided -- read and summarize key requirements)
- Mode-specific output format instructions

Write the prompt to `.context/codex-workflows/codex-review/<run-id>/review-instructions.md`.

Generate `<run-id>` as 8 hex chars (e.g., from `date +%s%N | md5sum | head -c 8`).

### Phase 3: Execute Review

See `references/codex-review-workflow.md` for the complete execution templates, polling loop, and result classification for each mode.

**report-only:** Launch `codex review` as a background Bash task. Poll for process completion.

**autofix:** Write `references/review-result-schema.json` to the scratch dir. Launch `codex exec` as a background Bash task. Poll for result JSON file.

### Phase 4: Present Results

**report-only:** Claude Code reads the raw `codex review` stdout output and reformats it using the standard output structure below.

**autofix:** Read the structured JSON result. Route findings by `autofix_class`:
- `safe_auto` + `applied: true` → applied fixes section
- `safe_auto` + `applied: false` → residual work section (Codex failed to apply)
- `gated_auto`, `manual` → residual work section
- `advisory` → advisory section

**Standard output structure:**

```
## Codex Review — <branch>

### Summary
<one paragraph summary>

### Findings

| Severity | File | Line | Issue | Action |
|----------|------|------|-------|--------|
| P0 | ... | ... | ... | ... |
| P1 | ... | ... | ... | ... |
...

### Applied Fixes (autofix mode only)
<list of safe_auto fixes that were applied>

### Residual Work
<gated_auto and manual findings requiring human decision>

### Testing Gaps
<identified gaps in test coverage>

### Verdict
> **<Ready to merge | Ready with fixes | Needs work>**
> <one sentence rationale>
```

**Reviewer column:** Shows `codex` for all findings (single reviewer, not persona names).

**Confidence note:** Codex review is a single-pass analysis. For critical merges, consider following up with `/ce:review` for multi-persona depth.

---

## Key Principles

- Never block on Codex availability -- always have a fallback to `/ce:review`
- report-only is always safe (inherently read-only, no sandbox needed)
- autofix mode follows the same rollback safety as work-beta (circuit breaker, rollback on failure)
- Scratch files are cleaned up after successful completion
- The output format is compatible with compound-engineering's review conventions
