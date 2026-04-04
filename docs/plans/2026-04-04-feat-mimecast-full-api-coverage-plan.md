---
title: "feat: Mimecast Plugin Full API Coverage"
type: feat
status: active
date: 2026-04-04
deepened: 2026-04-04
brainstorm: docs/brainstorms/2026-04-04-mimecast-full-api-coverage-brainstorm.md
---

# feat: Mimecast Plugin Full API Coverage

## Enhancement Summary

**Deepened on:** 2026-04-04
**Sections enhanced:** All major sections
**Research agents used:** kieran-python-reviewer, architecture-strategist, code-simplicity-reviewer, security-sentinel, performance-oracle, agent-native-reviewer, python-expert, refactoring-expert, best-practices-researcher, framework-docs-researcher, fastmcp-docs, learnings (mcp-tool-calling, celigo-put-full-replace)

### Key Improvements
1. **Security pre-work required before Phase 0**: Token cache not gitignored, XML injection in archive search, file permission hardening — must fix before expanding
2. **BaseDomain design corrected**: Replace `@staticmethod` handlers + `callable` annotation with `ABC`/`abstractmethod` + instance methods + `Callable[..., None]`
3. **MCP `_truncate()` is broken**: Hard truncation produces invalid JSON mid-object — must fix as part of Phase 0, not later
4. **Phase 0 vs YAGNI debate**: code-simplicity-reviewer recommends skipping module extraction (add directly to monolith), architecture-strategist recommends explicit imports over pkgutil. Implementation begins with Phase 1 directly, using explicit imports as a compromise.
5. **MCP coverage gap is larger than planned**: 18% coverage. Critical missing tools (quarantine release, sender block/permit, TTP impersonation) should be added in Phase 0.5.

### New Considerations Discovered
- `common_parser` in argparse is stateful — must use factory `make_common_parser()` per subparser, not shared parent
- `if source:` falsy-gates should be `if source is not None:` to allow `source=""` (empty string) through
- `_REGISTRY` needs duplicate registration guard to prevent silent overwrite
- `config/.gitignore` is missing `.mimecast_token_cache.json` — live credentials risk RIGHT NOW
- All API 2.0 tools need `openWorldHint=True` in ToolAnnotations
- `config backup/restore` MCP tools should be CLI-only — too high-impact for AI-accessible interface

---

## Overview

Expand the Mimecast plugin from **55 CLI operations / 10 MCP tools** to **~147 CLI operations / 31 MCP tools**, covering the complete Mimecast API 1.0 endpoint catalog plus new API 2.0-only categories.

The primary gap is **Awareness Training** (12 endpoints entirely missing). Beyond that, 10+ other API categories are partially or entirely absent. The expansion requires refactoring the 2,318-line monolithic `mimecast_api.py` into a domain module system to remain maintainable at scale.

## Problem Statement

The current plugin:
- Claims "28 operations" in `plugin.json` but actually has 55 — documentation is outdated
- Is missing the entire **Awareness Training API** (campaigns, phishing sims, SAFE scores, watchlists)
- Is missing **Web Security**, **Event Streaming**, **Address Alteration**, **SIEM Batch**, and others
- Has a monolithic 2,318-line `mimecast_api.py` that cannot scale to 147+ operations without becoming unmaintainable
- Has an MCP server with 10 tools (all API 1.0) that uses a dead code path for API 2.0
- Has **active security issues** that must be fixed before any expansion (see Security Pre-Work)

## Proposed Solution

### Architecture: Domain Module System

Replace the monolithic file with per-domain modules under `scripts/domains/`, each discovered by the orchestrator via **explicit imports** (not pkgutil auto-discovery). All existing CLI invocations (`python3 scripts/mimecast_api.py <resource> <action>`) are preserved exactly.

### Research Insights — Architecture

**From architecture-strategist:**
- Use **explicit imports** over pkgutil auto-discovery. `pkgutil.iter_modules` is implicit magic that hides dependencies, makes debugging hard, and violates "explicit is better than implicit" (PEP 20). Explicit imports make the dependency graph visible and are easier to test in isolation.
- The orchestrator's `_load_domains()` should be:
  ```python
  # Prefer this (explicit):
  from domains import account, email_security, ttp, user_management, ...
  # Over pkgutil auto-discovery
  ```
- If future plugins need dynamic loading, use Python entry_points packaging system — not filesystem scanning.

**From code-simplicity-reviewer (YAGNI challenge):**
- Phase 0 as a pure refactoring phase is a YAGNI violation. If the architecture supports it, add new domains directly and let the monolith coexist for now. The real question: "does the architecture enable Phase 1 work without Phase 0 first?" Answer: Yes, with incremental extraction.
- **Resolution**: Skip Phase 0 as a standalone phase. Instead, extract domains incrementally as each phase adds new endpoints. By Phase 4, the monolith will be fully extracted. This avoids shipping a zero-value refactor and gets Awareness Training delivered faster.

**Core design contracts (must be established before Phase 1):**

#### `BaseDomain` (scripts/domains/base.py) — Corrected Design
```python
from abc import ABC, abstractmethod
from typing import Callable, Any

class BaseDomain(ABC):
    def __init__(self, client: "MimecastClient"):
        self.client = client  # shared single instance

    @abstractmethod
    def get_cmd_map(self) -> dict[tuple[str, str], Callable[["argparse.Namespace"], None]]:
        """Return {(resource, action): bound_handler} dict."""
        ...

    @abstractmethod
    def register_parsers(self, subparsers: Any, make_common_parser: Callable) -> None:
        """Add argparse subparser entries to the two-level subparsers tree.

        Note: common_parser is a FACTORY FUNCTION — call it per subparser,
        do not share a single argparse parent across subparsers (argparse is stateful).
        """
        ...
```

