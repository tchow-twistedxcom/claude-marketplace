---
name: hudu-manage
description: Manage Hudu IT documentation — companies, assets, articles, passwords, procedures
---

# Hudu Manage

Interact with your Hudu IT documentation platform via the Python CLI.

## CLI Location

```bash
cd plugins/hudu-skills
```

## Common Operations

### List all companies
```bash
python3 scripts/hudu_api.py companies list
python3 scripts/hudu_api.py companies list --search "Acme"
```

### Look up a company's assets
```bash
python3 scripts/hudu_api.py assets list --company-id <COMPANY_ID>
python3 scripts/hudu_api.py assets list --company-id <COMPANY_ID> --layout-id <LAYOUT_ID>
```

### Search knowledge base articles
```bash
python3 scripts/hudu_api.py articles search --query "firewall"
python3 scripts/hudu_api.py articles list --company-id <COMPANY_ID>
```

### Retrieve asset passwords (credentials)
```bash
python3 scripts/hudu_api.py asset-passwords list --company-id <COMPANY_ID>
python3 scripts/hudu_api.py asset-passwords get --id <PASSWORD_ID>
```

### View available asset layouts (templates)
```bash
python3 scripts/hudu_api.py asset-layouts list
```

### Review recent activity
```bash
python3 scripts/hudu_api.py activity-logs list
python3 scripts/hudu_api.py activity-logs list --start-date 2026-04-01
```

### Create a KB article
```bash
python3 scripts/hudu_api.py articles create \
  --name "Firewall Config" \
  --content "<p>Steps to configure...</p>" \
  --company-id <COMPANY_ID>
```

### Get JSON output for scripting
```bash
python3 scripts/hudu_api.py companies list --output json | jq '.[] | {id, name}'
python3 scripts/hudu_api.py assets list --company-id 42 --output json | jq 'length'
```

## Full Resource Reference

See `skills/hudu-api/SKILL.md` or run:

```bash
python3 scripts/hudu_api.py --help
python3 scripts/hudu_api.py companies --help
python3 scripts/hudu_api.py articles --help
```
