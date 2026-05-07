---
name: hudu-upsert
description: |
  Upsert an asset of any Hudu asset_layout type using search-before-create with
  dry-run preview. Introspects the layout's field schema at runtime so field flags
  are always current. Use for one-off upserts against any layout, or to discover
  what fields a layout has before using the preset commands.
  Triggered by: hudu upsert, upsert asset, create or update hudu asset, upsert layout,
  upsert any layout, hudu asset upsert, generic upsert.
---

# Hudu Upsert (Generic)

Upsert an asset against any Hudu asset layout using runtime schema introspection.

## CLI Location

```bash
cd /home/tchow/.claude/plugins/marketplaces/tchow-essentials/plugins/hudu-skills
```

## Discover a layout's fields first

```bash
python3 scripts/hudu_api.py upsert "My Layout Name" --describe
# or equivalently:
python3 scripts/hudu_api.py asset-layouts show "My Layout Name"
```

This prints every field's CLI slug, label, type, and required flag.

## Upsert an asset (dry-run first, then live)

```bash
# Step 1: preview
python3 scripts/hudu_api.py upsert "My Layout" \
  --company "Client Corp" \
  --<slug> <value> \
  --dry-run

# Step 2: execute
python3 scripts/hudu_api.py upsert "My Layout" \
  --company "Client Corp" \
  --<slug> <value>
```

## Key flags

| Flag | Description |
|---|---|
| `<layout>` | Layout name (exact) or numeric ID — positional, required |
| `--company NAME` | Company name (resolved to ID) |
| `--company-id ID` | Company ID override |
| `--name NAME` | Asset name (derived from `--vendor`/`--product` if omitted) |
| `--asset-id ID` | Force update to a specific asset ID (disambiguation) |
| `--match-on SLUGS` | Comma-separated slugs for duplicate detection (e.g. `license-id,company`) |
| `--field SLUG=VAL` | Set any custom field by slug (repeatable; no schema needed) |
| `--data JSON` | Inline JSON payload merge |
| `--file PATH` | JSON file payload merge |
| `--dry-run` | Print resolved payload + match report, no API call |
| `--refresh-schema` | Bust the cached layout schema (auto-refreshed every 24h) |
| `--describe` | Print field schema for this layout and exit |

## Upsert semantics

- **0 matches** → POST (create)
- **1 match** → fetch-merge-PUT (update, preserving untouched fields)
- **2+ matches** → fail with candidate list; re-run with `--asset-id` to disambiguate

Default match key comes from `config/layout-defaults.json` for the layout, or falls back to `name`.

## Escape hatches

```bash
# --field: set a field not covered by named flags
python3 scripts/hudu_api.py upsert "Software License" \
  --company "Acme" --vendor "Adobe" \
  --field internal-tag="renewals-q1" --dry-run

# --data: full payload override
python3 scripts/hudu_api.py upsert "Software License" \
  --company "Acme" \
  --data '{"name": "Adobe CC", "custom_fields": [{"label": "Vendor", "value": "Adobe"}]}'

# --file: load payload from file
python3 scripts/hudu_api.py upsert "Software License" \
  --company "Acme" --file ~/license-payload.json
```

## Schema cache

Schema is cached at `~/.cache/hudu-skills/layouts/<id>.json` with a 24h TTL.
Bust with `--refresh-schema`. `--describe` uses a 1h TTL.
