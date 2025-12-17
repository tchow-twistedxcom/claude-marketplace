# Atlassian API Skill

A Python CLI for Atlassian Confluence and Jira operations with OAuth 2.0 authentication.

## Features

- **OAuth 2.0 with Auto-Refresh**: Automatic token management
- **Multi-Site Support**: Switch between Atlassian instances
- **Efficient Output**: ~97% token reduction vs MCP
- **Full API Coverage**: Confluence pages, Jira issues, transitions
- **Timeout Handling**: No more hanging requests

## Prerequisites

- Python 3.8+
- Atlassian Cloud account with admin access
- OAuth 2.0 app created in Atlassian Developer Console

## Installation

1. **Skill directory already created** at `~/.claude/skills/atlassian-api/`

2. **Create OAuth 2.0 App** (see below)

3. **Configure credentials**:
   ```bash
   cp config/atlassian_config.template.json config/atlassian_config.json
   # Edit with your credentials
   ```

4. **Test authentication**:
   ```bash
   python3 scripts/auth.py
   ```

## OAuth 2.0 Setup

### Step 1: Create OAuth App

1. Go to https://developer.atlassian.com/console/myapps/
2. Click **"Create"** → **"OAuth 2.0 integration"**
3. Name: `Claude Code Integration`
4. Accept terms and create

### Step 2: Configure Permissions

Navigate to **"Permissions"** tab and add these **v2 granular scopes**:

**Confluence API (v2 Granular Scopes):**
- `read:content:confluence` - Read content
- `write:content:confluence` - Write content
- `read:content-details:confluence` - Read content details
- `read:page:confluence` - Read pages
- `write:page:confluence` - Write pages
- `read:space:confluence` - Read spaces

**Jira API (Optional - only if using Jira features):**
- `read:jira-work` - Read issues
- `write:jira-work` - Create and update issues
- `read:jira-user` - Read user info (for assignee lookup)

**⚠️ REQUIRED for Refresh Tokens:**
- `offline_access` - **MUST be included** to get refresh tokens

Click **"Save"** after adding each scope.

> **Note:** This skill uses v2 granular OAuth scopes. Make sure the scopes in your
> Atlassian Developer Console app match exactly what's listed above.

### Step 3: Configure Authorization

1. Go to **"Authorization"** tab
2. Add callback URL: `http://localhost:8080/callback`
3. Click **"Save changes"**

### Step 4: Get Client Credentials

1. Go to **"Settings"** tab
2. Copy:
   - **Client ID**
   - **Client Secret** (click to reveal)

### Step 5: Get Refresh Token

Run the authorization flow to get your refresh token:

```bash
# Recommended: Use the built-in auth helper
python3 scripts/get_refresh_token.py
```

The script will:
1. Ask for your Client ID and Client Secret
2. Ask if you need Jira scopes (optional)
3. Show the exact scopes that will be requested
4. Open a browser for authorization
5. Display your refresh token

> **Important:** The scopes requested MUST match what's configured in your
> Atlassian Developer Console app. If they don't match, authorization will fail.

Exchange authorization code for tokens:
```bash
curl -X POST https://auth.atlassian.com/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "authorization_code",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "code": "AUTHORIZATION_CODE",
    "redirect_uri": "http://localhost:8080/callback"
  }'
```

Response includes `refresh_token` - save this to your config.

### Step 6: Configure the Skill

Edit `config/atlassian_config.json`:

```json
{
  "sites": {
    "twistedx": {
      "name": "Twisted X",
      "cloud_id": "72e4ede1-1aba-4eb0-b8b3-fc8a0515f327",
      "domain": "twistedx.atlassian.net"
    }
  },
  "oauth": {
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "refresh_token": "YOUR_REFRESH_TOKEN"
  },
  "defaults": {
    "site": "twistedx"
  }
}
```

### Finding Your Cloud ID

The cloud ID is needed for API calls. You can find it:

1. **From existing MCP calls** - check the `cloudId` parameter
2. **From API**: Use the accessible-resources endpoint after getting a token:
   ```bash
   curl -H "Authorization: Bearer ACCESS_TOKEN" \
     https://api.atlassian.com/oauth/token/accessible-resources
   ```
3. **Known values**:
   - Twisted X: `72e4ede1-1aba-4eb0-b8b3-fc8a0515f327`

## Usage

```bash
cd ~/.claude/skills/atlassian-api

# Test authentication
python3 scripts/auth.py

# Search Confluence
python3 scripts/atlassian_api.py --confluence search "PRI Container"

# Get page content
python3 scripts/atlassian_api.py --confluence get-page 3174662145 --format markdown

# Search Jira
python3 scripts/atlassian_api.py --jira search "project = TWXDEV" --limit 10

# Create issue
python3 scripts/atlassian_api.py --jira create-issue \
  --project TWXDEV \
  --type Task \
  --summary "New task from CLI"
```

See [SKILL.md](SKILL.md) for complete documentation.

## Troubleshooting

### "Config file not found"
```bash
cp config/atlassian_config.template.json config/atlassian_config.json
# Then edit with your credentials
```

### "Token refresh failed: invalid_grant"
Your refresh token has expired or been revoked. Re-run the OAuth flow:
```bash
python3 scripts/get_refresh_token.py
```

### "HTTP 403: Forbidden"
Missing required OAuth scopes. Verify your app has these v2 scopes configured:
- Confluence: `read:content:confluence`, `write:content:confluence`, `read:page:confluence`, etc.
- The scopes in your app MUST match what the script requests.

Check your app permissions at: https://developer.atlassian.com/console/myapps/

### "access_denied" during OAuth flow
The scopes requested don't match what's configured in your Atlassian app.
Make sure your app has all the v2 granular scopes listed in Step 2.

### "Unknown site: xyz"
Site not configured. Add it to `config/atlassian_config.json` under `sites`.

### Timeout errors
Increase timeout: `--timeout 60`

### No refresh token received
Make sure `offline_access` scope is included in your Atlassian app permissions.
This scope is REQUIRED to get refresh tokens.

## Security Notes

- **Never commit** `config/atlassian_config.json` to version control
- The config file is in `.gitignore` by default
- Refresh tokens auto-rotate - the skill updates the config file automatically
- Client secrets should be treated as passwords

## Development

```bash
# Run auth tests
python3 scripts/auth.py

# Run formatter tests
python3 scripts/formatters.py

# Verbose mode for debugging
python3 scripts/atlassian_api.py --verbose --confluence search "test"
```
