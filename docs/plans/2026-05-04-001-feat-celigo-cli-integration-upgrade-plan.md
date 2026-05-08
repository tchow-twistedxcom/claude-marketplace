---
title: 'feat(celigo-integration): wrap official CLI, add new resource families, ship EDI cross-system audit'
type: feat
status: active
date: 2026-05-04
---

# feat(celigo-integration): wrap official CLI, add new resource families, ship EDI cross-system audit

## Summary

Re-found `celigo-integration` (v3.0.0) on Celigo's official `@celigo/celigo-cli` (npm) as the execution layer, keep the existing Python `celigo_api.py` as a thin "extras" layer for gaps the CLI does not cover, add coverage for the resource families that landed in `developer.celigo.com/api` (Tools, APIs, MCP Servers, Async Helpers, Notifications, OPA, full EDI surface), and ship a new automated audit script that reconciles Celigo EDI job history against NetSuite EDI History records for both inbound (850/856) and outbound (810/846/855) flows. Bumps plugin to v4.0.0.

---

## Problem Frame

Our `celigo-integration` plugin (v3.0.0, ~160 operations) was built when Celigo's public API surface was thin. Celigo has since published much more verbose docs at `developer.celigo.com/api` covering whole resource families we don't touch (Tools, APIs, MCP Servers, Async Helpers, Notifications, OPA), expanded EDI primitives (Profiles, Trading Partner Connectors, Transactions update + download), and shipped an official CLI (`@celigo/celigo-cli`). Continuing to maintain a parallel hand-rolled Python wrapper for surface Celigo already covers is carrying cost we do not need; meanwhile we have no agent-facing way to audit EDI integrity end-to-end across Celigo and NetSuite, which is the question we ask most often when investigating partner issues.

---

## Requirements

- R1. Wrap `@celigo/celigo-cli` as the primary execution path; keep `celigo_api.py` as the customizations layer.
- R2. Document the wrap-vs-extras boundary so contributors know when to call the official CLI vs. our extras.
- R3. Add CLI coverage for **Tools** — list, get, create, update, delete, invoke, dependencies.
- R4. Add CLI coverage for **APIs** (builder-mode REST endpoint definitions) — list, get, create, update, delete, deploy, versions.
- R5. Add CLI coverage for **MCP Servers** — list, get, create, update, delete, server lifecycle (start/stop/status).
- R6. Add CLI coverage for **Async Helpers** — submit / poll / fetch-result three-phase pattern.
- R7. Add CLI coverage for **Notifications** — list, get, create, update, delete (per-resource, per-event subscriptions).
- R8. Add CLI coverage for **OPA management** (On-Premise Agents) — list, get, create, update, delete, status, restart.
- R9. Add CLI coverage for **EDI Profiles** (X12/EDIFACT envelopes) — list, get, create, update, delete, dependencies (immutable `fileType`).
- R10. Expand **EDI Transactions** coverage beyond current query/patch/fa-details to include update and download-raw-file.
- R11. Add CLI coverage for **Trading Partner Connectors** — list, get, create, update with `supportedBy` (connection / export / import / ediProfile).
- R12. Expand **File Definitions** coverage for delimited / fixed / x12 / edifact, schema versions 1 and 2, and EDI-specific fields (`documentType`, `globalId`).
- R13. Ship a new automated **EDI cross-system audit** command runnable as a single CLI invocation, covering both inbound and outbound legs with a structured (JSON) and human-readable report.
- R14. Update both skills (`celigo-integrator`, `celigo-integration-patterns`) so their activation triggers and reference content reflect the new surface.
- R15. Bump plugin to v4.0.0 and update the marketplace registry.
- R16. Preserve existing fetch-merge-PUT discipline ("PUT API is full-replace") for any new resources that PUT.
- R17. Audit command must use the existing NetSuite API gateway (`https://nsapi.twistedx.tech/api/suiteapi`, no auth) and existing Celigo credentials — no new credential plumbing.

---

## Scope Boundaries

- Rewriting `celigo_api.py` in Node/TypeScript — we wrap, we don't port.
- Auto-remediation of audit mismatches — report-only; remediation stays manual.
- Building a UI for the audit report — CLI / JSON output only.
- Replacing the existing health-digest flow architecture (separate system, untouched).
- Migrating existing flows to the new Tools / APIs / MCP Servers resources — that's a flow-level migration, separate work.
- Creating a brand-new plugin — this is an in-place upgrade of `celigo-integration`.

