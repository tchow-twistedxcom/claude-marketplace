# NetSuite Deployment Scripts

This directory contains deployment automation scripts for NetSuite SDF projects.

## Main Deployment Script

**Location**: `/home/tchow/NetSuiteBundlet/SDF/twx-sdf-deploy.sh`

This script is referenced but stored outside the plugin for security and operational reasons.

### Usage

```bash
# Deploy to SB2 environment
/home/tchow/NetSuiteBundlet/SDF/twx-sdf-deploy.sh deploy "Record Display" --env sb2

# Validate before deployment
/home/tchow/NetSuiteBundlet/SDF/twx-sdf-deploy.sh validate "Record Display" --env sb2

# List available bundles
/home/tchow/NetSuiteBundlet/SDF/twx-sdf-deploy.sh list
```

### Supported Environments

- `sb2` - Testing sandbox (SB2)
- `production` - Live NetSuite account
- `dev` - Development sandbox

### Adding Custom Scripts

To add custom deployment scripts to this plugin:

1. Create script in this directory
2. Make executable: `chmod +x script-name.sh`
3. Update plugin.json to reference the script
4. Document usage in command markdown files

### Script Template

```bash
#!/bin/bash
#
# NetSuite Deployment Script Template
#

set -e  # Exit on error

BUNDLE_NAME="$1"
ENVIRONMENT="$2"

if [ -z "$BUNDLE_NAME" ] || [ -z "$ENVIRONMENT" ]; then
    echo "Usage: $0 <bundle-name> <environment>"
    exit 1
fi

# Your deployment logic here
echo "Deploying $BUNDLE_NAME to $ENVIRONMENT..."
```

## Integration with Plugin Commands

The `/deploy-netsuite` command automatically calls the main deployment script.
Use the command for guided deployments with error handling and validation.