**Key correction from kieran-python-reviewer:**
- `callable` (lowercase) is **not a valid type annotation** — it is a builtin function. Use `Callable[..., None]` from `typing` (Python 3.8) or `collections.abc`.
- `@staticmethod cmd_*(domain, args)` is an anti-pattern for domain methods. Use **bound instance methods** instead:
  ```python
  # WRONG (anti-pattern):
  @staticmethod
  def cmd_campaigns(domain, args):
      result = domain.get_campaigns(...)

  # CORRECT (bound instance method):
  def cmd_campaigns(self, args):
      result = self.get_campaigns(...)
  ```
- Use `from abc import ABC, abstractmethod` — no `raise NotImplementedError` needed when using `@abstractmethod`.

#### `@register_domain` Decorator — Corrected
```python
from typing import TypeVar
T = TypeVar("T", bound=BaseDomain)

_REGISTRY: dict[str, type[BaseDomain]] = {}

def register_domain(name: str):
    """Register a domain class by name."""
    def decorator(cls: type[T]) -> type[T]:
        if name in _REGISTRY:
            raise ValueError(
                f"Domain '{name}' already registered by {_REGISTRY[name].__name__}. "
                f"Duplicate registration from {cls.__name__}."
            )
        _REGISTRY[name] = cls
        return cls
    return decorator
```

**Key correction:** Add duplicate registration guard. Without it, a second import of the same module silently overwrites the first registration with no error.

#### Domain Module Pattern — Corrected (example: scripts/domains/awareness_training.py)
```python
from .base import BaseDomain, register_domain
from typing import Callable
import argparse

@register_domain("awareness_training")
class AwarenessTrainingDomain(BaseDomain):
    def get_campaigns(self, source=None, status=None):
        data = {}
        if source is not None:    # IMPORTANT: not `if source:` — empty string is valid
            data["source"] = source
        return self.client.post("/api/awareness-training/campaign/get-campaigns", data)

    def cmd_campaigns(self, args):  # bound instance method, not @staticmethod
        result = self.get_campaigns(source=getattr(args, 'source', None))
        format_output(result, args.output, 'awareness-campaigns')

    def get_cmd_map(self) -> dict[tuple[str, str], Callable]:
        return {
            ("awareness", "campaigns"):  self.cmd_campaigns,
            ("awareness", "safe-score"): self.cmd_safe_score,
            # ...
        }

    def register_parsers(self, subparsers, make_common_parser) -> None:
        p = subparsers.add_parser("awareness", help="Awareness Training operations")
        sub = p.add_subparsers(dest="action")

        # IMPORTANT: call make_common_parser() each time — argparse parents are stateful
        camp = sub.add_parser("campaigns", parents=[make_common_parser()])
        camp.add_argument("--source", help="Filter by source")
```

**Key fix from kieran-python-reviewer:** `if source:` falsy-gates must be `if source is not None:` to allow empty string `""` as a valid filter value.

#### Slim Orchestrator (scripts/mimecast_api.py → ~200 lines) — Explicit Imports
```python
import sys
from pathlib import Path

# Add scripts/ to sys.path so `from domains.X import Y` works
sys.path.insert(0, str(Path(__file__).parent))

# Explicit domain imports (preferred over pkgutil auto-discovery)
from domains.account import AccountDomain
from domains.email_security import EmailSecurityDomain
from domains.ttp import TTPDomain
from domains.user_management import UserManagementDomain
# ... etc

def _build_domain_registry(client):
    """Instantiate all domain classes with shared client."""
    domains = [
        AccountDomain(client),
        EmailSecurityDomain(client),
        # ...
    ]
    cmd_map = {}
    for domain in domains:
        cmd_map.update(domain.get_cmd_map())
    return cmd_map

def make_common_parser():
    """Factory: fresh argparse parent parser with --output, --profile flags.

    Must be a factory (not a shared instance) because argparse parent parsers
    are stateful — reusing one across subparsers causes action conflicts.
    """
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--output", choices=["table", "json", "csv"], default="table")
    p.add_argument("--profile", help="Config profile name")
    return p
```

#### Date Helpers (scripts/domains/utils.py)
Move `_add_date_shortcuts()` and `_resolve_date_range()` from the monolith to `scripts/domains/utils.py` as shared utilities.

### Target File Structure

