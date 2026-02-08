#!/usr/bin/env node
/**
 * SEO Analyzer CLI
 * Combined GA4 + GSC analysis for revenue attribution and optimization
 */

const { DataCombiner } = require('./lib/data-combiner');

// Parse command line arguments
function parseArgs(args) {
  const parsed = { _: [], flags: {} };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg.startsWith('--')) {
      const key = arg.slice(2);
      const next = args[i + 1];

      if (next && !next.startsWith('--')) {
        parsed.flags[key] = next;
        i++;
      } else {
        parsed.flags[key] = true;
      }
    } else {
      parsed._.push(arg);
    }
  }

  return parsed;
}

// Format number with thousands separator
function formatNumber(num, decimals = 0) {
  if (num === null || num === undefined || isNaN(num)) return '-';
  return Number(num).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
}

// Format currency
function formatCurrency(num) {
  if (num === null || num === undefined || isNaN(num)) return '-';
  return '$' + formatNumber(num, 2);
}

// Format percentage
function formatPercent(num) {
  if (num === null || num === undefined || isNaN(num)) return '-';
  return (num * 100).toFixed(2) + '%';
}

// Format position
function formatPosition(num) {
  if (num === null || num === undefined || isNaN(num)) return '-';
  return num.toFixed(1);
}

// Format table output
function formatTable(data, columns, formatters = {}) {
  if (!data || data.length === 0) {
    return 'No data';
  }

  // Calculate column widths
  const widths = {};
  columns.forEach(col => {
    widths[col.key] = col.label.length;
    data.forEach(row => {
      let value = row[col.key];
      if (formatters[col.key]) {
        value = formatters[col.key](value);
      }
      widths[col.key] = Math.max(widths[col.key], Math.min(String(value ?? '').length, col.maxWidth || 50));
    });
  });

  // Build header
  let output = columns.map(col => col.label.padEnd(widths[col.key])).join(' | ') + '\n';
  output += columns.map(col => '-'.repeat(widths[col.key])).join('-|-') + '\n';

  // Build rows
  data.forEach(row => {
    output += columns.map(col => {
      let value = row[col.key];
      if (formatters[col.key]) {
        value = formatters[col.key](value);
      }
      value = String(value ?? '');
      if (col.maxWidth && value.length > col.maxWidth) {
        value = value.slice(0, col.maxWidth - 3) + '...';
      }
      return value.padEnd(widths[col.key]);
    }).join(' | ') + '\n';
  });

  return output;
}

