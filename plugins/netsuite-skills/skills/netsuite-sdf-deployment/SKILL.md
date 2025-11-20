---
name: netsuite-sdf-deployment
description: Comprehensive expertise for NetSuite SuiteCloud Development Framework (SDF) deployment, CI/CD automation, certificate-based machine-to-machine authentication, authId management, and multi-environment deployment workflows. Use this skill when working with NetSuite SDF projects, setting up CI/CD pipelines, configuring TBA authentication, refreshing authIds, troubleshooting deployment errors, or managing SuiteCloud CLI operations across multiple NetSuite environments.
---

# NetSuite SDF Deployment Expert

## Overview

Provide specialized knowledge for **NetSuite SuiteCloud Development Framework (SDF)** deployment automation, focusing on the `@twisted-x/netsuite-deploy` package - a production-ready CLI tool for managing multi-environment NetSuite deployments with certificate-based machine-to-machine (M2M) authentication.

## When to Use This Skill

Activate this skill when:

- **Setting up SDF authentication:** Configuring certificate-based TBA (Token-Based Authentication) for M2M deployments
- **Managing authIds:** Understanding how authIds work, registering new ones, or refreshing existing ones
- **Deploying to NetSuite:** Executing deployments to sandbox or production environments
- **CI/CD setup:** Configuring GitHub Actions or other CI systems for automated NetSuite deployments
- **Troubleshooting deployments:** Debugging authentication errors, deployment failures, or configuration issues
- **Multi-environment management:** Working with multiple NetSuite accounts (SB1, SB2, production)
- **Configuration questions:** Understanding twx-sdf.config.json, credential resolution, or environment variables
- **SDF project structure:** Validating manifest.xml, deploy.xml, or SDF project organization

**Keywords that trigger this skill:**
- SDF, SuiteCloud, NetSuite deployment
- authId, certificate auth, TBA, machine-to-machine
- twx-deploy, @twisted-x/netsuite-deploy
- suitecloud CLI, account:setup:ci
- GitHub Actions, CI/CD pipeline
- Certificate ID, private key, .pem file
- Environment variables, credential resolution
- twx-sdf.config.json, .sdfcli.json, project.json
- Monorepo, multi-project, shared credentials, workspace
- PathResolver, ProjectContext, environment-specific paths

## Core Capabilities

### 1. Certificate-Based M2M Authentication

**Architecture:**
- **Type:** Certificate-Based Machine-to-Machine (M2M) with Token-Based Authentication (TBA)
- **Auth Flow:** X.509 self-signed certificates + private keys (PEM format)
- **Management:** Automatic authId registration via `suitecloud account:setup:ci`

**5 Key Authentication Layers:**

1. **M2M Auth Setup** - Automatic authId registration
2. **AuthId Management** - Dynamic environment-specific credential routing
3. **Certificate Auth** - X.509 certificates with private keys
4. **Credential Resolution** - Multi-layer priority chain
5. **CI Authentication** - CI mode with SUITECLOUD_CI=1 and passkey support

For detailed authentication architecture, see `references/authentication.md`.

**Credential Resolution Priority Chain:**

| Resource | Priority Order |
|----------|---------------|
| **Certificate ID** | Env-specific vars → Shared env vars → Config file → ERROR |
| **Private Key Path** | Env-specific vars → Shared env vars → Config file → Auto-path from authId → ERROR |
| **CI Passkey** | Global env var → Env-specific var → Optional (undefined) |

**Environment Variable Pattern:**
```bash
# Environment-specific (highest priority)
TWX_SDF_{ENV}_CERT_ID=your-cert-id
TWX_SDF_{ENV}_PRIVATE_KEY_PATH=/path/to/key.pem

# Shared across environments
TWX_SDF_CERT_ID=shared-cert-id
TWX_SDF_PRIVATE_KEY_PATH=/shared/path/key.pem

# CI-specific
TWX_SDF_CI_PASSKEY=your-ci-passkey
```

### 2. Configuration System

**Configuration File:** `twx-sdf.config.json`

See `assets/twx-sdf.config.example.json` for a complete template.

**Key Features:**
- Zod schema validation for type safety
- Multi-environment support (sb1, sb2, prod, etc.)
- Optional build integration
- Flexible credential resolution
- Environment variable interpolation

For comprehensive configuration documentation, see `references/configuration.md`.

### 3. Monorepo Support (v0.1.8+)

**Architecture:**
Multiple NetSuite projects sharing common code, credentials, and configuration in a single repository.

**Automatic Detection:**
- Walks up directory tree from project root
- Looks for `package.json` with `workspaces` field
- Creates ProjectContext with monorepo root information

