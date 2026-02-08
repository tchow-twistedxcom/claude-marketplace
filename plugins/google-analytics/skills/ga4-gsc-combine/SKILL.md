---
name: ga4-gsc-combine
description: "Combine GA4 and GSC data for query-to-revenue attribution. Use when analyzing which search queries drive conversions and revenue."
license: MIT
version: 1.0.0
---

# GA4 + GSC Data Combination Skill

Join Google Analytics 4 conversion data with Search Console query data for revenue attribution.

## When to Use This Skill

Activate when you need to:
- Attribute revenue to specific search queries
- Find high-traffic queries with no conversions
- Analyze category-level SEO performance
- Understand which keywords drive actual sales
- Prioritize SEO efforts by revenue impact

## Attribution Model

Query-level conversions are estimated using **click share attribution**:

```
Query Revenue = (Query Clicks / Total Page Clicks) × Page Revenue
```

This distributes page-level conversions proportionally across the queries that drove traffic to that page.

## Quick Start

```bash
# Top revenue-generating queries
seo-analyzer revenue-queries

# Executive summary
seo-analyzer summary

# Find optimization opportunities
seo-analyzer opportunities
```

## Available Reports

| Report | Description |
|--------|-------------|
| `revenue-queries` | Queries ranked by attributed revenue |
| `category-performance` | Revenue by URL category (products, collections, etc.) |
| `opportunities` | High traffic queries with no conversions |
| `page-summary` | Page-level summary with top queries |
| `combined` | Full query-level attribution data |
| `summary` | Executive summary of SEO performance |

## Common Patterns

### Find Top Revenue Queries
```bash
# Last 30 days, top 50 queries by revenue
seo-analyzer revenue-queries --days 30 --limit 50
```

### Analyze Category Performance
```bash
# Revenue by URL category
seo-analyzer category-performance --days 14
```

**Default Categories** (based on URL patterns):
- `products` - /products/*
- `collections` - /collections/*
- `blog` - /blog/*
- `pages` - /pages/*
- `home` - /
- `other` - Everything else

### Find Optimization Opportunities
```bash
# Queries with clicks but no revenue
seo-analyzer opportunities --limit 30
```

These are queries driving traffic but not converting. Consider:
- Improving landing page conversion elements
- Better matching user intent with content
- Clearer calls-to-action

### Page-Level Analysis
```bash
# Top pages with their driving queries
seo-analyzer page-summary --days 7
```

### Full Attribution Data
```bash
# Export complete query-level attribution
seo-analyzer combined --days 14 --json > attribution.json
```

## Understanding the Data

### Key Metrics

| Metric | Description |
|--------|-------------|
| `attributed_revenue` | Estimated revenue from this query |
| `attributed_conversions` | Estimated conversions from this query |
| `click_share` | Query's share of page's total clicks |
| `revenue_per_click` | Average revenue per click |
| `page_conversions` | Total conversions for the page |
| `page_revenue` | Total revenue for the page |

### Attribution Example

If a page has:
- Total Page Revenue: $1,000
- Total Page Clicks: 100

And query "duty belt" has 40 clicks to that page:
- Click Share: 40/100 = 40%
- Attributed Revenue: $1,000 × 40% = $400

## Multi-Account Usage

```bash
# Use specific account
seo-analyzer revenue-queries --account production
seo-analyzer summary --account staging
```

## Executive Summary

The `summary` report provides a quick overview:

```bash
seo-analyzer summary --days 30
```

Shows:
- Total attributed revenue
- Top revenue query
- Category breakdown
- Quick wins available

## Cache Management

Combines cached data from both GA4 and GSC:

```bash
# View cache status
seo-analyzer cache

# Clear all cache
seo-analyzer clear-cache
```

## Prerequisites

1. Both GA4 and GSC configured for the same property
2. Organic traffic in GA4 must match GSC site
3. Account configured via `google-accounts add`

## Limitations

- Attribution is an estimate based on click share
- Works best with significant organic traffic
- Requires both GA4 and GSC to have the same site
- GSC data lags 2-3 days

## Related Skills

- `ga4-analytics` - Raw GA4 data
- `gsc-search` - Raw GSC data
- `seo-optimizer` - Actionable optimization workflows