```
plugins/mimecast-skills/
  plugin.json                          # Bump version per phase; update mcpServers if needed
  config/
    .gitignore                         # MUST ADD: .mimecast_token_cache.json
  scripts/
    mimecast_api.py                    # Slim orchestrator (~200 lines)
    mimecast_auth.py                   # Add chmod 0o600 to token cache writes
    mimecast_client.py                 # Add put_v2(), delete_v2(), patch_v2(), paginate_v2()
    mimecast_formatter.py              # Add new table formatters per phase
    domains/
      __init__.py                      # Empty package marker
      base.py                          # BaseDomain (ABC) + @register_domain + get_registry()
      utils.py                         # make_common_parser(), date shortcuts, _add_limit_arg
      account.py                       # account info/support-info/products/notifications
      email_security.py                # messages, archive (fix XML injection here)
      ttp.py                           # TTP URL/attachment/impersonation/decode/managed/summary
      user_management.py               # users CRUD + cloud-gateway + advanced ops
      group_management.py              # groups CRUD + members/find + groups-v2
      policy_management.py             # policies + blocked/permitted + anti-spoofing + greylisting
      reporting.py                     # audit/siem/stats/threat-intel + reports aliases
      quarantine.py                    # quarantine list/release/delete
      senders.py                       # senders blocked/permitted/unblock/unpermit
      dkim.py                          # dkim status/create
      delivery.py                      # delivery info/routes
      rejection.py                     # rejection logs
      domains_mgmt.py                  # domains list/external/internal
      track.py                         # message tracking search
      awareness_training.py            # Phase 1: 12 new endpoints
      web_security.py                  # Phase 3: 4 endpoints
      threat_intel_advanced.py         # Phase 3: 7 endpoints
      logs_advanced.py                 # Phase 3: 5 endpoints
      event_streaming.py               # Phase 4: 4 endpoints
      email_send.py                    # Phase 4: 2 endpoints
      directory_sync.py                # Phase 4: 2 endpoints
      domain_advanced.py               # Phase 4: 5 endpoints
      address_alteration.py            # Phase 4: 8 endpoints
      message_queues.py                # Phase 4: 4 endpoints
      seg_onboarding.py                # Phase 5: ~5 endpoints (API 2.0)
      analysis_response.py             # Phase 5: ~4 endpoints (API 2.0)
      threat_stats.py                  # Phase 5: ~3 endpoints (API 2.0)
      siem_batch.py                    # Phase 5: ~3 endpoints (API 2.0)
      config_backup.py                 # Phase 5: ~3 endpoints (API 2.0, CLI-only)
  skills/mimecast-api/
    SKILL.md                           # Update activation triggers each phase
    references/
      mimecast-authentication.md       # Existing — update with OAuth 2.0 requirement for Phase 1+
      mimecast-email-security.md       # Existing
      mimecast-user-management.md      # Existing — update Phase 2
      mimecast-policy-management.md    # Existing — update Phase 2/3
      mimecast-reporting.md            # Existing
      mimecast-awareness-training.md   # Phase 1: NEW
      mimecast-web-security.md         # Phase 3: NEW
      mimecast-threat-intel-advanced.md # Phase 3: NEW
      mimecast-event-streaming.md      # Phase 4: NEW
      mimecast-advanced-operations.md  # Phase 4: NEW (dir sync, domain adv, queues, address alteration)
      mimecast-api-2.0-endpoints.md    # Phase 5: NEW
  commands/
    mimecast-setup.md                  # Update Phase 1: warn HMAC-only users re: OAuth requirement
    mimecast-manage.md                 # Update each phase with new CLI examples
extensions/mimecast/
  src/server.py                        # Expand from 10 → 31 MCP tools (each phase)
  manifest.json                        # Update tools array each phase
  mimecast.dxt                         # Rebuild each phase
```

## Security Pre-Work (BEFORE Phase 0)

**From security-sentinel — critical issues that must be fixed before any expansion:**

### 1. Token Cache Not Gitignored
`config/.gitignore` excludes `mimecast_config.json` but NOT `.mimecast_token_cache.json`.

**Fix:**
```
# config/.gitignore — add this line:
.mimecast_token_cache.json
```

### 2. Token Cache File Permissions
When `mimecast_auth.py` writes the token cache, it uses default umask permissions (664 = world-readable on many systems).

**Fix in `mimecast_auth.py` wherever the token cache is written:**
```python
import os, stat

def _write_token_cache(self, cache_path, data):
    with open(cache_path, 'w') as f:
        json.dump(data, f)
    os.chmod(cache_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
```

### 3. XML Injection in Archive Search
`cmd_archive_search` in `email_security.py` passes user-supplied `subject`, `sender`, `recipient` directly into XML/JSON request fields without sanitization.

**Fix:** Strip or escape XML special characters (`<`, `>`, `&`, `"`, `'`) in these fields before including in request data. Use `html.escape()` or a simple sanitizer.

### 4. Confirmation Gate for `mimecast_send_email` MCP Tool
`destructiveHint: True` is insufficient for email send — AI could trigger mass sends. Add a required `confirm_send: bool` parameter that must be explicitly `True`.

**Implementation:**
```python
@mcp.tool(
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=False)
)
async def mimecast_send_email(
    to: str,
    subject: str,
    body: str,
    confirm_send: bool  # REQUIRED — must be True to proceed
) -> str:
    if not confirm_send:
        raise ToolError("Email send requires confirm_send=True. Review the email details and retry with confirm_send=True.")
    # proceed
```

### 5. Config Backup/Restore — CLI Only
`config backup/restore/export` (Phase 5) must never become MCP tools. They affect global account configuration and could cause irreversible damage when triggered by an AI agent. Implement as CLI-only; do NOT add to `server.py`.

## Implementation Phases

### Phase 0: Security + MCP Fixes (v1.0.1) — Pre-expansion Hardening

**Scope:** Security fixes + MCP quality fixes. Zero new CLI commands. Ships independently.

**Required security fixes (from Security Pre-Work above):**
1. Add `.mimecast_token_cache.json` to `config/.gitignore`
2. Add `chmod 0o600` to token cache write in `mimecast_auth.py`
3. Fix XML injection in `cmd_archive_search`
4. Add `confirm_send` gate to `mimecast_send_email` if it existed (deferred to Phase 4)

**MCP quality fixes (from agent-native-reviewer + performance-oracle):**

Fix `_truncate()` in `server.py` — current implementation hard-truncates at 25,000 chars, which produces invalid JSON mid-object and breaks Claude's ability to parse results:
```python
# CURRENT (broken):
def _truncate(data, max_chars=25000):
    s = json.dumps(data)
    return s[:max_chars]  # can cut mid-key or mid-string

# CORRECT:
def _truncate(data, max_items=100):
    """Return a JSON-safe summary when result sets are large."""
    if isinstance(data, list) and len(data) > max_items:
        return {
            "items": data[:max_items],
            "truncated": True,
            "total_returned": max_items,
            "hint": f"Use --limit or date filters to narrow results."
        }
    return data
```

