/**
 * Cache Manager for Google Analytics Data
 * Per-account JSON file caching with TTL
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { accountManager, expandPath } = require('./account-manager');

class CacheManager {
  constructor(accountName = null) {
    const account = accountManager.getAccount(accountName);
    this.accountName = account.account_name;
    this.defaults = accountManager.getDefaults();
    this.outputConfig = accountManager.getOutputConfig();

    this.cacheDir = path.join(this.outputConfig.output_directory, 'cache', this.accountName);
    this.ensureCacheDir();
  }

  ensureCacheDir() {
    if (!fs.existsSync(this.cacheDir)) {
      fs.mkdirSync(this.cacheDir, { recursive: true });
    }
  }

  // Generate cache key from query parameters
  generateKey(type, params) {
    const normalized = JSON.stringify({
      type,
      ...params
    });
    const hash = crypto.createHash('md5').update(normalized).digest('hex').slice(0, 12);
    return `${type}_${hash}`;
  }

  // Get cache file path
  getCachePath(key) {
    return path.join(this.cacheDir, `${key}.json`);
  }

  // Get TTL in milliseconds for cache type
  getTTL(type) {
    const ttlHours = this.defaults.cache_ttl_hours;
    let hours;

    switch (type) {
      case 'gsc':
      case 'gsc_queries':
      case 'gsc_pages':
        hours = ttlHours.gsc || 24;
        break;
      case 'ga4_historical':
        hours = ttlHours.ga4_historical || 24;
        break;
      case 'ga4':
      case 'ga4_recent':
        hours = ttlHours.ga4_recent || 1;
        break;
      default:
        hours = 24;
    }

    return hours * 60 * 60 * 1000;
  }

  // Check if cache entry is valid (exists and not expired)
  isValid(key, type) {
    const cachePath = this.getCachePath(key);

    if (!fs.existsSync(cachePath)) {
      return false;
    }

    try {
      const stats = fs.statSync(cachePath);
      const age = Date.now() - stats.mtimeMs;
      const ttl = this.getTTL(type);

      return age < ttl;
    } catch (error) {
      return false;
    }
  }

  // Get cached data
  get(key, type) {
    if (!this.isValid(key, type)) {
      return null;
    }

    try {
      const cachePath = this.getCachePath(key);
      const content = fs.readFileSync(cachePath, 'utf8');
      const cached = JSON.parse(content);

      return cached.data;
    } catch (error) {
      return null;
    }
  }

  // Set cached data
  set(key, data, metadata = {}) {
    const cachePath = this.getCachePath(key);
    const cached = {
      account: this.accountName,
      cached_at: new Date().toISOString(),
      key,
      metadata,
      data
    };

    try {
      fs.writeFileSync(cachePath, JSON.stringify(cached, null, 2));
      return true;
    } catch (error) {
      console.error(`Cache write error: ${error.message}`);
      return false;
    }
  }

  // Get or fetch pattern - returns cached data or executes fetch function
  async getOrFetch(type, params, fetchFn) {
    const key = this.generateKey(type, params);

    // Try cache first
    const cached = this.get(key, type);
    if (cached) {
      return {
        data: cached,
        fromCache: true,
        cacheKey: key
      };
    }

    // Fetch fresh data
    const data = await fetchFn();

    // Cache the result
    this.set(key, data, { type, params });

    return {
      data,
      fromCache: false,
      cacheKey: key
    };
  }

  // Clear cache for this account
  clear() {
    const files = fs.readdirSync(this.cacheDir);
    let cleared = 0;

    for (const file of files) {
      if (file.endsWith('.json')) {
        fs.unlinkSync(path.join(this.cacheDir, file));
        cleared++;
      }
    }

    return cleared;
  }

  // Clear expired cache entries only
  clearExpired() {
    const files = fs.readdirSync(this.cacheDir);
    let cleared = 0;

    for (const file of files) {
      if (!file.endsWith('.json')) continue;

      const filePath = path.join(this.cacheDir, file);
      try {
        const content = fs.readFileSync(filePath, 'utf8');
        const cached = JSON.parse(content);
        const type = cached.metadata?.type || 'ga4';
        const key = file.replace('.json', '');

        if (!this.isValid(key, type)) {
          fs.unlinkSync(filePath);
          cleared++;
        }
      } catch (error) {
        // Remove corrupt files
        fs.unlinkSync(filePath);
        cleared++;
      }
    }

    return cleared;
  }

  // List cache entries
  list() {
    const files = fs.readdirSync(this.cacheDir);
    const entries = [];

    for (const file of files) {
      if (!file.endsWith('.json')) continue;

      const filePath = path.join(this.cacheDir, file);
      try {
        const stats = fs.statSync(filePath);
        const content = fs.readFileSync(filePath, 'utf8');
        const cached = JSON.parse(content);
        const type = cached.metadata?.type || 'ga4';

        entries.push({
          key: file.replace('.json', ''),
          type,
          cached_at: cached.cached_at,
          size_bytes: stats.size,
          valid: this.isValid(file.replace('.json', ''), type),
          params: cached.metadata?.params
        });
      } catch (error) {
        // Skip corrupt files
      }
    }

    return entries;
  }

  // Get cache stats
  stats() {
    const entries = this.list();
    const totalSize = entries.reduce((sum, e) => sum + e.size_bytes, 0);
    const validCount = entries.filter(e => e.valid).length;

    return {
      account: this.accountName,
      total_entries: entries.length,
      valid_entries: validCount,
      expired_entries: entries.length - validCount,
      total_size_bytes: totalSize,
      total_size_mb: (totalSize / (1024 * 1024)).toFixed(2),
      cache_directory: this.cacheDir
    };
  }
}

module.exports = { CacheManager };