// Reports
const reports = {
  'revenue-queries': async (combiner, days, limit) => {
    console.log('\n=== Top Revenue-Generating Queries ===\n');
    console.log('Attribution based on click share per landing page.\n');

    const result = await combiner.getRevenueQueries(days, limit);

    console.log(formatTable(result.data, [
      { key: 'query', label: 'Query', maxWidth: 40 },
      { key: 'total_clicks', label: 'Clicks' },
      { key: 'total_attributed_revenue', label: 'Attr Revenue' },
      { key: 'total_attributed_conversions', label: 'Attr Conv' },
      { key: 'avg_position', label: 'Avg Pos' },
      { key: 'revenue_per_click', label: 'Rev/Click' }
    ], {
      total_clicks: formatNumber,
      total_attributed_revenue: formatCurrency,
      total_attributed_conversions: v => formatNumber(v, 1),
      avg_position: formatPosition,
      revenue_per_click: formatCurrency
    }));

    // Summary
    const totalRevenue = result.data.reduce((sum, r) => sum + r.total_attributed_revenue, 0);
    const totalClicks = result.data.reduce((sum, r) => sum + r.total_clicks, 0);

    console.log(`\nTotal Attributed Revenue: ${formatCurrency(totalRevenue)}`);
    console.log(`Total Clicks: ${formatNumber(totalClicks)}`);
    console.log(`Queries Analyzed: ${result.total_queries}`);
    console.log(`\n(${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  'category-performance': async (combiner, days, limit) => {
    console.log('\n=== Category Performance (URL-Based) ===\n');

    const result = await combiner.getCategoryPerformance(days);

    console.log(formatTable(result.data, [
      { key: 'category', label: 'Category' },
      { key: 'total_clicks', label: 'Clicks' },
      { key: 'total_attributed_revenue', label: 'Revenue' },
      { key: 'total_attributed_conversions', label: 'Conv' },
      { key: 'query_count', label: 'Queries' },
      { key: 'page_count', label: 'Pages' },
      { key: 'revenue_per_click', label: 'Rev/Click' }
    ], {
      total_clicks: formatNumber,
      total_attributed_revenue: formatCurrency,
      total_attributed_conversions: v => formatNumber(v, 1),
      query_count: formatNumber,
      page_count: formatNumber,
      revenue_per_click: formatCurrency
    }));

    console.log(`\n(${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  opportunities: async (combiner, days, limit) => {
    console.log('\n=== Content Optimization Opportunities ===\n');
    console.log('High traffic queries with no attributed revenue.\n');

    const result = await combiner.getContentOpportunities(days);

    const data = result.data.slice(0, limit);
    console.log(formatTable(data, [
      { key: 'query', label: 'Query', maxWidth: 40 },
      { key: 'page', label: 'Page', maxWidth: 30 },
      { key: 'clicks', label: 'Clicks' },
      { key: 'position', label: 'Pos' },
      { key: 'opportunity_score', label: 'Opp Score' }
    ], {
      clicks: formatNumber,
      position: formatPosition,
      opportunity_score: v => formatNumber(v, 1)
    }));

    console.log('\nThese queries drive traffic but no conversions.');
    console.log('Possible actions:');
    console.log('  - Improve landing page conversion elements');
    console.log('  - Better match user intent with content');
    console.log('  - Add clearer calls-to-action');

    console.log(`\nTotal: ${result.data.length} opportunities (${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  'page-summary': async (combiner, days, limit) => {
    console.log('\n=== Page Performance Summary ===\n');

    const result = await combiner.getPageSummary(days);

    const data = result.data.slice(0, limit);

    for (const page of data) {
      console.log(`\n📄 ${page.page}`);
      console.log('-'.repeat(70));
      console.log(`   Sessions: ${formatNumber(page.page_sessions)} | Conversions: ${formatNumber(page.page_conversions)} | Revenue: ${formatCurrency(page.page_revenue)}`);
      console.log(`   Organic Clicks: ${formatNumber(page.total_clicks)} | Impressions: ${formatNumber(page.total_impressions)} | Queries: ${page.query_count}`);

      if (page.top_queries.length > 0) {
        console.log('\n   Top Queries:');
        for (const q of page.top_queries.slice(0, 5)) {
          console.log(`     • "${q.query}" - ${formatNumber(q.clicks)} clicks, pos ${formatPosition(q.position)}`);
        }
      }
    }

    console.log(`\n\nTotal: ${result.data.length} pages (${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  combined: async (combiner, days, limit) => {
    console.log('\n=== Full Query-Level Attribution ===\n');

    const result = await combiner.combine(days);

    // Sort by attributed revenue
    result.data.sort((a, b) => b.attributed_revenue - a.attributed_revenue);

    const data = result.data.slice(0, limit);
    console.log(formatTable(data, [
      { key: 'query', label: 'Query', maxWidth: 35 },
      { key: 'page', label: 'Page', maxWidth: 25 },
      { key: 'clicks', label: 'Clicks' },
      { key: 'attributed_revenue', label: 'Attr Rev' },
      { key: 'position', label: 'Pos' },
      { key: 'click_share', label: 'Share' }
    ], {
      clicks: formatNumber,
      attributed_revenue: formatCurrency,
      position: formatPosition,
      click_share: formatPercent
    }));

    // Summary
    const totalRevenue = result.data.reduce((sum, r) => sum + r.attributed_revenue, 0);
    console.log(`\nTotal Attributed Revenue: ${formatCurrency(totalRevenue)}`);
    console.log(`Total Query-Page Combinations: ${result.data.length}`);
    console.log(`\n(GA4: ${result.ga4FromCache ? 'cached' : 'fresh'}, GSC: ${result.gscFromCache ? 'cached' : 'fresh'})`);
  },

  summary: async (combiner, days) => {
    console.log('\n=== SEO Performance Summary ===\n');

    // Get multiple reports
    const [revenue, categories, opportunities] = await Promise.all([
      combiner.getRevenueQueries(days, 10),
      combiner.getCategoryPerformance(days),
      combiner.getContentOpportunities(days)
    ]);

    // Overall stats
    const totalRevenue = revenue.data.reduce((sum, r) => sum + r.total_attributed_revenue, 0);
    const totalClicks = revenue.data.reduce((sum, r) => sum + r.total_clicks, 0);
    const topQuery = revenue.data[0];

    console.log('📊 Overall Performance');
    console.log('-'.repeat(50));
    console.log(`   Total Attributed Revenue: ${formatCurrency(totalRevenue)}`);
    console.log(`   Total Organic Clicks: ${formatNumber(totalClicks)}`);
    console.log(`   Queries Tracked: ${revenue.total_queries}`);
    console.log(`   Avg Revenue/Click: ${formatCurrency(totalRevenue / totalClicks)}`);

    console.log('\n🏆 Top Revenue Query');
    console.log('-'.repeat(50));
    if (topQuery) {
      console.log(`   "${topQuery.query}"`);
      console.log(`   Revenue: ${formatCurrency(topQuery.total_attributed_revenue)} | Clicks: ${formatNumber(topQuery.total_clicks)} | Pos: ${formatPosition(topQuery.avg_position)}`);
    }

    console.log('\n📂 Category Breakdown');
    console.log('-'.repeat(50));
    for (const cat of categories.data.slice(0, 5)) {
      console.log(`   ${cat.category.padEnd(15)} ${formatCurrency(cat.total_attributed_revenue).padStart(12)} (${formatNumber(cat.total_clicks)} clicks)`);
    }

    console.log('\n⚡ Quick Wins Available');
    console.log('-'.repeat(50));
    console.log(`   ${opportunities.data.length} queries with traffic but no conversions`);
    if (opportunities.data.length > 0) {
      console.log('   Top 3:');
      for (const opp of opportunities.data.slice(0, 3)) {
        console.log(`     • "${opp.query}" (${formatNumber(opp.clicks)} clicks, pos ${formatPosition(opp.position)})`);
      }
    }

    console.log(`\n(${revenue.fromCache ? 'from cache' : 'fresh data'})`);
  },

  cache: async (combiner) => {
    console.log('\n=== Cache Status ===\n');
    const stats = combiner.getCacheStats();

    console.log('GA4 Cache:');
    console.log(`  Total:   ${stats.ga4.total_entries} entries`);
    console.log(`  Valid:   ${stats.ga4.valid_entries} entries`);
    console.log(`  Size:    ${stats.ga4.total_size_mb} MB`);

    console.log('\nGSC Cache:');
    console.log(`  Total:   ${stats.gsc.total_entries} entries`);
    console.log(`  Valid:   ${stats.gsc.valid_entries} entries`);
    console.log(`  Size:    ${stats.gsc.total_size_mb} MB`);
  },

  'clear-cache': async (combiner) => {
    const cleared = combiner.clearCache();
    console.log(`Cleared ${cleared} cache entries.`);
  }
};

// Help text
function showHelp() {
  console.log(`
SEO Analyzer CLI - Combined GA4 + GSC Attribution Analysis

USAGE:
  seo-analyzer <report> [options]

REPORTS:
  revenue-queries     Top queries by attributed revenue
  category-performance Revenue by URL category (products, collections, etc.)
  opportunities       High traffic queries with no conversions
  page-summary        Page-level summary with top queries
  combined            Full query-level attribution data
  summary             Executive summary of SEO performance
  cache               Show cache status
  clear-cache         Clear cached data

OPTIONS:
  --account <name>    Use specific account (default: default account)
  --days <n>          Date range in days (default: 30)
  --limit <n>         Limit number of rows (default: 20)
  --json              Output as JSON
  --help              Show this help

ATTRIBUTION MODEL:
  Query-level conversions are estimated using click share:

  Query Revenue = (Query Clicks / Total Page Clicks) × Page Revenue

  This distributes page conversions across the queries that drove traffic.

EXAMPLES:
  # Get top revenue-generating queries
  seo-analyzer revenue-queries

  # Get executive summary
  seo-analyzer summary --days 14

  # Find optimization opportunities
  seo-analyzer opportunities --limit 30

  # Full query attribution data
  seo-analyzer combined --days 7 --json
`);
}

// Main
async function main() {
  const args = parseArgs(process.argv.slice(2));

  if (args.flags.help || args._.length === 0) {
    showHelp();
    return;
  }

  const report = args._[0];
  const accountName = args.flags.account || null;
  const days = parseInt(args.flags.days) || 30;
  const limit = parseInt(args.flags.limit) || 20;
  const asJson = args.flags.json === true;

  if (!reports[report]) {
    console.error(`Unknown report: ${report}`);
    console.error('Run "seo-analyzer --help" for available reports.');
    process.exit(1);
  }

  try {
    const combiner = new DataCombiner(accountName);

    if (!asJson) {
      console.log('═'.repeat(60));
      console.log(`  SEO Analyzer: ${report}`);
      console.log(`  Account: ${accountName || 'default'}`);
      console.log(`  Date Range: Last ${days} days`);
      console.log('═'.repeat(60));
    }

    if (asJson && report !== 'cache' && report !== 'clear-cache') {
      // For JSON output
      let result;
      switch (report) {
        case 'revenue-queries':
          result = await combiner.getRevenueQueries(days, limit);
          break;
        case 'category-performance':
          result = await combiner.getCategoryPerformance(days);
          break;
        case 'opportunities':
          result = await combiner.getContentOpportunities(days);
          break;
        case 'page-summary':
          result = await combiner.getPageSummary(days);
          break;
        case 'combined':
          result = await combiner.combine(days);
          break;
        default:
          result = await reports[report](combiner, days, limit);
      }
      if (result && result.data) {
        console.log(JSON.stringify(result.data, null, 2));
      }
    } else {
      await reports[report](combiner, days, limit);
    }

  } catch (error) {
    console.error(`Error: ${error.message}`);
    if (process.env.DEBUG) {
      console.error(error.stack);
    }
    process.exit(1);
  }
}

main();
