---
name: n8n-setup
description: "Configure n8n accounts, manage connections, and verify API access"
---

# /n8n:setup - n8n Account Management

Configure and manage multiple n8n instance connections. Supports adding, removing, testing, and switching between accounts.

## Usage

```bash
/n8n:setup [options]
```

## Account Management

| Command | Description |
|---------|-------------|
| `--list-accounts` | List all configured accounts |
| `--add <id>` | Add a new account |
| `--remove <id>` | Remove an account |
| `--set-default <id>` | Set default account |
| `--test` | Test connection |
| `--diagnose` | Run detailed diagnostics |

## Adding Accounts

### Interactive (Recommended)

```bash
/n8n:setup --add production

# Claude will prompt for:
# - API URL
# - API Key
# - Display name (optional)
# - Description (optional)
```

### With Parameters

```bash
/n8n:setup --add twistedx \
  --url "https://n8n.twistedx.com/api/v1" \
  --key "your-api-key" \
  --name "TwistedX n8n"
```

### Parameters for --add

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--url` | Yes | n8n API URL (e.g., http://localhost:5679/api/v1) |
| `--key` | Yes | n8n API key |
| `--name` | No | Display name for the account |
| `--description` | No | Description of the instance |

## Listing Accounts

```bash
/n8n:setup --list-accounts
```

Output:
```
n8n Configured Accounts
================================
* local (default)
    Name: Local n8n
    URL: http://localhost:5679/api/v1
    Description: Local Docker instance

  twistedx
    Name: TwistedX n8n
    URL: https://n8n.twistedx.com/api/v1
    Description: TwistedX production

  staging
    Name: Staging n8n
    URL: https://n8n-staging.example.com/api/v1
```

## Testing Connections

### Test Default Account

```bash
/n8n:setup --test
```

### Test Specific Account

```bash
/n8n:setup --test --account production
```

### Test All Accounts

```bash
/n8n:setup --test-all
```

Output:
```
Testing all n8n accounts...

✅ local: Connected (v1.106.3)
✅ twistedx: Connected (v1.98.0)
❌ staging: Connection refused
```

## Setting Default Account

```bash
/n8n:setup --set-default twistedx
```

Output:
```
Default account changed: local → twistedx
```

## Removing Accounts

```bash
/n8n:setup --remove staging
```

Output:
```
Account 'staging' removed from configuration.
```

## Diagnostics

### Basic Diagnostics

```bash
/n8n:setup --diagnose
```

### Diagnose Specific Account

```bash
/n8n:setup --diagnose --account production
```

Output:
```
n8n Diagnostic Report: production
================================
Configuration:
  Config File: ~/.config/n8n-integration/accounts.yaml
  Account ID: production
  URL: https://n8n.example.com/api/v1
  API Key: ****...3f7a (configured)

Connection Test:
  Status: Connected
  Latency: 45ms
  n8n Version: 1.106.3

Capabilities:
  Workflows API: Available
  Executions API: Available
  Activation API: Available

Environment:
  N8N_API_URL: (not set - using config)
  N8N_API_KEY: (not set - using config)
```

## Configuration File

Accounts are stored in `~/.config/n8n-integration/accounts.yaml`:

```yaml
default_account: local

accounts:
  local:
    name: "Local n8n"
    url: "http://localhost:5679/api/v1"
    api_key: "your-api-key"
    description: "Local Docker instance"

  production:
    name: "Production n8n"
    url: "https://n8n.example.com/api/v1"
    api_key: "prod-api-key"
```

## Workflow

When Claude executes `/n8n:setup`:

### For --list-accounts
1. Read `~/.config/n8n-integration/accounts.yaml`
2. Display all accounts with their details (mask API keys)
3. Indicate which account is default

### For --add <id>
1. Prompt for missing parameters (url, key) if not provided
2. Validate URL format
3. Test connection to verify credentials
4. Add to accounts.yaml
5. Confirm addition

### For --remove <id>
1. Verify account exists
2. Confirm if removing default account
3. Remove from accounts.yaml
4. Update default if needed

### For --set-default <id>
1. Verify account exists
2. Update default_account in config
3. Confirm change

### For --test
1. Load account configuration
2. Call n8n health check API
3. Report connection status and version

### For --diagnose
1. Load account configuration
2. Check environment variables
3. Test API connectivity
4. Report detailed diagnostics

## CLI Tools Used

| Script | Purpose |
|--------|---------|
| `scripts/n8n_config.py` | Account management (add, remove, list, set-default) |
| `scripts/n8n_auth.py` | Connection testing and diagnostics |
| `scripts/n8n_api.py` | API operations (health check) |

### Example CLI Commands

```bash
# List accounts
python3 scripts/n8n_config.py --list-accounts

# Add account
python3 scripts/n8n_config.py --add production --url "https://n8n.example.com/api/v1" --key "YOUR_KEY"

# Test connection
python3 scripts/n8n_auth.py --test --account local

# Set default
python3 scripts/n8n_config.py --set-default production
```

## Examples

### First-Time Setup

```bash
/n8n:setup --add local --url http://localhost:5679/api/v1 --key YOUR_KEY

# Output:
Testing connection to http://localhost:5679/api/v1...
✅ Connected to n8n v1.106.3

Account 'local' added successfully.
Set as default account.
```

### Add Production Environment

```bash
/n8n:setup --add production \
  --url "https://n8n.company.com/api/v1" \
  --key "prod-key" \
  --name "Production n8n" \
  --description "Production workflow automation"
```

### Switch Default

```bash
/n8n:setup --set-default production
/n8n:status  # Now shows production status
```

### Quick Health Check

```bash
/n8n:setup --test --account local
```

## Troubleshooting

### "Config file not found"

Run any add command to create it:
```bash
/n8n:setup --add local --url http://localhost:5679/api/v1 --key YOUR_KEY
```

### "Account already exists"

Use --remove first, or the account will be updated:
```bash
/n8n:setup --remove old-account
/n8n:setup --add old-account --url ... --key ...
```

### "Cannot remove default account"

Set a different default first:
```bash
/n8n:setup --set-default other-account
/n8n:setup --remove old-default
```

## Related Commands

- `/n8n:status` - Check current account health
- `/n8n:list --account <id>` - List workflows for specific account
- `/n8n:help` - Full command reference

## See Also

- [AUTHENTICATION.md](../AUTHENTICATION.md) - Full authentication guide
- [API_LIMITATIONS.md](../../docs/API_LIMITATIONS.md) - API constraints
