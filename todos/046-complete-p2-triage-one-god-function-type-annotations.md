---
status: pending
priority: p2
issue_id: "046"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 046 — `_triage_one` god-function (180+ lines) and missing type annotations in server.py

## Problem Statement

Two related code quality issues in `server.py` that affect maintainability and readability. Neither is a correctness issue today but both increase the cost of future modifications.

## Findings

### 1. `_triage_one` is 180+ lines (`server.py`)

This function handles a single user's full incident triage: fetches sign-ins, UAL forensics, email events, OAuth grants, MFA changes, role changes, and builds the report. All of this logic is co-located in one function body. The current god-function is hard to test in isolation — there is no way to call just the sign-in fetching or just the persistence check without running the entire triage. It is also hard to modify one phase without risking side-effects on another.

It should be decomposed into sub-functions (e.g., `_triage_sign_ins()`, `_triage_ual()`, `_triage_email()`, `_triage_persistence()`) that each return typed results, with `_triage_one` becoming an orchestrator that calls them in sequence.

### 2. `Optional[X]` type annotations (`server.py`)

Approximately 40 function parameters and return types still use `Optional[X]` (pre-Python 3.10 style) instead of `X | None`. This is inconsistent with newer parameters added in recent todos, creating a mixed style that confuses static analysis and readability. The project targets Python 3.10+.

## Proposed Solutions

### Option A — Full decomposition + type annotation update (Recommended)

- Extract `_triage_one` into 4–5 focused sub-functions. Each should be independently testable and have clear typed inputs/outputs.
- Run a targeted find+replace to modernize `Optional[X]` → `X | None` syntax globally across `server.py`.
- Effort: Medium for decomposition, Small for types, Risk: Low

### Option B — Types only

- Leave `_triage_one` as-is and document it as intentional co-location. Only update type annotations.
- Effort: Small, Risk: None

## Acceptance Criteria

- [ ] `_triage_one` is decomposed into testable sub-functions (OR decision to keep as-is is documented in a code comment)
- [ ] `Optional[X]` → `X | None` applied consistently across server.py
- [ ] All sub-functions have type annotations on parameters and return values

## Work Log

- 2026-04-08: Identified in 3rd review pass
- 2026-04-08: Type annotation sweep (`Optional[X]` → `X | None`) deferred — global find+replace across ~40 existing occurrences carries risk of silent breakage (e.g. places where `Optional` is imported but not re-exported). New code written in this PR pass already uses `X | None` style. Full sweep tracked here as remaining work. `_triage_one` decomposition also deferred — no correctness issue, leaving as future refactor.