**Shared Resources:**
```json
{
  "monorepo": {
    "sharedEnvPath": "SDF/.env",
    "sharedKeysPath": "SDF/keys",
    "sharedModules": [
      "SDF/shared/SuiteScripts/Common"
    ]
  }
}
```

**Environment-Specific Path Overrides:**
```json
{
  "environments": {
    "sb1": {
      "accountId": "1234567_SB1",
      "authId": "myapp-sb1",
      "sdfPath": "./sdf-sandbox"
    },
    "prod": {
      "accountId": "1234567",
      "authId": "myapp-prod",
      "sdfPath": "./sdf-production"
    }
  }
}
```

**Multi-Tier .env Resolution:**
1. Monorepo shared .env (via `monorepo.sharedEnvPath`)
2. Legacy shared .env (`~/NetSuiteBundlet/SDF/.env`)
3. Project .env (highest priority)

**Key Benefits:**
- ✅ Single source of truth for credentials
- ✅ DRY principle for shared SuiteScript modules
- ✅ Consistent deployment patterns across projects
- ✅ Environment-specific SDF directories
- ✅ Automatic credential and key path resolution

**Example Monorepo Structure:**
```
my-netsuite-monorepo/
├── package.json                   # Monorepo root (workspaces)
├── SDF/
│   ├── .env                      # Shared credentials
│   ├── keys/                     # Shared private keys
│   └── shared/                   # Shared SuiteScripts
├── apps/
│   ├── customer-portal/          # Project 1
│   │   ├── twx-sdf.config.json
│   │   └── sdf/
│   └── inventory-mgmt/           # Project 2
│       ├── twx-sdf.config.json
│       └── sdf/
└── packages/                     # Shared TypeScript packages
```

For comprehensive monorepo documentation, see the project's `MONOREPO.md` file.

### 4. Deployment Workflow

**Basic Commands:**
```bash
# Deploy to specific environment
npx twx-deploy deploy sb1
npx twx-deploy deploy sb2 --build
npx twx-deploy deploy prod --dry-run
```

**Deployment Flow (9 Steps):**
1. Load configuration from twx-sdf.config.json
2. Extract environment-specific config
3. Resolve credentials via multi-layer priority chain
4. Update .sdfcli.json and project.json with environment authId
5. Execute suitecloud account:setup:ci (safely handles "already registered")
6. Validate SDF structure (manifest.xml, deploy.xml)
7. Run optional build step
8. Deploy via suitecloud project:deploy with CI mode
9. Restore original config files (ALWAYS, even on failure)

For detailed deployment workflows, see `references/deployment-workflow.md`.

**Key Safety Features:**
- ⚠️ **Fail Closed:** Auth errors halt deployment (except "already registered")
- 📋 **Always Restore:** Config files restored even if deployment fails
- ✅ **Private Key Validation:** Checks file exists before deployment
- 🔄 **Graceful Deduplication:** "Already registered" authIds handled safely

### 5. AuthId Management & Automatic Credential Refresh

**What is an authId?**
- Unique identifier for a Token-Based Authentication (TBA) credential in NetSuite
- Contains **COMPLETE credentials**: accountId, certificateId, privateKeyPath, User/Role binding
- NOT just an alias - it's a **credential snapshot** stored in `~/.suitecloud-sdk/credentials_ci.p12`
- Registered with SuiteCloud CLI via `suitecloud account:setup:ci`

**Critical Understanding: Stale Credential Problem**

After NetSuite sandbox refresh or certificate rotation:
- ❌ Config updated with new certificate ID
- ❌ Cached credentials still have OLD certificate ID
- 🔥 Could deploy to wrong account (production instead of sandbox)

**Automatic Credential Refresh (v0.1.6+):**

The tool now **automatically detects and refreshes stale credentials**:

1. **Detects:** "Authentication ID already in use" error
2. **Backs up:** `credentials_ci.p12` → `credentials_ci.p12.backup`
3. **Removes:** Old credentials file
4. **Re-registers:** Fresh credentials from config
5. **Cleanup:** Removes backup on success
6. **Fail-safe:** Restores backup if refresh fails

**Expected Output:**
```
ℹ  AuthId exists - refreshing credentials to ensure they match config...
✓ Backed up existing credentials...
✓ Forcing fresh credential registration...
✓ CI authentication refreshed with updated credentials
```

**When Credential Refresh Happens:**
- ✅ Sandbox refresh from production (certificate ID changes)
- ✅ Certificate rotation (new certificate uploaded)
- ✅ Account ID changes (rare but possible)
- ✅ AuthId points to wrong credentials
- ✅ Moving between development machines