**Add 6 missing critical MCP tools** (agent-native-reviewer: 18% coverage gap):
- `mimecast_release_held_message(message_id, reason)` — quarantine release (destructive)
- `mimecast_block_sender(address, comment)` — add sender to block list
- `mimecast_permit_sender(address, comment)` — add sender to permit list
- `mimecast_block_url(url, comment)` — TTP URL block
- `mimecast_permit_url(url, comment)` — TTP URL permit
- `mimecast_get_ttp_impersonation_logs(days, limit)` — impersonation threat data

**Update ToolAnnotations** to use typed object (not dict):
```python
from mcp.types import ToolAnnotations  # or fastmcp equivalent

@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True  # all Mimecast tools read live external data
    ),
    timeout=30.0  # network I/O tools need explicit timeout
)
```

**Fix API 2.0 dead code path** in `_mimecast_request()`:
```python
async def _mimecast_request(uri=None, body=None, v2_path=None):
    if v2_path:
        # API 2.0 — currently plumbed but never called
        resp = client.get_v2(v2_path)
    else:
        resp = client.post(uri, body)
    return _truncate(resp)
```

**Add `page_token` pagination** to list tools that return large result sets:
```python
async def mimecast_list_held_messages(
    page_token: str = None,
    limit: int = 50
) -> str:
    body = {"meta": {"pagination": {"pageSize": limit}}}
    if page_token:
        body["meta"]["pagination"]["pageToken"] = page_token
    result = client.get("/api/gateway/get-hold-message-list", body)
    return json.dumps(_truncate(result))
```

**Files modified:**
- `config/.gitignore` (add token cache)
- `scripts/mimecast_auth.py` (chmod fix)
- `scripts/mimecast_api.py` (XML injection fix in cmd_archive_search)
- `extensions/mimecast/src/server.py` (truncate fix, 6 new tools, annotations, pagination)

### Research Insights — Phase 0

**From performance-oracle:**
- The `all_logs = []` accumulation in `_fetch_ttp_logs_paginated` is a memory issue. If there are 100k TTP log entries, it builds a 100k-entry list in memory before returning. Consider streaming / early `max_results` cap:
  ```python
  def paginate_v2(self, uri, params=None, max_results=None):
      results = []
      next_token = None
      while True:
          if next_token:
              params = params or {}
              params["pageToken"] = next_token
          resp = self.get_v2(uri, params)
          page = resp.get("data", resp.get("value", []))
          results.extend(page)
          if max_results and len(results) >= max_results:
              return results[:max_results]
          next_token = resp.get("@nextLink") or resp.get("nextPageToken")
          if not next_token:
              break
      return results
  ```

**From python-expert (urllib → requests):**
- `mimecast_client.py` uses `urllib.request` which lacks connection pooling, session reuse, and proper SSL certificate handling by default. For a tool making 100+ requests, consider migrating to `requests.Session`. However, this is a deferred optimization — defer to post-v2.0.0 cleanup to avoid scope creep.

---

### Phase 1: Module Extraction + Architecture Foundation (v1.1.0)

**Scope:** Extract existing 55 operations into domain modules using the corrected architecture. Zero new endpoints.

**Note:** Revised from the YAGNI debate — we still do this extraction because Phase 1+ awareness training work is substantially cleaner with the domain module system. The extraction is also the moment to fix the argparse `common_parser` factory pattern.

**Pre-work (required before writing any code):**
1. Write regression baseline script `scripts/test_regression_baseline.sh` — invokes all 46 `cmd_map` entries with `--output json`, captures to `/tmp/mimecast_baseline/`
2. Audit all monolith helpers: `_add_date_shortcuts`, `_resolve_date_range`, `common_parser`, `args.output` default logic (line 2207)
3. Confirm `server.py` does NOT import from `mimecast_api.py` (verify it is self-contained)

**Key backward-compatibility requirements:**
- Alias: `("reports", "audit")` maps to same handler as `("audit", "events")` — must be explicitly registered in both `reporting.py` domain's `get_cmd_map()`
- `groups` (API 1.0) and `groups-v2` (API 2.0) remain separate resources
- `args.output` defaults to `"table"` when None (must be set in orchestrator, not each domain)
- `--profile` flag passed to `MimecastClient` before any domain is called

**Files created:**
- `scripts/domains/__init__.py`
- `scripts/domains/base.py` — `BaseDomain` (ABC), `@register_domain`, `get_registry()`
- `scripts/domains/utils.py` — `make_common_parser()` factory, `_add_date_shortcuts`, `_resolve_date_range`, `_add_limit_arg`
- One module per existing resource group (15 modules)

**Files modified:**
- `scripts/mimecast_api.py` — gutted to ~200-line orchestrator with explicit imports
- `scripts/mimecast_client.py` — add `put_v2()`, `delete_v2()`, `patch_v2()`, `paginate_v2(max_results=None)`

**Verification:**
```bash
# Before Phase 1 — capture baseline
bash scripts/test_regression_baseline.sh > /tmp/before.json

# After Phase 1 — diff against baseline
bash scripts/test_regression_baseline.sh > /tmp/after.json
diff /tmp/before.json /tmp/after.json  # must be empty
```

### Research Insights — Phase 1

**From refactoring-expert:**
- Extract `_add_date_shortcuts` and `_resolve_date_range` to `domains/utils.py` first — they are the most widely used helpers across domain modules. Test these utilities independently before refactoring domain classes.
- The `common_parser` argparse anti-pattern is the highest-risk item in Phase 1. A shared argparse parent across multiple `add_parser(..., parents=[common_parser])` calls will silently add duplicate actions on the second call, causing `argparse.ArgumentError`. Fix: `make_common_parser()` factory in `utils.py`.

