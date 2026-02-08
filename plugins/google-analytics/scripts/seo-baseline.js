#!/usr/bin/env node

/**
 * SEO Baseline Export Script
 * Creates a comprehensive snapshot for before/after comparison
 */

const fs = require('fs');
const path = require('path');
const { GA4Client } = require('./lib/ga4-client');
const { GSCClient } = require('./lib/gsc-client');
const { DataCombiner } = require('./lib/data-combiner');
const { accountManager, expandPath } = require('./lib/account-manager');

async function createBaseline(days = 90, label = null) {
  const timestamp = new Date().toISOString().split('T')[0];
  const baselineLabel = label || `baseline_${timestamp}`;

  console.log('════════════════════════════════════════════════════════════');
  console.log('  SEO Baseline Export');
  console.log(`  Label: ${baselineLabel}`);
  console.log(`  Date Range: Last ${days} days`);
  console.log('════════════════════════════════════════════════════════════');
  console.log('');

  const ga4 = new GA4Client();
  const gsc = new GSCClient();
  const combiner = new DataCombiner();

  // Create output directory
  const outputConfig = accountManager.getOutputConfig();
  const baselineDir = path.join(outputConfig.output_directory, 'baselines', baselineLabel);

  if (!fs.existsSync(baselineDir)) {
    fs.mkdirSync(baselineDir, { recursive: true });
  }

  const results = {
    metadata: {
      label: baselineLabel,
      created_at: new Date().toISOString(),
      days: days,
      date_range: {
        start: new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        end: new Date().toISOString().split('T')[0]
      }
    },
    summary: {},
    files: []
  };

  try {
    // 1. GA4 Ecommerce Overview
    console.log('📊 Exporting GA4 ecommerce overview...');
    const ecommerce = await ga4.getEcommerceOverview(days);
    saveData(baselineDir, 'ga4_ecommerce.json', ecommerce);
    results.files.push('ga4_ecommerce.json');
    results.summary.ga4_sessions = ecommerce.data[0]?.sessions || 0;
    results.summary.ga4_revenue = ecommerce.data[0]?.purchaseRevenue || 0;
    results.summary.ga4_transactions = ecommerce.data[0]?.transactions || 0;

    // 2. GA4 Traffic Sources
    console.log('📊 Exporting GA4 traffic sources...');
    const traffic = await ga4.getTrafficSources(days);
    saveData(baselineDir, 'ga4_traffic_sources.json', traffic);
    results.files.push('ga4_traffic_sources.json');

    // Extract organic stats
    const organic = traffic.data.find(r => r.sessionMedium === 'organic' && r.sessionSource === 'google');
    results.summary.organic_sessions = organic?.sessions || 0;
    results.summary.organic_revenue = organic?.purchaseRevenue || 0;
    results.summary.organic_conversions = organic?.conversions || 0;

    // 3. GA4 Landing Pages (Organic)
    console.log('📊 Exporting GA4 organic landing pages...');
    const landingPages = await ga4.getOrganicLandingPages(days);
    saveData(baselineDir, 'ga4_landing_pages.json', landingPages);
    results.files.push('ga4_landing_pages.json');
    results.summary.landing_page_count = landingPages.data.length;

    // 4. GA4 Daily Trends
    console.log('📊 Exporting GA4 daily trends...');
    const ga4Daily = await ga4.getDailyTrends(days);
    saveData(baselineDir, 'ga4_daily.json', ga4Daily);
    results.files.push('ga4_daily.json');

    // 5. GSC Top Queries
    console.log('🔍 Exporting GSC top queries...');
    const queries = await gsc.getQueries(days, 500);
    saveData(baselineDir, 'gsc_queries.json', queries);
    results.files.push('gsc_queries.json');
    results.summary.gsc_query_count = queries.data.length;
    results.summary.gsc_total_clicks = queries.data.reduce((s, r) => s + r.clicks, 0);
    results.summary.gsc_total_impressions = queries.data.reduce((s, r) => s + r.impressions, 0);

    // 6. GSC Top Pages
    console.log('🔍 Exporting GSC top pages...');
    const pages = await gsc.getPages(days, 200);
    saveData(baselineDir, 'gsc_pages.json', pages);
    results.files.push('gsc_pages.json');

    // 7. GSC Daily Trends
    console.log('🔍 Exporting GSC daily trends...');
    const gscDaily = await gsc.getDailyQueryTrends(days);
    saveData(baselineDir, 'gsc_daily.json', gscDaily);
    results.files.push('gsc_daily.json');

    // 8. GSC Opportunities
    console.log('🔍 Exporting GSC opportunities...');
    const opportunities = await gsc.getOpportunities(days, 100);
    saveData(baselineDir, 'gsc_opportunities.json', opportunities);
    results.files.push('gsc_opportunities.json');
    results.summary.opportunity_count = opportunities.data.length;

    // 9. GSC Cannibalization
    console.log('🔍 Exporting GSC cannibalization...');
    const cannibalization = await gsc.getCannibalization(days, 50);
    saveData(baselineDir, 'gsc_cannibalization.json', cannibalization);
    results.files.push('gsc_cannibalization.json');
    results.summary.cannibalized_queries = cannibalization.data.length;

    // 10. Combined Revenue Attribution
    console.log('💰 Exporting revenue attribution...');
    const revenueQueries = await combiner.getRevenueQueries(days, 200);
    saveData(baselineDir, 'revenue_queries.json', revenueQueries);
    results.files.push('revenue_queries.json');
    results.summary.attributed_revenue = revenueQueries.data.reduce((s, r) => s + r.total_attributed_revenue, 0);

    // 11. Category Performance
    console.log('💰 Exporting category performance...');
    const categories = await combiner.getCategoryPerformance(days);
    saveData(baselineDir, 'category_performance.json', categories);
    results.files.push('category_performance.json');

    // 12. Content Opportunities
    console.log('💰 Exporting content opportunities...');
    const contentOpps = await combiner.getContentOpportunities(days);
    saveData(baselineDir, 'content_opportunities.json', contentOpps);
    results.files.push('content_opportunities.json');

    // Calculate key metrics for summary
    const avgPosition = queries.data.length > 0
      ? queries.data.reduce((s, r) => s + r.position * r.impressions, 0) / queries.data.reduce((s, r) => s + r.impressions, 0)
      : 0;
    const avgCTR = results.summary.gsc_total_impressions > 0
      ? results.summary.gsc_total_clicks / results.summary.gsc_total_impressions
      : 0;

    results.summary.avg_position = parseFloat(avgPosition.toFixed(2));
    results.summary.avg_ctr = parseFloat((avgCTR * 100).toFixed(2));
    results.summary.revenue_per_click = results.summary.gsc_total_clicks > 0
      ? parseFloat((results.summary.organic_revenue / results.summary.gsc_total_clicks).toFixed(2))
      : 0;

    // Save manifest
    saveData(baselineDir, 'manifest.json', results);
    results.files.push('manifest.json');

    console.log('');
    console.log('════════════════════════════════════════════════════════════');
    console.log('  ✅ Baseline Export Complete');
    console.log('════════════════════════════════════════════════════════════');
    console.log('');
    console.log(`📁 Location: ${baselineDir}`);
    console.log(`📄 Files: ${results.files.length} exported`);
    console.log('');
    console.log('📊 Key Metrics Snapshot:');
    console.log('--------------------------------------------------');
    console.log(`   Organic Sessions:     ${results.summary.organic_sessions.toLocaleString()}`);
    console.log(`   Organic Revenue:      $${results.summary.organic_revenue.toLocaleString()}`);
    console.log(`   Organic Conversions:  ${results.summary.organic_conversions}`);
    console.log(`   GSC Clicks:           ${results.summary.gsc_total_clicks.toLocaleString()}`);
    console.log(`   GSC Impressions:      ${results.summary.gsc_total_impressions.toLocaleString()}`);
    console.log(`   Avg CTR:              ${results.summary.avg_ctr}%`);
    console.log(`   Avg Position:         ${results.summary.avg_position}`);
    console.log(`   Attributed Revenue:   $${results.summary.attributed_revenue.toLocaleString()}`);
    console.log(`   Revenue/Click:        $${results.summary.revenue_per_click}`);
    console.log('');
    console.log('💡 To compare after SEO changes take effect (4-8 weeks):');
    console.log(`   node seo-baseline.js compare ${baselineLabel}`);
    console.log('');

    return results;

  } catch (error) {
    console.error('Error creating baseline:', error.message);
    process.exit(1);
  }
}

