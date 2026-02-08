---
name: gsc-search
description: "Query Google Search Console for SEO data. Use when analyzing search queries, rankings, CTR, impressions, or finding SEO opportunities."
license: MIT
version: 1.0.0
---

# GSC Search Skill

Query Google Search Console for search performance, rankings, and SEO opportunities.

## When to Use This Skill

Activate when working with:
- Search query analysis (clicks, impressions, CTR, position)
- Page performance in search results
- SEO opportunity detection
- Keyword cannibalization
- Device and geographic search data
- Position tracking over time

## Quick Start

```bash
# Top search queries
gsc-report queries

# Top pages by clicks
gsc-report pages

# CTR improvement opportunities
gsc-report opportunities

# Keyword cannibalization
gsc-report cannibalization
```

## Available Reports

| Report | Description |
|--------|-------------|
| `queries` | Top search queries by clicks |
| `pages` | Top pages by search performance |
| `opportunities` | High impressions, low CTR queries (quick wins) |
| `positions` | Queries ranking 4-20 (page 1-2 improvement targets) |
| `cannibalization` | Queries with multiple ranking pages |
| `devices` | Performance by device type |
| `countries` | Performance by country |
| `daily` | Daily trend data |
| `query-for-page` | Queries driving traffic to a specific page |

## Common Patterns

### Find Quick Wins
```bash
# High impressions but low CTR - improve titles/descriptions
gsc-report opportunities --days 30

# Good rankings that could be #1-3
gsc-report positions --limit 30
```

### Diagnose Cannibalization
```bash
# Find queries with multiple competing pages
gsc-report cannibalization --days 14

# Check specific query's pages
gsc-report query-for-page --page "/products/duty-belt"
```

### Track Performance
```bash
# Daily trends
gsc-report daily --days 30

# Device breakdown
gsc-report devices

# Geographic performance
gsc-report countries --limit 20
```

## Multi-Account Usage

```bash
# Use specific account
gsc-report queries --account production
gsc-report pages --account staging

# Default account used if not specified
gsc-report opportunities
```

## Understanding Metrics

| Metric | Description |
|--------|-------------|
| Clicks | Users who clicked to your site |
| Impressions | Times your page appeared in search |
| CTR | Click-through rate (clicks/impressions) |
| Position | Average ranking position (1 = top) |

## Opportunity Types

### CTR Opportunities
```
High impressions + Low CTR = Poor title/description
```
**Action**: Improve meta titles and descriptions to increase clicks.

### Position Opportunities
```
Position 4-20 + High impressions = Almost there
```
**Action**: Strengthen content, add internal links, improve page experience.

### Cannibalization
```
Same query + Multiple pages = Split rankings
```
**Action**: Consolidate content or differentiate pages with unique focus.

## Cache Management

GSC data lags 2-3 days and caches for 24 hours:

```bash
# View cache status
gsc-report cache

# Clear cache for fresh data
gsc-report clear-cache
```

## Output Formats

```bash
# Table output (default)
gsc-report queries

# JSON output for scripting
gsc-report queries --json > queries.json
```

## Prerequisites

1. Google Cloud project with Search Console API enabled
2. Service account with Search Console property access
3. Configured account via `google-accounts add`

## Related Skills

- `ga4-analytics` - Traffic and conversion data
- `ga4-gsc-combine` - Query-to-revenue attribution
- `seo-optimizer` - Optimization workflows