**From best-practices-researcher:**
- Python's `pkgutil.iter_modules` + `importlib.import_module` (original plan) is used internally by Flask blueprints and Django apps — it works but is considered implicit. The alternative `entry_points` packaging system is for external plugin loading. For this project's internal domains, explicit `from domains.X import XDomain` is the right choice.
- At ~150 CLI operations, consider migrating from argparse to Click. Click has better sub-command support, built-in `--help` generation, and a cleaner command group pattern. Defer to Phase 5 cleanup — not in scope now.

---

### Phase 2: Awareness Training (v1.2.0) ⭐ Priority

**12 new CLI commands + 4 new MCP tools.**

All endpoints use `POST` to `/api/awareness-training/...` (API 1.0 with HMAC or OAuth — **must confirm with Mimecast docs; likely OAuth-only**).

| CLI Command | API Endpoint |
|---|---|
| `awareness campaigns` | `POST /api/awareness-training/campaign/get-campaigns` |
| `awareness campaign-users` | `POST /api/awareness-training/campaign/get-user-data` |
| `awareness performance` | `POST /api/awareness-training/company/get-performance-details` |
| `awareness performance-summary` | `POST /api/awareness-training/company/get-performance-summary` |
| `awareness phishing` | `POST /api/awareness-training/phishing/campaign/get-campaign` |
| `awareness phishing-users` | `POST /api/awareness-training/phishing/campaign/get-user-data` |
| `awareness safe-score` | `POST /api/awareness-training/company/get-safe-score-details` |
| `awareness safe-score-summary` | `POST /api/awareness-training/company/get-safe-score-summary` |
| `awareness queue` | `POST /api/awareness-training/queue/get-queue` |
| `awareness training-details` | `POST /api/awareness-training/user/get-training-details` |
| `awareness watchlist` | `POST /api/awareness-training/company/get-watchlist-details` |
| `awareness watchlist-summary` | `POST /api/awareness-training/company/get-watchlist-summary` |

**New MCP tools (server.py):**
- `mimecast_list_campaigns` — list training campaigns (readOnlyHint, openWorldHint)
- `mimecast_get_safe_scores` — get per-user SAFE scores (readOnlyHint, openWorldHint)
- `mimecast_get_phishing_results` — get phishing campaign data (readOnlyHint, openWorldHint)
- `mimecast_get_watchlist` — get high-risk user watchlist (readOnlyHint, openWorldHint)

**New formatters (mimecast_formatter.py):**
- `print_campaigns_table(items)` — columns: ID, Name, Launch Date, Sent, Completed, % Correct
- `print_safe_scores_table(items)` — columns: Email, Name, Dept, Risk Grade, Knowledge, Engagement
- `print_phishing_table(items)` — columns: Campaign, Sent, Clicked, Opened, Submitted
- `print_watchlist_table(items)` — columns: Email, Name, Dept, Risk Level

**New files:**
- `scripts/domains/awareness_training.py`
- `skills/mimecast-api/references/mimecast-awareness-training.md`

**Updated files:**
- `commands/mimecast-setup.md` — add OAuth requirement note for Awareness Training product
- `skills/mimecast-api/SKILL.md` — add awareness training trigger keywords
- `plugins/mimecast-skills/plugin.json` — bump to 1.2.0, update description
- `.claude-plugin/marketplace.json` — bump version to match

### Research Insights — Phase 2 (Awareness Training)

**From framework-docs-researcher (FastMCP):**
- Use `ToolAnnotations` typed import: `from mcp.types import ToolAnnotations` (or `from fastmcp import ToolAnnotations`). Pass as `annotations=ToolAnnotations(...)` — not a dict.
- All 4 Awareness Training MCP tools should use `timeout=30.0` since these endpoints aggregate training data and can be slow.
- Use `ToolError` (not Python `Exception`) for user-visible error messages: `raise ToolError("Awareness Training requires OAuth 2.0. Configure OAuth in mimecast_config.json.")` — this surfaces cleanly to Claude rather than a traceback.
- Set `openWorldHint=True` for all Mimecast tools — they read live external data.

**SAFE score API notes:**
- The `safe-score-details` endpoint returns per-user risk breakdown including behavioral analytics. The `mimecast_get_safe_scores` MCP tool should support `--email` filtering to avoid returning all users (privacy + performance).
- Watchlist endpoint may require special Awareness Training product license. Add graceful license check: if response contains `err_licence_check_failed`, return a friendly message explaining the license requirement.

---

### Phase 3: Expand Existing Categories (v1.3.0)

**~21 new CLI commands + 4 new MCP tools.**

Fills gaps in already-implemented categories.

**Account (+3):**
| `account support-info` | `POST /api/account/get-support-info` |
| `account products` | `POST /api/account/get-products` |
| `account notifications` | `POST /api/account/get-dashboard-notifications` |

**Groups (+4):**
| `groups update` | `POST /api/directory/update-group` |
| `groups delete` | `POST /api/directory/delete-group` |
| `groups members` | `POST /api/directory/get-group-members` |
| `groups find` | `POST /api/directory/find-groups` |

**Users Advanced (+8):**
| `users delegates` | `POST /api/user/get-user-delegates` |
| `users attributes` | `POST /api/user/get-user-attributes` |
| `users aliases` | `POST /api/user/get-user-aliases` |
| `users profile` | `POST /api/user/get-user-profile` |
| `users contacts` | `POST /api/user/get-most-used-contacts` |
| `users import` | `POST /api/user/import-users` |
| `users update-attributes` | `POST /api/user/update-user-attributes` |
| `users add-alias` | `POST /api/user/add-user-alias` |

