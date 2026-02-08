---
name: google-setup
description: Set up Google Analytics and Search Console API access with service account authentication
---

# Google Analytics Setup

Configure service account access for GA4 and Google Search Console APIs.

## Prerequisites

- Google Cloud Console access
- Admin access to GA4 property
- Owner access to Search Console property

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Note the project ID for later

## Step 2: Enable APIs

1. Go to **APIs & Services > Library**
2. Search and enable:
   - **Google Analytics Data API**
   - **Search Console API**

## Step 3: Create Service Account

1. Go to **IAM & Admin > Service Accounts**
2. Click **Create Service Account**
3. Enter details:
   - Name: `ga4-gsc-integration`
   - Description: `Service account for GA4 and GSC API access`
4. Click **Create and Continue**
5. Skip role assignment (we'll add access in the products)
6. Click **Done**

## Step 4: Generate JSON Key

1. Click on the created service account
2. Go to **Keys** tab
3. Click **Add Key > Create new key**
4. Select **JSON** format
5. Download and save securely:
   ```bash
   mkdir -p ~/.config/google
   mv ~/Downloads/*.json ~/.config/google/production-service-account.json
   chmod 600 ~/.config/google/production-service-account.json
   ```

## Step 5: Grant GA4 Access

1. Go to [Google Analytics](https://analytics.google.com)
2. Select your property
3. Go to **Admin > Property Access Management**
4. Click **+** to add user
5. Enter the service account email (from Step 3)
6. Select role: **Viewer** (for read-only access)
7. Click **Add**

## Step 6: Grant Search Console Access

1. Go to [Search Console](https://search.google.com/search-console)
2. Select your property
3. Go to **Settings > Users and permissions**
4. Click **Add user**
5. Enter the service account email
6. Select permission: **Restricted** (for read-only access)
7. Click **Add**

## Step 7: Find Your Property IDs

### GA4 Property ID
1. In Google Analytics, go to **Admin**
2. Under Property column, click **Property Settings**
3. Copy the **Property ID** (numeric only, e.g., `123456789`)
4. Format for config: `properties/123456789`

### GSC Site URL
1. In Search Console, note your property URL
2. Format options:
   - URL prefix: `https://yoursite.com`
   - Domain property: `sc-domain:yoursite.com`

## Step 8: Configure Account

```bash
# Add your account
google-accounts add \
  --name production \
  --display-name "Production Store" \
  --ga4 "properties/123456789" \
  --gsc "https://yoursite.com" \
  --credentials "~/.config/google/production-service-account.json" \
  --default

# Validate configuration
google-accounts validate --name production
```

## Step 9: Test Access

```bash
# Test GA4 access
ga4-report ecommerce --days 7

# Test GSC access
gsc-report queries --days 7

# Test combined
seo-analyzer summary --days 7
```

## Adding Multiple Accounts

```bash
# Add staging environment
google-accounts add \
  --name staging \
  --ga4 "properties/987654321" \
  --gsc "https://staging.yoursite.com" \
  --credentials "~/.config/google/staging-service-account.json"

# Add another store
google-accounts add \
  --name other-store \
  --ga4 "properties/555555555" \
  --gsc "https://other-store.com" \
  --credentials "~/.config/google/other-store-service-account.json"

# List all accounts
google-accounts list
```

## Troubleshooting

### "Credentials file not found"
```bash
# Check file exists
ls -la ~/.config/google/

# Check permissions
chmod 600 ~/.config/google/*.json
```

### "Permission denied" errors
- Verify service account email was added correctly to GA4/GSC
- Wait 5-10 minutes for permissions to propagate
- Ensure correct role (Viewer for GA4, Restricted for GSC)

### "Property not found"
- Verify property ID format: `properties/XXXXXXXXX` for GA4
- Verify site URL matches exactly for GSC
- Check you're using the correct property type (GA4, not Universal Analytics)

### Clear cached tokens
```bash
# If auth issues persist
rm -rf ~/.config/google-analytics/tokens/
google-accounts validate
```

## Security Best Practices

1. **Never commit credentials**: Add to `.gitignore`
2. **Use least privilege**: Viewer/Restricted roles only
3. **Rotate keys**: Periodically create new keys and revoke old ones
4. **Secure storage**: Set file permissions to 600
5. **Separate accounts**: Use different service accounts per environment

## Next Steps

- Run `google-accounts list` to see configured accounts
- Run `ga4-report --help` for GA4 reporting options
- Run `gsc-report --help` for GSC reporting options
- Run `seo-analyzer --help` for combined analysis options
