---
name: netsuite-setup
description: Set up NetSuite SDF project structure and configuration
---

Guide the user through NetSuite SDF project setup and configuration.

## Project Structure Setup

### 1. Initialize SDF Project
```bash
cd /path/to/project
suitecloud project:create -i
```

### 2. Configure Authentication
```bash
suitecloud account:setup
```
- Enter Account ID
- Provide Authentication Token
- Configure Role permissions

### 3. Project Structure
```
NetSuiteBundlet/SDF/
├── src/
│   ├── FileCabinet/         # File cabinet resources
│   ├── Objects/             # Custom objects (records, fields)
│   ├── SuiteScripts/        # JavaScript files
│   └── Templates/           # Email/PDF templates
├── manifest.xml             # Bundle manifest
├── deploy.xml               # Deployment configuration
└── twx-sdf-deploy.sh       # Deployment script
```

## Configuration Files

### manifest.xml
```xml
<manifest projecttype="ACCOUNTCUSTOMIZATION">
  <projectname>Record Display</projectname>
  <frameworkversion>1.0</frameworkversion>
</manifest>
```

### deploy.xml
Define deployment preferences:
- Object dependencies
- Deployment sequence
- Environment-specific settings

## Environment Configuration

### Supported Environments
- **dev**: Development sandbox
- **sb2**: Testing sandbox (SB2)
- **production**: Live NetSuite account

### Configure Environment
1. Create environment-specific config files
2. Store credentials securely (use environment variables)
3. Test connection: `suitecloud account:ci`

## Deployment Script Setup

The deployment script (`twx-sdf-deploy.sh`) should support:
- Multiple environments (--env flag)
- Bundle selection
- Validation before deployment
- Rollback capabilities

## Usage Workflow

1. **Initial Setup**: Run this command to guide setup
2. **Development**: Develop customizations locally
3. **Deployment**: Use `/deploy-netsuite` command
4. **Validation**: Test in sandbox before production

## Security Best Practices

1. **Never Commit Credentials**: Use environment variables or secure vaults
2. **Role-Based Access**: Limit deployment permissions
3. **Audit Logging**: Track all deployments
4. **Backup Before Deploy**: Always have rollback plan

## Examples

**User:** "Set up a new NetSuite project"
**Action:** Guide through project:create, account:setup, structure creation

**User:** "Configure SB2 environment"
**Action:** Set up environment-specific auth and configuration

**User:** "What's the correct project structure?"
**Action:** Display structure guide and create directories