**Anti-Spoofing (+4, full CRUD):**
| `policies anti-spoofing-create` | `POST /api/policy/antispoofing-bypass/create-policy` |
| `policies anti-spoofing-update` | `POST /api/policy/antispoofing-bypass/update-policy` |
| `policies anti-spoofing-delete` | `POST /api/policy/antispoofing-bypass/delete-policy` |
| `policies anti-spoofing-list` | `POST /api/policy/antispoofing-bypass/get-policy` (already exists as partial) |

**Note:** Anti-spoofing update/delete use **fetch-merge-PUT pattern** to prevent silent field destruction (per institutional learning).

**New MCP tools:** `mimecast_get_group_members`, `mimecast_find_groups`, `mimecast_get_user_profile`, `mimecast_list_user_delegates`

**Updated refs:** `mimecast-user-management.md`, `mimecast-policy-management.md`

### Research Insights — Phase 3

**From agent-native-reviewer:**
- `mimecast_find_groups` should support fuzzy search, not just exact match. The Mimecast `find-groups` endpoint accepts a query string — expose it as a `query` parameter in the MCP tool.
- `mimecast_get_user_profile` needs `email` as a required parameter (not optional). Make it explicit in the function signature to avoid confusing tool calls.
- Group delete is a destructive operation. Add `mimecast_delete_group` to MCP tool list with `destructiveHint=True` and a `confirm_delete: bool` gate (same pattern as email send).

**From kieran-python-reviewer:**
- `users import` is a write operation. The CLI handler for `cmd_users_import` must validate the input file exists and is valid JSON/CSV before making the API call. Add `--dry-run` flag that validates the file without submitting.
- For `update-attributes`, always GET current attributes first, merge with user-supplied changes, then PUT — never send partial attribute payloads.

---

### Phase 4: Security Operations (v1.4.0)

**16 new CLI commands + 4 new MCP tools.**

**Web Security (+4):**
| `web-security create` | `POST /api/ttp/websecurity/create-policy` |
| `web-security list` | `POST /api/ttp/websecurity/get-policy` |
| `web-security update` | `POST /api/ttp/websecurity/update-policy` |
| `web-security delete` | `POST /api/ttp/websecurity/delete-policy` |

**Advanced Threat Intel (+7):**
| `threat-intel byod-create` | `POST /api/ttp/remediation/create` |
| `threat-intel byod-get` | `POST /api/ttp/remediation/get-remediation-incident` |
| `threat-intel byod-delete` | `POST /api/ttp/remediation/delete` |
| `threat-intel incident-find` | `POST /api/ttp/remediation/find-incidents` |
| `threat-intel incident-get` | `POST /api/ttp/remediation/get-incident` |
| `threat-intel incident-create` | `POST /api/ttp/remediation/create-incident` |
| `threat-intel incident-create-v2` | `POST /api/ttp/remediation/create-incident-v2` |

**Advanced Logs (+5):**
| `logs dlp` | `POST /api/dlp/get-logs` |
| `logs journal` | `POST /api/journal/get-journal-entries` |
| `logs archive-view` | `POST /api/archive/get-view-logs` |
| `logs archive-search` | `POST /api/archive/get-search-logs` |
| `logs search` | `POST /api/log/get-search-logs` |

**New files:** `web_security.py`, `threat_intel_advanced.py`, `logs_advanced.py`
**New refs:** `mimecast-web-security.md`, `mimecast-threat-intel-advanced.md`
**New MCP tools:** `mimecast_list_web_security_policies`, `mimecast_find_incidents`, `mimecast_get_dlp_logs`, `mimecast_search_logs`

### Research Insights — Phase 4

**From security-sentinel:**
- DLP log endpoint returns sensitive email content (PII). `mimecast_get_dlp_logs` MCP tool must include `readOnlyHint=True, openWorldHint=True` and its description should warn: "Returns sensitive email content. Ensure compliance with data access policies before use."
- Incident creation (`threat-intel incident-create`) is a destructive/write operation. Add `destructiveHint=True` to `mimecast_create_incident` MCP tool.
- Archive search (`logs archive-search`) subject/sender/recipient fields — this is where the XML injection risk lives. The fix from Phase 0 security pre-work must be verified here.

**From performance-oracle:**
- Journal entries can be extremely large. `logs journal` must support pagination and a `--max-results` cap (default 500). Do not pull all journal entries without limits.
- DLP logs response format differs by Mimecast plan — some plans return JSON, others return a CSV-like format. Add format detection in `cmd_logs_dlp`.

---

### Phase 5: Infrastructure Operations (v1.5.0)

**25 new CLI commands + 4 new MCP tools.**

**Event Streaming (+4):** `events get`, `events latest-token`, `events dns-logs`, `events proxy-logs`
**Email Send (+2):** `email send`, `email upload` (destructiveHint in MCP)
**Directory Sync (+2):** `dir-sync connection`, `dir-sync execute`
**Advanced Domain (+5):** `domain-adv verify`, `domain-adv get-code`, `domain-adv pending`, `domain-adv create`, `domain-adv provision-status`
**Address Alteration (+8):** `address-alter def-list/create/update/delete`, `address-alter pol-list/create`, `address-alter set-list/create`
**Message Queues (+4):** `queues processing`, `queues hold-summary`, `queues inbound`, `queues outbound`

**Note:** All address alteration updates use **fetch-merge-PUT pattern** per institutional learning.

