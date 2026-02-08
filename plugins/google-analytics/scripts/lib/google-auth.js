/**
 * Google API Authentication
 * Service account authentication with token caching
 */

const fs = require('fs');
const path = require('path');
const { accountManager, expandPath, CONFIG_DIR } = require('./account-manager');

// Token cache per account
const TOKEN_CACHE_DIR = path.join(CONFIG_DIR, 'tokens');

class GoogleAuth {
  constructor(accountName = null) {
    this.account = accountManager.getAccount(accountName);
    this.accountName = this.account.account_name;
    this.credentials = null;
    this.authClient = null;
    this.tokenCachePath = path.join(TOKEN_CACHE_DIR, `${this.accountName}-token.json`);

    this.ensureCacheDir();
  }

  ensureCacheDir() {
    if (!fs.existsSync(TOKEN_CACHE_DIR)) {
      fs.mkdirSync(TOKEN_CACHE_DIR, { recursive: true, mode: 0o700 });
    }
  }

  // Load service account credentials from JSON file
  loadCredentials() {
    if (this.credentials) return this.credentials;

    const credPath = this.account.credentials_path;
    if (!fs.existsSync(credPath)) {
      throw new Error(`Credentials file not found: ${credPath}\n\nSetup instructions:\n1. Go to console.cloud.google.com\n2. Create a service account\n3. Download JSON key\n4. Save to: ${credPath}`);
    }

    try {
      const content = fs.readFileSync(credPath, 'utf8');
      this.credentials = JSON.parse(content);
      return this.credentials;
    } catch (error) {
      throw new Error(`Failed to parse credentials file: ${error.message}`);
    }
  }

  // Get cached token if valid
  getCachedToken() {
    if (!fs.existsSync(this.tokenCachePath)) {
      return null;
    }

    try {
      const content = fs.readFileSync(this.tokenCachePath, 'utf8');
      const cached = JSON.parse(content);

      // Check expiration (with 5 minute buffer)
      const expiresAt = cached.acquired_at + (cached.expires_in * 1000);
      const bufferMs = 5 * 60 * 1000; // 5 minutes

      if (Date.now() + bufferMs >= expiresAt) {
        return null; // Token expired or about to expire
      }

      return cached;
    } catch (error) {
      return null;
    }
  }

  // Cache token to file
  cacheToken(token) {
    try {
      const cached = {
        access_token: token.access_token,
        token_type: token.token_type || 'Bearer',
        expires_in: token.expires_in || 3600,
        acquired_at: Date.now()
      };
      fs.writeFileSync(this.tokenCachePath, JSON.stringify(cached, null, 2), { mode: 0o600 });
      return cached;
    } catch (error) {
      console.error(`Warning: Failed to cache token: ${error.message}`);
      return token;
    }
  }

  // Get authenticated client for Google APIs
  async getAuthClient() {
    if (this.authClient) return this.authClient;

    // Check for cached token first
    const cached = this.getCachedToken();
    if (cached) {
      // Use cached token
      const { google } = require('googleapis');
      const auth = new google.auth.OAuth2();
      auth.setCredentials({
        access_token: cached.access_token,
        token_type: cached.token_type
      });
      this.authClient = auth;
      return this.authClient;
    }

    // Load credentials and create new client
    this.loadCredentials();

    const { google } = require('googleapis');
    const auth = new google.auth.GoogleAuth({
      credentials: this.credentials,
      scopes: [
        'https://www.googleapis.com/auth/analytics.readonly',
        'https://www.googleapis.com/auth/webmasters.readonly'
      ]
    });

    this.authClient = await auth.getClient();

    // Get and cache the access token
    const tokenResponse = await this.authClient.getAccessToken();
    if (tokenResponse.token) {
      this.cacheToken({
        access_token: tokenResponse.token,
        token_type: 'Bearer',
        expires_in: 3600 // Default 1 hour
      });
    }

    return this.authClient;
  }

  // Get GA4 Data API client
  async getGA4Client() {
    const { BetaAnalyticsDataClient } = require('@google-analytics/data');
    this.loadCredentials();

    return new BetaAnalyticsDataClient({
      credentials: this.credentials
    });
  }

  // Get Search Console API client
  async getGSCClient() {
    const { google } = require('googleapis');
    const auth = await this.getAuthClient();
    return google.searchconsole({ version: 'v1', auth });
  }

  // Get account info
  getAccountInfo() {
    return {
      name: this.accountName,
      display_name: this.account.name,
      ga4_property_id: this.account.ga4_property_id,
      gsc_site_url: this.account.gsc_site_url
    };
  }

  // Validate credentials can authenticate
  async validateAuth() {
    try {
      await this.getAuthClient();
      return { valid: true };
    } catch (error) {
      return {
        valid: false,
        error: error.message
      };
    }
  }

  // Clear cached token (force re-auth)
  clearCache() {
    if (fs.existsSync(this.tokenCachePath)) {
      fs.unlinkSync(this.tokenCachePath);
      return true;
    }
    return false;
  }
}

// Factory function to get auth for an account
async function getAuth(accountName = null) {
  return new GoogleAuth(accountName);
}

module.exports = { GoogleAuth, getAuth };