### Deferred to Follow-Up Work

- Auto-resolving common audit mismatches (e.g., re-trigger Celigo retry when NS shows partner-received-but-no-success): separate plan once we have audit telemetry.
- Slack-bot / scheduled cron for audit: separate plan, depends on this audit landing first.

---

## Context & Research

### Relevant Code and Patterns

- `plugins/celigo-integration/scripts/celigo_api.py` — Python wrapper, 22 `cmd_*` handlers, already covers integrations / flows / connections / exports / imports / scripts / jobs / errors / caches / tags / users / state / filedefinitions / recyclebin / audit / iclients / connectors / processors / templates / edi.
- `plugins/celigo-integration/scripts/celigo_auth.py` — auth helper, reads `~/.config/celigo-integration/`.
- `plugins/celigo-integration/skills/celigo-integrator/SKILL.md` — primary "do-something" skill (339 lines).
- `plugins/celigo-integration/skills/celigo-integration-patterns/SKILL.md` — patterns reference (592 lines).
- `plugins/celigo-integration/commands/celigo-setup.md`, `celigo-manage.md` — existing slash commands.
- Existing partial EDI Transactions coverage in `cmd_edi` (lines around `/ediTransactions`, `/ediTransactions/query`, `/ediTransactions/{id}/faDetails`) — extend, don't duplicate.

### Institutional Learnings (from auto-memory)

- **PUT is full-replace** — always fetch-merge-PUT for any new PUT-supporting resource.
- **Sandbox connection mismatch** — connection IDs differ between sandbox and prod; the audit must be sandbox-aware.
- **NS gateway needs no auth** — POST `{action:'queryRun', query:sql, netsuiteAccount:'twistedx', netsuiteEnvironment:'production'}`.
- **NS EDI History schema** — `customrecord_twx_edi_history`, `custrecord_twx_edi_history_status` (2=success, 6=error), `custrecord_twx_edi_history_transaction` (linked SO, NULL if no SO), `custrecord_twx_edi_history_json` (full EDI blob), `externalid` format `HIST_{PO}_{PARTNER}_00`.
- **EDI doc-type mapping** — 850→3, 856→5, 810→1, 846→2 in `custrecord_twx_edi_type`.
- **850 validation model** — Celigo `numSuccess` = EDI line items, NS EDI TH = 1 record per PO doc; need three-stage validation: (1) Celigo job_errors, (2) `ns_processing_failed` (status≠2), (3) `pos_without_order` (status=2 but transaction NULL).
- **EDI partner regex** — `/^(.+?)\s*-\s*EDI\s+(\d{3})\s+(IB|OB|INB)\b/i`; staging detection: `/\(\d{1,2}\/\d{1,2}\/\d{4}\)$/`.

### External References

- `developer.celigo.com/api` — primary source of truth for new resource families; pulled during brainstorm.
- `@celigo/celigo-cli` (npm) — official CLI, Node 22+, pattern: `celigo <resource> <verb>`.

---

## Key Technical Decisions

- **Wrap, don't port.** Invoke `@celigo/celigo-cli` as a subprocess from Python (keep current entry point) rather than rewriting `celigo_api.py` in Node. Rationale: agents already use `celigo_api.py`'s argparse surface; preserving it minimizes downstream churn while we gain CLI parity for free where it covers our resources.
- **Extras layer is opt-in fallback.** When the official CLI covers a verb cleanly, route through it; only call the REST API directly from Python for things the CLI doesn't expose (audit, custom batch operations, postResponseMap-style hooks).
- **New resources extend `celigo_api.py`'s `cmd_*` pattern** rather than introducing a new file structure. Keeps the CLI surface uniform: `python celigo_api.py tools list`, `… apis deploy`, `… mcp-servers status`, `… edi-profiles get`, etc.
- **Audit script lives at `plugins/celigo-integration/scripts/edi_audit.py`** — separate file, not folded into `celigo_api.py`, because it composes Celigo + NS gateway calls and has materially different error-handling needs. Invokable as `python edi_audit.py [--since N] [--until N] [--partner X] [--direction inbound|outbound|both]`.
- **Audit window default 24h**, overridable via `--since` / `--until` (ISO timestamps or relative like `24h`, `7d`).
- **Audit output: structured JSON + human summary**, both written to stdout by default; `--json-only` for piping. Three-bucket report: `celigo_success_ns_missing`, `ns_sent_celigo_missing`, `ns_status_error`.
- **Plugin v4.0.0** — bumping major because the wrap-vs-extras boundary is a structural change in how the plugin executes work, even if the agent-facing argparse surface stays compatible. No deprecation cycle (internal plugin).
- **No new credential storage** — reuse `~/.config/celigo-integration/` and the existing NS gateway URL.

