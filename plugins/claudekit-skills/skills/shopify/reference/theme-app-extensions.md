# Theme App Extensions Reference

Complete guide to Theme App Extensions for adding custom functionality to Shopify themes.

## Table of Contents
1. [Overview](#overview)
2. [Key Concepts](#key-concepts)
3. [Configuration](#configuration)
4. [Assets & Files](#assets--files)
5. [CDN Path Structure](#cdn-path-structure)
6. [Deployment Workflow](#deployment-workflow)
7. [Enabling in Theme Customizer](#enabling-in-theme-customizer)
8. [Troubleshooting](#troubleshooting)

## Overview

Theme App Extensions allow apps to add custom functionality to themes **without modifying theme code directly**. They're ideal for:
- Custom CSS/JS that needs to persist through theme updates
- App embed blocks (site-wide functionality)
- App blocks (section-specific content)
- Custom Liquid snippets injected into themes

### Key Benefits
- **Update-safe:** Survives theme updates since code lives in app, not theme
- **No theme editing required:** Works with any theme automatically
- **Merchant-controlled:** Merchants enable/disable via Theme Customizer
- **Version controlled:** Changes deploy via CLI, not manual file editing

## Key Concepts

### Extension UUID

**CRITICAL: Extension UUIDs are APP-SCOPED**

- Each extension has a unique UUID
- The UUID is generated **per app** - different apps = different UUIDs
- UUID appears in all CDN URLs for the extension's assets
- **Deploying to a different app creates a DIFFERENT UUID**
- Live site loads assets from the specific UUID of the installed app

**Example UUID:** `019bb7e4-d63a-756f-b971-3720f5e1bcd5`

### Extension Types

#### App Embed Blocks
- **Site-wide functionality** (analytics, chat widgets, custom CSS)
- Appear in Theme Customizer → App embeds section
- Must be explicitly **enabled by merchant** to load
- Toggle on/off without uninstalling app

#### App Blocks
- **Section-specific content** (product badges, reviews, upsells)
- Added to specific sections by merchant
- Configurable via section settings
- Can be reordered with other blocks

### Relationship: App → Extension → Store

```
Partner/Custom App (partners.shopify.com or dev.shopify.com)
  └── Theme App Extension (extensions/my-extension/)
        ├── shopify.extension.toml (config + UUID)
        ├── blocks/ (app blocks)
        ├── snippets/ (Liquid snippets)
        └── assets/ (CSS, JS files)

Store Installation:
  1. App installed on store
  2. Extension appears in Theme Customizer
  3. Merchant enables embed/adds blocks
  4. Assets load from Shopify CDN
```

## Configuration

### shopify.extension.toml

Located at: `extensions/{extension-name}/shopify.extension.toml`

```toml
name = "my-theme-extension"
type = "theme"
uid = "019bb7e4-d63a-756f-b971-3720f5e1bcd5"
```

**Fields:**
- `name` - Display name in Partner Dashboard
- `type` - Must be `"theme"` for theme extensions
- `uid` - Auto-generated UUID (do NOT manually set)

### App Embed Block Configuration

Create: `extensions/{extension-name}/blocks/my-embed.liquid`

```liquid
{% comment %}
  @name My Custom Embed
  @description Adds custom functionality site-wide
  @category overlay
{% endcomment %}

{{ 'my-custom.css' | asset_url | stylesheet_tag }}
{{ 'my-custom.js' | asset_url | script_tag }}

<div class="my-custom-widget">
  <!-- Embed content here -->
</div>

{% schema %}
{
  "name": "My Custom Embed",
  "target": "body",
  "javascript": "my-embed.js",
  "stylesheet": "my-embed.css",
  "settings": [
    {
      "type": "checkbox",
      "id": "enabled",
      "label": "Enable widget",
      "default": true
    }
  ]
}
{% endschema %}
```

**Target options:**
- `head` - Inject in `<head>`
- `body` - Inject in `<body>`
- `section` - Inject in specific section

## Assets & Files

### Directory Structure

```
extensions/my-theme-extension/
├── shopify.extension.toml
├── assets/
│   ├── custom.css
│   ├── custom.js
│   └── logo.svg
├── blocks/
│   ├── embed.liquid      (app embed)
│   └── product-badge.liquid (app block)
├── snippets/
│   └── helper.liquid
└── locales/
    └── en.default.json
```

### Asset Loading in Liquid

**CSS:**
```liquid
{{ 'custom.css' | asset_url | stylesheet_tag }}
```

**JavaScript:**
```liquid
{{ 'custom.js' | asset_url | script_tag }}
```

**Images:**
```liquid
<img src="{{ 'logo.svg' | asset_url }}" alt="Logo">
```

## CDN Path Structure

**CRITICAL: Understanding this prevents 90% of "CSS not loading" issues**

### URL Format
```
https://cdn.shopify.com/extensions/{UUID}/{app-handle}-{version}/assets/{filename}
```

### Components

| Component | Description | Example |
|-----------|-------------|---------|
| `{UUID}` | Extension's unique ID (app-scoped) | `019bb7e4-d63a-756f-b971-3720f5e1bcd5` |
| `{app-handle}` | App's URL handle | `graph-ql-admin` |
| `{version}` | Deployed version number | `12` |
| `{filename}` | Asset filename | `custom.css` |

### Full Example
```
https://cdn.shopify.com/extensions/019bb7e4-d63a-756f-b971-3720f5e1bcd5/graph-ql-admin-12/assets/custom.css
```

### Version Numbering
- Versions increment with each `shopify app deploy`
- Old versions remain accessible (for rollback)
- Live theme loads the **currently published** version

## Deployment Workflow

### Initial Setup

1. **Create extension:**
   ```bash
   shopify app generate extension --type theme_app_extension
   ```

2. **Link to existing app (if not new):**
   ```bash
   shopify app config link
   ```
   Select the correct app from the list.

3. **Add assets and blocks:**
   Edit files in `extensions/{name}/`

4. **Deploy:**
   ```bash
   shopify app deploy --force
   ```

### CI/CD Deployment

**GitHub Actions example:**
```yaml
- name: Deploy to Shopify
  env:
    SHOPIFY_CLI_PARTNERS_TOKEN: ${{ secrets.SHOPIFY_CLI_PARTNERS_TOKEN }}
  run: |
    npm install -g @shopify/cli@latest
    shopify app deploy --force
```

**Required secrets:**
- `SHOPIFY_CLI_PARTNERS_TOKEN` - Partner API token

### Verifying Deployment

1. **Check Partner Dashboard:**
   - Go to partners.shopify.com → Apps → Your App → Versions
   - Verify new version appears with extension

2. **Check CDN directly:**
   ```bash
   curl -I "https://cdn.shopify.com/extensions/{UUID}/{app-handle}-{version}/assets/{file}"
   ```
   Should return `200 OK`

3. **Check live site source:**
   - View page source
   - Search for `cdn.shopify.com/extensions`
   - Verify UUID and version match expected values

## Enabling in Theme Customizer

### For App Embeds

1. **App must be installed** on the store
2. Open Theme Customizer
3. Click **App embeds** (left sidebar, bottom)
4. Find your extension
5. Toggle **ON** to enable
6. **Save** the theme

### For App Blocks

1. Open Theme Customizer
2. Navigate to section supporting app blocks
3. Click **Add block**
4. Select your app block
5. Configure settings
6. **Save** the theme

### Why Extension Doesn't Appear

If your extension doesn't show in Theme Customizer:

1. **App not installed?** Check Apps section in store admin
2. **Not deployed?** Run `shopify app deploy`
3. **Wrong app linked?** Run `shopify app info` to verify
4. **Extension type wrong?** Must be `type = "theme"`

## Troubleshooting

### CSS Not Loading After Deployment

**Symptom:** Deployed successfully but CSS not appearing on live site

**Diagnostic Steps:**

1. **Verify correct app is linked:**
   ```bash
   shopify app info
   ```
   Check `client_id` matches your intended app

2. **Compare UUIDs:**
   - Local: `extensions/{name}/shopify.extension.toml` → `uid`
   - Live site: View source → search `cdn.shopify.com/extensions`
   - **Must match exactly**

3. **Check CDN returns 200:**
   ```bash
   curl -I "https://cdn.shopify.com/extensions/{UUID}/{app-handle}-{version}/assets/custom.css"
   ```

4. **Verify embed is enabled:**
   - Theme Customizer → App embeds → Your extension → Toggle ON

5. **Clear caches:**
   - Browser cache
   - Try incognito/private window
   - Shopify CDN has ~5 min propagation

### Wrong UUID in Live Site

**Cause:** Deployed to wrong app (each app generates unique UUIDs)

**Fix:**
1. Identify correct app (where extension should live)
2. Run `shopify app config link` and select correct app
3. Redeploy: `shopify app deploy --force`
4. Enable embed in Theme Customizer (may need re-enable)

### Deployment Succeeded but Nothing Changed

**Possible causes:**

1. **Deployed to different app** than live site loads from
2. **Extension disabled** in Theme Customizer
3. **Browser cache** showing old version
4. **CDN propagation** (wait 5 minutes)

**Debug:**
```bash
# Check which app is linked
shopify app info

# Verify extension included
cat extensions/*/shopify.extension.toml
```

### Extension Shows But Toggle Does Nothing

**Cause:** Usually theme incompatibility or Liquid error

**Fix:**
1. Check browser console for JavaScript errors
2. Validate Liquid syntax: `shopify theme check`
3. Ensure schema is valid JSON

### Multiple Apps Have Same Extension

**Scenario:** Old app still has extension visible in Theme Customizer

**Fix:** Deploy empty version to old app:
```bash
# Link to old app
shopify app config link  # Select old app

# Temporarily move extensions
mv extensions extensions_backup

# Deploy (removes extensions from old app)
shopify app deploy --force

# Restore and link back
mv extensions_backup extensions
shopify app config link  # Select correct app
```

## Best Practices

1. **One source of truth:** Keep extension in single app only
2. **Version your assets:** Use cache-busting or versioned filenames
3. **Test in dev store:** Always verify on development store first
4. **Document the UUID:** Note which UUID maps to which app
5. **CI/CD early:** Set up automated deploys to prevent manual errors
6. **Backup configs:** Store `shopify.app.toml` in version control

## Related Documentation

- [App Deployment Guide](app-deployment-guide.md) - Full deployment workflow
- [App Types and Distribution](app-types-and-distribution.md) - Custom vs Partner apps
- [CLI Commands](cli-commands.md) - Complete CLI reference
