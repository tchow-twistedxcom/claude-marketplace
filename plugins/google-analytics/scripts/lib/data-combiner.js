/**
 * Data Combiner for GA4 + GSC Attribution
 * Joins GA4 conversion data with GSC query data
 * Uses ratio-based attribution algorithm
 */

const { GA4Client } = require('./ga4-client');
const { GSCClient } = require('./gsc-client');

class DataCombiner {
  constructor(accountName = null) {
    this.ga4 = new GA4Client(accountName);
    this.gsc = new GSCClient(accountName);
    this.accountName = accountName;
  }

  // Normalize landing page URL for joining
  normalizePath(url) {
    // Skip empty, null, or "(not set)" values - don't normalize to '/'
    if (!url || url === '' || url === '(not set)') return null;

    try {
      // If full URL, extract path
      if (url.startsWith('http')) {
        const parsed = new URL(url);
        return parsed.pathname + (parsed.search || '');
      }
      // Already a path
      return url.startsWith('/') ? url : '/' + url;
    } catch (e) {
      return url;
    }
  }

  // Fetch both GA4 and GSC data
  async fetchData(days = null) {
    // Fetch in parallel
    const [ga4Result, gscResult] = await Promise.all([
      this.ga4.getOrganicLandingPages(days),
      this.gsc.getNormalizedPages(days)
    ]);

    return {
      ga4: ga4Result,
      gsc: gscResult
    };
  }

  // Combine data with query-level attribution
  async combine(days = null) {
    const { ga4, gsc } = await this.fetchData(days);

    // Index GA4 data by normalized landing page
    const ga4ByPage = {};
    for (const row of ga4.data) {
      const path = this.normalizePath(row.landingPage);
      if (path) {  // Skip null/empty paths
        ga4ByPage[path] = row;
      }
    }

    // Group GSC data by page
    const gscByPage = {};
    for (const row of gsc.data) {
      const path = row.page_normalized || this.normalizePath(row.page);
      if (!path) continue;  // Skip null paths
      if (!gscByPage[path]) {
        gscByPage[path] = {
          queries: [],
          totalClicks: 0
        };
      }
      gscByPage[path].queries.push(row);
      gscByPage[path].totalClicks += row.clicks;
    }

    // Combine and calculate attribution
    const combined = [];

    for (const [path, gscData] of Object.entries(gscByPage)) {
      const ga4Data = ga4ByPage[path];

      if (!ga4Data) continue; // No GA4 data for this page

      // Calculate attribution for each query
      for (const query of gscData.queries) {
        const clickShare = gscData.totalClicks > 0
          ? query.clicks / gscData.totalClicks
          : 0;

        combined.push({
          // Query info
          query: query.query,
          page: path,
          page_full: query.page,

          // GSC metrics
          clicks: query.clicks,
          impressions: query.impressions,
          ctr: query.ctr,
          position: query.position,

          // GA4 page metrics
          page_sessions: ga4Data.sessions,
          page_users: ga4Data.totalUsers,
          page_bounce_rate: ga4Data.bounceRate,
          page_conversions: ga4Data.conversions,
          page_revenue: ga4Data.purchaseRevenue,
          page_transactions: ga4Data.transactions,

          // Attributed metrics (query-level estimate)
          click_share: clickShare,
          attributed_conversions: (ga4Data.conversions || 0) * clickShare,
          attributed_revenue: (ga4Data.purchaseRevenue || 0) * clickShare,
          attributed_transactions: (ga4Data.transactions || 0) * clickShare,

          // Calculated metrics
          conversion_rate: ga4Data.sessions > 0
            ? (ga4Data.conversions || 0) / ga4Data.sessions
            : 0,
          revenue_per_click: query.clicks > 0
            ? ((ga4Data.purchaseRevenue || 0) * clickShare) / query.clicks
            : 0
        });
      }
    }

    return {
      data: combined,
      ga4FromCache: ga4.fromCache,
      gscFromCache: gsc.fromCache,
      ga4CacheKey: ga4.cacheKey,
      gscCacheKey: gsc.cacheKey
    };
  }

  // Get top revenue-generating queries
  async getRevenueQueries(days = null, limit = 50) {
    const result = await this.combine(days);

    // Aggregate by query (sum across all pages)
    const queryAggregates = {};
    for (const row of result.data) {
      if (!queryAggregates[row.query]) {
        queryAggregates[row.query] = {
          query: row.query,
          total_clicks: 0,
          total_impressions: 0,
          total_attributed_revenue: 0,
          total_attributed_conversions: 0,
          total_attributed_transactions: 0,
          avg_position: 0,
          avg_ctr: 0,
          page_count: 0,
          pages: []
        };
      }

      const agg = queryAggregates[row.query];
      agg.total_clicks += row.clicks;
      agg.total_impressions += row.impressions;
      agg.total_attributed_revenue += row.attributed_revenue;
      agg.total_attributed_conversions += row.attributed_conversions;
      agg.total_attributed_transactions += row.attributed_transactions;
      agg.avg_position += row.position;
      agg.page_count++;
      agg.pages.push({
        page: row.page,
        clicks: row.clicks,
        attributed_revenue: row.attributed_revenue
      });
    }

    // Calculate averages and sort
    const queries = Object.values(queryAggregates).map(q => ({
      ...q,
      avg_position: q.avg_position / q.page_count,
      avg_ctr: q.total_clicks / q.total_impressions,
      revenue_per_click: q.total_clicks > 0
        ? q.total_attributed_revenue / q.total_clicks
        : 0,
      conversion_rate: q.total_clicks > 0
        ? q.total_attributed_conversions / q.total_clicks
        : 0
    }));

    // Sort by attributed revenue
    queries.sort((a, b) => b.total_attributed_revenue - a.total_attributed_revenue);

    return {
      data: queries.slice(0, limit),
      total_queries: queries.length,
      fromCache: result.ga4FromCache && result.gscFromCache
    };
  }