---

## Open Questions

### Resolved During Planning

- **Stay on Python wrapper or switch to Node?** → Stay on Python; subprocess the official CLI. (See Key Technical Decisions.)
- **Audit lives where?** → Standalone `edi_audit.py`, not a `cmd_audit_edi` inside `celigo_api.py`.
- **One bundle for AI-runtime resources?** → No; split Tools / APIs / MCP Servers into separate units because each has a meaningfully different verb set despite sharing the `/v1/<resource>` REST pattern.

### Deferred to Implementation

- Exact subprocess invocation pattern for the official CLI (env var passthrough, working-directory handling, error-string parsing) — needs a real install + smoke run to lock down.
- Whether `@celigo/celigo-cli` supports our config file format directly or needs a translation step — verify on first install.
- Whether `Async Helpers` poll loop should default to exponential backoff or fixed cadence — needs one real long-running call to calibrate.
- Audit performance under large volumes (a partner with 10k+ EDI docs/day) — instrument first, optimize if needed.

---

## Output Structure

    plugins/celigo-integration/
    ├── plugin.json                          # bump to 4.0.0; no shape change
    ├── AUTHENTICATION.md                    # existing, may add CLI-install note
    ├── scripts/
    │   ├── celigo_api.py                    # extend with new cmd_* handlers
    │   ├── celigo_auth.py                   # unchanged
    │   ├── celigo_cli_wrapper.py            # NEW — subprocess helper for @celigo/celigo-cli
    │   ├── edi_audit.py                     # NEW — cross-system audit
    │   └── (existing health-digest scripts unchanged)
    ├── skills/
    │   ├── celigo-integrator/SKILL.md       # update activation triggers + examples
    │   └── celigo-integration-patterns/SKILL.md  # add new resource family sections
    ├── commands/
    │   ├── celigo-setup.md                  # add CLI-install step
    │   ├── celigo-manage.md                 # mention new resources
    │   └── celigo-edi-audit.md              # NEW — slash command for audit
    ├── docs/
    │   └── new-resources/                   # NEW reference docs (one per family)
    │       ├── tools.md
    │       ├── apis.md
    │       ├── mcp-servers.md
    │       ├── async-helpers.md
    │       ├── notifications.md
    │       ├── opa.md
    │       ├── edi-profiles.md
    │       ├── trading-partner-connectors.md
    │       └── file-definitions-edi.md
    └── tests/                               # NEW (does not exist today)
        ├── test_celigo_cli_wrapper.py
        ├── test_new_resource_handlers.py
        └── test_edi_audit.py

    .claude-plugin/marketplace.json          # bump celigo-integration version to 4.0.0

---

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

**Wrap-vs-extras routing:**

```
agent prompt
   │
   ▼
celigo_api.py argparse  ── cmd_<resource>(args)
   │
   ├── covered by official CLI?
   │     ├── YES → celigo_cli_wrapper.run("<resource> <verb>", args) ──► subprocess @celigo/celigo-cli ──► Celigo API
   │     └── NO  → direct REST call via existing http client ──────────► Celigo API
   │
   └── audit / multi-system ops → edi_audit.py composes Celigo REST + NS gateway calls
```

**EDI audit data flow (inbound leg, 850/856):**

