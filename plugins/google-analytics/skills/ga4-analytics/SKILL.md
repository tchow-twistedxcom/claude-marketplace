---
name: ga4-analytics
description: "Query Google Analytics 4 ecommerce data. Use when analyzing traffic, conversions, revenue, landing pages, or funnel performance from GA4."
license: MIT
version: 1.0.0
---

# GA4 Analytics Skill

Query Google Analytics 4 for ecommerce and traffic analysis using the GA4 Data API.

## When to Use This Skill

Activate when working with:
- Ecommerce performance metrics (revenue, transactions, conversions)
- Landing page analysis
- Traffic source breakdown
- Conversion funnel analysis
- Device and geographic performance
- Daily/weekly trends

## Quick Start

```bash
# Get ecommerce overview
ga4-report ecommerce

# Top organic landing pages
ga4-report landing-pages --days 30

# Traffic by source/medium
ga4-report traffic-sources

# Conversion funnel
ga4-report funnel
```

## Available Reports

| Report | Description |
|--------|-------------|
| `ecommerce` | Overview: sessions, revenue, transactions, cart adds, checkouts |
| `landing-pages` | Top organic landing pages with conversion metrics |
| `traffic-sources` | Traffic breakdown by source/medium |
| `funnel` | Conversion funnel: sessions → cart → checkout → purchase |
| `devices` | Performance by device category |
| `daily` | Daily trend data |
| `geography` | Performance by country |

## Common Patterns

### Analyze Ecommerce Performance
```bash
# Last 30 days overview
ga4-report ecommerce --days 30

# Compare with previous period (run twice with different date ranges)
ga4-report ecommerce --days 30
ga4-report ecommerce --days 60  # Compare to 60-day for broader context
```

### Find Top Converting Pages
```bash
# Organic landing pages sorted by revenue
ga4-report landing-pages --days 14 --limit 50
```

### Track Channel Performance
```bash
# All traffic sources
ga4-report traffic-sources --days 7

# Export for analysis
ga4-report traffic-sources --json > traffic.json
```

## Multi-Account Usage

```bash
# Use specific account
ga4-report ecommerce --account production
ga4-report landing-pages --account staging

# Default account used if not specified
ga4-report funnel
```

## Cache Management

Data is cached to reduce API calls:
- Recent data (< 7 days): 1 hour cache
- Historical data (> 7 days): 24 hour cache

```bash
# View cache status
ga4-report cache

# Clear cache for fresh data
ga4-report clear-cache
```

## Output Formats

```bash
# Table output (default)
ga4-report ecommerce

# JSON output for scripting
ga4-report ecommerce --json
```

## Prerequisites

1. Google Cloud project with Analytics Data API enabled
2. Service account with GA4 property access
3. Configured account via `google-accounts add`

## Related Skills

- `gsc-search` - Search Console query and page data
- `ga4-gsc-combine` - Query-to-revenue attribution
- `seo-optimizer` - Optimization workflows
