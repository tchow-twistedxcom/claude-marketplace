---
name: google-manage
description: Manage Google Analytics and Search Console integration - run reports, analyze SEO, and optimize conversions
---

# Google Analytics & Search Console Management

Comprehensive guide for using GA4 and GSC integration tools.

## CLI Tools

| Tool | Purpose |
|------|---------|
| `google-accounts` | Manage multi-account configurations |
| `ga4-report` | Google Analytics 4 reports |
| `gsc-report` | Search Console reports |
| `seo-analyzer` | Combined GA4+GSC attribution analysis |

## Account Management

```bash
# List configured accounts
google-accounts list

# Add new account
google-accounts add \
  --name myaccount \
  --ga4 "properties/123456789" \
  --gsc "https://mysite.com" \
  --credentials "~/.config/google/myaccount.json"

# Set default account
google-accounts set-default myaccount

# Validate account
google-accounts validate --name myaccount

# Remove account
google-accounts remove myaccount
```

## GA4 Reports

### Available Reports

```bash
ga4-report ecommerce          # Revenue, transactions, cart, checkout
ga4-report landing-pages      # Top organic landing pages
ga4-report traffic-sources    # Source/medium breakdown
ga4-report funnel             # Conversion funnel analysis
ga4-report devices            # Device category breakdown
ga4-report daily              # Daily trend data
ga4-report geography          # Country breakdown
```

### Common Options

```bash
--account <name>    # Use specific account
--days <n>          # Date range (default: 30)
--limit <n>         # Row limit (default: 20)
--json              # Output as JSON
```

### Examples

```bash
# Last 7 days ecommerce for production account
ga4-report ecommerce --account production --days 7

# Top 50 landing pages
ga4-report landing-pages --days 14 --limit 50

# Export traffic sources as JSON
ga4-report traffic-sources --json > traffic.json
```

## GSC Reports

### Available Reports

```bash
gsc-report queries            # Top search queries
gsc-report pages              # Top pages
gsc-report opportunities      # High impressions, low CTR
gsc-report positions          # Position 4-20 opportunities
gsc-report cannibalization    # Multiple pages per query
gsc-report devices            # Device breakdown
gsc-report countries          # Country breakdown
gsc-report daily              # Daily trends
gsc-report query-for-page     # Queries for specific page
```

### Examples

```bash
# Find CTR improvement opportunities
gsc-report opportunities --days 14

# Keyword cannibalization analysis
gsc-report cannibalization --limit 20

# Queries driving traffic to a page
gsc-report query-for-page --page "/products/duty-belt"
```

## SEO Analyzer (Combined)

### Available Reports

```bash
seo-analyzer revenue-queries      # Queries by attributed revenue
seo-analyzer category-performance # Revenue by URL category
seo-analyzer opportunities        # Traffic without conversions
seo-analyzer page-summary         # Pages with driving queries
seo-analyzer combined             # Full attribution data
seo-analyzer summary              # Executive summary
```

### Attribution Model

Revenue is attributed to queries using click share:

```
Query Revenue = (Query Clicks / Total Page Clicks) × Page Revenue
```

### Examples

```bash
# Top revenue-generating queries
seo-analyzer revenue-queries --days 30 --limit 50

# Executive summary
seo-analyzer summary --days 14

# Find optimization opportunities
seo-analyzer opportunities --limit 30

# Export full attribution data
seo-analyzer combined --json > attribution.json
```

## Common Workflows

### Weekly SEO Report

```bash
# 1. Executive summary
seo-analyzer summary --days 7

# 2. Top revenue queries
seo-analyzer revenue-queries --days 7 --limit 20

# 3. Quick wins
gsc-report opportunities --days 7
seo-analyzer opportunities --days 7

# 4. Cannibalization check
gsc-report cannibalization --days 7
```

### Monthly Deep Dive

```bash
# Full analysis
seo-analyzer revenue-queries --days 30 --limit 100
seo-analyzer category-performance --days 30
gsc-report cannibalization --days 30
seo-analyzer page-summary --days 30 --limit 50
```

### Quick Health Check

```bash
# Daily trends
ga4-report daily --days 7
gsc-report daily --days 7
```

## Cache Management

Data is cached to reduce API calls:

| Data Type | Cache Duration |
|-----------|----------------|
| GSC data | 24 hours |
| GA4 historical (>7 days) | 24 hours |
| GA4 recent (<7 days) | 1 hour |

```bash
# View cache status
ga4-report cache
gsc-report cache
seo-analyzer cache

# Clear cache
ga4-report clear-cache
gsc-report clear-cache
seo-analyzer clear-cache
```

## Output Formats

### Table Output (Default)

Human-readable formatted tables:

```bash
ga4-report ecommerce
```

### JSON Output

Machine-readable for scripting:

```bash
ga4-report ecommerce --json
gsc-report queries --json
seo-analyzer combined --json
```

### Export to File

```bash
seo-analyzer revenue-queries --json > revenue.json
gsc-report queries --json > queries.json
```

## Multi-Account Usage

```bash
# Explicit account
ga4-report ecommerce --account production
gsc-report queries --account staging

# Compare accounts
seo-analyzer summary --account production --days 30
seo-analyzer summary --account staging --days 30
```

## Troubleshooting

### "No account configured"
```bash
# Check accounts
google-accounts list

# Add if missing
google-accounts add --name myaccount ...
```

### "Authentication error"
```bash
# Validate account
google-accounts validate

# Clear token cache
rm -rf ~/.config/google-analytics/tokens/
```

### "No data returned"
- Check date range (GSC lags 2-3 days)
- Verify property has organic traffic
- Clear cache and retry

### Debug mode
```bash
# Enable debug output
DEBUG=1 ga4-report ecommerce
```

## Best Practices

1. **Use caching**: Reduces API calls and speeds up reports
2. **Export regularly**: Keep JSON backups of key data
3. **Monitor trends**: Run daily reports to catch issues early
4. **Focus on revenue**: Prioritize queries that drive sales
5. **Fix cannibalization**: Consolidate competing pages
6. **Test changes**: Use staging account before production

## Related Documentation

- `/google-setup` - Initial configuration guide
- `ga4-analytics` skill - GA4 data details
- `gsc-search` skill - GSC data details
- `ga4-gsc-combine` skill - Attribution algorithm
- `seo-optimizer` skill - Optimization workflows