```
Celigo: GET /v1/jobs?type=<edi-flow-id>&status=success&since=<ts>
   │
   ▼ extract: PO numbers, partner, doc type, success count
   │
   ▼
NS gateway: SuiteQL query against customrecord_twx_edi_history
   WHERE custrecord_twx_edi_type = <doc-type> AND created >= <ts>
   │
   ▼ extract: status, linked transaction, externalid (PO number)
   │
   ▼
Reconciler: per-PO match
   ├── celigo_success + ns_status=2 + transaction NOT NULL → ✅ pass
   ├── celigo_success + ns_status=6 (or != 2)             → ⚠ ns_processing_failed
   ├── celigo_success + ns_status=2 + transaction NULL    → ⚠ pos_without_order
   ├── celigo_success + no NS row at all                  → ❌ celigo_success_ns_missing
   └── (outbound leg flips: ns_sent + no celigo job → ❌ ns_sent_celigo_missing)
```

---

## Implementation Units

- U1. **CLI wrapper foundation**

**Goal:** Establish the `@celigo/celigo-cli` subprocess invocation pattern and document the wrap-vs-extras boundary, so subsequent units have a stable rail to follow.

**Requirements:** R1, R2, R16

**Dependencies:** None

**Files:**
- Create: `plugins/celigo-integration/scripts/celigo_cli_wrapper.py`
- Create: `plugins/celigo-integration/tests/test_celigo_cli_wrapper.py`
- Modify: `plugins/celigo-integration/AUTHENTICATION.md` (add CLI install + auth handoff note)
- Modify: `plugins/celigo-integration/commands/celigo-setup.md` (add `npm i -g @celigo/celigo-cli` step + `node --version` check)
- Modify: `plugins/celigo-integration/skills/celigo-integration-patterns/SKILL.md` (add "When to use the official CLI vs the extras layer" section)

**Approach:**
- Wrapper exposes `run(verb_string, args, *, json_output=True)` that builds an argv array, runs `subprocess.run`, parses JSON stdout, and surfaces stderr on non-zero exit.
- Auto-detect CLI presence (`shutil.which("celigo")`); raise a clear error directing to `celigo-setup` when missing.
- Honor existing `~/.config/celigo-integration/` config — if the official CLI consumes a different format, translate at wrapper boundary, do not duplicate config files.
- Leave no global state; wrapper is stateless per call.

**Patterns to follow:**
- Existing subprocess patterns in `plugins/infra-skills/` scripts.
- Argparse cmd_* shape in `celigo_api.py`.

**Test scenarios:**
- Happy path — `run("integrations list", ...)` returns parsed JSON when CLI is installed and reachable.
- Error path — CLI not installed → raises with install hint.
- Error path — non-zero exit with stderr → raises with stderr surfaced.
- Edge case — CLI returns non-JSON stdout (e.g., a help banner) → wrapper degrades gracefully and returns raw text when `json_output=False`.

**Verification:**
- `python -c "from celigo_cli_wrapper import run; print(run('--version'))"` returns the installed CLI version.
- `celigo-setup` documents the CLI install step end-to-end.

---

- U2. **Tools resource coverage**

**Goal:** Add `cmd_tools` covering list / get / create / update / delete / invoke / dependencies for Celigo Tools (reusable processing units).

**Requirements:** R3, R16

**Dependencies:** U1

**Files:**
- Modify: `plugins/celigo-integration/scripts/celigo_api.py` (add `cmd_tools`, register in argparse)
- Create: `plugins/celigo-integration/docs/new-resources/tools.md`
- Modify: `plugins/celigo-integration/tests/test_new_resource_handlers.py` (or create)

**Approach:**
- Mirror existing `cmd_imports` shape. Route list/get/delete/invoke through the official CLI when supported; route update through fetch-merge-PUT in our extras layer (PUT is full-replace).
- `dependencies` returns the resources referencing this tool (read-only).

**Patterns to follow:**
- `cmd_imports` and `cmd_processors` in `celigo_api.py`.

**Test scenarios:**
- Happy path — `tools list` returns array of tools.
- Happy path — `tools invoke <id> --data <json>` returns invocation response.
- Edge case — `tools update <id>` without prior `get` → fetch-merge-PUT path is exercised; no fields silently dropped.
- Error path — `tools delete <id>` on non-existent ID → surfaces 404 cleanly.

**Verification:**
- All 7 verbs callable via `python celigo_api.py tools <verb>`.

---

- U3. **APIs (builder-mode) resource coverage**

**Goal:** Add `cmd_apis` covering list / get / create / update / delete / deploy / versions for Celigo builder-mode REST endpoint definitions.

