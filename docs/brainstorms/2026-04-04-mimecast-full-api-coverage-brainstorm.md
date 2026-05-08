# Mimecast Full API Coverage Brainstorm

**Date**: 2026-04-04
**Status**: Decided — proceeding to plan

## What We're Building

Expanding the Mimecast plugin from 55 CLI operations / 10 MCP tools to ~147 CLI operations / 31 MCP tools, covering the complete Mimecast API 1.0 endpoint catalog plus new API 2.0-only categories.

The most critical gap is **Awareness Training** (12 endpoints) — campaigns, phishing simulations, SAFE scores, watchlists, performance metrics, and training completion tracking. Beyond that, 10+ other API categories are partially or entirely missing.

## Why This Approach

**Modular architecture** over continuing the monolithic pattern:
- Current `mimecast_api.py` is 2,318 lines with 55 operations. Adding ~90 more would push it past 5,000 lines.
- Per-domain modules (awareness_training.py, web_security.py, etc.) with a shared `BaseDomain` class and decorator-based registration.
- Slim orchestrator pattern: `mimecast_api.py` becomes ~200 lines of argparse + routing.
- Backward compatible: all existing `(resource, action)` CLI invocations work identically.

**Simultaneous CLI + MCP** because:
- CLI gives full control with argparse flags, output formatting, piping
- MCP tools enable conversational AI interaction with key read operations
- Not 1:1 — only ~31 of ~147 operations become MCP tools (read-heavy selection)

**Phased delivery** (6 phases, v1.1.0 → v2.0.0):
- Phase 0: Module extraction (no new endpoints, pure refactoring with regression testing)
- Phase 1: Awareness Training (the specific gap identified)
- Phase 2-4: Fill remaining API 1.0 gaps by priority
- Phase 5: API 2.0-only categories (major version bump)

## Key Decisions

1. **Split into domain modules** — each domain is a class in `scripts/domains/<name>.py` with `@register_domain` decorator
2. **CLI + MCP simultaneously** — every phase adds both CLI commands and selected MCP tools
3. **Full reference docs** — new `.md` files per API category in `skills/mimecast-api/references/`
4. **API 1.0 + API 2.0** — complete coverage of both API generations
5. **Awareness Training is Phase 1** — highest priority gap to fill first after module extraction

## Resolved Questions

- **Scope**: Full API 1.0 + API 2.0 (user confirmed)
- **Architecture**: Modular split (user selected over monolithic or hybrid)
- **API 2.0 target**: Both CLI and MCP simultaneously (user selected)
- **Documentation**: Full reference docs for all new categories (user confirmed)