async function compareBaseline(baselineLabel) {
  const outputConfig = accountManager.getOutputConfig();
  const baselineDir = path.join(outputConfig.output_directory, 'baselines', baselineLabel);
  const manifestPath = path.join(baselineDir, 'manifest.json');

  if (!fs.existsSync(manifestPath)) {
    console.error(`Baseline not found: ${baselineLabel}`);
    console.error(`Expected path: ${manifestPath}`);
    process.exit(1);
  }

  const baseline = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const days = baseline.metadata.days;

  console.log('════════════════════════════════════════════════════════════');
  console.log('  SEO Baseline Comparison');
  console.log(`  Baseline: ${baselineLabel} (${baseline.metadata.created_at.split('T')[0]})`);
  console.log(`  Comparing: Last ${days} days vs baseline`);
  console.log('════════════════════════════════════════════════════════════');
  console.log('');

  // Get current data
  const ga4 = new GA4Client();
  const gsc = new GSCClient();
  const combiner = new DataCombiner();

  const currentSummary = {};

  // GA4 organic
  const traffic = await ga4.getTrafficSources(days);
  const organic = traffic.data.find(r => r.sessionMedium === 'organic' && r.sessionSource === 'google');
  currentSummary.organic_sessions = organic?.sessions || 0;
  currentSummary.organic_revenue = organic?.purchaseRevenue || 0;
  currentSummary.organic_conversions = organic?.conversions || 0;

  // GSC
  const queries = await gsc.getQueries(days, 500);
  currentSummary.gsc_total_clicks = queries.data.reduce((s, r) => s + r.clicks, 0);
  currentSummary.gsc_total_impressions = queries.data.reduce((s, r) => s + r.impressions, 0);

  const avgPosition = queries.data.length > 0
    ? queries.data.reduce((s, r) => s + r.position * r.impressions, 0) / queries.data.reduce((s, r) => s + r.impressions, 0)
    : 0;
  currentSummary.avg_position = parseFloat(avgPosition.toFixed(2));
  currentSummary.avg_ctr = currentSummary.gsc_total_impressions > 0
    ? parseFloat((currentSummary.gsc_total_clicks / currentSummary.gsc_total_impressions * 100).toFixed(2))
    : 0;

  // Attribution
  const revenueQueries = await combiner.getRevenueQueries(days, 200);
  currentSummary.attributed_revenue = revenueQueries.data.reduce((s, r) => s + r.total_attributed_revenue, 0);
  currentSummary.revenue_per_click = currentSummary.gsc_total_clicks > 0
    ? parseFloat((currentSummary.organic_revenue / currentSummary.gsc_total_clicks).toFixed(2))
    : 0;

  // Compare
  const b = baseline.summary;
  const c = currentSummary;

  const pct = (current, base) => {
    if (base === 0) return current > 0 ? '+∞' : '0.0%';
    const change = ((current - base) / base * 100).toFixed(1);
    return change >= 0 ? `+${change}%` : `${change}%`;
  };

  const delta = (current, base, invert = false) => {
    const diff = current - base;
    const isGood = invert ? diff < 0 : diff > 0;
    const sign = diff >= 0 ? '+' : '';
    return { value: `${sign}${diff.toFixed(1)}`, good: isGood };
  };

  console.log('Metric               | Baseline     | Current      | Change');
  console.log('---------------------|--------------|--------------|------------');
  console.log(`Organic Sessions     | ${b.organic_sessions.toLocaleString().padStart(12)} | ${c.organic_sessions.toLocaleString().padStart(12)} | ${pct(c.organic_sessions, b.organic_sessions)}`);
  console.log(`Organic Revenue      | $${b.organic_revenue.toLocaleString().padStart(11)} | $${c.organic_revenue.toLocaleString().padStart(11)} | ${pct(c.organic_revenue, b.organic_revenue)}`);
  console.log(`Organic Conversions  | ${b.organic_conversions.toString().padStart(12)} | ${c.organic_conversions.toString().padStart(12)} | ${pct(c.organic_conversions, b.organic_conversions)}`);
  console.log(`GSC Clicks           | ${b.gsc_total_clicks.toLocaleString().padStart(12)} | ${c.gsc_total_clicks.toLocaleString().padStart(12)} | ${pct(c.gsc_total_clicks, b.gsc_total_clicks)}`);
  console.log(`GSC Impressions      | ${b.gsc_total_impressions.toLocaleString().padStart(12)} | ${c.gsc_total_impressions.toLocaleString().padStart(12)} | ${pct(c.gsc_total_impressions, b.gsc_total_impressions)}`);
  console.log(`Avg CTR              | ${(b.avg_ctr + '%').padStart(12)} | ${(c.avg_ctr + '%').padStart(12)} | ${delta(c.avg_ctr, b.avg_ctr).value}%`);
  console.log(`Avg Position         | ${b.avg_position.toString().padStart(12)} | ${c.avg_position.toString().padStart(12)} | ${delta(c.avg_position, b.avg_position, true).value} (${c.avg_position < b.avg_position ? 'better' : 'worse'})`);
  console.log(`Attributed Revenue   | $${b.attributed_revenue.toLocaleString().padStart(11)} | $${c.attributed_revenue.toLocaleString().padStart(11)} | ${pct(c.attributed_revenue, b.attributed_revenue)}`);
  console.log(`Revenue/Click        | $${b.revenue_per_click.toString().padStart(11)} | $${c.revenue_per_click.toString().padStart(11)} | ${pct(c.revenue_per_click, b.revenue_per_click)}`);
  console.log('');
}