**Requirements:** R4, R16

**Dependencies:** U1

**Files:**
- Modify: `plugins/celigo-integration/scripts/celigo_api.py` (add `cmd_apis`)
- Create: `plugins/celigo-integration/docs/new-resources/apis.md`
- Modify: `plugins/celigo-integration/tests/test_new_resource_handlers.py`

**Approach:**
- Same shape as U2. `deploy` and `versions` are API-specific verbs.
- `versions` returns the version history list; `deploy` triggers a deployment of the current draft.

**Patterns to follow:** U2.

**Test scenarios:**
- Happy path — `apis list` and `apis versions <id>` return arrays.
- Happy path — `apis deploy <id>` returns the deployment ID.
- Edge case — `apis update <id>` preserves unsent fields (full-replace discipline).

**Verification:**
- All 7 verbs callable.

---

- U4. **MCP Servers resource coverage**

**Goal:** Add `cmd_mcp_servers` covering list / get / create / update / delete plus server lifecycle (start / stop / status).

**Requirements:** R5, R16

**Dependencies:** U1

**Files:**
- Modify: `plugins/celigo-integration/scripts/celigo_api.py` (add `cmd_mcp_servers`)
- Create: `plugins/celigo-integration/docs/new-resources/mcp-servers.md`
- Modify: `plugins/celigo-integration/tests/test_new_resource_handlers.py`

**Approach:**
- CRUD verbs follow U2 pattern. Lifecycle verbs (`start`, `stop`, `status`) hit dedicated endpoints; `status` is a simple GET, `start`/`stop` are POSTs.

**Patterns to follow:** U2.

**Test scenarios:**
- Happy path — `mcp-servers status <id>` returns server state.
- Happy path — full lifecycle: create → start → status → stop → delete.
- Error path — `start` on already-running server → surfaces server-side conflict cleanly.

**Verification:**
- All 8 verbs callable.

---

- U5. **Async Helpers (3-phase pattern)**

**Goal:** Add `cmd_async` covering submit / poll / fetch-result for Celigo's long-running operation pattern.

**Requirements:** R6

**Dependencies:** U1

**Files:**
- Modify: `plugins/celigo-integration/scripts/celigo_api.py` (add `cmd_async`)
- Create: `plugins/celigo-integration/docs/new-resources/async-helpers.md`
- Modify: `plugins/celigo-integration/tests/test_new_resource_handlers.py`

**Approach:**
- `submit <op> --data <json>` returns an async job ID.
- `poll <job-id>` returns current status (pending / running / done / failed).
- `result <job-id>` returns the final payload (errors if polled too early).
- Provide a convenience `wait <op> --data <json> [--timeout N] [--interval N]` that submits + polls + returns the result. Default interval 2s, timeout 120s; backoff strategy deferred (see Open Questions).

**Patterns to follow:**
- Existing job-polling logic in `cmd_jobs` (if present); otherwise greenfield within `celigo_api.py` conventions.

**Test scenarios:**
- Happy path — `wait` returns the result for a fast-completing op.
- Edge case — `poll` immediately after submit returns pending status.
- Error path — `result` before completion returns a clear "not ready" error.
- Error path — `wait` exceeds `--timeout` → exits non-zero with timeout message.

**Verification:**
- A short-lived test op completes end-to-end via `wait`.

---

- U6. **Notifications + OPA management**

**Goal:** Add `cmd_notifications` (list / get / create / update / delete) and `cmd_opa` (list / get / create / update / delete / status / restart). Bundled because both are admin/ops resources with small individual surfaces and similar shapes.

**Requirements:** R7, R8, R16

**Dependencies:** U1

**Files:**
- Modify: `plugins/celigo-integration/scripts/celigo_api.py` (add `cmd_notifications`, `cmd_opa`)
- Create: `plugins/celigo-integration/docs/new-resources/notifications.md`
- Create: `plugins/celigo-integration/docs/new-resources/opa.md`
- Modify: `plugins/celigo-integration/tests/test_new_resource_handlers.py`

**Approach:**
- Standard CRUD via U2 pattern.
- Notifications create payload requires `_resourceId` + `_resourceType` + `event` + `recipients[]`.
- OPA `status` returns connection state; `restart` triggers reconnect.

