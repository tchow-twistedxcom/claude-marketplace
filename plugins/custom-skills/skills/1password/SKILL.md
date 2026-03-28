---
name: 1password
description: "Manage 1Password credentials via CLI. Use when storing, retrieving, or updating secrets in 1Password vaults. Covers op CLI auth, item CRUD, field access, and integration patterns."
---

# 1Password CLI Integration

The `op` CLI is pre-authenticated in this environment via a service account token. No login or manual auth is required.

## Authentication

The CLI authenticates via the `OP_SERVICE_ACCOUNT_TOKEN` environment variable. It is persisted in `~/.profile` and `~/.bashrc` on this server so it is available in all Claude Code sessions automatically.

**You never need to `op signin` or manage sessions manually.**

### Where the token is stored (twistedx-docker / local dev)

| Location | Purpose |
|----------|---------|
| `~/.profile` | Login shells, Claude Code sessions |
| `~/.bashrc` | Interactive bash sessions |

> For system-wide access (all users), write to `/etc/profile.d/1password.sh` — requires `sudo`.

### Setting up on a new machine or for a new user

```bash
# 1. Get the service account token from 1Password (requires existing access)
#    Vault: "Twisted X AI Agent" → item: "1Password Service Account" or ask team lead

# 2. Add to shell profile (choose one)
echo 'export OP_SERVICE_ACCOUNT_TOKEN="ops_..."' >> ~/.bashrc
echo 'export OP_SERVICE_ACCOUNT_TOKEN="ops_..."' >> ~/.profile

# 3. Apply immediately
export OP_SERVICE_ACCOUNT_TOKEN="ops_..."

# 4. Verify
op vault list
```

### Verify auth works

```bash
op account list   # should return silently (no error) for service accounts
op vault list     # should list "Twisted X AI Agent"
```

> **Note:** `op account list` returns no output for service accounts — that is normal. Use `op vault list` to confirm access.

## Vault

**Primary vault**: `Twisted X AI Agent`

All project credentials, tokens, and secrets are stored here.

```bash
# List all items in the vault
op item list --vault "Twisted X AI Agent"
```

## Retrieving Credentials

### Get all fields from an item

```bash
op item get "Item Name" --vault "Twisted X AI Agent"
```

### Get specific fields (fastest — avoids parsing full output)

```bash
op item get "Item Name" --vault "Twisted X AI Agent" \
  --fields field1,field2 --reveal
```

> `--reveal` is required for secret/password fields, otherwise they are masked.

### Get a single field value (script-friendly)

```bash
SECRET=$(op item get "Item Name" --vault "Twisted X AI Agent" \
  --fields password --reveal)
```

### Get by item ID (if name is ambiguous)

```bash
op item get <item-uuid> --vault "Twisted X AI Agent" --reveal
```

## Creating Items

### Generic credential item

```bash
op item create \
  --vault "Twisted X AI Agent" \
  --category "API Credential" \
  --title "Service Name" \
  "username[text]=myuser" \
  "password[password]=mysecret" \
  "api_key[password]=key123" \
  "notes[text]=Created for Project X"
```

### Login item

```bash
op item create \
  --vault "Twisted X AI Agent" \
  --category "Login" \
  --title "Service Login" \
  --url "https://service.example.com" \
  "username[text]=admin@example.com" \
  "password[password]=securepass"
```

### Secure Note

```bash
op item create \
  --vault "Twisted X AI Agent" \
  --category "Secure Note" \
  --title "Project Notes" \
  "notesPlain[text]=Important info here"
```

## Updating Items

### Update a single field

```bash
op item edit "Item Name" --vault "Twisted X AI Agent" \
  "field_name=new_value"
```

### Update multiple fields

```bash
op item edit "Amazon SP-API" --vault "Twisted X AI Agent" \
  "vendor_refresh_token=Atzr|..." \
  "notes=Updated 2025-01-15"
```

### Add a new field to existing item

```bash
op item edit "Item Name" --vault "Twisted X AI Agent" \
  "new_field[password]=new_secret"
```

## Caching (Recommended — Avoids Rate Limiting)

The `op` CLI is rate-limited for service account tokens. Use `op_cache.py` (in this skill directory) to cache secret values locally and avoid repeated API calls.

**Security:** Cache is encrypted at rest with Fernet (AES-128-CBC) + PBKDF2-derived key from `OP_SERVICE_ACCOUNT_TOKEN`. File permissions: `0600`. Same trust boundary as calling `op` directly.

### Import pattern

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.claude/skills/1password"))
from op_cache import get_secret, get_secrets, clear_cache
```

### Usage

```python
# Single field (returns string)
password = get_secret("Snowflake - Admin (tchowtwistedxcom)", "password")

