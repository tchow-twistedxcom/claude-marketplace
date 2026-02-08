#!/usr/bin/env node
/**
 * GSC Report CLI
 * Generate search performance reports from Google Search Console
 */

const { GSCClient } = require('./lib/gsc-client');

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
  if (num === null || num === undefined) return '-';
  return Number(num).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
}

// Format percentage
function formatPercent(num) {
  if (num === null || num === undefined) return '-';
  return (num * 100).toFixed(2) + '%';
}

// Format position
function formatPosition(num) {
  if (num === null || num === undefined) return '-';
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
      widths[col.key] = Math.max(widths[col.key], Math.min(String(value ?? '').length, col.maxWidth || 60));
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
  queries: async (client, days, limit) => {
    console.log('\n=== Top Search Queries ===\n');
    const result = await client.getQueries(days, limit);

    console.log(formatTable(result.data, [
      { key: 'query', label: 'Query', maxWidth: 50 },
      { key: 'clicks', label: 'Clicks' },
      { key: 'impressions', label: 'Impr' },
      { key: 'ctr', label: 'CTR' },
      { key: 'position', label: 'Pos' }
    ], {
      clicks: formatNumber,
      impressions: formatNumber,
      ctr: formatPercent,
      position: formatPosition
    }));

    console.log(`\nTotal: ${result.data.length} queries (${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  pages: async (client, days, limit) => {
    console.log('\n=== Top Pages ===\n');
    const result = await client.getPages(days, limit);

    console.log(formatTable(result.data, [
      { key: 'page', label: 'Page', maxWidth: 60 },
      { key: 'clicks', label: 'Clicks' },
      { key: 'impressions', label: 'Impr' },
      { key: 'ctr', label: 'CTR' },
      { key: 'position', label: 'Pos' }
    ], {
      clicks: formatNumber,
      impressions: formatNumber,
      ctr: formatPercent,
      position: formatPosition
    }));

    console.log(`\nTotal: ${result.data.length} pages (${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  opportunities: async (client, days, limit) => {
    console.log('\n=== CTR Opportunities (High Impressions, Low CTR) ===\n');
    const result = await client.getOpportunities(days, {
      minImpressions: 100,
      maxCtr: 0.03,
      maxPosition: 20
    });

    const data = result.data.slice(0, limit);
    console.log(formatTable(data, [
      { key: 'query', label: 'Query', maxWidth: 50 },
      { key: 'impressions', label: 'Impr' },
      { key: 'clicks', label: 'Clicks' },
      { key: 'ctr', label: 'CTR' },
      { key: 'position', label: 'Pos' }
    ], {
      clicks: formatNumber,
      impressions: formatNumber,
      ctr: formatPercent,
      position: formatPosition
    }));

    console.log('\nThese queries have high visibility but low click-through rates.');
    console.log('Consider improving titles and meta descriptions.\n');
    console.log(`Total: ${result.data.length} opportunities (${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  positions: async (client, days, limit) => {
    console.log('\n=== Position Improvement Opportunities (Rank 4-20) ===\n');
    const result = await client.getPositionOpportunities(days);

    const data = result.data.slice(0, limit);
    console.log(formatTable(data, [
      { key: 'query', label: 'Query', maxWidth: 40 },
      { key: 'page', label: 'Page', maxWidth: 30 },
      { key: 'impressions', label: 'Impr' },
      { key: 'position', label: 'Pos' }
    ], {
      impressions: formatNumber,
      position: formatPosition
    }));

    console.log('\nThese queries rank on page 1-2 and could reach top 3 with optimization.\n');
    console.log(`Total: ${result.data.length} opportunities (${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  cannibalization: async (client, days, limit) => {
    console.log('\n=== Keyword Cannibalization (Multiple Pages per Query) ===\n');
    const result = await client.getCannibalization(days);

    const data = result.data.slice(0, limit);

    for (const item of data) {
      console.log(`\n📍 "${item.query}" (${item.page_count} pages, ${formatNumber(item.total_impressions)} impressions)`);
      console.log('-'.repeat(70));

      for (const page of item.pages) {
        console.log(`  ${page.page}`);
        console.log(`    Clicks: ${formatNumber(page.clicks)} | Impr: ${formatNumber(page.impressions)} | Pos: ${formatPosition(page.position)}`);
      }
    }

    console.log('\nThese queries have multiple pages competing. Consider consolidation.\n');
    console.log(`Total: ${result.data.length} cannibalized queries (${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  devices: async (client, days) => {
    console.log('\n=== Device Breakdown ===\n');
    const result = await client.getDeviceBreakdown(days);

    console.log(formatTable(result.data, [
      { key: 'device', label: 'Device' },
      { key: 'clicks', label: 'Clicks' },
      { key: 'impressions', label: 'Impr' },
      { key: 'ctr', label: 'CTR' },
      { key: 'position', label: 'Avg Pos' }
    ], {
      clicks: formatNumber,
      impressions: formatNumber,
      ctr: formatPercent,
      position: formatPosition
    }));

    console.log(`\n(${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  countries: async (client, days, limit) => {
    console.log('\n=== Country Breakdown ===\n');
    const result = await client.getCountryBreakdown(days);

    const data = result.data
      .sort((a, b) => b.clicks - a.clicks)
      .slice(0, limit);

    console.log(formatTable(data, [
      { key: 'country', label: 'Country' },
      { key: 'clicks', label: 'Clicks' },
      { key: 'impressions', label: 'Impr' },
      { key: 'ctr', label: 'CTR' },
      { key: 'position', label: 'Avg Pos' }
    ], {
      clicks: formatNumber,
      impressions: formatNumber,
      ctr: formatPercent,
      position: formatPosition
    }));

    console.log(`\n(${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  daily: async (client, days) => {
    console.log('\n=== Daily Trends ===\n');
    const result = await client.getDailyQueryTrends(days);

    console.log(formatTable(result.data, [
      { key: 'date', label: 'Date' },
      { key: 'clicks', label: 'Clicks' },
      { key: 'impressions', label: 'Impr' },
      { key: 'ctr', label: 'CTR' },
      { key: 'position', label: 'Avg Pos' }
    ], {
      clicks: formatNumber,
      impressions: formatNumber,
      ctr: formatPercent,
      position: formatPosition
    }));

    console.log(`\n(${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  'query-for-page': async (client, days, limit, page) => {
    if (!page) {
      console.error('Error: --page <url> is required for this report');
      process.exit(1);
    }

    console.log(`\n=== Queries for Page: ${page} ===\n`);
    const result = await client.getQueriesForPage(page, days);

    const data = result.data.slice(0, limit);
    console.log(formatTable(data, [
      { key: 'query', label: 'Query', maxWidth: 50 },
      { key: 'clicks', label: 'Clicks' },
      { key: 'impressions', label: 'Impr' },
      { key: 'ctr', label: 'CTR' },
      { key: 'position', label: 'Pos' }
    ], {
      clicks: formatNumber,
      impressions: formatNumber,
      ctr: formatPercent,
      position: formatPosition
    }));

    console.log(`\nTotal: ${result.data.length} queries (${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  cache: async (client) => {
    console.log('\n=== Cache Status ===\n');
    const stats = client.getCacheStats();
    console.log(`Account:     ${stats.account}`);
    console.log(`Total:       ${stats.total_entries} entries`);
    console.log(`Valid:       ${stats.valid_entries} entries`);
    console.log(`Expired:     ${stats.expired_entries} entries`);
    console.log(`Size:        ${stats.total_size_mb} MB`);
    console.log(`Directory:   ${stats.cache_directory}`);
  },

  'clear-cache': async (client) => {
    const cleared = client.clearCache();
    console.log(`Cleared ${cleared} cache entries.`);
  }
};

// Help text
function showHelp() {
  console.log(`
GSC Report CLI - Google Search Console Reports

USAGE:
  gsc-report <report> [options]

REPORTS:
  queries             Top search queries by clicks
  pages               Top pages by clicks
  opportunities       High impressions, low CTR queries (quick wins)
  positions           Position 4-20 queries (page 1-2 improvement targets)
  cannibalization     Queries with multiple ranking pages
  devices             Performance by device type
  countries           Performance by country
  daily               Daily trend data
  query-for-page      Queries driving traffic to a specific page
  cache               Show cache status
  clear-cache         Clear cached data

OPTIONS:
  --account <name>    Use specific account (default: default account)
  --days <n>          Date range in days (default: 30)
  --limit <n>         Limit number of rows (default: 20)
  --page <url>        Page URL (for query-for-page report)
  --json              Output as JSON
  --help              Show this help

EXAMPLES:
  # Get top queries for last 30 days
  gsc-report queries

  # Find CTR improvement opportunities
  gsc-report opportunities --days 14

  # Find keyword cannibalization
  gsc-report cannibalization --limit 10

  # Get queries for a specific page
  gsc-report query-for-page --page "/products/duty-belt"

  # Export as JSON
  gsc-report queries --days 7 --json
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
  const page = args.flags.page || null;
  const asJson = args.flags.json === true;

  if (!reports[report]) {
    console.error(`Unknown report: ${report}`);
    console.error('Run "gsc-report --help" for available reports.');
    process.exit(1);
  }

  try {
    const client = new GSCClient(accountName);
    const info = client.account;

    if (!asJson) {
      console.log('═'.repeat(60));
      console.log(`  GSC Report: ${report}`);
      console.log(`  Account: ${info.name} (${info.gsc_site_url})`);
      console.log(`  Date Range: Last ${days} days`);
      console.log('═'.repeat(60));
    }

    if (asJson) {
      // For JSON output, need to capture result
      const result = await reports[report](client, days, limit, page);
      if (result && result.data) {
        console.log(JSON.stringify(result.data, null, 2));
      }
    } else {
      await reports[report](client, days, limit, page);
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