**New files:** `event_streaming.py`, `email_send.py`, `directory_sync.py`, `domain_advanced.py`, `address_alteration.py`, `message_queues.py`
**New refs:** `mimecast-event-streaming.md`, `mimecast-advanced-operations.md`
**New MCP tools:** `mimecast_get_events`, `mimecast_send_email` (destructive + confirm gate), `mimecast_get_queue_summary`, `mimecast_list_address_alterations`

### Research Insights — Phase 5

**From security-sentinel:**
- `email send` is the highest-risk operation in the entire plugin. The MCP tool MUST have `confirm_send: bool` parameter (see Security Pre-Work, item 4). Without this gate, an AI agent could trigger mass email sends.
- `dir-sync execute` is also high-risk — it triggers a directory sync which could propagate deletions from a corrupt LDAP source. Add `mimecast_execute_directory_sync` as CLI-only. Do NOT add to MCP.
- Event streaming DNS/proxy logs should be treated as sensitive data (reveals internal network patterns). MCP tools for these should include data sensitivity warning in description.

**From agent-native-reviewer:**
- `mimecast_get_queue_summary` is the most useful new MCP tool in this phase. It answers "what's stuck?" — critical for email delivery troubleshooting. Prioritize this tool's implementation and test it thoroughly.
- Queue inbound/outbound breakdown is more useful than a flat count. The MCP tool should return both current queue depth AND recent trends (last 1h, 24h).

---

### Phase 6: API 2.0 New Categories (v2.0.0)

**~18 new CLI commands + 5 new MCP tools. Major version bump.**

All use `client.get_v2()` / `client.post_v2()` with `services.mimecast.com` base URL. **Require OAuth credentials** — HMAC users will get a graceful error with instruction to configure OAuth.

**SEG Onboarding (~5):** `seg-onboard status/domains/connectors/policies/validate`
**Analysis & Response (~4):** `analysis search/remediate/status/indicators`
**Threat & Security Statistics (~3):** `stats threats/email/ttp`
**SIEM Batch (~3):** `siem-batch create/status/download`
**Config Backup (~3):** `config backup/restore/export` — **CLI-only, never MCP**

**New files:** `seg_onboarding.py`, `analysis_response.py`, `threat_stats.py`, `siem_batch.py`, `config_backup.py`
**New ref:** `mimecast-api-2.0-endpoints.md`
**New MCP tools:** `mimecast_get_threat_stats`, `mimecast_search_analysis`, `mimecast_create_siem_batch`, `mimecast_get_seg_status`
*(Note: `mimecast_backup_config` removed from MCP — CLI-only per security policy)*

**SIEM batch note:** `siem-batch download` may return large responses — implement file output (`--output-file`) rather than stdout for this endpoint.

### Research Insights — Phase 6

**From best-practices-researcher (API 2.0 patterns):**
- API 2.0 uses cursor-based pagination (`nextPageToken` or `@nextLink`) rather than API 1.0's `pageToken`. The `paginate_v2()` method in `mimecast_client.py` must detect both formats.
- API 2.0 responses may include `value` array key instead of `data` — response normalization must handle both: `items = resp.get("data") or resp.get("value") or []`.
- OAuth token refresh is handled by `mimecast_auth.py`. Verify that token refresh errors in API 2.0 flows produce a user-friendly message ("OAuth token expired, re-authenticate with `mimecast setup --oauth`").

**From framework-docs-researcher (FastMCP for API 2.0):**
- API 2.0 tools in `server.py` should use the `v2_path` parameter of `_mimecast_request()` (currently dead code — must be activated in Phase 0). Example:
  ```python
  async def mimecast_get_threat_stats(days: int = 30) -> str:
      result = await _mimecast_request(
          v2_path="/api/stats/get-threat-statistics",
          body={"data": [{"days": days}]}
      )
      return json.dumps(_truncate(result))
  ```

---

## Technical Considerations

### API 1.0 vs 2.0 Endpoint Rules

| Endpoint prefix | Client method | Auth | Base URL |
|---|---|---|---|
| `/api/...` | `client.post()` / `client.get()` | HMAC or OAuth | `api.mimecast.com` |
| `/**/cloud-gateway/...` | `client.get_v2()` / `client.post_v2()` | OAuth only | `services.mimecast.com` |

**Awareness Training API** (`/api/awareness-training/...`): Despite `/api/` prefix, these endpoints require **Awareness Training product assignment** in the Mimecast admin console. Test before assuming HMAC works — they may require OAuth.

### API 2.0 Response Normalization

API 2.0 responses are not wrapped in `{"data": [...]}`. Handlers must normalize to the API 1.0 format for consistent `format_output()` processing:
```python
# In cmd_* handlers for API 2.0 endpoints:
result = self.list_external_domains()
items = result.get("data") or result.get("value") or []
format_output({"data": items}, args.output, 'domains')
```

### MCP Server Expansion

The MCP `server.py` is self-contained (does not import from `mimecast_api.py` — confirmed). Expansion adds `@mcp.tool` decorated async functions using the existing `_mimecast_request(uri, body, v2_path)` helper. API 2.0 tools pass `v2_path=` instead of `uri=`.

**Tool naming convention:**
- `mimecast_list_*` — listing/search (readOnlyHint, openWorldHint)
- `mimecast_get_*` — single item (readOnlyHint, openWorldHint)
- `mimecast_create_*` — creation (openWorldHint: False, idempotentHint: False)
- `mimecast_delete_*` — deletion (destructiveHint: True, confirm_delete gate)
- `mimecast_send_*` — sends/triggers (destructiveHint: True, confirm_send gate)

**ToolAnnotations pattern:**
```python
@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True
    ),
    timeout=30.0
)
```

