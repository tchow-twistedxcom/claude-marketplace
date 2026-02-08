#!/usr/bin/env node
/**
 * GA4 Report CLI
 * Generate ecommerce and traffic reports from Google Analytics 4
 */

const { GA4Client } = require('./lib/ga4-client');

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

// Format currency
function formatCurrency(num) {
  if (num === null || num === undefined) return '-';
  return '$' + formatNumber(num, 2);
}

// Format percentage
function formatPercent(num) {
  if (num === null || num === undefined) return '-';
  return (num * 100).toFixed(2) + '%';
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
      widths[col.key] = Math.max(widths[col.key], String(value ?? '').length);
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
      return String(value ?? '').padEnd(widths[col.key]);
    }).join(' | ') + '\n';
  });

  return output;
}

// Reports
const reports = {
  ecommerce: async (client, days) => {
    console.log('\n=== Ecommerce Overview ===\n');
    const result = await client.getEcommerceOverview(days);

    if (result.data.length === 0) {
      console.log('No ecommerce data found.');
      return;
    }

    const data = result.data[0];
    console.log(`Sessions:     ${formatNumber(data.sessions)}`);
    console.log(`Users:        ${formatNumber(data.totalUsers)}`);
    console.log(`Transactions: ${formatNumber(data.transactions)}`);
    console.log(`Revenue:      ${formatCurrency(data.purchaseRevenue)}`);
    console.log(`Add to Carts: ${formatNumber(data.addToCarts)}`);
    console.log(`Checkouts:    ${formatNumber(data.checkouts)}`);
    console.log(`Purchases:    ${formatNumber(data.ecommercePurchases)}`);

    if (data.sessions > 0) {
      console.log(`\nConversion Rate: ${formatPercent(data.transactions / data.sessions)}`);
    }
    if (data.transactions > 0) {
      console.log(`AOV: ${formatCurrency(data.purchaseRevenue / data.transactions)}`);
    }

    console.log(`\n(${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  'landing-pages': async (client, days, limit) => {
    console.log('\n=== Top Landing Pages (Organic) ===\n');
    const result = await client.getOrganicLandingPages(days);

    const data = result.data.slice(0, limit);
    console.log(formatTable(data, [
      { key: 'landingPage', label: 'Landing Page' },
      { key: 'sessions', label: 'Sessions' },
      { key: 'conversions', label: 'Conv' },
      { key: 'purchaseRevenue', label: 'Revenue' },
      { key: 'bounceRate', label: 'Bounce' }
    ], {
      sessions: formatNumber,
      conversions: formatNumber,
      purchaseRevenue: formatCurrency,
      bounceRate: formatPercent
    }));

    console.log(`\nTotal: ${result.data.length} pages (${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  'traffic-sources': async (client, days, limit) => {
    console.log('\n=== Traffic Sources ===\n');
    const result = await client.getTrafficSources(days);

    const data = result.data.slice(0, limit);
    console.log(formatTable(data, [
      { key: 'sessionSource', label: 'Source' },
      { key: 'sessionMedium', label: 'Medium' },
      { key: 'sessions', label: 'Sessions' },
      { key: 'conversions', label: 'Conv' },
      { key: 'purchaseRevenue', label: 'Revenue' }
    ], {
      sessions: formatNumber,
      conversions: formatNumber,
      purchaseRevenue: formatCurrency
    }));

    console.log(`\n(${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  funnel: async (client, days) => {
    console.log('\n=== Conversion Funnel ===\n');
    const result = await client.getConversionFunnel(days);

    if (result.data.length === 0) {
      console.log('No funnel data found.');
      return;
    }

    const data = result.data[0];
    const steps = [
      { name: 'Sessions', value: data.sessions },
      { name: 'Add to Cart', value: data.addToCarts },
      { name: 'Checkout', value: data.checkouts },
      { name: 'Purchase', value: data.ecommercePurchases }
    ];

    let prev = steps[0].value;
    steps.forEach((step, i) => {
      const rate = i === 0 ? 100 : (step.value / prev * 100);
      const dropoff = i === 0 ? 0 : (1 - step.value / prev) * 100;
      console.log(`${step.name.padEnd(15)} ${formatNumber(step.value).padStart(10)} (${rate.toFixed(1)}%${i > 0 ? `, -${dropoff.toFixed(1)}%` : ''})`);
      prev = steps[0].value; // Always compare to sessions
    });

    console.log(`\nRevenue: ${formatCurrency(data.purchaseRevenue)}`);
    console.log(`\n(${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  devices: async (client, days) => {
    console.log('\n=== Device Breakdown ===\n');
    const result = await client.getDeviceBreakdown(days);

    console.log(formatTable(result.data, [
      { key: 'deviceCategory', label: 'Device' },
      { key: 'sessions', label: 'Sessions' },
      { key: 'conversions', label: 'Conv' },
      { key: 'purchaseRevenue', label: 'Revenue' },
      { key: 'transactions', label: 'Trans' }
    ], {
      sessions: formatNumber,
      conversions: formatNumber,
      purchaseRevenue: formatCurrency,
      transactions: formatNumber
    }));

    console.log(`\n(${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  daily: async (client, days, limit) => {
    console.log('\n=== Daily Trends ===\n');
    const result = await client.getDailyTrends(days);

    const data = result.data.slice(-limit); // Last N days
    console.log(formatTable(data, [
      { key: 'date', label: 'Date' },
      { key: 'sessions', label: 'Sessions' },
      { key: 'totalUsers', label: 'Users' },
      { key: 'conversions', label: 'Conv' },
      { key: 'purchaseRevenue', label: 'Revenue' }
    ], {
      sessions: formatNumber,
      totalUsers: formatNumber,
      conversions: formatNumber,
      purchaseRevenue: formatCurrency
    }));

    console.log(`\n(${result.fromCache ? 'from cache' : 'fresh data'})`);
  },

  geography: async (client, days, limit) => {
    console.log('\n=== Geographic Breakdown ===\n');
    const result = await client.getGeography(days);

    const data = result.data.slice(0, limit);
    console.log(formatTable(data, [
      { key: 'country', label: 'Country' },
      { key: 'sessions', label: 'Sessions' },
      { key: 'conversions', label: 'Conv' },
      { key: 'purchaseRevenue', label: 'Revenue' }
    ], {
      sessions: formatNumber,
      conversions: formatNumber,
      purchaseRevenue: formatCurrency
    }));

    console.log(`\n(${result.fromCache ? 'from cache' : 'fresh data'})`);
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
GA4 Report CLI - Google Analytics 4 Ecommerce Reports

USAGE:
  ga4-report <report> [options]

REPORTS:
  ecommerce           Ecommerce overview (revenue, transactions, etc.)
  landing-pages       Top organic landing pages by performance
  traffic-sources     Traffic breakdown by source/medium
  funnel              Conversion funnel analysis
  devices             Device category breakdown
  daily               Daily trend data
  geography           Geographic breakdown by country
  cache               Show cache status
  clear-cache         Clear cached data

OPTIONS:
  --account <name>    Use specific account (default: default account)
  --days <n>          Date range in days (default: 30)
  --limit <n>         Limit number of rows (default: 20)
  --json              Output as JSON
  --help              Show this help

EXAMPLES:
  # Get ecommerce overview for last 30 days
  ga4-report ecommerce

  # Get landing pages for specific account
  ga4-report landing-pages --account production --days 7

  # Export traffic sources as JSON
  ga4-report traffic-sources --days 14 --json

  # View cache status
  ga4-report cache
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
    console.error('Run "ga4-report --help" for available reports.');
    process.exit(1);
  }

  try {
    const client = new GA4Client(accountName);
    const info = client.account;

    if (!asJson) {
      console.log('═'.repeat(60));
      console.log(`  GA4 Report: ${report}`);
      console.log(`  Account: ${info.name} (${info.ga4_property_id})`);
      console.log(`  Date Range: Last ${days} days`);
      console.log('═'.repeat(60));
    }

    if (asJson) {
      // For JSON output, run report and output JSON
      const result = await reports[report](client, days, limit);
      if (result && result.data) {
        console.log(JSON.stringify(result.data, null, 2));
      }
    } else {
      await reports[report](client, days, limit);
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