  // Get category performance (based on URL patterns)
  async getCategoryPerformance(days = null, categoryPatterns = null) {
    const result = await this.combine(days);

    // Default patterns if not provided
    if (!categoryPatterns) {
      categoryPatterns = {
        'products': /^\/products\//,
        'collections': /^\/collections\//,
        'blog': /^\/blogs?\//,
        'pages': /^\/pages\//,
        'home': /^\/$/
      };
    }

    // Categorize and aggregate
    const categories = {};
    for (const row of result.data) {
      let category = 'other';

      for (const [name, pattern] of Object.entries(categoryPatterns)) {
        if (pattern.test(row.page)) {
          category = name;
          break;
        }
      }

      if (!categories[category]) {
        categories[category] = {
          category,
          total_clicks: 0,
          total_impressions: 0,
          total_attributed_revenue: 0,
          total_attributed_conversions: 0,
          query_count: 0,
          page_count: 0,
          pages: new Set()
        };
      }

      const cat = categories[category];
      cat.total_clicks += row.clicks;
      cat.total_impressions += row.impressions;
      cat.total_attributed_revenue += row.attributed_revenue;
      cat.total_attributed_conversions += row.attributed_conversions;
      cat.query_count++;
      cat.pages.add(row.page);
    }

    // Convert to array and calculate metrics
    const categoryData = Object.values(categories).map(cat => ({
      ...cat,
      page_count: cat.pages.size,
      pages: undefined, // Remove Set
      avg_ctr: cat.total_clicks / cat.total_impressions,
      revenue_per_click: cat.total_clicks > 0
        ? cat.total_attributed_revenue / cat.total_clicks
        : 0,
      conversion_rate: cat.total_clicks > 0
        ? cat.total_attributed_conversions / cat.total_clicks
        : 0
    }));

    // Sort by revenue
    categoryData.sort((a, b) => b.total_attributed_revenue - a.total_attributed_revenue);

    return {
      data: categoryData,
      fromCache: result.ga4FromCache && result.gscFromCache
    };
  }

  // Get content opportunities (high traffic, low conversions)
  async getContentOpportunities(days = null) {
    const result = await this.combine(days);

    // Find queries with good traffic but poor conversions
    const opportunities = result.data.filter(row =>
      row.clicks >= 10 && // Has meaningful traffic
      row.attributed_revenue === 0 && // But no revenue
      row.position <= 10 // Good position
    );

    // Calculate opportunity score (potential improvement)
    opportunities.forEach(row => {
      // Score based on clicks * (1 - position/10)
      row.opportunity_score = row.clicks * (1 - row.position / 10);
    });

    // Sort by opportunity score
    opportunities.sort((a, b) => b.opportunity_score - a.opportunity_score);

    return {
      data: opportunities,
      fromCache: result.ga4FromCache && result.gscFromCache
    };
  }

  // Get page-level summary with all queries
  async getPageSummary(days = null) {
    const result = await this.combine(days);

    // Group by page
    const pages = {};
    for (const row of result.data) {
      if (!pages[row.page]) {
        pages[row.page] = {
          page: row.page,
          page_sessions: row.page_sessions,
          page_conversions: row.page_conversions,
          page_revenue: row.page_revenue,
          total_clicks: 0,
          total_impressions: 0,
          query_count: 0,
          top_queries: []
        };
      }

      const page = pages[row.page];
      page.total_clicks += row.clicks;
      page.total_impressions += row.impressions;
      page.query_count++;
      page.top_queries.push({
        query: row.query,
        clicks: row.clicks,
        impressions: row.impressions,
        position: row.position
      });
    }

    // Sort queries within each page and convert to array
    const pageData = Object.values(pages).map(page => {
      page.top_queries.sort((a, b) => b.clicks - a.clicks);
      page.top_queries = page.top_queries.slice(0, 10); // Top 10 queries
      return page;
    });

    // Sort pages by revenue
    pageData.sort((a, b) => b.page_revenue - a.page_revenue);

    return {
      data: pageData,
      fromCache: result.ga4FromCache && result.gscFromCache
    };
  }

  // Clear all caches
  clearCache() {
    const ga4Cleared = this.ga4.clearCache();
    const gscCleared = this.gsc.clearCache();
    return ga4Cleared + gscCleared;
  }

  // Get cache stats
  getCacheStats() {
    return {
      ga4: this.ga4.getCacheStats(),
      gsc: this.gsc.getCacheStats()
    };
  }
}

module.exports = { DataCombiner };