**Patterns to follow:** U2.

**Test scenarios:**
- Notifications — happy path create with multiple recipients; update preserves event filter.
- OPA — happy path status returns reachable/unreachable.
- Error path — OPA restart on disconnected agent surfaces error rather than hanging.

**Verification:**
- All verbs callable for both resources.

---

- U7. **EDI Profiles + Trading Partner Connectors**

**Goal:** Add `cmd_edi_profiles` (list / get / create / update / delete / dependencies) and `cmd_trading_partners` (list / get / create / update with `supportedBy` resolution). Bundled because both are EDI-onboarding-shaped and reviewers will think of them together.

**Requirements:** R9, R11, R16

**Dependencies:** U1

**Files:**
- Modify: `plugins/celigo-integration/scripts/celigo_api.py` (add `cmd_edi_profiles`, `cmd_trading_partners`)
- Create: `plugins/celigo-integration/docs/new-resources/edi-profiles.md`
- Create: `plugins/celigo-integration/docs/new-resources/trading-partner-connectors.md`
- Modify: `plugins/celigo-integration/tests/test_new_resource_handlers.py`

**Approach:**
- EDI Profiles: CRUD plus `dependencies` (read-only). `fileType` is immutable post-create; reject mutation attempts client-side with a clear error.
- Trading Partner Connectors: list/get/create/update (no delete in API). `supportedBy` accepts `connection`, `export`, `import`, or `ediProfile`; resolver looks up by name when ID isn't given.

**Patterns to follow:**
- Existing `cmd_edi` partial coverage in `celigo_api.py`.

**Test scenarios:**
- EDI Profiles happy path — create X12 850 profile, fetch dependencies, update non-fileType field.
- EDI Profiles error path — attempting to mutate `fileType` fails client-side before hitting the API.
- TPC happy path — create connector with `supportedBy: ediProfile` resolved by name.
- TPC error path — `supportedBy` references nonexistent resource → clear error with the unresolved name.

**Verification:**
- Both resources fully callable; profiles dependencies surface flows / TPCs that reference them.

---

- U8. **EDI Transactions expansion + File Definitions expansion**

**Goal:** Extend the existing `cmd_edi` to cover EDI Transactions update + download-raw-file (in addition to current query / patch / fa-details), and expand `cmd_filedefinitions` to handle delimited / fixed / x12 / edifact across schema versions 1 and 2 (with `documentType` and `globalId` for EDI cases).

**Requirements:** R10, R12, R16

**Dependencies:** U1, U7 (TPCs may reference file definitions)

**Files:**
- Modify: `plugins/celigo-integration/scripts/celigo_api.py` (extend `cmd_edi`, extend `cmd_filedefinitions`)
- Create: `plugins/celigo-integration/docs/new-resources/file-definitions-edi.md`
- Modify: `plugins/celigo-integration/tests/test_new_resource_handlers.py`

**Approach:**
- EDI Transactions: add `update <id> --data <json>` (PATCH) and `download <id> [--out PATH]` (GET raw file content; default stdout, optional file write).
- File Definitions: when `format` is `x12` or `edifact`, require `documentType` + `globalId`; route schema v1/v2 selection via `--schema-version` flag (default 2).

**Patterns to follow:**
- Existing `cmd_edi` partial implementation.

**Test scenarios:**
- EDI Transactions update — happy path PATCHes `faStatus`.
- EDI Transactions download — happy path returns raw EDI envelope; `--out path` writes file.
- File Definitions create x12 — requires `documentType`; missing field → clear error.
- File Definitions schema version — v1 and v2 both create successfully with their respective shapes.

**Verification:**
- Existing EDI verbs still work; new verbs callable; file definitions support all 4 formats × 2 schema versions where applicable.

---

- U9. **EDI cross-system audit script**

**Goal:** Ship `edi_audit.py`, a standalone command that reconciles Celigo EDI job history against NetSuite EDI History for both inbound (850/856) and outbound (810/846/855) flows. Outputs structured JSON + human summary identifying three failure buckets.

**Requirements:** R13, R17

**Dependencies:** U1, U8 (uses extended EDI Transactions; benefits from file-def context)

