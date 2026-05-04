---
title: "feat: Add `twx-deploy import` subcommand for SDF object XML extraction"
type: feat
status: active
date: 2026-04-29
---

# feat: Add `twx-deploy import` subcommand for SDF object XML extraction

**Target repo:** `netsuite-deploy` (`~/netsuite-deploy`). File paths below are relative to that repo root unless prefixed with `tchow-essentials/` (marketplace repo).

## Summary

Add a first-class `import` subcommand to `@twisted-x/netsuite-deploy` that pulls SDF object XMLs from a NetSuite account using the same cert-based OAuth2 bypass already proven by `import_object.py`. The command supports single, multiple, and wildcard `--scriptid` patterns, reads environment and credentials from `twx-sdf.config.json` exactly like `deploy <env>`, and writes XML files to the SDF project's `Objects/` tree. Once verified, the standalone Python script is retired.

---

## Problem Frame

`suitecloud object:import` requires the OS keyring, which breaks on headless developer boxes and CI. A standalone Python script (`import_object.py`) in the skill's `scripts/` directory already bypasses this by calling NetSuite's SDF IDE endpoint directly with a PS256 JWT + OAuth2 token, but it lives outside the npm CLI users already trust and has no connection to the project's config system.

---

## Requirements

- R1. `twx-deploy import <env>` accepts environment as a positional arg and reads credentials from `twx-sdf.config.json`, matching the `deploy` command's UX.
- R2. `--type` (required) specifies the SDF object type (e.g. `SAVEDSEARCH`, `CUSTOMRECORDTYPE`).
- R3. `--scriptid` (required, repeatable) specifies one or more script IDs to import; wildcards (e.g. `customsearch_twx_*`) are passed through to NetSuite.
- R4. `--dest` (optional) overrides the destination folder within the project's SDF path; default is `Objects/<lowercase type>`.
- R5. `--dry-run` prints the OAuth2 request payload and form data without making a network call.
- R6. `--overwrite` allows replacing existing XML files; without it, attempting to overwrite is an error.
- R7. Auth uses direct cert-based OAuth2 to `/app/ide/ide.nl` (no `suitecloud` CLI subprocess).
- R8. `import_object.py` is deleted from the skill's `scripts/` directory once TypeScript parity is verified.
- R9. `SKILL.md` is updated with an "Object Import" section documenting the new command.

---

## Scope Boundaries

- File-cabinet imports (SuiteScript files) — only object XMLs
- Manifest-driven batch imports from a JSON/YAML file
- Field-level or sublist-level partial imports
- XML transformation (stripping account-specific IDs, normalizing whitespace)
- A reciprocal push-from-disk command (`deploy` covers deployment)

### Deferred to Follow-Up Work

- Wildcard response-shape verification: if the IDE endpoint rejects wildcard `scriptid` values, implementation should fall back to a list-then-fetch pattern (no client-side glob expansion). This is an empirical verification step deferred to implementation.

---

## Context & Research

### Relevant Code and Patterns

- `src/cli/commands/deploy.ts` — commander pattern to mirror: positional env arg, `loadConfig` + `getEnvironmentConfig` + `CredentialManager`, chalk/ora UX
- `src/cli/index.ts` — where new command must be registered
- `src/auth/credentials.ts` — `CredentialManager.resolve()` already handles all env-var and config-file credential resolution; reuse without modification
- `src/config/loader.ts` — `loadConfig()` returns `{ config, context, pathResolver }`; `getEnvironmentConfig()` validates env name
- `src/utils/paths.ts` — `PathResolver.getSdfPath(environment)` returns the absolute path to the SDF directory for the target env
- `src/core/deployment.test.ts` — test pattern to follow (vitest, vi.mock, co-located with source)
- `tchow-essentials/plugins/netsuite-skills/skills/netsuite-sdf-deployment/scripts/import_object.py` — reference implementation for OAuth2 token flow, IDE endpoint parameters, and XML extraction logic

### Key API Mechanics (from import_object.py)

- **Token URL**: `https://<normalized-account-id>.suitetalk.api.netsuite.com/services/rest/auth/oauth2/v1/token`
- **JWT claims**: `iss` = `SUITECLOUD_PROD_CLIENT_ID` (hardcoded), `scope: 'restlets'`, `aud` = token URL, `kid` = certificateId, algorithm PS256
- **IDE endpoint**: `https://<normalized-account-id>.app.netsuite.com/app/ide/ide.nl`
- **Form fields**: `type`, `scriptid`, `projectfolder`, `destinationfolder`, `isexcludefiles: 'true'`
- **Header**: `Sdf-Action: IMPORTOBJECTS`, `Authorization: Bearer <token>`
- **Account normalization**: `4138030_SB2` → `4138030-sb2` (lowercase, underscores to hyphens)

