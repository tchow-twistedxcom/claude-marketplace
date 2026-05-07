---
name: hudu-upsert-license
description: |
  Upsert a software license asset in Hudu using the "Software License" asset layout.
  Supports vendor, company, seats, pricing, license ID, portal, start/renewal dates,
  notes, and category fields. Includes duplicate detection (keyed on license ID by
  default), dry-run preview, and a JSON escape hatch for additional custom fields.
  Triggered by: hudu license, upsert license, license upsert, add license to hudu,
  create license, update license, software license, license management, license tracking,
  hudu license record, license renewal.
---

# Hudu Upsert License

Upsert a software license record into Hudu's "Software License" asset layout.

## CLI Location

```bash
cd /home/tchow/.claude/plugins/marketplaces/tchow-essentials/plugins/hudu-skills
```

## Discover your layout's actual field slugs first

Your "Software License" layout may have different custom-field slugs than the examples below. Run:

```bash
python3 scripts/hudu_api.py upsert "Software License" --describe
```

This prints every field's CLI slug, label, and type.

## Basic upsert (dry-run first)

```bash
# Preview before writing
python3 scripts/hudu_api.py upsert "Software License" \
  --company "Acme Corp" \
  --vendor "Microsoft 365" \
  --license-id "ABC-123-XYZ" \
  --seats 50 \
  --dry-run

# Execute when ready
python3 scripts/hudu_api.py upsert "Software License" \
  --company "Acme Corp" \
  --vendor "Microsoft 365" \
  --license-id "ABC-123-XYZ" \
  --seats 50
```

## Full example with all common fields

```bash
python3 scripts/hudu_api.py upsert "Software License" \
  --company "Acme Corp" \
  --vendor "Adobe Creative Cloud" \
  --license-id "ADOBECC-2026-001" \
  --seats 25 \
  --pricing 1200.00 \
  --portal "https://adminconsole.adobe.com" \
  --start-date "2026-01-01" \
  --renewal-date "2027-01-01" \
  --category "Design" \
  --notes "Annual subscription — auto-renews" \
  --dry-run
```

## Duplicate detection

Default match key: **license-id** (set in `config/layout-defaults.json`).
If no `--license-id` is provided, falls back to matching on `name` (vendor value).

Override with `--match-on`:
```bash
python3 scripts/hudu_api.py upsert "Software License" \
  --company "Acme" --vendor "Microsoft" \
  --match-on "vendor" --dry-run
```

## Update a specific asset (bypass duplicate search)

```bash
python3 scripts/hudu_api.py upsert "Software License" \
  --company "Acme" --asset-id 1234 \
  --renewal-date "2028-01-01"
```

## Add extra custom fields not covered by named flags

```bash
python3 scripts/hudu_api.py upsert "Software License" \
  --company "Acme" --vendor "Zoom" \
  --field po-number="PO-2026-0042" \
  --field internal-notes="Approved by finance Q1"
```

## Output as JSON (for piping)

```bash
python3 scripts/hudu_api.py upsert "Software License" \
  --company "Acme" --vendor "Zoom" --output json | jq '.id'
```
