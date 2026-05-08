---
name: hudu-upsert-contract
description: |
  Upsert a vendor contract asset in Hudu using the "Contracts / Licenses" asset layout.
  Supports name, license ID, pricing, portal, start/renewal dates, notes, category,
  version, and importance fields. Category is required and must be one of:
  CRM, Database, EDI, ERP, Finance, Marketing, Sales, Other.
  Includes duplicate detection (keyed on license ID by default), dry-run preview,
  and a JSON escape hatch for additional custom fields.
  Triggered by: hudu contract, upsert contract, contract upsert, add contract to hudu,
  create contract, update contract, vendor contract, contract management, contract tracking,
  contract renewal, vendor agreement, MSA, SLA, service agreement.
---

# Hudu Upsert Contract

Upsert a vendor contract record into Hudu's "Contracts / Licenses" asset layout.

> **Note:** This tenant uses a single "Contracts / Licenses" layout for both licenses
> and vendor contracts. Use `--category` to distinguish (e.g. `Other` for generic contracts).

## CLI Location

```bash
cd /home/tchow/.claude/plugins/marketplaces/tchow-essentials/plugins/hudu-skills
```

## Discover the layout's actual field slugs first

```bash
python3 scripts/hudu_api.py upsert "Contracts / Licenses" --describe
```

This prints every field's CLI slug, label, type, required flag, and allowed values for dropdowns.

## Basic upsert (dry-run first)

```bash
# Preview before writing
python3 scripts/hudu_api.py upsert "Contracts / Licenses" \
  --company "Acme Corp" \
  --name "Cloudflare Enterprise" \
  --category "Other" \
  --dry-run

# Execute when ready
python3 scripts/hudu_api.py upsert "Contracts / Licenses" \
  --company "Acme Corp" \
  --name "Cloudflare Enterprise" \
  --category "Other"
```

## Full example with all common fields

```bash
python3 scripts/hudu_api.py upsert "Contracts / Licenses" \
  --company "Acme Corp" \
  --name "Cloudflare Enterprise" \
  --pricing "4800.00/yr" \
  --portal "https://dash.cloudflare.com" \
  --start-date "2026-01-01" \
  --expiration-renewal-date "2027-01-01" \
  --category "Other" \
  --importance "High" \
  --notes "Enterprise plan — includes DDoS + WAF" \
  --dry-run
```

## Category field — required, allowed values

| Value | Use for |
|---|---|
| `CRM` | CRM platforms |
| `Database` | Database tools |
| `EDI` | EDI platforms |
| `ERP` | ERP / business systems |
| `Finance` | Finance / accounting tools |
| `Marketing` | Marketing platforms |
| `Sales` | Sales tools |
| `Other` | Vendor contracts, service agreements, MSAs |

Importance (optional): `Critical`, `High`, `Medium`, `Low`

## Duplicate detection

Default match key: **license-id** (set in `config/layout-defaults.json`).
For contracts without a license ID, use `--match-on name`:

```bash
python3 scripts/hudu_api.py upsert "Contracts / Licenses" \
  --company "Acme" --name "Cloudflare Enterprise" \
  --match-on "name" --dry-run
```

## Update a specific asset (bypass duplicate search)

```bash
python3 scripts/hudu_api.py upsert "Contracts / Licenses" \
  --company "Acme" --asset-id 5678 \
  --expiration-renewal-date "2028-01-01" \
  --notes "Renewed for 2 years"
```

## Add extra custom fields not covered by named flags

```bash
python3 scripts/hudu_api.py upsert "Contracts / Licenses" \
  --company "Acme" --name "AWS Enterprise" \
  --field new-computer-user-setup="See onboarding doc"
```
