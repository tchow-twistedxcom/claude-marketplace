#!/usr/bin/env node
/**
 * Google Analytics Account Manager CLI
 * Manage multiple GA4/GSC account configurations
 */

const { AccountManager } = require('./lib/account-manager');
const { GoogleAuth } = require('./lib/google-auth');

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

// Format table output
function formatTable(data, columns) {
  if (!data || data.length === 0) {
    return 'No data';
  }

  // Calculate column widths
  const widths = {};
  columns.forEach(col => {
    widths[col] = col.length;
    data.forEach(row => {
      const value = String(row[col] ?? '');
      widths[col] = Math.max(widths[col], value.length);
    });
  });

  // Build header
  let output = columns.map(col => col.padEnd(widths[col])).join(' | ') + '\n';
  output += columns.map(col => '-'.repeat(widths[col])).join('-|-') + '\n';

  // Build rows
  data.forEach(row => {
    output += columns.map(col => String(row[col] ?? '').padEnd(widths[col])).join(' | ') + '\n';
  });

  return output;
}

// Commands
const commands = {
  list: async (args) => {
    const manager = new AccountManager();
    const accounts = manager.listAccounts();

    if (accounts.length === 0) {
      console.log('No accounts configured.');
      console.log('\nAdd an account with:');
      console.log('  google-accounts add --name myaccount --ga4 "properties/123456" --gsc "https://mysite.com" --credentials "~/.config/google/myaccount.json"');
      return;
    }

    console.log('\n=== Configured Accounts ===\n');
    console.log(formatTable(accounts.map(a => ({
      Name: a.name + (a.is_default ? ' *' : ''),
      'Display Name': a.display_name,
      'GA4 Property': a.ga4_property_id,
      'GSC Site': a.gsc_site_url
    })), ['Name', 'Display Name', 'GA4 Property', 'GSC Site']));

    console.log('* = default account\n');
  },

  add: async (args) => {
    const manager = new AccountManager();

    const name = args.flags.name;
    if (!name) {
      console.error('Error: --name is required');
      process.exit(1);
    }

    const options = {
      displayName: args.flags['display-name'] || name,
      description: args.flags.description || '',
      ga4PropertyId: args.flags.ga4 || args.flags['ga4-property'],
      gscSiteUrl: args.flags.gsc || args.flags['gsc-site'],
      credentialsPath: args.flags.credentials || args.flags['credentials-path'],
      setDefault: args.flags.default === true
    };

    if (!options.ga4PropertyId) {
      console.error('Error: --ga4 (GA4 property ID) is required');
      process.exit(1);
    }

    if (!options.gscSiteUrl) {
      console.error('Error: --gsc (GSC site URL) is required');
      process.exit(1);
    }

    if (!options.credentialsPath) {
      console.error('Error: --credentials (path to service account JSON) is required');
      process.exit(1);
    }

    try {
      manager.addAccount(name, options);
      console.log(`Account '${name}' added successfully.`);

      if (options.setDefault || manager.listAccountNames().length === 1) {
        console.log(`Set as default account.`);
      }
    } catch (error) {
      console.error(`Error: ${error.message}`);
      process.exit(1);
    }
  },

  update: async (args) => {
    const manager = new AccountManager();

    const name = args.flags.name || args._[0];
    if (!name) {
      console.error('Error: Account name is required');
      process.exit(1);
    }

    const options = {};
    if (args.flags['display-name']) options.displayName = args.flags['display-name'];
    if (args.flags.description) options.description = args.flags.description;
    if (args.flags.ga4) options.ga4PropertyId = args.flags.ga4;
    if (args.flags.gsc) options.gscSiteUrl = args.flags.gsc;
    if (args.flags.credentials) options.credentialsPath = args.flags.credentials;
    if (args.flags.default) options.setDefault = true;

    try {
      manager.updateAccount(name, options);
      console.log(`Account '${name}' updated successfully.`);
    } catch (error) {
      console.error(`Error: ${error.message}`);
      process.exit(1);
    }
  },

  remove: async (args) => {
    const manager = new AccountManager();

    const name = args.flags.name || args._[0];
    if (!name) {
      console.error('Error: Account name is required');
      process.exit(1);
    }

    try {
      manager.removeAccount(name);
      console.log(`Account '${name}' removed.`);
    } catch (error) {
      console.error(`Error: ${error.message}`);
      process.exit(1);
    }
  },

  'set-default': async (args) => {
    const manager = new AccountManager();

    const name = args.flags.name || args._[0];
    if (!name) {
      console.error('Error: Account name is required');
      process.exit(1);
    }

    try {
      manager.setDefault(name);
      console.log(`Default account set to '${name}'.`);
    } catch (error) {
      console.error(`Error: ${error.message}`);
      process.exit(1);
    }
  },

  validate: async (args) => {
    const manager = new AccountManager();

    const name = args.flags.name || args.flags.account || args._[0];

    try {
      // Validate config
      const validation = manager.validateAccount(name);

      if (!validation.valid) {
        console.log('Configuration errors:');
        validation.errors.forEach(e => console.log(`  - ${e}`));
        process.exit(1);
      }

      console.log('Configuration: OK\n');

      // Test authentication
      console.log('Testing authentication...');
      const auth = new GoogleAuth(name);
      const authResult = await auth.validateAuth();

      if (!authResult.valid) {
        console.log(`Authentication failed: ${authResult.error}`);
        process.exit(1);
      }

      console.log('Authentication: OK\n');

      const info = auth.getAccountInfo();
      console.log('Account details:');
      console.log(`  Name: ${info.name}`);
      console.log(`  GA4 Property: ${info.ga4_property_id}`);
      console.log(`  GSC Site: ${info.gsc_site_url}`);

    } catch (error) {
      console.error(`Error: ${error.message}`);
      process.exit(1);
    }
  },

  help: async () => {
    console.log(`
Google Analytics Account Manager

USAGE:
  google-accounts <command> [options]

COMMANDS:
  list                    List all configured accounts
  add                     Add a new account
  update                  Update an existing account
  remove                  Remove an account
  set-default             Set the default account
  validate                Validate account configuration and authentication

ADD OPTIONS:
  --name <name>           Account identifier (required)
  --display-name <name>   Human-readable name
  --description <text>    Account description
  --ga4 <property-id>     GA4 property ID (required, e.g., properties/123456)
  --gsc <site-url>        GSC site URL (required, e.g., https://mysite.com)
  --credentials <path>    Path to service account JSON (required)
  --default               Set as default account

UPDATE OPTIONS:
  --name <name>           Account to update (required)
  [any add option]        Fields to update

EXAMPLES:
  # Add production account
  google-accounts add \\
    --name production \\
    --display-name "Production Store" \\
    --ga4 "properties/123456789" \\
    --gsc "https://mystore.com" \\
    --credentials "~/.config/google/production.json" \\
    --default

  # Add staging account
  google-accounts add \\
    --name staging \\
    --ga4 "properties/987654321" \\
    --gsc "https://staging.mystore.com" \\
    --credentials "~/.config/google/staging.json"

  # Validate configuration
  google-accounts validate --name production

  # Set default
  google-accounts set-default staging

  # List accounts
  google-accounts list
`);
  }
};

// Main
async function main() {
  const args = parseArgs(process.argv.slice(2));
  const command = args._[0] || 'help';

  // Remove command from positional args
  args._ = args._.slice(1);

  if (!commands[command]) {
    console.error(`Unknown command: ${command}`);
    console.error('Run "google-accounts help" for usage.');
    process.exit(1);
  }

  try {
    await commands[command](args);
  } catch (error) {
    console.error(`Error: ${error.message}`);
    if (process.env.DEBUG) {
      console.error(error.stack);
    }
    process.exit(1);
  }
}

main();