**Manual Refresh (if needed):**
```bash
# 1. Backup and remove credentials
cp ~/.suitecloud-sdk/credentials_ci.p12 ~/.suitecloud-sdk/credentials_ci.p12.backup
rm ~/.suitecloud-sdk/credentials_ci.p12

# 2. Re-deploy (triggers fresh registration)
npx twx-deploy deploy sb1

# 3. Remove backup if successful
rm ~/.suitecloud-sdk/credentials_ci.p12.backup
```

For comprehensive credential refresh guide, see `references/credential-refresh.md`.

For certificate generation and management, use `scripts/generate_cert.sh`.

### 6. CI/CD Integration

**GitHub Actions Template:**
See `assets/github-actions-template.yml` for a complete workflow example.

**Required Secrets:**
- `NETSUITE_CERT_ID` - Certificate ID for TBA
- `NETSUITE_PRIVATE_KEY` - Private key content (PEM format)
- `NETSUITE_CI_PASSKEY` - CI passkey for account:setup:ci

For comprehensive CI/CD setup guide, see `references/ci-cd-setup.md`.

### 7. Error Handling & Troubleshooting

**Common Errors:**
- "Auth ID already registered" - Safe to ignore
- "Private key not found" - Verify path and permissions
- "Invalid certificate ID" - Check NetSuite cert setup
- "Account ID mismatch" - Verify account ID
- "Validation failed" - Check SDF project structure

For complete troubleshooting guide, see `references/troubleshooting.md`.

## How to Use This Skill

### For Authentication Setup

1. Review `references/authentication.md` for architecture overview
2. Generate certificates if needed with `scripts/generate_cert.sh`
3. Configure credentials using environment variables or config file
4. Validate setup with dry-run deployment

### For Deployment Tasks

1. Load `references/deployment-workflow.md` for detailed process
2. Use `assets/twx-sdf.config.example.json` as configuration template
3. Execute deployment with appropriate environment
4. Troubleshoot using `references/troubleshooting.md`

### For CI/CD Setup

1. Review `references/ci-cd-setup.md` for complete guide
2. Use `assets/github-actions-template.yml` as starting point
3. Configure secrets in repository settings
4. Test workflow with manual dispatch

## Package Information

- **Package:** `@twisted-x/netsuite-deploy`
- **Version:** 0.1.8 (as of November 2025)
- **Node:** 18+, npm 9+
- **Type:** ESM Module
- **Registry:** GitHub Packages (Private)
- **Repository:** `/home/tchow/netsuite-deploy`

**Latest Features (v0.1.8):**
- ✅ **Monorepo Support:** Multi-project deployments with shared credentials and code
- ✅ **Automatic Monorepo Detection:** Discovers workspace roots automatically
- ✅ **Shared Resources:** Centralized credentials, keys, and SuiteScript modules
- ✅ **Environment-Specific Paths:** Per-environment SDF directory overrides
- ✅ **Context-Aware Path Resolution:** PathResolver handles single-project and monorepo scenarios
- ✅ Multi-tier .env resolution (monorepo → legacy → project)
- ✅ Automatic stale credential detection and refresh
- ✅ Post-sandbox-refresh credential validation
- ✅ Fail-safe backup/restore for credential operations
- ✅ Prevention of wrong-environment deployments

## Key Principles

1. **Safety First:** All deployments include validation gates and config restoration
2. **Environment Isolation:** Separate credentials and configs per environment
3. **Credential Security:** Multi-layer resolution with environment variables
4. **Automatic Recovery:** Config files always restored, even on failure
5. **CI-Native:** Designed for automated CI/CD workflows
6. **Type-Safe:** Zod schema validation for all configurations

## Bundled Resources

This skill includes comprehensive reference documentation and templates:

### scripts/
- `generate_cert.sh` - Generate self-signed certificates for NetSuite TBA

### references/
- `authentication.md` - Detailed authentication architecture and credential storage
- `configuration.md` - Complete configuration reference and schema
- `deployment-workflow.md` - Step-by-step deployment process
- `ci-cd-setup.md` - GitHub Actions and CI/CD integration guide
- `credential-refresh.md` - **NEW**: Stale credential detection and automatic refresh
- `troubleshooting.md` - Common errors and solutions (now includes stale credential scenarios)
- `api-reference.md` - Package API and programmatic usage

### assets/
- `twx-sdf.config.example.json` - Complete configuration file template
- `github-actions-template.yml` - GitHub Actions workflow template
- `env.example` - Environment variables template

---

**Note:** This skill focuses on the `@twisted-x/netsuite-deploy` package. For general SuiteCloud CLI operations not related to this package, consult official NetSuite documentation.