**Files:**
- Create: `plugins/celigo-integration/scripts/edi_audit.py`
- Create: `plugins/celigo-integration/commands/celigo-edi-audit.md`
- Create: `plugins/celigo-integration/tests/test_edi_audit.py`
- Modify: `plugins/celigo-integration/skills/celigo-integrator/SKILL.md` (add audit example to triggers)
- Modify: `plugins/celigo-integration/plugin.json` (register new command)

**Approach:**
- Discover EDI flows via partner-name regex (`/^(.+?)\s*-\s*EDI\s+(\d{3})\s+(IB|OB|INB)\b/i`); skip staging flows (`/\(\d{1,2}\/\d{1,2}\/\d{4}\)$/`).
- Inbound leg (850 / 856): for each successful Celigo job, extract PO numbers (from `numSuccess` line items in the job context); query NS for `customrecord_twx_edi_history` rows in the same window; per-PO reconcile using doc-type mapping (850→3, 856→5).
- Outbound leg (810 / 846 / 855): for each NS EDI History row marked sent (status=2) for outbound types, query Celigo job history for the matching transmission window; flag missing.
- Buckets: `celigo_success_ns_missing`, `ns_sent_celigo_missing`, `ns_status_error` (covers `ns_processing_failed` and `pos_without_order`).
- CLI flags: `--since` (default `24h`), `--until` (default now), `--partner <name>` (filter), `--direction inbound|outbound|both` (default both), `--json-only` (suppress human summary), `--exit-nonzero-on-mismatch` (for CI use).
- NS query uses existing gateway (`https://nsapi.twistedx.tech/api/suiteapi`, `{action:'queryRun', query, netsuiteAccount:'twistedx', netsuiteEnvironment:'production'}`).
- Reuse Celigo auth via `celigo_auth.py`.

**Patterns to follow:**
- Existing health-digest scripts in `scripts/` for cross-system orchestration shape.
- NS SuiteQL query patterns documented in auto-memory.

**Test scenarios:**
- Happy path — single inbound 850 PO, Celigo success + NS status=2 + transaction set → reports clean (zero mismatches).
- Mismatch — Celigo success, no NS row → `celigo_success_ns_missing` bucket populated with PO + partner.
- Mismatch — NS status=2 but transaction NULL → `pos_without_order` under `ns_status_error`.
- Mismatch — NS sent (810) but no Celigo job in window → `ns_sent_celigo_missing`.
- Edge case — staging-suffixed flow names are skipped.
- Edge case — partner filter narrows scope correctly.
- Error path — NS gateway unreachable → exits with clear error; does not partial-write JSON.
- Error path — Celigo API rate-limited → backs off and retries up to 3 times.
- Integration — full audit run against a fixture covering multiple partners and both directions produces the expected bucket counts.

**Verification:**
- `python edi_audit.py --since 24h --direction both` runs cleanly against current account and emits well-formed JSON.
- Slash command `/celigo-edi-audit` invokes the script with sensible defaults.

---

- U10. **Skills documentation refresh**

**Goal:** Update both skills so activation triggers and reference content reflect the new resource families and the wrap-vs-extras model.

**Requirements:** R2, R14

**Dependencies:** U1–U9 (so docs reflect what actually shipped)

**Files:**
- Modify: `plugins/celigo-integration/skills/celigo-integrator/SKILL.md`
- Modify: `plugins/celigo-integration/skills/celigo-integration-patterns/SKILL.md`
- Modify: `plugins/celigo-integration/commands/celigo-manage.md`

**Approach:**
- `celigo-integrator`: add activation triggers covering "set up an MCP server for our Celigo tools", "audit our EDI inbound for last week", "create an async helper for…", "manage OPAs". Add one example per new resource family.
- `celigo-integration-patterns`: add sections for each new family with the canonical CRUD pattern, the wrap-vs-extras decision, and the audit invocation.
- Cross-link to the `docs/new-resources/*.md` references created in U2–U8.

**Patterns to follow:**
- Existing skill structure; do not change frontmatter shape.

**Test scenarios:**
- Test expectation: none — pure documentation updates with no runnable behavior.

**Verification:**
- `/plugin reload celigo-integration` succeeds; new triggers fire on representative prompts in a fresh chat.

---

- U11. **Version bump + marketplace registration**

**Goal:** Bump the plugin to v4.0.0 and update the marketplace registry.