### Institutional Learnings

- No existing PS256 JWT signing in this codebase — Node 18's `crypto` module (built-in) handles RSASSA-PSS; avoids a new runtime dep.
- Existing test style: vitest with `vi.mock`, `vi.fn()`, co-located `.test.ts` files.
- `jsonwebtoken` is NOT in `package.json`; Node crypto is the preferred no-dep path.

---

## Key Technical Decisions

- **No new JWT library**: Use Node 18's `crypto.createPrivateKey` + `crypto.sign` with `RSA-PSS` padding for PS256 JWT generation. Avoids a new runtime dep; the JWT structure is fixed and simple enough for direct construction.
- **Native `fetch` for HTTP**: Node 18+ has `globalThis.fetch`; no `axios` or `node-fetch` needed.
- **`URLSearchParams` for form body**: The IDE endpoint accepts `application/x-www-form-urlencoded`; no `form-data` dep needed.
- **Tag-boundary XML extraction**: Response for a single object is raw XML. Response for wildcards is unknown at plan time — implementation should log and preserve the raw response on failure to aid debugging. Use string-based tag-boundary scanning (as in `import_object.py`) with a fallback to a whole-file write for unrecognized shapes. Defer `fast-xml-parser` adoption to a follow-up if needed.
- **Per-scriptid loop at CLI layer**: For multiple `--scriptid` values, re-use the single OAuth2 token across calls (one token per `twx-deploy import` invocation) and call the IDE endpoint once per scriptid. This avoids wildcards-as-API-feature unknowns for the multi-explicit-ids case while allowing wildcards to be tested separately.
- **Continue-on-error for multiple imports**: When importing multiple scriptids and one fails, continue and report a final error summary. Do not abort mid-batch.
- **Version bump**: `package.json` bumps from `0.2.0` → `0.3.0` (new public CLI subcommand is a minor feature release).

---

## Open Questions

### Resolved During Planning

- **JWT library**: Node crypto built-in — no new dep.
- **HTTP**: Native `fetch` — no new dep.
- **Form encoding**: `URLSearchParams` — no new dep.

### Deferred to Implementation

- **Wildcard response shape**: The IDE endpoint's response when `scriptid` contains `*` is unverified. Implementation should first test with `--dry-run`, then a live call, and document the actual response structure. If the endpoint returns a zip or multi-part response, the extraction logic in `object-import.ts` must adapt.
- **`projectfolder` field value**: The Python passes the SDF project directory path as `projectfolder`. The correct absolute path for the TypeScript version should be verified against a working call — it may need to be the SDF root, not the project root.

---

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification.*

```
twx-deploy import sb2 --type SAVEDSEARCH --scriptid customsearch_twx_*
              │
              ▼
   loadConfig() + getEnvironmentConfig()       ← existing config/loader.ts
              │
              ▼
   CredentialManager.resolve()                  ← existing auth/credentials.ts
   → { accountId, certificateId, privateKeyPath }
              │
              ▼
   fetchOAuth2Token()                           ← new core/object-import.ts
   1. Read PEM from privateKeyPath
   2. Build JWT header+payload
   3. Sign with PS256 (Node crypto)
   4. POST to suitetalk token endpoint
   → accessToken
              │
              ▼
   for each scriptid:
     importObjectFromApi()                      ← new core/object-import.ts
     POST /app/ide/ide.nl
       Sdf-Action: IMPORTOBJECTS
       type, scriptid, projectfolder,
       destinationfolder, isexcludefiles
     → rawXml (string)
              │
              ▼
     extractObjectXmls(rawXml, type)            ← handles single or multi-object
     → [{ scriptId, xml }, ...]
              │
              ▼
     writeObjectXml()                           ← writes to Objects/<type>/<id>.xml
     (respects --overwrite, errors on conflict)
              │
              ▼
   Final summary: N imported, M failed
```

---

## Implementation Units

- U1. **Core object-import module**

**Goal:** Implement the cert-OAuth2 + IDE endpoint call, XML extraction, and file-writing logic as a standalone module.

**Requirements:** R1–R7

**Dependencies:** None (uses only Node built-ins + existing auth/config types)

**Files:**
- Create: `src/core/object-import.ts`
- Test: `src/core/object-import.test.ts`

