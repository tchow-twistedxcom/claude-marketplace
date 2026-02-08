/**
 * Google Search Console API Client
 * Wrapper for Search Console API with SEO focus
 */

const { GoogleAuth } = require('./google-auth');
const { CacheManager } = require('./cache-manager');
const { accountManager } = require('./account-manager');

class GSCClient {
  constructor(accountName = null) {
    this.auth = new GoogleAuth(accountName);
    this.cache = new CacheManager(accountName);
    this.account = this.auth.getAccountInfo();
    this.siteUrl = this.account.gsc_site_url;
    this.client = null;
    this.defaults = accountManager.getDefaults();
  }

  async getClient() {
    if (!this.client) {
      this.client = await this.auth.getGSCClient();
    }
    return this.client;
  }

  // Calculate date range
  getDateRange(days = null) {
    days = days || this.defaults.date_range_days;

    // GSC data has 2-3 day lag
    const endDate = new Date();
    endDate.setDate(endDate.getDate() - 3);

    const startDate = new Date(endDate);
    startDate.setDate(startDate.getDate() - days);

    return {
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0]
    };
  }

  // Run a search analytics query with pagination
  async query(options) {
    const client = await this.getClient();
    const dateRange = options.dateRange || this.getDateRange(options.days);

    const cacheParams = {
      siteUrl: this.siteUrl,
      ...dateRange,
      dimensions: options.dimensions,
      filters: options.filters
    };

    const result = await this.cache.getOrFetch('gsc', cacheParams, async () => {
      let allRows = [];
      let startRow = 0;
      const rowLimit = this.defaults.row_limit;
      let hasMore = true;

      while (hasMore) {
        const request = {
          siteUrl: this.siteUrl,
          requestBody: {
            startDate: dateRange.startDate,
            endDate: dateRange.endDate,
            dimensions: options.dimensions || ['query', 'page'],
            rowLimit: rowLimit,
            startRow: startRow
          }
        };

        // Add dimension filters if provided
        if (options.filters && options.filters.length > 0) {
          request.requestBody.dimensionFilterGroups = [{
            filters: options.filters
          }];
        }

        const response = await client.searchanalytics.query(request);

        if (response.data.rows && response.data.rows.length > 0) {
          allRows = allRows.concat(response.data.rows);

          if (response.data.rows.length === rowLimit) {
            startRow += rowLimit;
          } else {
            hasMore = false;
          }
        } else {
          hasMore = false;
        }
      }

      return this.parseResponse(allRows, options.dimensions);
    });

    return result;
  }

  // Parse GSC response into clean data
  parseResponse(rows, dimensions) {
    if (!rows || rows.length === 0) {
      return [];
    }

    return rows.map(row => {
      const obj = {};

      // Map dimensions to keys
      if (dimensions) {
        dimensions.forEach((dim, i) => {
          obj[dim] = row.keys[i] || '';
        });
      }

      // Add metrics
      obj.clicks = row.clicks || 0;
      obj.impressions = row.impressions || 0;
      obj.ctr = row.ctr || 0;
      obj.position = row.position || 0;

      return obj;
    });
  }

  // === Query Reports ===

  // Get all queries with clicks/impressions
  async getQueries(days = null, limit = null) {
    const result = await this.query({
      days,
      dimensions: ['query']
    });

    // Sort by clicks descending
    result.data.sort((a, b) => b.clicks - a.clicks);

    if (limit) {
      result.data = result.data.slice(0, limit);
    }

    return result;
  }

  // Get queries for a specific page
  async getQueriesForPage(page, days = null) {
    return this.query({
      days,
      dimensions: ['query'],
      filters: [{
        dimension: 'page',
        operator: 'equals',
        expression: page
      }]
    });
  }

  // Get queries with page data (for attribution)
  async getQueriesWithPages(days = null) {
    return this.query({
      days,
      dimensions: ['query', 'page']
    });
  }

  // === Page Reports ===

  // Get all pages performance
  async getPages(days = null, limit = null) {
    const result = await this.query({
      days,
      dimensions: ['page']
    });

    // Sort by clicks descending
    result.data.sort((a, b) => b.clicks - a.clicks);

    if (limit) {
      result.data = result.data.slice(0, limit);
    }

    return result;
  }

  // Get pages matching a pattern
  async getPagesMatching(pattern, days = null) {
    return this.query({
      days,
      dimensions: ['page'],
      filters: [{
        dimension: 'page',
        operator: 'contains',
        expression: pattern
      }]
    });
  }

  // === Device and Country Reports ===

  // Get queries by device
  async getQueriesByDevice(days = null) {
    return this.query({
      days,
      dimensions: ['query', 'device']
    });
  }

  // Get queries by country
  async getQueriesByCountry(days = null) {
    return this.query({
      days,
      dimensions: ['query', 'country']
    });
  }

  // Get device breakdown
  async getDeviceBreakdown(days = null) {
    return this.query({
      days,
      dimensions: ['device']
    });
  }

  // Get country breakdown
  async getCountryBreakdown(days = null) {
    return this.query({
      days,
      dimensions: ['country']
    });
  }

  // === Date Trend Reports ===

  // Get daily query trends
  async getDailyQueryTrends(days = null) {
    return this.query({
      days,
      dimensions: ['date']
    });
  }

  // Get query performance over time
  async getQueryTrend(query, days = null) {
    return this.query({
      days,
      dimensions: ['date'],
      filters: [{
        dimension: 'query',
        operator: 'equals',
        expression: query
      }]
    });
  }

  // === Opportunity Detection ===

  // Find high impression, low CTR opportunities
  async getOpportunities(days = null, options = {}) {
    const result = await this.getQueries(days);

    const minImpressions = options.minImpressions || 100;
    const maxCtr = options.maxCtr || 0.03; // 3%
    const maxPosition = options.maxPosition || 20;

    const opportunities = result.data.filter(row =>
      row.impressions >= minImpressions &&
      row.ctr < maxCtr &&
      row.position <= maxPosition
    );

    // Sort by impressions (potential impact)
    opportunities.sort((a, b) => b.impressions - a.impressions);

    return {
      ...result,
      data: opportunities
    };
  }

  // Find position improvement opportunities (rankings 4-20)
  async getPositionOpportunities(days = null) {
    const result = await this.getQueriesWithPages(days);

    const opportunities = result.data.filter(row =>
      row.position >= 4 &&
      row.position <= 20 &&
      row.impressions >= 50
    );

    // Sort by impressions (most impactful to improve)
    opportunities.sort((a, b) => b.impressions - a.impressions);

    return {
      ...result,
      data: opportunities
    };
  }

  // Find keyword cannibalization (multiple pages ranking for same query)
  async getCannibalization(days = null) {
    const result = await this.getQueriesWithPages(days);

    // Group by query
    const queryPages = {};
    for (const row of result.data) {
      if (!queryPages[row.query]) {
        queryPages[row.query] = [];
      }
      queryPages[row.query].push(row);
    }

    // Find queries with multiple pages
    const cannibalized = [];
    for (const [query, pages] of Object.entries(queryPages)) {
      if (pages.length >= 2) {
        // Sort pages by clicks
        pages.sort((a, b) => b.clicks - a.clicks);

        cannibalized.push({
          query,
          page_count: pages.length,
          total_clicks: pages.reduce((sum, p) => sum + p.clicks, 0),
          total_impressions: pages.reduce((sum, p) => sum + p.impressions, 0),
          pages: pages.map(p => ({
            page: p.page,
            clicks: p.clicks,
            impressions: p.impressions,
            position: p.position
          }))
        });
      }
    }

    // Sort by total impressions (most impactful to fix)
    cannibalized.sort((a, b) => b.total_impressions - a.total_impressions);

    return {
      ...result,
      data: cannibalized
    };
  }

  // === Utility Methods ===

  // Normalize page URL (remove domain for GA4 correlation)
  normalizePageUrl(url) {
    try {
      const parsed = new URL(url);
      return parsed.pathname + parsed.search;
    } catch (e) {
      // If parsing fails, try to extract path
      const match = url.match(/https?:\/\/[^/]+(\/.*)?/);
      return match ? match[1] || '/' : url;
    }
  }

  // Get normalized pages data (for GA4 joining)
  async getNormalizedPages(days = null) {
    const result = await this.getQueriesWithPages(days);

    // Normalize page URLs
    result.data = result.data.map(row => ({
      ...row,
      page_normalized: this.normalizePageUrl(row.page)
    }));

    return result;
  }

  // Clear cache
  clearCache() {
    return this.cache.clear();
  }

  // Get cache stats
  getCacheStats() {
    return this.cache.stats();
  }
}

module.exports = { GSCClient };
