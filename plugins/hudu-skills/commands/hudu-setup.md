---
name: hudu-setup
description: Set up Hudu API configuration and verify connectivity
---

# Hudu Setup

Configure the Hudu API CLI and verify connectivity to your Hudu instance.

## Prerequisites

- Python 3.8+
- `pip install tabulate` (for table output)
- Hudu API key from your Hudu admin panel

## Step 1 — Get Your API Key

1. Log in to your Hudu instance
2. Go to **Admin → API Keys** (or **Settings → API Keys**)
3. Create a new API key (name it "Claude Integration" or similar)
4. Copy the key — it's shown only once

## Step 2 — Configure

```bash
cd plugins/hudu-skills
cp config/hudu_config.template.json config/hudu_config.json
```

Edit `config/hudu_config.json`:

```json
{
  "default_profile": "production",
  "profiles": {
    "production": {
      "name": "production",
      "base_url": "https://yourcompany.huducloud.com",
      "api_key": "YOUR_HUDU_API_KEY"
    }
  }
}
```

**Note:** `base_url` is your Hudu tenant root — do not include `/api/v1` (the client appends it automatically).

## Step 3 — Verify

```bash
python3 scripts/hudu_auth.py --test
```

Expected output:
```
Connection successful
  Version:  X.Y.Z
  Base URL: https://yourcompany.huducloud.com/api/v1
```

## Step 4 — Test a Query

```bash
python3 scripts/hudu_api.py companies list
```

## Multiple Profiles

Add entries under `profiles` in your config and select with `--profile`:

```json
{
  "default_profile": "production",
  "profiles": {
    "production": {
      "name": "production",
      "base_url": "https://company1.huducloud.com",
      "api_key": "KEY_1"
    },
    "staging": {
      "name": "staging",
      "base_url": "https://company2.huducloud.com",
      "api_key": "KEY_2"
    }
  }
}
```

```bash
python3 scripts/hudu_api.py --profile staging companies list
```

## Available Operations

| Resource | Actions |
|---|---|
| companies | list, get, create, update, delete, archive, unarchive |
| articles | list, get, search, create, update, delete, archive |
| assets | list, get, create, update, delete, archive |
| asset-layouts | list, get |
| asset-passwords | list, get, create, delete |
| procedures | list, get, delete |
| websites | list, get, delete |
| networks | list, get |
| users | list, get |
| folders | list, get |
| activity-logs | list |

## Output Formats

```bash
# Table (default)
python3 scripts/hudu_api.py companies list

# JSON (pipeable to jq)
python3 scripts/hudu_api.py companies list --output json | jq '.[0].name'
```

## Security Best Practices

- Keep `config/hudu_config.json` out of source control (it is gitignored)
- Use a dedicated API key for Claude integrations with only the scopes you need
- Rotate the key via Hudu admin if it's ever exposed in chat or logs
- Use read-only scopes for discovery tasks, read-write only when creating/updating

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| Config not found | Missing `hudu_config.json` | Run `cp config/hudu_config.template.json config/hudu_config.json` |
| HTTP 401 | Wrong API key | Check `api_key` in config |
| HTTP 403 | Key lacks permission | Check API key scope in Hudu admin |
| Connection refused / URLError | Wrong `base_url` | Verify subdomain: `https://yourcompany.huducloud.com` |
| Profile not found | Wrong `--profile` | Run without `--profile` to use `default_profile` |
| tabulate not installed | Missing dependency | `pip install tabulate` |