async function listBaselines() {
  const outputConfig = accountManager.getOutputConfig();
  const baselinesDir = path.join(outputConfig.output_directory, 'baselines');

  if (!fs.existsSync(baselinesDir)) {
    console.log('No baselines found.');
    return;
  }

  const baselines = fs.readdirSync(baselinesDir).filter(f => {
    const manifestPath = path.join(baselinesDir, f, 'manifest.json');
    return fs.existsSync(manifestPath);
  });

  if (baselines.length === 0) {
    console.log('No baselines found.');
    return;
  }

  console.log('════════════════════════════════════════════════════════════');
  console.log('  Available SEO Baselines');
  console.log('════════════════════════════════════════════════════════════');
  console.log('');

  for (const name of baselines) {
    const manifestPath = path.join(baselinesDir, name, 'manifest.json');
    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    console.log(`📁 ${name}`);
    console.log(`   Created: ${manifest.metadata.created_at.split('T')[0]}`);
    console.log(`   Days: ${manifest.metadata.days}`);
    console.log(`   Organic Revenue: $${manifest.summary.organic_revenue.toLocaleString()}`);
    console.log(`   GSC Clicks: ${manifest.summary.gsc_total_clicks.toLocaleString()}`);
    console.log('');
  }
}

function saveData(dir, filename, data) {
  const filepath = path.join(dir, filename);
  fs.writeFileSync(filepath, JSON.stringify(data, null, 2));
}

// CLI
const args = process.argv.slice(2);
const command = args[0] || 'create';

switch (command) {
  case 'create':
    const days = parseInt(args.find(a => a.startsWith('--days='))?.split('=')[1]) || 90;
    const label = args.find(a => a.startsWith('--label='))?.split('=')[1] || null;
    createBaseline(days, label);
    break;

  case 'compare':
    const baselineLabel = args[1];
    if (!baselineLabel) {
      console.error('Usage: seo-baseline.js compare <baseline-label>');
      process.exit(1);
    }
    compareBaseline(baselineLabel);
    break;

  case 'list':
    listBaselines();
    break;

  default:
    console.log('SEO Baseline Tool');
    console.log('');
    console.log('Usage:');
    console.log('  seo-baseline.js create [--days=90] [--label=name]  Create baseline snapshot');
    console.log('  seo-baseline.js compare <baseline-label>           Compare current vs baseline');
    console.log('  seo-baseline.js list                               List available baselines');
}
