---
status: pending
priority: p3
issue_id: "065"
tags: [code-review, architecture]
dependencies: []
---

# 065 — Architecture tech debt — cross-plugin path coupling + service account prefixes not configurable

## Problem Statement

Two architectural issues in `audit_m365_sync.py` that would cause pain when extending the system:

1. **Cross-plugin path coupling**: `audit_m365_sync.py` hardcodes a filesystem path into the `m365-skills` peer plugin via relative navigation: `REPO_ROOT = PLUGIN_DIR.parent.parent` then `AZURE_CLI = REPO_ROOT / "plugins" / "m365-skills" / ...`. This is a direct plugin boundary violation — the mimecast plugin knows the exact directory name of the m365-skills plugin. Moving or renaming either plugin breaks the audit silently.

2. **Service account exclusion patterns baked into source**: `AZURE_SVC_PREFIXES`, `AZURE_SVC_CONTAINS`, and `MIMECAST_INFRA_PREFIXES` are organization-specific naming patterns encoded at source level (lines 36-53). A new deployment with different naming conventions (e.g., `admin-` instead of `svc-`) cannot override these without editing the source file.

## Findings

```python
# audit_m365_sync.py lines 58-63
SCRIPT_DIR = Path(__file__).parent
PLUGIN_DIR = SCRIPT_DIR.parent
REPO_ROOT = PLUGIN_DIR.parent.parent  # mimecast plugin knows m365-skills path
AZURE_CLI = REPO_ROOT / "plugins" / "m365-skills" / "skills" / "azure-ad" / "scripts" / "azure_ad_api.py"

# audit_m365_sync.py lines 36-53 (organization-specific, no override mechanism)
AZURE_SVC_PREFIXES = ("svc-", "sync_", "ntservice", "dnsuser", "ncldap", "snipe",)
AZURE_SVC_CONTAINS = ("ldapsync",)
MIMECAST_INFRA_PREFIXES = ("abuse@", "postmaster@", "noreply@", ...)
```

## Proposed Solutions

Option A (Recommended):
1. Replace hardcoded `AZURE_CLI` path with environment variable: `AZURE_CLI = Path(os.environ.get("AZURE_AD_CLI_PATH", str(REPO_ROOT / "plugins" / "m365-skills" / ...)))`. Document in SKILL.md as optional override.
2. Add `--svc-prefixes` CLI arg (comma-separated list) that replaces or augments `AZURE_SVC_PREFIXES`. Default to current tuple for backward compatibility.
- Effort: Small. Risk: Low.

Option B: Leave as-is with a comment documenting the coupling assumption. Acceptable for single-repo deployment but blocks portability.

## Acceptance Criteria

- [ ] `AZURE_CLI` path derives from `AZURE_AD_CLI_PATH` env var if set (falls back to current path derivation)
- [ ] SKILL.md documents `AZURE_AD_CLI_PATH` as an optional override env var
- [ ] `--svc-prefixes` CLI arg (or equivalent) allows overriding service account prefix patterns without source edits

## Work Log

- 2026-04-08: Found by architecture-strategist in 4th review pass