# Multiple fields (returns dict)
creds = get_secrets("Amazon SP-API", ["lwa_client_id", "lwa_client_secret",
                                       "seller_refresh_token", "vendor_refresh_token"])
lwa_id = creds["lwa_client_id"]

# Custom TTL (seconds, default 900 = 15 min)
password = get_secret("Airbyte - Snowflake", "password", ttl=1800)

# After rotating a secret — clear cache so next call fetches fresh value
clear_cache("Amazon SP-API")  # specific item
clear_cache()                  # everything
```

### How it works
1. Check in-memory cache (same process) — fastest
2. Check encrypted disk cache at `~/.cache/op-cache/vault.enc`
3. If stale or missing — call `op item get` and cache result

### CLI testing

```bash
python3 ~/.claude/skills/1password/op_cache.py "Airbyte - Snowflake" "password"
python3 ~/.claude/skills/1password/op_cache.py --clear
python3 ~/.claude/skills/1password/op_cache.py --clear "Amazon SP-API"
```

---

## Common Patterns in This Environment

### Retrieve AWS/API credentials for use in scripts

```bash
API_KEY=$(op item get "Service API" --vault "Twisted X AI Agent" \
  --fields api_key --reveal)
curl -H "Authorization: Bearer $API_KEY" https://api.example.com/
```

### Store tokens after rotation (end-to-end pattern)

```bash
# 1. Generate new token externally (e.g., from Vendor Central console)
NEW_TOKEN="Atzr|..."

# 2. Test it works
python3 test_script.py --token "$NEW_TOKEN"

# 3. Save to 1Password
op item edit "Amazon SP-API" --vault "Twisted X AI Agent" \
  "vendor_refresh_token=$NEW_TOKEN"

# 4. Update the consuming service (e.g., Airbyte via API, config file, etc.)
```

### Check if an item exists before creating

```bash
if op item get "Item Name" --vault "Twisted X AI Agent" &>/dev/null; then
  echo "Item exists — updating"
  op item edit "Item Name" --vault "Twisted X AI Agent" "field=value"
else
  echo "Creating new item"
  op item create --vault "Twisted X AI Agent" --title "Item Name" ...
fi
```

## Known Items in "Twisted X AI Agent" Vault

| Item Name | Purpose | Key Fields |
|-----------|---------|------------|
| Amazon SP-API | LWA credentials for SP-API | `lwa_client_id`, `lwa_client_secret`, `seller_refresh_token`, `vendor_refresh_token` |
| Airbyte - twistedx-docker | Airbyte admin access | `url`, `username`, `password`, `client_id`, `client_secret` |
| Airbyte Application Client | OAuth client for API auth | `client_id`, `client_secret` |
| Airbyte - Snowflake | Snowflake destination password for Airbyte sync | `password` |
| Snowflake - Admin (tchowtwistedxcom) | Snowflake admin/ACCOUNTADMIN password | `password` |

## Field Types Reference

| Syntax | Type |
|--------|------|
| `field[text]=value` | Plaintext string |
| `field[password]=value` | Secret (masked by default) |
| `field[url]=https://...` | URL |
| `field[email]=addr` | Email |
| `field[phone]=+1...` | Phone number |
| `notes[text]=...` | Notes field |

## Secrets Safety Rules

When retrieving secrets to pass into APIs or scripts:

1. **Never echo secrets to stdout** — store in a variable, not `echo $SECRET`
2. **Use subprocess in Python** to call `op` so secrets stay in memory, not shell history
3. **Don't PATCH APIs with masked values** — if an API GET returns `**` for a secret field, do NOT send that back in a PATCH. Always fetch fresh from 1Password and send the real value.

```python
# Safe pattern: fetch creds via subprocess, pass directly to API
import subprocess, json

result = subprocess.run(
    ["op", "item", "get", "Amazon SP-API", "--vault", "Twisted X AI Agent",
     "--fields", "lwa_client_secret,refresh_token", "--reveal"],
    capture_output=True, text=True
)
lwa_secret, refresh_token = result.stdout.strip().split(',')
# Use directly — never print or log these values
```

## Troubleshooting

```bash
# Check if op is authenticated (service accounts return no output — that is normal)
op vault list     # Use this instead to confirm access

# Search for an item by partial name
op item list --vault "Twisted X AI Agent" | grep -i "partial"

# Get raw JSON output for inspection
op item get "Item Name" --vault "Twisted X AI Agent" --format json

# If OP_SERVICE_ACCOUNT_TOKEN is not set
echo $OP_SERVICE_ACCOUNT_TOKEN   # should print the token
source ~/.profile                 # reload if missing from current session
```

## Integration with Other Skills

- **airbyte-integration**: Uses 1Password to store Airbyte credentials and retrieve them when rotating Amazon SP-API tokens
- **amazon-spapi**: Stores LWA client credentials and refresh tokens; retrieve with `op item get "Amazon SP-API"`