### Version Strategy

| Version | Phase | CLI Ops | MCP Tools |
|---|---|---|---|
| 1.0.0 | Current | 55 | 10 |
| 1.0.1 | Phase 0 — security + MCP fixes | 55 | 16 |
| 1.1.0 | Phase 1 — module extraction | 55 | 16 |
| 1.2.0 | Phase 2 — awareness training | 67 | 20 |
| 1.3.0 | Phase 3 — expand categories | 88 | 24 |
| 1.4.0 | Phase 4 — security ops | 104 | 28 |
| 1.5.0 | Phase 5 — infrastructure | 129 | 32 |
| 2.0.0 | Phase 6 — API 2.0 categories | ~147 | 36 |

## Acceptance Criteria

### Phase 0 (Security + MCP Fixes)
- [ ] `.mimecast_token_cache.json` in `config/.gitignore`
- [ ] Token cache file created with 0o600 permissions
- [ ] `_truncate()` returns valid JSON structure (not hard-truncated string)
- [ ] 6 new MCP tools appear in `fastmcp list` output
- [ ] All MCP tools use `ToolAnnotations` typed object with `openWorldHint=True`
- [ ] API 2.0 `v2_path` code path activated and tested in `_mimecast_request()`

### Phase 1 (Module Extraction)
- [ ] All 46 existing `cmd_map` entries produce identical `--output json` output before and after extraction (diff test passes)
- [ ] `("reports", "audit")` alias still maps to same handler as `("audit", "events")`
- [ ] `groups` (API 1.0) and `groups-v2` (API 2.0) remain separate working resources
- [ ] `make_common_parser()` factory confirmed — no argparse action conflicts on multiple calls
- [ ] `--profile` flag correctly reaches all domain module clients
- [ ] `mimecast_api.py` is ≤ 250 lines
- [ ] MCP `server.py` unchanged and still starts + lists 16 tools

### Phase 2 (Awareness Training)
- [ ] All 12 `awareness *` commands return valid JSON or graceful `ToolError` message
- [ ] `awareness safe-score --output table` renders SAFE score grades in tabular format
- [ ] `awareness campaigns` with no data returns "No results found." (not error)
- [ ] 4 new MCP tools appear in `fastmcp list` output
- [ ] OAuth-only auth requirement documented in `mimecast-setup.md`
- [ ] `plugin.json` version = 1.2.0, matches `marketplace.json`

### Phases 3-6
- [ ] All new `(resource, action)` keys are unique (no cmd_map collisions)
- [ ] All update operations that use PUT follow fetch-merge-PUT pattern
- [ ] Phase 6 commands gracefully error for HMAC-only users: "This endpoint requires OAuth 2.0 credentials. See mimecast-setup for configuration instructions."
- [ ] `plugin.json` and `marketplace.json` versions stay in sync at each phase
- [ ] All destructive MCP tools require confirmation gate parameter
- [ ] `config backup/restore/export` has NO MCP tool (CLI-only)

## Dependencies & Risks

| Risk | Mitigation |
|---|---|
| Awareness Training endpoints require OAuth, but user has HMAC-only | Raise `ToolError` with setup instructions; `awareness` commands check at startup |
| argparse common_parser shared instance causes action conflicts | `make_common_parser()` factory in Phase 1 pre-work |
| `_REGISTRY` duplicate registration on module reimport | Duplicate registration guard added to `@register_domain` |
| Domain loader fails silently | Explicit warning to stderr per failed module; print loaded module count at startup with `--verbose` |
| `server.py` breaks when monolith is split | Confirm `server.py` is self-contained before Phase 1 starts (already confirmed) |
| Alias `("reports", "audit")` lost in extraction | Explicit comment in `reporting.py` registering both keys |
| Phase 6 SIEM batch responses exceed memory | Implement `--output-file` flag for `siem-batch download` |
| API endpoint paths may differ from docs | Test each Phase 2 endpoint against sandbox before declaring complete |
| AI agent triggers mass email send via MCP | `confirm_send: bool` required parameter gate on `mimecast_send_email` |
| config backup/restore causes account-wide damage | `config_backup.py` CLI-only — never added to `server.py` |

## References

### Key Files to Modify
- `plugins/mimecast-skills/config/.gitignore` — add token cache (Phase 0)
- `plugins/mimecast-skills/scripts/mimecast_auth.py` — chmod fix (Phase 0)
- `plugins/mimecast-skills/scripts/mimecast_api.py` — decompose to orchestrator (Phase 1)
- `plugins/mimecast-skills/scripts/mimecast_client.py` — add `put_v2`, `delete_v2`, `patch_v2`, `paginate_v2`
- `plugins/mimecast-skills/scripts/mimecast_formatter.py` — add formatters per phase
- `extensions/mimecast/src/server.py` — expand 10 → 36 MCP tools
- `extensions/mimecast/manifest.json` — update tools array per phase
- `plugins/mimecast-skills/plugin.json` — version + description per phase
- `.claude-plugin/marketplace.json` — version sync per phase

### Mimecast API Documentation
- API 1.0 Endpoint Reference: https://integrations.mimecast.com/documentation/endpoint-reference/
- Awareness Training API: https://integrations.mimecast.com/documentation/endpoint-reference/awareness-training/
- API 2.0 Reference: https://integrations.mimecast.com/documentation/api-2,-d-,0-reference/

### Institutional Learnings Applied
- `docs/solutions/integration-issues/celigo-put-full-replace-*.md` — fetch-merge-PUT pattern for all update operations
- n8n MCP tool patterns — calling convention and tool exposure architecture
- Security: token cache permissions pattern (from security-sentinel review)
