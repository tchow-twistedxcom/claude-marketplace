# n8n Integration Authentication Guide

## Overview

The n8n integration plugin supports **multiple n8n accounts** across different servers. You can configure local instances, cloud instances, and production/staging environments, then switch between them using the `--account` flag.

## Quick Start

```bash
# Add your first account
/n8n:setup --add local --url http://localhost:5679/api/v1 --key YOUR_API_KEY

# Test connection
/n8n:status

# Switch accounts
/n8n:status --account production
```

## Multi-Account Configuration

### Configuration File

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
    description: "Production environment"

  staging:
    name: "Staging n8n"
    url: "https://n8n-staging.example.com/api/v1"
    api_key: "staging-api-key"
    description: "Staging environment"
```

### Account Management Commands

```bash
# List all configured accounts
/n8n:setup --list-accounts

# Add a new account
/n8n:setup --add <account-id> --url <api-url> --key <api-key>

# Add with description
/n8n:setup --add twistedx --url https://n8n.twistedx.com/api/v1 --key xxx --name "TwistedX n8n"

# Remove an account
/n8n:setup --remove <account-id>

# Set default account
/n8n:setup --set-default <account-id>

# Test specific account
/n8n:setup --test --account production
```

### Using Accounts with Commands

All n8n commands support the `--account` flag:

```bash
# Status of specific account
/n8n:status --account production

# List workflows on staging
/n8n:list --account staging

# Run workflow on production
/n8n:run my-workflow --account production

# Validate across all accounts
/n8n:validate workflow-id --account local
```

### Default Account Behavior

- If `--account` is not specified, the `default_account` from config is used
- If no config exists, falls back to environment variables (`N8N_API_URL`, `N8N_API_KEY`)
- Environment variables always override config when set

## Prerequisites

1. **n8n Instance**: Running n8n installation (self-hosted or cloud)
2. **API Access**: n8n API enabled with a valid API key
3. **Config Directory**: `~/.config/n8n-integration/` (created automatically)

## Generating API Keys

### For Each n8n Instance:

1. Open your n8n instance
2. Navigate to **Settings** (gear icon)
3. Select **API** from the left menu
4. Click **Create API Key**
5. Give it a descriptive name (e.g., "Claude Code Integration")
6. Copy the generated API key

## Configuration Methods

### Method 1: Interactive Setup (Recommended)

```bash
/n8n:setup --add production
# Prompts for URL and API key interactively
```

### Method 2: Command Line

```bash
/n8n:setup --add production \
  --url "https://n8n.example.com/api/v1" \
  --key "your-api-key" \
  --name "Production n8n"
```

### Method 3: Direct File Edit

Edit `~/.config/n8n-integration/accounts.yaml`:

```yaml
accounts:
  myserver:
    name: "My Server"
    url: "https://n8n.myserver.com/api/v1"
    api_key: "api-key-here"
    description: "My custom n8n server"
```

### Method 4: Environment Variables (Legacy)

For single-instance usage or CI/CD:

```bash
export N8N_API_URL="http://localhost:5678/api/v1"
export N8N_API_KEY="your-api-key"
```

## Account Resolution Priority

1. `--account` flag (explicit selection)
2. Environment variables (`N8N_API_URL` + `N8N_API_KEY`)
3. `default_account` from config file
4. First account in config file

## n8n Cloud vs Self-Hosted

### Self-Hosted Examples

```yaml
accounts:
  local:
    url: "http://localhost:5678/api/v1"

  docker:
    url: "http://localhost:5679/api/v1"

  reverse-proxy:
    url: "https://n8n.yourdomain.com/api/v1"
```

### n8n Cloud

```yaml
accounts:
  cloud:
    name: "n8n Cloud"
    url: "https://your-instance.app.n8n.cloud/api/v1"
    api_key: "cloud-api-key"
```

## Troubleshooting

### Connection Refused

```
Error: ECONNREFUSED
```

**Solutions:**
- Verify n8n is running: `docker ps | grep n8n`
- Check the correct port
- Ensure firewall allows connection
- Try: `/n8n:setup --test --account <account-id>`

### 401 Unauthorized

```
Error: 401 Unauthorized
```

**Solutions:**
- Verify API key is correct
- Check API key hasn't expired
- Regenerate API key in n8n settings
- Update config: `/n8n:setup --add <account-id> --key <new-key>`

### Account Not Found

```
Error: Account 'xyz' not found in configuration
```

**Solutions:**
- List accounts: `/n8n:setup --list-accounts`
- Add missing account: `/n8n:setup --add xyz --url ... --key ...`

### Timeout Errors

```
Error: ETIMEDOUT
```

**Solutions:**
- Check network connectivity
- Verify URL is correct
- Try accessing URL in browser first

## Security Best Practices

1. **File Permissions**: Config file is created with `600` permissions
2. **API Key Rotation**: Rotate keys periodically per instance
3. **Least Privilege**: Create API keys with minimal permissions
4. **Never Commit**: Add config path to `.gitignore`
5. **HTTPS**: Use HTTPS for production instances
6. **Separate Keys**: Use different API keys per environment

## API Limitations

| Operation | Support |
|-----------|---------|
| Workflow CRUD | Full |
| Execution Monitoring | Full |
| Workflow Activation | Limited (set during create/update, no toggle endpoint) |
| Credential Management | Read-only (list only, cannot create/modify) |
| Execution Control | Cannot stop/retry |
| Direct Execution | Not supported (webhook trigger only) |

**Note**: Workflows must be manually activated in the n8n UI. The API can set the `active` field during workflow create/update, but there's no dedicated activation endpoint.

See `docs/API_LIMITATIONS.md` for detailed workarounds.

## Related Commands

- `/n8n:setup` - Account management and setup
- `/n8n:status` - Check connection and instance health
- `/n8n:list` - List workflows (supports --account)
- `/n8n:help` - Full command reference
