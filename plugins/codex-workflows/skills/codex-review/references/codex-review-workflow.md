# Codex Review Delegation Workflow

When `review_delegate_active` is true, code review is delegated to the Codex CLI instead of spawning Claude Code sub-agents. The orchestrating Claude Code agent retains control of scope detection, prompt construction, result formatting, and git operations.

## Pre-Delegation Checks

Run these checks **once before execution**. If any check fails, fall back to standard mode: invoke `/ce:review mode:<review_mode>` passing any `plan:` argument.

**0. Platform Gate**

Only supported when orchestrating agent is running in Claude Code. If the current session is Codex, Gemini CLI, OpenCode, or any other platform, fall back silently.

**1. Environment Guard**

Check whether the current agent is already inside a Codex sandbox:

```bash
if [ -n "$CODEX_SANDBOX" ] || [ -n "$CODEX_SESSION_ID" ]; then
  echo "inside_sandbox=true"
else
  echo "inside_sandbox=false"
fi
```

If `inside_sandbox=true`, fall back to standard mode. If argument-triggered, emit: "Already inside Codex sandbox -- falling back to ce:review."

**2. Availability Check**

**Codex availability (pre-resolved):**
!`command -v codex >/dev/null 2>&1 && echo "CODEX_AVAILABLE" || echo "CODEX_NOT_FOUND"`

If `CODEX_AVAILABLE`, proceed. If `CODEX_NOT_FOUND`, emit: "Codex CLI not found (install via `npm install -g @openai/codex`) -- falling back to ce:review." and fall back.

**3. Consent Flow**

If `review_consent` is not `true`:

Present a one-time consent warning using `AskUserQuestion`:
- Delegation sends the diff and review instructions to `codex review` or `codex exec`
- **report-only mode** is inherently read-only -- no file modifications, no sandbox needed
- **autofix mode** applies safe fixes to files (uses the sandbox setting from `work_delegate_sandbox`)

Ask for consent and (if autofix mode is expected) sandbox choice.

On acceptance: write `review_delegate_consent: true` to `<repo-root>/.compound-engineering/config.local.yaml`. Merge with existing keys -- do not overwrite. Update `review_consent` in resolved state.

On decline: fall back to standard mode for this invocation.

**Headless consent:** If no interactive tool is available, proceed only if `review_delegate_consent: true` is already in config. Otherwise fall back silently.

---

## Delegation Decision

If `review_delegate_decision` is `ask`, present the choice:
> "Codex review delegation active."
> 1. Delegate to Codex *(recommended)*
> 2. Review with Claude Code instead

If `auto` (default), announce in one line and proceed: "Delegating review to Codex."

---

## Execution: report-only Mode

**Scratch directory:** `.context/codex-workflows/codex-review/<run-id>/`

Create directory:
```bash
mkdir -p .context/codex-workflows/codex-review/<run-id>/
```

**Step A — Launch (background, separate Bash call):**

```bash
codex review \
  --base "$BASE" \
  -c 'model="<review_model>"' \
  -c 'model_reasoning_effort="<review_effort>"' \
  - < .context/codex-workflows/codex-review/<run-id>/review-instructions.md \
  > .context/codex-workflows/codex-review/<run-id>/review-output.txt 2>&1
echo $? > .context/codex-workflows/codex-review/<run-id>/exit-code.txt
```

Launch via `run_in_background: true` Bash tool parameter (NOT shell `&`). This removes the 2-minute timeout ceiling.

**Step B — Poll (foreground, separate Bash calls):**

```bash
EXIT_CODE_FILE=".context/codex-workflows/codex-review/<run-id>/exit-code.txt"
for i in $(seq 1 6); do
  test -f "$EXIT_CODE_FILE" && echo "DONE" && exit 0
  sleep 10
done
echo "Waiting for Codex..."
```

If "Waiting for Codex...", issue another polling round. Repeat until "DONE". Timeout after 5 rounds (~5 min) -- treat as failure and fall back to ce:review.

**Step C — Read output:**

```bash
cat .context/codex-workflows/codex-review/<run-id>/review-output.txt
cat .context/codex-workflows/codex-review/<run-id>/exit-code.txt
```

**Result classification:**

| Signal | Action |
|--------|--------|
| Exit code != 0 | CLI failure. Fall back to ce:review. |
| Exit code 0, output file missing/empty | Task failure. Fall back to ce:review. |
| Exit code 0, output present | Success. Reformat output into standard structure. |

---

## Execution: autofix Mode

**Scratch directory:** Same as above.

**Write result schema** (once before launch):
```bash
cp references/review-result-schema.json .context/codex-workflows/codex-review/<run-id>/review-result-schema.json
```

**Resolve sandbox flag:**
```bash
SANDBOX_MODE="<sandbox_mode>"
if [ "$SANDBOX_MODE" = "full-auto" ]; then
  SANDBOX_FLAG="--full-auto"
else
  SANDBOX_FLAG="--dangerously-bypass-approvals-and-sandbox"
fi
```

**Step A — Launch (background, separate Bash call):**

```bash
codex exec \
  -m "<review_model>" \
  -c 'model_reasoning_effort="<review_effort>"' \
  $SANDBOX_FLAG \
  --output-schema .context/codex-workflows/codex-review/<run-id>/review-result-schema.json \
  -o .context/codex-workflows/codex-review/<run-id>/review-result.json \
  - < .context/codex-workflows/codex-review/<run-id>/review-instructions.md
```

Launch via `run_in_background: true`. Do NOT add shell `&`.

**Step B — Poll (foreground, separate Bash calls):**

```bash
RESULT_FILE=".context/codex-workflows/codex-review/<run-id>/review-result.json"
for i in $(seq 1 6); do
  test -s "$RESULT_FILE" && echo "DONE" && exit 0
  sleep 10
done
echo "Waiting for Codex..."
```

Repeat if "Waiting for Codex...". Timeout after 5 rounds -- fall back to ce:review.

**Result classification:**

| # | Signal | Action |
|---|--------|--------|
| 1 | Exit code != 0 | CLI failure. Fall back to ce:review. |
| 2 | Exit 0, result JSON missing/malformed | Task failure. Fall back to ce:review. |
| 3 | Exit 0, `status: "failed"` | Task failure. Fall back to ce:review. |
| 4 | Exit 0, `status: "partial"` | Partial -- present findings, note incomplete review. |
| 5 | Exit 0, `status: "completed"` | Success. Route findings and present output. |

**Circuit breaker:** Not applicable for review (single invocation, not batched). On any failure, fall back to ce:review immediately.

---

## Result Surface Format

After reading the result, display a summary before presenting full findings:

> **Codex review — <classification>**
> <summary from review>
>
> **Files reviewed:** <count>
> **Findings:** P0: N, P1: N, P2: N, P3: N
> **Applied fixes (autofix):** N

Then present the full findings table.

---

## Scratch Cleanup

After successful completion:

```bash
rm -rf .context/codex-workflows/codex-review/<run-id>/
```

On failure, leave files in place for debugging.

---

## Fallback Invocation

When falling back to standard ce:review, invoke:

```
/ce:review mode:<review_mode> [plan:<plan-path>]
```

Emit a brief message explaining why: "Falling back to ce:review: <reason>."