**Requirements:** R15

**Dependencies:** U1–U10 (everything else done)

**Files:**
- Modify: `plugins/celigo-integration/plugin.json` (version 3.0.0 → 4.0.0; description refresh; register `celigo-edi-audit` command)
- Modify: `.claude-plugin/marketplace.json` (version 3.0.0 → 4.0.0; description refresh)

**Approach:**
- Update both version strings in the same commit.
- Refresh descriptions to mention the new resource families and the EDI cross-system audit.
- Confirm `commands` array in `plugin.json` includes the new `celigo-edi-audit.md`.

**Patterns to follow:**
- Existing version-bump pattern from `netsuite-skills` v1.7→v1.8 and `mimecast-skills` v1.2→v1.3.

**Test scenarios:**
- Test expectation: none — metadata-only change covered by smoke tests in verification.

**Verification:**
- `/plugin marketplace refresh` and `/plugin reload celigo-integration` both succeed.
- `/plugin list` shows celigo-integration at v4.0.0.

---

## System-Wide Impact

- **Interaction graph:** New audit script reaches the NS gateway (`nsapi.twistedx.tech`) — adds a new outbound dependency for this plugin (previously Celigo-only). No callbacks; pure on-demand.
- **Error propagation:** Audit script must surface partial failures (Celigo OK, NS unreachable) clearly without producing a misleading "all clean" report. CLI wrapper must surface official-CLI stderr verbatim.
- **State lifecycle risks:** `cmd_edi_profiles` immutable-`fileType` rule must reject client-side, not silently let a 422 land mid-edit.
- **API surface parity:** Existing `cmd_edi` callers must continue working unchanged after U8 expansion. Existing v3 argparse subcommands all preserved.
- **Integration coverage:** End-to-end audit run is the only true integration test; everything else is unit-shaped.
- **Unchanged invariants:** Health digest flow architecture (Phase 1b orchestrator, dashboard ingest, fallback PPs) is untouched. PRI / NetSuite plugins untouched. Existing `~/.config/celigo-integration/` config format unchanged.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| `@celigo/celigo-cli` config format incompatible with our config layout | Detect on first install during U1; translate at wrapper boundary; document the translation |
| Official CLI verb coverage incomplete for one of the new families | Fall back to direct REST in extras layer per resource; document which verbs route which way |
| EDI audit performance under high partner volumes | Default 24h window keeps initial volume bounded; add `--max-records` cap if needed during U9 testing |
| NS gateway sandbox vs prod confusion | Audit script reads gateway URL + account from config; fails closed if the account label doesn't match expected env |
| 850 PO count vs line-item count confusion (per institutional learning) | Audit reconciles at the PO-document level using `externalid` extraction, not `numSuccess` line counts; documented inline in `edi_audit.py` |
| Resource families ship under different access tiers (some Celigo features are paid) | Each new `cmd_*` surfaces the API's 403/feature-disabled response cleanly; we don't pre-gate on plan tier |
| Plugin major-version bump breaks installed users on v3 | Internal plugin only; communicate via commit message + README. No API surface removed. |

---

## Documentation / Operational Notes

- Update `plugins/celigo-integration/AUTHENTICATION.md` with the `@celigo/celigo-cli` install note and Node 22+ requirement.
- Add one entry per new resource family in `plugins/celigo-integration/docs/new-resources/`.
- Add an EDI-audit walkthrough section in `celigo-integration-patterns/SKILL.md` showing a real cross-system mismatch and its triage path.
- After landing: add a `docs/solutions/` entry under `integration-issues/` capturing one full audit-run example so future runs have a known-good baseline.
- Commit/PR conventions: single feature branch `feat/celigo-cli-integration-upgrade`, conventional commit `feat(celigo-integration): wrap official CLI + new resources + EDI audit (v4.0.0)`.

---

## Sources & References

- Celigo developer docs: https://developer.celigo.com/api
- `@celigo/celigo-cli` (npm)
- `plugins/celigo-integration/scripts/celigo_api.py` — current 22-handler surface
- `plugins/celigo-integration/skills/celigo-integration-patterns/SKILL.md` — patterns reference
- Auto-memory entries on Celigo PUT discipline, EDI doc-type mapping, NS gateway, NS EDI History schema, and 850 validation model
