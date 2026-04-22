---
name: hudu-api
description: |
  Execute Hudu documentation platform operations via Python CLI. Use when managing
  MSP-style client documentation, asset inventories, KB articles, credential/password
  records, networks, procedures, and activity logs across one or more Hudu tenants.
  Supports full CRUD on companies, articles, assets, asset layouts, asset passwords,
  procedures, websites, and read access to users, networks, folders, activity logs.
  Triggered by: Hudu, documentation, knowledge base, IT glue, MSP docs, client assets,
  password vault, runbooks, procedures, company records, IT documentation platform.
---

# Hudu API Skill

Execute operations against the Hudu IT documentation platform via the Python CLI.

## When to Use

- Looking up client companies, assets, or KB articles in Hudu
- Retrieving passwords/credentials stored as Hudu asset passwords
- Creating or updating documentation articles, procedures, or runbooks
- Auditing Hudu activity logs or listing users
- Onboarding a new client (create company + assets)
- Bulk operations across multiple companies

## CLI Location

```bash
cd /home/tchow/.claude/plugins/marketplaces/tchow-essentials/plugins/hudu-skills
```

## Quick Reference

### Companies
```bash
python3 scripts/hudu_api.py companies list
python3 scripts/hudu_api.py companies list --search "Acme"
python3 scripts/hudu_api.py companies get --id 42
python3 scripts/hudu_api.py companies create --name "Acme Corp" --website "https://acme.com"
python3 scripts/hudu_api.py companies update --id 42 --phone "555-1234"
python3 scripts/hudu_api.py companies delete --id 42
python3 scripts/hudu_api.py companies archive --id 42
```

### Articles (Knowledge Base)
```bash
python3 scripts/hudu_api.py articles list --company-id 42
python3 scripts/hudu_api.py articles search --query "firewall"
python3 scripts/hudu_api.py articles get --id 100
python3 scripts/hudu_api.py articles create --name "VPN Setup" --content "<p>Steps...</p>" --company-id 42
python3 scripts/hudu_api.py articles update --id 100 --name "VPN Setup v2"
python3 scripts/hudu_api.py articles delete --id 100
```

### Assets
```bash
python3 scripts/hudu_api.py assets list --company-id 42
python3 scripts/hudu_api.py assets list --company-id 42 --layout-id 7
python3 scripts/hudu_api.py assets get --id 200
python3 scripts/hudu_api.py assets create --company-id 42 --name "Core Switch" --layout-id 7
python3 scripts/hudu_api.py assets archive --id 200
```

### Asset Layouts
```bash
python3 scripts/hudu_api.py asset-layouts list
python3 scripts/hudu_api.py asset-layouts get --id 7
```

### Asset Passwords
```bash
python3 scripts/hudu_api.py asset-passwords list --company-id 42
python3 scripts/hudu_api.py asset-passwords get --id 300
python3 scripts/hudu_api.py asset-passwords create --name "Router Admin" --company-id 42 \
  --username admin --password "secret" --url "https://192.168.1.1"
python3 scripts/hudu_api.py asset-passwords delete --id 300
```

### Procedures
```bash
python3 scripts/hudu_api.py procedures list --company-id 42
python3 scripts/hudu_api.py procedures get --id 50
```

### Websites
```bash
python3 scripts/hudu_api.py websites list --company-id 42
python3 scripts/hudu_api.py websites get --id 75
```

### Networks / Users / Folders
```bash
python3 scripts/hudu_api.py networks list --company-id 42
python3 scripts/hudu_api.py users list
python3 scripts/hudu_api.py folders list --company-id 42
```

### Activity Logs
```bash
python3 scripts/hudu_api.py activity-logs list
python3 scripts/hudu_api.py activity-logs list --resource-type Company --start-date 2026-01-01
```

## Output Formats

```bash
python3 scripts/hudu_api.py companies list --output json | jq '.[0]'
```

## Profile Selection

```bash
python3 scripts/hudu_api.py --profile production companies list
```

## Authentication

API key is stored in `config/hudu_config.json` (gitignored). The `x-api-key` header is sent on every request. Run `hudu-setup` or `python3 scripts/hudu_auth.py --test` to verify connectivity.
