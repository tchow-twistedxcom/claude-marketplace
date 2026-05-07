---
name: hudu-upsert-contract
description: |
  Upsert a vendor contract asset in Hudu using the "Vendor Contract" asset layout.
  Supports vendor, company, pricing, contract ID, portal, start/renewal dates,
  notes, and category fields. Includes duplicate detection (keyed on vendor by
  default), dry-run preview, and a JSON escape hatch for additional custom fields.
  Triggered by: hudu contract, upsert contract, contract upsert, add contract to hudu,
  create contract, update contract, vendor contract, contract management, contract tracking,
  contract renewal, vendor agreement, MSA, SLA, service agreement.
---

# Hudu Upsert Contract

Upsert a vendor contract record into Hudu's "Vendor Contract" asset layout.

## CLI Location

```bash
cd /home/tchow/.claude/plugins/marketplaces/tchow-essentials/plugins/hudu-skills
```

## Discover your layout's actual field slugs first

Your "Vendor Contract" layout may have different custom-field slugs than the examples below. Run:

```bash
python3 scripts/hudu_api.py upsert "Vendor Contract" --describe
```

This prints every field's CLI slug, label, and type.

## Basic upsert (dry-run first)

```bash
# Preview before writing
python3 scripts/hudu_api.py upsert "Vendor Contract" \
  --company "Acme Corp" \
  --vendor "Cloudflare" \
  --dry-run

# Execute when ready
python3 scripts/hudu_api.py upsert "Vendor Contract" \
  --company "Acme Corp" \
  --vendor "Cloudflare"
```

## Full example with all common fields

```bash
python3 scripts/hudu_api.py upsert "Vendor Contract" \
  --company "Acme Corp" \
  --vendor "Cloudflare" \
  --pricing 4800.00 \
  --portal "https://dash.cloudflare.com" \
  --start-date "2026-01-01" \
  --renewal-date "2027-01-01" \
  --category "Security" \
  --notes "Enterprise plan — includes DDoS + WAF" \
  --dry-run
```

## Duplicate detection

Default match key: **vendor** (set in `config/layout-defaults.json`).
One vendor contract per company per vendor — second upsert updates the existing record.

Override with `--match-on`:
```bash
python3 scripts/hudu_api.py upsert "Vendor Contract" \
  --company "Acme" --vendor "AWS" \
  --match-on "vendor,start-date" --dry-run
```

## Update a specific asset (bypass duplicate search)

```bash
python3 scripts/hudu_api.py upsert "Vendor Contract" \
  --company "Acme" --asset-id 5678 \
  --renewal-date "2028-01-01" \
  --notes "Renewed for 2 years"
```

## Add extra custom fields not covered by named flags

```bash
python3 scripts/hudu_api.py upsert "Vendor Contract" \
  --company "Acme" --vendor "AWS" \
  --field contract-number="AWS-2026-ENT" \
  --field account-manager="Jane Doe"
```
