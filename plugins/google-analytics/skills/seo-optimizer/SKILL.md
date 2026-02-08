---
name: seo-optimizer
description: "SEO optimization workflows combining GA4 and GSC data. Use when creating SEO reports, finding optimization opportunities, or analyzing search performance."
license: MIT
version: 1.0.0
---

# SEO Optimizer Skill

Actionable SEO optimization workflows combining GA4 conversions with GSC search data.

## When to Use This Skill

Activate when you need to:
- Create weekly/monthly SEO performance reports
- Find and prioritize optimization opportunities
- Analyze query-to-revenue attribution
- Detect keyword cannibalization
- Build SEO improvement action plans

## Core Workflows

### 1. Weekly SEO Report

Generate a comprehensive weekly performance summary:

```bash
# Full summary with key metrics
seo-analyzer summary --days 7

# Revenue attribution
seo-analyzer revenue-queries --days 7 --limit 20

# Opportunities to address
seo-analyzer opportunities --days 7 --limit 10
```

### 2. Find Quick Wins

Identify high-impact, low-effort improvements:

```bash
# CTR opportunities (improve titles/meta)
gsc-report opportunities --days 14

# Position opportunities (almost page 1)
gsc-report positions --days 14 --limit 30

# Content with traffic but no conversions
seo-analyzer opportunities --days 14
```

### 3. Revenue Analysis

Understand which keywords drive sales:

```bash
# Top revenue queries
seo-analyzer revenue-queries --days 30

# Category performance
seo-analyzer category-performance --days 30

# Page-level breakdown
seo-analyzer page-summary --days 30
```

### 4. Cannibalization Audit

Find and fix competing pages:

```bash
# Identify cannibalized queries
gsc-report cannibalization --days 30

# Analyze specific page's queries
gsc-report query-for-page --page "/products/duty-belt"
```

## Optimization Playbook

### CTR Improvement (Quick Win)

**Signal**: High impressions, low CTR, good position

**Check**:
```bash
gsc-report opportunities --days 14
```

**Actions**:
1. Review and improve title tags
2. Enhance meta descriptions with benefits/CTAs
3. Add structured data for rich snippets
4. Target position 1-3 for featured snippet

### Position Improvement

**Signal**: Position 4-20 with high impressions

**Check**:
```bash
gsc-report positions --days 14
```

**Actions**:
1. Strengthen content (more depth, E-E-A-T signals)
2. Add internal links from high-authority pages
3. Improve page experience (Core Web Vitals)
4. Build relevant backlinks

### Conversion Improvement

**Signal**: Good traffic, no conversions

**Check**:
```bash
seo-analyzer opportunities --days 14
```

**Actions**:
1. Review landing page alignment with query intent
2. Add clearer calls-to-action
3. Improve product images and descriptions
4. Add trust signals and social proof
5. Test different page layouts

### Cannibalization Fix

**Signal**: Multiple pages ranking for same query

**Check**:
```bash
gsc-report cannibalization --days 30
```

**Actions**:
1. Choose primary page for the query
2. Redirect or consolidate secondary pages
3. Differentiate content focus if keeping both
4. Update internal linking to primary page
5. Add canonical tags if appropriate

## Report Templates

### Executive Summary Template

```markdown
## SEO Performance Summary (Last 30 Days)

### Key Metrics
- Total Organic Revenue: $X,XXX
- Total Organic Clicks: X,XXX
- Revenue per Click: $X.XX

### Top Performing Queries
1. "query 1" - $XXX revenue
2. "query 2" - $XXX revenue
3. "query 3" - $XXX revenue

### Opportunities Identified
- X CTR improvement opportunities
- X position improvement opportunities
- X content optimization opportunities

### Recommended Actions
1. Priority action 1
2. Priority action 2
3. Priority action 3
```

### Generate Data for Template

```bash
# Run these commands and use output
seo-analyzer summary --days 30
seo-analyzer revenue-queries --days 30 --limit 10
gsc-report opportunities --days 30
seo-analyzer opportunities --days 30
```

## Scheduled Reports

### Daily Monitoring

```bash
# Quick health check
gsc-report daily --days 7
ga4-report daily --days 7
```

### Weekly Analysis

```bash
# Comprehensive weekly review
seo-analyzer summary --days 7
gsc-report opportunities --days 7
seo-analyzer opportunities --days 7
```

### Monthly Deep Dive

```bash
# Full monthly analysis
seo-analyzer revenue-queries --days 30 --limit 100
seo-analyzer category-performance --days 30
gsc-report cannibalization --days 30
seo-analyzer page-summary --days 30 --limit 50
```

## Multi-Account Comparison

Compare performance across properties:

```bash
# Production
seo-analyzer summary --account production --days 30

# Compare to staging/test
seo-analyzer summary --account staging --days 30
```

## Export for External Tools

```bash
# Export all data as JSON
seo-analyzer revenue-queries --json > revenue.json
gsc-report queries --json > queries.json
seo-analyzer combined --json > attribution.json
```

## Cache Management

```bash
# Clear cache before important reports
seo-analyzer clear-cache

# Check cache status
seo-analyzer cache
```

## Related Skills

- `ga4-analytics` - Raw GA4 data queries
- `gsc-search` - Raw GSC data queries
- `ga4-gsc-combine` - Attribution algorithm details
