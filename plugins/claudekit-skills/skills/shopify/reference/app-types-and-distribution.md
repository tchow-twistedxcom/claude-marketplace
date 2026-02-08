# Shopify App Types and Distribution

Understanding the critical differences between app types and how to distribute them.

## Table of Contents
1. [App Types Overview](#app-types-overview)
2. [Custom Apps (Merchant Apps)](#custom-apps-merchant-apps)
3. [Partner Apps](#partner-apps)
4. [Critical Differences](#critical-differences)
5. [Distribution Methods](#distribution-methods)
6. [Installation Flow](#installation-flow)
7. [When to Use Which](#when-to-use-which)
8. [Common Mistakes](#common-mistakes)

## App Types Overview

Shopify has **two fundamentally different app types** with different:
- Creation methods
- Management dashboards
- CI/CD authentication
- Distribution capabilities
- Extension UUID behavior

**Mixing these up causes deployment failures and CSS not loading.**

## Custom Apps (Merchant Apps)

### Characteristics

| Aspect | Details |
|--------|---------|
| **Created in** | Store Admin → Settings → Apps → Develop apps |
| **Managed at** | dev.shopify.com (store's developer dashboard) |
| **Ownership** | Merchant's organization |
| **Distribution** | Single store only |
| **CI/CD Token** | Merchant-level authentication |
| **Dashboard URL** | `https://dev.shopify.com/store/{store}/apps/{app-id}` |

### How to Create

1. Go to Store Admin → Settings → Apps
2. Click **Develop apps**
3. Click **Create an app**
4. Configure app name and settings
5. Install app on the store

### When to Use Custom Apps

- Single-store functionality only
- Store-specific integrations
- Internal tools for one merchant
- When you ARE the merchant (not a partner)

### Custom App Limitations

- Cannot be installed on other stores
- Cannot be listed in App Store
- No partner dashboard access
- Limited CI/CD integration

## Partner Apps

### Characteristics

| Aspect | Details |
|--------|---------|
| **Created via** | Shopify CLI (`shopify app init`) or Partner Dashboard |
| **Managed at** | partners.shopify.com |
| **Ownership** | Partner's organization |
| **Distribution** | Custom (private) or Public (App Store) |
| **CI/CD Token** | `SHOPIFY_CLI_PARTNERS_TOKEN` |
| **Dashboard URL** | `https://partners.shopify.com/organizations/{org-id}/apps/{app-id}` |

### How to Create

**Via CLI (Recommended):**
```bash
shopify app init
```
Follow prompts to create app in Partner Dashboard.

**Via Partner Dashboard:**
1. Go to partners.shopify.com
2. Click **Apps**
3. Click **Create app**
4. Configure app settings

### When to Use Partner Apps

- Apps for multiple merchants
- Apps requiring custom distribution
- Apps targeting App Store listing
- Professional app development
- CI/CD automated deployments

## Critical Differences

### Side-by-Side Comparison

| Aspect | Custom App | Partner App |
|--------|-----------|-------------|
| Creation | Store Admin UI | CLI or Partner Dashboard |
| Dashboard | dev.shopify.com | partners.shopify.com |
| Organization | Merchant's org | Partner's org |
| CI/CD Token | Merchant token | Partner token |
| Distribution | Single store | Multiple stores |
| App Store Eligible | No | Yes (if public) |
| Extension UUIDs | Store-scoped | App-scoped |
| Development Stores | N/A | Yes |

### Dashboard URLs

**Custom App:**
```
https://dev.shopify.com/store/your-store/apps/your-app-id
```

**Partner App:**
```
https://partners.shopify.com/organizations/12345/apps/67890
```

### CI/CD Authentication

**Custom App:**
- Requires store-specific authentication
- More complex for automation
- Token scoped to single store

**Partner App:**
```bash
export SHOPIFY_CLI_PARTNERS_TOKEN=your_partner_token
shopify app deploy --force
```

## Distribution Methods

### Custom Distribution (Private)

For Partner Apps that shouldn't be public:

1. **Generate install link:**
   - Partner Dashboard → App → Distribution → Custom
   - Click **Generate link**

2. **Share with merchants:**
   - Send install URL to specific merchants
   - Each merchant authorizes separately

3. **No review required:**
   - Immediate availability
   - No App Store listing

**Install URL format:**
```
https://admin.shopify.com/oauth/install?client_id=YOUR_CLIENT_ID
```

### Public Distribution (App Store)

For apps available to all merchants:

1. **Meet requirements:**
   - Built for Shopify standards
   - Complete app listing
   - Privacy policy & support

2. **Submit for review:**
   - Partner Dashboard → App → Distribution → Public
   - Submit for Shopify review

3. **After approval:**
   - Listed in Shopify App Store
   - Discoverable by all merchants

### Distribution Comparison

| Method | Audience | Review | Discoverability |
|--------|----------|--------|-----------------|
| Custom App | Single store | None | N/A |
| Custom Distribution | Selected merchants | None | Share link |
| Public Distribution | All merchants | Required | App Store |

## Installation Flow

### Installing a Partner App (Custom Distribution)

1. **Generate distribution link:**
   ```
   Partner Dashboard → App → Distribution → Generate link
   ```

2. **Merchant visits link:**
   ```
   https://admin.shopify.com/oauth/install?client_id=YOUR_CLIENT_ID
   ```

3. **Merchant approves permissions:**
   - Reviews requested scopes
   - Clicks Install

4. **App installed:**
   - Appears in merchant's Apps section
   - Extensions appear in Theme Customizer

5. **Enable extensions:**
   - Theme Customizer → App embeds
   - Toggle ON for theme extensions

### Verification

**Check app is installed:**
- Store Admin → Settings → Apps → Installed apps
- Your app should appear in the list

**Check extension is active:**
- Theme Customizer → App embeds
- Toggle should be available and enabled

## When to Use Which

### Use Custom App When:
- Building for a single store you own/manage
- No need to distribute to other merchants
- Simple internal tools
- Quick one-off integrations

### Use Partner App When:
- Building for multiple merchants
- Need CI/CD automated deployment
- Planning App Store listing
- Professional app development
- Need development stores for testing
- Building reusable functionality

### Decision Flow

```
Need to install on multiple stores?
├── Yes → Partner App
└── No
    └── Need CI/CD deployment?
        ├── Yes → Partner App
        └── No
            └── Is this for a client?
                ├── Yes → Partner App (custom distribution)
                └── No → Custom App (simpler setup)
```

## Common Mistakes

### Mistake 1: Wrong Dashboard

**Problem:** Looking for app at wrong URL

| App Type | Wrong Dashboard | Correct Dashboard |
|----------|----------------|-------------------|
| Custom App | partners.shopify.com | dev.shopify.com |
| Partner App | dev.shopify.com | partners.shopify.com |

### Mistake 2: Wrong CI/CD Token

**Problem:** Deployment fails with authentication error

**For Partner Apps:**
```bash
export SHOPIFY_CLI_PARTNERS_TOKEN=your_partner_token
```

**Get token:**
1. Partner Dashboard → Settings → Partner API clients
2. Create or copy existing token

### Mistake 3: App Not Installed

**Symptom:** Extension doesn't appear in Theme Customizer

**Cause:** App was deployed but never installed on store

**Fix:**
1. Generate custom distribution link
2. Visit link and install app
3. Refresh Theme Customizer

### Mistake 4: Deploying to Wrong App

**Symptom:** CSS deployed but not loading on live site

**Cause:** Local project linked to different app than installed on store

**Fix:**
```bash
# Check which app is linked
shopify app info

# Link to correct app
shopify app config link
# Select the app that's installed on the store
```

### Mistake 5: Creating New App When Updating

**Symptom:** `shopify app init` creates duplicate app

**Cause:** Using `init` instead of `config link`

**Fix:**
- Use `shopify app config link` to connect to existing apps
- Only use `shopify app init` for brand new apps

## Related Documentation

- [App Deployment Guide](app-deployment-guide.md) - init vs config link
- [Theme App Extensions](theme-app-extensions.md) - Extension UUIDs
- [CLI Commands](cli-commands.md) - Complete CLI reference
