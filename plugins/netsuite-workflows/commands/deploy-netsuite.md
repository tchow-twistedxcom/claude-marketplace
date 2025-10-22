---
name: deploy-netsuite
description: Deploy NetSuite SDF bundles to specified environment (sb2, production, etc.)
---

Execute the NetSuite SDF deployment script for bundles like Record Display app.

## Prerequisites

- NetSuite SDF CLI installed and configured
- Deployment script available at: `/home/tchow/NetSuiteBundlet/SDF/twx-sdf-deploy.sh`
- Valid NetSuite credentials configured for target environment
- Bundle project properly structured

## Usage

When the user requests NetSuite deployment:

### 1. Gather Deployment Information
- **Bundle Name**: Default is "Record Display" (or ask user)
- **Target Environment**: sb2, production, dev, etc. (ask user if not specified)
- **Deployment Type**: deploy, validate, list, etc.

### 2. Execute Deployment
```bash
/home/tchow/NetSuiteBundlet/SDF/twx-sdf-deploy.sh deploy "Record Display" --env sb2
```

### 3. Monitor Output
- Watch for compilation errors
- Check for validation warnings
- Verify successful deployment message
- Note any customization conflicts

### 4. Report Status
- **Success**: Confirm deployment completed, provide bundle version deployed
- **Warnings**: List any warnings encountered, suggest resolutions
- **Errors**: Provide error details, suggest troubleshooting steps

## Command Variations

### Standard Deployment
```bash
/home/tchow/NetSuiteBundlet/SDF/twx-sdf-deploy.sh deploy "Record Display" --env sb2
```

### Validate Before Deploy
```bash
/home/tchow/NetSuiteBundlet/SDF/twx-sdf-deploy.sh validate "Record Display" --env sb2
```

### List Available Bundles
```bash
/home/tchow/NetSuiteBundlet/SDF/twx-sdf-deploy.sh list
```

## Troubleshooting

### Common Issues

**Authentication Failure**
- Verify NetSuite credentials in SDF config
- Check environment configuration
- Ensure account access permissions

**Compilation Errors**
- Review SuiteScript syntax errors
- Check file dependencies
- Verify XML manifest structure

**Customization Conflicts**
- List conflicting customizations
- Suggest resolution strategy (overwrite, merge, skip)
- Document changes for review

## Examples

**User:** "Deploy Record Display to SB2"
**Action:** Execute deployment script with env=sb2, report results

**User:** "Validate the bundle before deploying"
**Action:** Run validate command, review warnings, confirm before deploy

**User:** "Deploy to production"
**Action:** Warn about production deployment, confirm twice, execute carefully