**Approach:**
- Export `fetchOAuth2Token(params: { accountId, certificateId, privateKeyPath }): Promise<string>` — reads PEM, constructs PS256 JWT manually (header + payload base64url-encoded, signed with `crypto.sign`), POSTs to token endpoint, returns `access_token`.
- Export `importObjectFromApi(params: { accountId, accessToken, type, scriptId, projectFolder, destFolder, dryRun }): Promise<string>` — builds form body with `URLSearchParams`, calls IDE endpoint, returns raw response text. In dry-run mode, logs request details and returns empty string.
- Export `extractObjectXmls(rawXml: string, type: string): Array<{ scriptId: string; xml: string }>` — uses tag-boundary scanning to split response into named objects. For unrecognized shapes, returns a single entry with scriptId `unknown` so the caller can write the raw content and warn.
- Export `writeObjectXml(params: { destDir: string; scriptId: string; xml: string; overwrite: boolean }): Promise<string>` — creates destination directory if needed, writes `<scriptId>.xml`, throws on conflict when `overwrite` is false, returns written path.
- Utility: `normalizeAccountId(accountId: string): string` — transforms `4138030_SB2` → `4138030-sb2` for URL construction.
- Utility: `buildNetsuiteBaseUrl(accountId: string): string` and `buildTokenUrl(accountId: string): string` — derive the two NetSuite endpoints.

**Patterns to follow:**
- `src/core/deployment.ts` for module structure and chalk/ora usage
- `import_object.py` for OAuth2 flow and IDE form fields

**Test scenarios:**
- Happy path: `fetchOAuth2Token` returns an access token given mock PEM and cert ID
- Happy path: `importObjectFromApi` with `dryRun: true` returns empty string and logs request details without making HTTP call
- Happy path: `extractObjectXmls` parses a single `<savedsearch>...</savedsearch>` response into one entry with the correct scriptId extracted from the XML
- Happy path: `extractObjectXmls` parses a response with two objects and returns two entries
- Happy path: `writeObjectXml` writes file to expected path and returns the absolute path
- Edge case: `extractObjectXmls` with unrecognized shape returns one entry with `scriptId: 'unknown'`
- Edge case: `writeObjectXml` with `overwrite: false` throws when file already exists
- Edge case: `writeObjectXml` with `overwrite: true` succeeds when file already exists
- Edge case: `normalizeAccountId` correctly transforms `4138030_SB2` → `4138030-sb2` and `4138030` → `4138030`
- Error path: `fetchOAuth2Token` throws a descriptive error when the token endpoint returns non-200
- Error path: `importObjectFromApi` throws when IDE endpoint returns non-200

**Verification:**
- All unit tests pass under `npm test` in `netsuite-deploy`
- `fetchOAuth2Token` produces a correctly-structured JWT (header.payload.signature, algorithm PS256) verifiable by decoding the header+payload

---

- U2. **Import CLI command**

**Goal:** Implement the `import <env>` commander command, wiring config/credential loading to the core module.

**Requirements:** R1–R6

**Dependencies:** U1

**Files:**
- Create: `src/cli/commands/import.ts`
- Test: `src/cli/commands/import.test.ts`

**Approach:**
- `createImportCommand()` returns a `Command` with argument `<environment>` and options: `--type <type>` (required), `--scriptid <id>` (collect array), `--dest <path>` (optional), `--dry-run` (flag), `--overwrite` (flag), `--config <path>` (optional, same as deploy).
- In action handler: call `loadConfig` → `getEnvironmentConfig` → `CredentialManager.resolve` (identical to deploy.ts boilerplate). Derive `destFolder` from `--dest` or `Objects/<type.toLowerCase()>`. Derive `projectFolder` from `pathResolver.getSdfPath(environment)`.
- Call `fetchOAuth2Token` once. Loop over `--scriptid` values: call `importObjectFromApi`, then `extractObjectXmls`, then `writeObjectXml` for each extracted object. Collect errors; on completion log a summary (`N imported, M failed`).
- Use `chalk` for output colors, `ora` for spinner during token fetch, matching deploy.ts UX.

**Patterns to follow:**
- `src/cli/commands/deploy.ts` — commander pattern, error handling, process.exit(1) on failure

**Test scenarios:**
- Happy path: command resolves env config, calls `fetchOAuth2Token` once, then calls `importObjectFromApi` per scriptid
- Happy path: `--dry-run` flag is passed through to `importObjectFromApi` and no file is written
- Happy path: multiple `--scriptid` values each produce separate `importObjectFromApi` + `writeObjectXml` calls
- Happy path: `--dest` override is used instead of the default `Objects/<type>` path
- Edge case: unknown environment name logs a descriptive error and exits with code 1
- Edge case: one of three `--scriptid` imports fails — other two succeed and final summary reports 2 imported, 1 failed
- Error path: `fetchOAuth2Token` throws — command exits with code 1, no imports attempted

