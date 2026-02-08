/**
 * Google Analytics Multi-Account Manager
 * Manages multiple GA4/GSC account configurations
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

// Expand ~ to home directory
function expandPath(filepath) {
  if (filepath.startsWith('~')) {
    return path.join(os.homedir(), filepath.slice(1));
  }
  return filepath;
}

// Default config path
const CONFIG_DIR = expandPath('~/.config/google-analytics');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');
const PLUGIN_CONFIG_TEMPLATE = path.join(__dirname, '../../config/google_config.template.json');

class AccountManager {
  constructor() {
    this.config = null;
    this.ensureConfigDir();
    this.loadConfig();
  }

  ensureConfigDir() {
    if (!fs.existsSync(CONFIG_DIR)) {
      fs.mkdirSync(CONFIG_DIR, { recursive: true, mode: 0o700 });
    }
  }

  loadConfig() {
    if (fs.existsSync(CONFIG_FILE)) {
      try {
        const content = fs.readFileSync(CONFIG_FILE, 'utf8');
        this.config = JSON.parse(content);
      } catch (error) {
        console.error(`Error loading config: ${error.message}`);
        this.config = this.getDefaultConfig();
      }
    } else {
      this.config = this.getDefaultConfig();
    }
  }

  getDefaultConfig() {
    // Load from template if available
    if (fs.existsSync(PLUGIN_CONFIG_TEMPLATE)) {
      try {
        const template = fs.readFileSync(PLUGIN_CONFIG_TEMPLATE, 'utf8');
        return JSON.parse(template);
      } catch (e) {
        // Fall through to default
      }
    }

    return {
      default_account: null,
      accounts: {},
      defaults: {
        date_range_days: 30,
        row_limit: 25000,
        cache_ttl_hours: {
          gsc: 24,
          ga4_historical: 24,
          ga4_recent: 1
        },
        retry: {
          max_attempts: 3,
          delay_ms: 2000,
          backoff_multiplier: 2
        }
      },
      output: {
        default_format: 'table',
        output_directory: expandPath('~/.cache/google-analytics')
      }
    };
  }

  saveConfig() {
    try {
      const content = JSON.stringify(this.config, null, 2);
      fs.writeFileSync(CONFIG_FILE, content, { mode: 0o600 });
      return true;
    } catch (error) {
      console.error(`Error saving config: ${error.message}`);
      return false;
    }
  }

  // Get account by name, or default account
  getAccount(accountName = null) {
    const name = accountName || this.config.default_account;

    if (!name) {
      throw new Error('No account specified and no default account configured. Run: google-accounts add --name <name>');
    }

    const account = this.config.accounts[name];
    if (!account) {
      throw new Error(`Account '${name}' not found. Available accounts: ${this.listAccountNames().join(', ') || 'none'}`);
    }

    // Expand credential path
    account.credentials_path = expandPath(account.credentials_path);
    account.account_name = name;

    return account;
  }

  // List all account names
  listAccountNames() {
    return Object.keys(this.config.accounts);
  }

  // List all accounts with details
  listAccounts() {
    const accounts = [];
    for (const [name, account] of Object.entries(this.config.accounts)) {
      accounts.push({
        name,
        display_name: account.name,
        description: account.description,
        ga4_property_id: account.ga4_property_id,
        gsc_site_url: account.gsc_site_url,
        credentials_path: account.credentials_path,
        is_default: name === this.config.default_account
      });
    }
    return accounts;
  }

  // Add a new account
  addAccount(name, options) {
    if (this.config.accounts[name]) {
      throw new Error(`Account '${name}' already exists. Use update or remove first.`);
    }

    this.config.accounts[name] = {
      name: options.displayName || name,
      description: options.description || '',
      ga4_property_id: options.ga4PropertyId,
      gsc_site_url: options.gscSiteUrl,
      credentials_path: options.credentialsPath
    };

    // Set as default if first account or explicitly requested
    if (Object.keys(this.config.accounts).length === 1 || options.setDefault) {
      this.config.default_account = name;
    }

    return this.saveConfig();
  }

  // Update an existing account
  updateAccount(name, options) {
    if (!this.config.accounts[name]) {
      throw new Error(`Account '${name}' not found.`);
    }

    const account = this.config.accounts[name];

    if (options.displayName) account.name = options.displayName;
    if (options.description) account.description = options.description;
    if (options.ga4PropertyId) account.ga4_property_id = options.ga4PropertyId;
    if (options.gscSiteUrl) account.gsc_site_url = options.gscSiteUrl;
    if (options.credentialsPath) account.credentials_path = options.credentialsPath;
    if (options.setDefault) this.config.default_account = name;

    return this.saveConfig();
  }

  // Remove an account
  removeAccount(name) {
    if (!this.config.accounts[name]) {
      throw new Error(`Account '${name}' not found.`);
    }

    delete this.config.accounts[name];

    // Clear default if removed account was default
    if (this.config.default_account === name) {
      const remaining = Object.keys(this.config.accounts);
      this.config.default_account = remaining.length > 0 ? remaining[0] : null;
    }

    return this.saveConfig();
  }

  // Set default account
  setDefault(name) {
    if (!this.config.accounts[name]) {
      throw new Error(`Account '${name}' not found.`);
    }
    this.config.default_account = name;
    return this.saveConfig();
  }

  // Get defaults
  getDefaults() {
    return this.config.defaults;
  }

  // Get output config
  getOutputConfig() {
    const output = { ...this.config.output };
    output.output_directory = expandPath(output.output_directory);
    return output;
  }

  // Validate account credentials exist
  validateAccount(name) {
    const account = this.getAccount(name);
    const errors = [];

    if (!account.ga4_property_id || account.ga4_property_id.includes('YOUR_')) {
      errors.push('GA4 property ID not configured');
    }

    if (!account.gsc_site_url || account.gsc_site_url.includes('yoursite')) {
      errors.push('GSC site URL not configured');
    }

    const credPath = expandPath(account.credentials_path);
    if (!fs.existsSync(credPath)) {
      errors.push(`Credentials file not found: ${credPath}`);
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }
}

// Export singleton instance and class
const accountManager = new AccountManager();
module.exports = { AccountManager, accountManager, expandPath, CONFIG_DIR };
