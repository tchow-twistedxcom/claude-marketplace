/**
 * GA4 Data API Client
 * Wrapper for Google Analytics 4 Data API with ecommerce focus
 */

const { GoogleAuth } = require('./google-auth');
const { CacheManager } = require('./cache-manager');
const { accountManager } = require('./account-manager');

class GA4Client {
  constructor(accountName = null) {
    this.auth = new GoogleAuth(accountName);
    this.cache = new CacheManager(accountName);
    this.account = this.auth.getAccountInfo();
    this.propertyId = this.account.ga4_property_id;
    this.client = null;
    this.defaults = accountManager.getDefaults();
  }

  async getClient() {
    if (!this.client) {
      this.client = await this.auth.getGA4Client();
    }
    return this.client;
  }

  // Calculate date range
  getDateRange(days = null) {
    days = days || this.defaults.date_range_days;

    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    return {
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0]
    };
  }

  // Determine cache type based on date range
  getCacheType(dateRange) {
    const endDate = new Date(dateRange.endDate);
    const now = new Date();
    const daysDiff = Math.floor((now - endDate) / (1000 * 60 * 60 * 24));

    // If end date is within last 7 days, use shorter cache
    return daysDiff <= 7 ? 'ga4_recent' : 'ga4_historical';
  }

  // Run a GA4 report
  async runReport(options) {
    const client = await this.getClient();
    const dateRange = options.dateRange || this.getDateRange(options.days);

    const request = {
      property: this.propertyId,
      dateRanges: [dateRange],
      dimensions: (options.dimensions || []).map(d => ({ name: d })),
      metrics: (options.metrics || []).map(m => ({ name: m })),
      limit: options.limit || this.defaults.row_limit
    };

    // Add dimension filter if provided
    if (options.dimensionFilter) {
      request.dimensionFilter = options.dimensionFilter;
    }

    // Add metric filter if provided
    if (options.metricFilter) {
      request.metricFilter = options.metricFilter;
    }

    // Add order by if provided
    if (options.orderBys) {
      request.orderBys = options.orderBys;
    }

    const cacheType = this.getCacheType(dateRange);
    const cacheParams = {
      property: this.propertyId,
      ...dateRange,
      dimensions: options.dimensions,
      metrics: options.metrics
    };

    const result = await this.cache.getOrFetch(cacheType, cacheParams, async () => {
      const [response] = await client.runReport(request);
      return this.parseResponse(response, options.dimensions, options.metrics);
    });

    return result;
  }

  // Parse GA4 response into clean data
  parseResponse(response, dimensions, metrics) {
    if (!response.rows || response.rows.length === 0) {
      return [];
    }

    return response.rows.map(row => {
      const obj = {};

      // Map dimensions
      if (dimensions) {
        dimensions.forEach((dim, i) => {
          obj[dim] = row.dimensionValues[i]?.value || '';
        });
      }

      // Map metrics
      if (metrics) {
        metrics.forEach((metric, i) => {
          const value = row.metricValues[i]?.value || '0';
          // Parse as number if numeric
          obj[metric] = /^[0-9.]+$/.test(value) ? parseFloat(value) : value;
        });
      }

      return obj;
    });
  }

  // === Ecommerce Reports ===

  // Get ecommerce overview
  async getEcommerceOverview(days = null) {
    return this.runReport({
      days,
      dimensions: [],
      metrics: [
        'sessions',
        'totalUsers',
        'transactions',
        'purchaseRevenue',
        'ecommercePurchases',
        'addToCarts',
        'checkouts'
      ]
    });
  }

  // Get landing page performance with conversions
  async getLandingPagePerformance(days = null) {
    return this.runReport({
      days,
      dimensions: ['landingPage'],
      metrics: [
        'sessions',
        'totalUsers',
        'bounceRate',
        'averageSessionDuration',
        'conversions',
        'purchaseRevenue',
        'transactions'
      ],
      orderBys: [{ metric: { metricName: 'sessions' }, desc: true }]
    });
  }

  // Get organic traffic landing pages (for GSC correlation)
  async getOrganicLandingPages(days = null) {
    return this.runReport({
      days,
      dimensions: ['landingPage'],
      metrics: [
        'sessions',
        'totalUsers',
        'newUsers',
        'bounceRate',
        'engagementRate',
        'averageSessionDuration',
        'conversions',
        'purchaseRevenue',
        'transactions'
      ],
      dimensionFilter: {
        filter: {
          fieldName: 'sessionMedium',
          stringFilter: { value: 'organic' }
        }
      },
      orderBys: [{ metric: { metricName: 'sessions' }, desc: true }]
    });
  }

  // Get traffic by source/medium
  async getTrafficSources(days = null) {
    return this.runReport({
      days,
      dimensions: ['sessionSource', 'sessionMedium'],
      metrics: [
        'sessions',
        'totalUsers',
        'bounceRate',
        'conversions',
        'purchaseRevenue'
      ],
      orderBys: [{ metric: { metricName: 'sessions' }, desc: true }]
    });
  }

  // Get conversion funnel
  async getConversionFunnel(days = null) {
    return this.runReport({
      days,
      dimensions: [],
      metrics: [
        'sessions',
        'addToCarts',
        'checkouts',
        'ecommercePurchases',
        'transactions',
        'purchaseRevenue'
      ]
    });
  }

  // Get product category performance (if available)
  async getProductCategoryPerformance(days = null) {
    return this.runReport({
      days,
      dimensions: ['itemCategory'],
      metrics: [
        'itemsViewed',
        'itemsAddedToCart',
        'itemsPurchased',
        'itemRevenue'
      ],
      orderBys: [{ metric: { metricName: 'itemRevenue' }, desc: true }]
    });
  }

  // Get device breakdown
  async getDeviceBreakdown(days = null) {
    return this.runReport({
      days,
      dimensions: ['deviceCategory'],
      metrics: [
        'sessions',
        'totalUsers',
        'conversions',
        'purchaseRevenue',
        'transactions'
      ],
      orderBys: [{ metric: { metricName: 'sessions' }, desc: true }]
    });
  }

  // Get daily trends
  async getDailyTrends(days = null) {
    return this.runReport({
      days,
      dimensions: ['date'],
      metrics: [
        'sessions',
        'totalUsers',
        'conversions',
        'purchaseRevenue',
        'transactions'
      ],
      orderBys: [{ dimension: { dimensionName: 'date' }, desc: false }]
    });
  }

  // Get new vs returning users
  async getNewVsReturning(days = null) {
    return this.runReport({
      days,
      dimensions: ['newVsReturning'],
      metrics: [
        'sessions',
        'totalUsers',
        'conversions',
        'purchaseRevenue',
        'transactions',
        'bounceRate'
      ]
    });
  }

  // Get geographic breakdown
  async getGeography(days = null) {
    return this.runReport({
      days,
      dimensions: ['country'],
      metrics: [
        'sessions',
        'totalUsers',
        'conversions',
        'purchaseRevenue'
      ],
      orderBys: [{ metric: { metricName: 'purchaseRevenue' }, desc: true }]
    });
  }

  // === Utility Methods ===

  // Clear cache
  clearCache() {
    return this.cache.clear();
  }

  // Get cache stats
  getCacheStats() {
    return this.cache.stats();
  }
}

module.exports = { GA4Client };
