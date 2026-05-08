---
name: hudu-upsert-license
description: |
  Upsert a software license or contract asset in Hudu using the "Contracts / Licenses"
  asset layout. Supports name, license ID, seats, pricing, portal, start/renewal dates,
  notes, category, version, and importance fields. Category is required and must be one of:
  CRM, Database, EDI, ERP, Finance, Marketing, Sales, Other.
  Includes duplicate detection (keyed on license ID by default), dry-run preview,
  and a JSON escape hatch for additional custom fields.
  Triggered by: hudu license, upsert license, license upsert, add license to hudu,
  create license, update license, software license, license management, license tracking,
  hudu license record, license renewal, contracts licenses.
---

# Hudu Upsert License

Upsert a software license record into Hudu's "Contracts / Licenses" asset layout.

## CLI Location

```bash
cd /home/tchow/.claude/plugins/marketplaces/tchow-essentials/plugins/hudu-skills
```

## Discover your layout's actual field slugs first

```bash
python3 scripts/hudu_api.py upsert "Contracts / Licenses" --describe
```

This prints every field's CLI slug, label, type, required flag, and allowed values for dropdowns.

## Basic upsert (dry-run first)

```bash
# Preview before writing
python3 scripts/hudu_api.py upsert "Contracts / Licenses" \
  --company "Acme Corp" \
  --name "Microsoft 365" \
  --license-id "ABC-123-XYZ" \
  --license-seats "50" \
  --category "ERP" \
  --dry-run

# Execute when ready
python3 scripts/hudu_api.py upsert "Contracts / Licenses" \
  --company "Acme Corp" \
  --name "Microsoft 365" \
  --license-id "ABC-123-XYZ" \
  --license-seats "50" \
  --category "ERP"
```

## Full example with all common fields

```bash
python3 scripts/hudu_api.py upsert "Contracts / Licenses" \
  --company "Acme Corp" \
  --name "Adobe Creative Cloud" \
  --license-id "ADOBECC-2026-001" \
  --license-seats "25" \
  --pricing "1200.00/yr" \
  --portal "https://adminconsole.adobe.com" \
  --start-date "2026-01-01" \
  --expiration-renewal-date "2027-01-01" \
  --category "Marketing" \
  --importance "High" \
  --notes "Annual subscription — auto-renews" \
  --dry-run
```

## Category field — required, allowed values

| Value | Use for |
|---|---|
| `CRM` | CRM platforms (Salesforce, HubSpot, etc.) |
| `Database` | Database tools |
| `EDI` | EDI platforms |
| `ERP` | ERP / business systems (NetSuite, SAP, etc.) |
| `Finance` | Finance / accounting tools |
| `Marketing` | Marketing platforms |
| `Sales` | Sales tools |
| `Other` | Anything else |

Importance (optional): `Critical`, `High`, `Medium`, `Low`

## Duplicate detection

Default match key: **license-id** (set in `config/layout-defaults.json`).
If no `--license-id` is provided, falls back to matching on `name`.

Override with `--match-on`:
```bash
python3 scripts/hudu_api.py upsert "Contracts / Licenses" \
  --company "Acme" --name "Microsoft" \
  --match-on "name" --dry-run
```

## Update a specific asset (bypass duplicate search)

```bash
python3 scripts/hudu_api.py upsert "Contracts / Licenses" \
  --company "Acme" --asset-id 1234 \
  --expiration-renewal-date "2028-01-01"
```

## Add extra custom fields not covered by named flags

```bash
python3 scripts/hudu_api.py upsert "Contracts / Licenses" \
  --company "Acme" --name "Zoom" \
  --field po-number="PO-2026-0042"
```

## Output as JSON (for piping)

```bash
python3 scripts/hudu_api.py upsert "Contracts / Licenses" \
  --company "Acme" --name "Zoom" --output json | jq '.id'
```