**Verification:**
- `twx-deploy import --help` shows all flags
- All unit tests pass

---

- U3. **Register command and bump version**

**Goal:** Wire the `import` command into the CLI entry point and advance the package version.

**Requirements:** R1 (discoverable via `twx-deploy --help`)

**Dependencies:** U2

**Files:**
- Modify: `src/cli/index.ts`
- Modify: `package.json`

**Approach:**
- Add `import { createImportCommand } from './commands/import.js';` and `program.addCommand(createImportCommand());` in `src/cli/index.ts`.
- Bump `version` in `package.json` from `0.2.0` to `0.3.0`.

**Test expectation:** none — registration is structural; covered by the CLI help-text check in U2 verification.

**Verification:**
- `twx-deploy --help` lists `import` alongside `deploy` and `init`
- `npm run build` succeeds without TypeScript errors

---

- U4. **Skill documentation update and Python script retirement**

**Goal:** Document `twx-deploy import` in the skill reference, and delete the now-superseded Python script.

**Requirements:** R8, R9

**Dependencies:** U3 (build must pass before docs claim the feature exists)

**Files (tchow-essentials repo):**
- Modify: `plugins/netsuite-skills/skills/netsuite-sdf-deployment/SKILL.md`
- Delete: `plugins/netsuite-skills/skills/netsuite-sdf-deployment/scripts/import_object.py`
- Delete: `plugins/netsuite-skills/skills/netsuite-sdf-deployment/scripts/__pycache__/` (directory)
- Review and update if needed: `plugins/netsuite-skills/skills/netsuite-sdf-deployment/references/api-reference.md`

**Approach:**
- Add "### 8. Object Import" section to `SKILL.md` mirroring the structure of existing sections (Overview, Commands, Options, Examples). Document the CLI surface from R1–R6.
- Update the "Package Information" note at the bottom of `SKILL.md` to reflect v0.3.0.
- Verify `api-reference.md` has no references to `import_object.py`; update if found.
- Delete `import_object.py` and `__pycache__/`.

**Test expectation:** none — documentation change.

**Verification:**
- `SKILL.md` section 8 accurately describes `twx-deploy import` with correct flags and examples
- No mention of `import_object.py` remains in any skill reference file
- `scripts/` directory contains only `generate_cert.sh`

---

## System-Wide Impact

- **Interaction graph:** New command is additive; no existing commands affected.
- **Error propagation:** OAuth2 errors and IDE API errors surface via `chalk.red('Error:')` + `process.exit(1)`, matching deploy.ts behavior.
- **State lifecycle risks:** Partial writes on multi-scriptid failure — each file is written atomically; failed imports leave no partial file at destination.
- **API surface parity:** No existing API surface changes; `src/index.ts` (public exports) does not need to export the new module — it is CLI-only.
- **Integration coverage:** Live NetSuite calls are not covered by unit tests; the dry-run verification step serves as manual integration gate.
- **Unchanged invariants:** `deploy` command behavior, config schema, `CredentialManager` API — none of these change.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| NetSuite IDE endpoint rejects wildcard `scriptid` | Detect 400/error response; fall back to per-scriptid calls with no wildcard. Deferred to implementation empirical test. |
| Multi-object response format is a zip or binary | Log raw response on extraction failure; let implementation determine correct parsing. |
| PS256 JWT construction differs subtly from PyJWT output | Verify token exchange returns 200 on first dry-run live test; diff JWT headers if not. |
| Node crypto RSASSA-PSS API differs across Node 18 patch versions | Pin the signing approach to `crypto.sign` (sync) + explicit PSS parameters; test on Node 18 LTS. |

---

## Documentation / Operational Notes

- Build the npm package (`npm run build` in `netsuite-deploy`) after U3 before running any end-to-end import tests.
- `npm link` in `netsuite-deploy` + `npm link @twisted-x/netsuite-deploy` in an SDF project is the fastest way to test without publishing.
- The Python script (`import_object.py`) can be used for comparison testing before deletion — run both against the same scriptid and diff the resulting XML files.

---

## Sources & References

- Brainstorm approved plan: `.claude/plans/check-the-twx-deploy-skill-spicy-scone.md`
- Reference implementation: `plugins/netsuite-skills/skills/netsuite-sdf-deployment/scripts/import_object.py`
- Deploy command pattern: `src/cli/commands/deploy.ts` (netsuite-deploy repo)
- Credential manager: `src/auth/credentials.ts` (netsuite-deploy repo)
- NetSuite SDF IDE endpoint: internal, `Sdf-Action: IMPORTOBJECTS` on `/app/ide/ide.nl`
