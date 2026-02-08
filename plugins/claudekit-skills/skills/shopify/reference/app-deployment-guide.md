# Shopify App Deployment Guide

Complete guide for deploying Shopify apps, with emphasis on avoiding common pitfalls.

## Table of Contents
1. [Critical: init vs config link](#critical-init-vs-config-link)
2. [Deployment Workflow](#deployment-workflow)
3. [Extension UUIDs](#extension-uuids)
4. [CI/CD Setup](#cicd-setup)
5. [Verifying Deployments](#verifying-deployments)
6. [Multi-App Management](#multi-app-management)
7. [Troubleshooting](#troubleshooting)

## Critical: init vs config link

**The #1 cause of deployment failures is using the wrong command.**

### `shopify app init` - Creates NEW App

```bash
shopify app init
```

**What it does:**
- Creates a brand new app in Partner Dashboard
- Generates new `client_id`
- Generates new extension UUIDs
- Creates new project structure

**When to use:**
- Starting a brand new app from scratch
- Never used before in Partner Dashboard

**DANGER:** Using `init` when you should use `config link` creates a duplicate app with different UUIDs. Your existing store will load from the OLD UUIDs while you deploy to NEW UUIDs.

### `shopify app config link` - Connect to EXISTING App

```bash
shopify app config link
```

**What it does:**
- Connects local project to existing app
- Preserves existing `client_id`
- Preserves existing extension UUIDs
- Updates `shopify.app.toml` with correct config

**When to use:**
- Connecting to an app that already exists
- Setting up a new machine for existing project
- Switching between multiple apps
- **99% of the time this is what you want**

### Decision Flow

```
Is this a brand new app that doesn't exist anywhere?
├── Yes → shopify app init
└── No (app exists in Partner/Custom Dashboard)
    └── shopify app config link
```

### How config link Works

1. Run command:
   ```bash
   shopify app config link
   ```

2. CLI prompts for organization:
   ```
   ? Select your organization:
   > My Partner Organization
     Another Organization
   ```

3. Select existing app:
   ```
   ? Select an app:
   > Dutyman Theme Extension
     GraphQL Admin
     Other App
   ```

4. Config file created/updated:
   ```toml
   # shopify.app.{app-name}.toml
   client_id = "1afd38abb280b3497001ec770595cb11"
   name = "Dutyman Theme Extension"
   ...
   ```

## Deployment Workflow

### Standard Workflow

1. **Verify correct app is linked:**
   ```bash
   shopify app info
   ```
   Confirm `client_id` matches your target app.

2. **Make changes:**
   Edit files in `extensions/` directory.

3. **Deploy:**
   ```bash
   shopify app deploy --force
   ```

4. **Verify deployment:**
   - Check Partner Dashboard → Versions
   - Check CDN returns 200
   - Check live site source

### First-Time Setup (Existing App)

1. **Clone/create project directory:**
   ```bash
   mkdir my-app && cd my-app
   ```

2. **Link to existing app:**
   ```bash
   shopify app config link
   ```

3. **Verify connection:**
   ```bash
   shopify app info
   ```

4. **Create extension (if needed):**
   ```bash
   shopify app generate extension --type theme_app_extension
   ```

5. **Deploy:**
   ```bash
   shopify app deploy --force
   ```

### After Deployment

1. **Install app on store** (if not already):
   - Generate distribution link in Partner Dashboard
   - Visit link and install

2. **Enable in Theme Customizer:**
   - Theme Customizer → App embeds
   - Toggle ON

3. **Clear cache and verify:**
   - Incognito window
   - Check page source for correct UUID

## Extension UUIDs

### Understanding UUIDs

**CRITICAL: Extension UUIDs are app-scoped**

Each app generates unique UUIDs for its extensions:

| App | Extension UUID |
|-----|----------------|
| App A | `019bb7e4-d63a-756f-b971-3720f5e1bcd5` |
| App B | `abcd1234-efgh-5678-ijkl-9012mnop3456` |

**Consequence:** Deploying extension to different app = different UUID

### Why This Matters

Live site loads CSS from specific UUID:
```html
<link href="https://cdn.shopify.com/extensions/019bb7e4.../assets/custom.css">
```

If you deploy to wrong app:
- New version goes to different UUID
- Live site still loads from old UUID
- CSS appears "not updated" or 404s

### Finding the Correct UUID

**From local config:**
```bash
cat extensions/*/shopify.extension.toml
```
Look for `uid = "..."`

**From live site:**
1. View page source
2. Search for `cdn.shopify.com/extensions`
3. Extract UUID from URL

**From Partner Dashboard:**
1. Apps → Your App → Extensions
2. Find extension → UUID shown in details

### UUID Mismatch Resolution

1. **Identify which app owns the live UUID:**
   Compare UUIDs across your apps

2. **Link to correct app:**
   ```bash
   shopify app config link
   # Select app with matching UUID
   ```

3. **Redeploy:**
   ```bash
   shopify app deploy --force
   ```

## CI/CD Setup

### GitHub Actions

```yaml
name: Deploy to Shopify

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install Shopify CLI
        run: npm install -g @shopify/cli@latest

      - name: Deploy
        env:
          SHOPIFY_CLI_PARTNERS_TOKEN: ${{ secrets.SHOPIFY_CLI_PARTNERS_TOKEN }}
        run: shopify app deploy --force
```

### Required Secrets

**SHOPIFY_CLI_PARTNERS_TOKEN:**
1. Partner Dashboard → Settings → Partner API clients
2. Create new client or use existing
3. Copy the API token
4. Add to GitHub repository secrets

### Config File Requirements

Commit `shopify.app.toml` (or named variant) to repo:
```toml
client_id = "your-client-id"
name = "Your App Name"
application_url = "https://example.com"
embedded = false

[webhooks]
api_version = "2025-01"

[access_scopes]
scopes = ""
```

## Verifying Deployments

### Step 1: Check Partner Dashboard

1. Partner Dashboard → Apps → Your App
2. Click **Versions** tab
3. Verify latest version shows:
   - Correct timestamp
   - Extension included
   - Status: Active

### Step 2: Check CDN

```bash
# Get UUID from local config
UUID=$(grep uid extensions/*/shopify.extension.toml | cut -d'"' -f2)

# Get version from dashboard (e.g., 12)
VERSION=12
APP_HANDLE="your-app-handle"

# Check CDN
curl -I "https://cdn.shopify.com/extensions/${UUID}/${APP_HANDLE}-${VERSION}/assets/custom.css"
```

Expected: `HTTP/2 200`

### Step 3: Check Live Site

1. Open live store in incognito
2. View page source (Ctrl+U / Cmd+U)
3. Search for `cdn.shopify.com/extensions`
4. Verify:
   - Correct UUID
   - Correct version number
   - File loads (not 404)

### Verification Checklist

- [ ] `shopify app info` shows correct `client_id`
- [ ] Partner Dashboard shows new version
- [ ] CDN returns 200 for assets
- [ ] Live site source shows correct UUID
- [ ] Live site source shows correct version
- [ ] App embed is enabled in Theme Customizer
- [ ] Browser cache cleared / incognito tested

## Multi-App Management

### Switching Between Apps

```bash
# See current app
shopify app info

# Switch to different app
shopify app config link
# Select target app from list

# Verify switch
shopify app info
```

### Named Config Files

For projects with multiple apps, use named configs:

```bash
# Creates shopify.app.staging.toml
shopify app config link --config=staging

# Creates shopify.app.production.toml
shopify app config link --config=production
```

Deploy to specific config:
```bash
shopify app deploy --config=staging
shopify app deploy --config=production
```

### Project Structure for Multi-App

```
my-project/
├── shopify.app.toml          # Default config
├── shopify.app.staging.toml  # Staging app
├── shopify.app.production.toml # Production app
└── extensions/
    └── my-extension/
        └── ...
```

## Troubleshooting

### Deployment Succeeded but CSS Not on Live Site

**Diagnostic commands:**
```bash
# Check which app is linked
shopify app info

# Check extension UUID
cat extensions/*/shopify.extension.toml

# Check versions
shopify app versions list
```

**Common causes:**

1. **Wrong app linked:**
   - `shopify app info` shows different `client_id` than expected
   - Fix: `shopify app config link` → select correct app

2. **App not installed:**
   - Extension won't appear in Theme Customizer
   - Fix: Generate distribution link, install app

3. **Embed not enabled:**
   - App installed but toggle is OFF
   - Fix: Theme Customizer → App embeds → Enable

4. **Wrong UUID:**
   - Local UUID differs from live site
   - Fix: Link to app that owns live UUID

5. **Browser cache:**
   - Old version cached
   - Fix: Incognito or hard refresh (Ctrl+Shift+R)

### CDN Returns 404

**Causes:**

1. **Version doesn't exist:**
   - Typo in version number
   - Version not deployed yet
   - Fix: Check Partner Dashboard for actual version

2. **Wrong UUID:**
   - UUID doesn't match app
   - Fix: Verify UUID from `shopify app info`

3. **Asset not included:**
   - File not in `assets/` directory
   - Filename typo
   - Fix: Check extension directory structure

4. **Deployment failed:**
   - Check deployment logs
   - Fix: Re-run `shopify app deploy --force`

### Extension Not Appearing in Theme Customizer

**Checklist:**
1. App installed on store? (Check Apps section)
2. Extension deployed? (`shopify app versions list`)
3. Extension type correct? (`type = "theme"`)
4. Store on correct plan? (Some extensions need Plus)

### CI/CD Deployment Fails

**Common errors:**

1. **"No apps found":**
   - Missing or incorrect `client_id` in config
   - Fix: Run `shopify app config link` locally, commit config

2. **"Authentication failed":**
   - Invalid or expired `SHOPIFY_CLI_PARTNERS_TOKEN`
   - Fix: Generate new token in Partner Dashboard

3. **"Permission denied":**
   - Token doesn't have access to app's organization
   - Fix: Ensure token from correct organization

### Accidental Duplicate App

**Symptom:** Used `init` when should have used `config link`

**Fix:**
1. Identify correct app (the one installed on store)
2. Delete duplicate from Partner Dashboard
3. Link to correct app:
   ```bash
   shopify app config link
   ```
4. Redeploy

## Quick Reference

### Essential Commands

```bash
# Check current app
shopify app info

# Link to existing app
shopify app config link

# Deploy
shopify app deploy --force

# List versions
shopify app versions list

# Generate extension
shopify app generate extension --type theme_app_extension
```

### Config File Location

```
./shopify.app.toml          # Default
./shopify.app.{name}.toml   # Named config
```

### Extension Directory

```
./extensions/{extension-name}/
├── shopify.extension.toml
├── assets/
├── blocks/
└── snippets/
```

## Related Documentation

- [Theme App Extensions](theme-app-extensions.md) - Extension details
- [App Types and Distribution](app-types-and-distribution.md) - App differences
- [CLI Commands](cli-commands.md) - Complete CLI reference
