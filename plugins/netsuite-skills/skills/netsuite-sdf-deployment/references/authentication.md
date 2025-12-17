# NetSuite SDF Authentication Architecture

## Overview

The `@twisted-x/netsuite-deploy` package implements certificate-based machine-to-machine (M2M) authentication for NetSuite SuiteCloud Development Framework (SDF) deployments. This document provides comprehensive details on the authentication architecture, flows, and implementation.

## Authentication Type

**Certificate-Based Machine-to-Machine (M2M) with Token-Based Authentication (TBA)**

- **Protocol:** X.509 self-signed certificates with private keys (PEM format)
- **Integration:** NetSuite Token-Based Authentication (TBA)
- **Management:** Automatic authId registration via SuiteCloud CLI
- **Mode:** CI-optimized with SUITECLOUD_CI=1 environment variable

## 5 Key Authentication Layers

### 1. M2M Auth Setup
Automatic authId registration eliminates manual setup steps:
- Executes `suitecloud account:setup:ci` automatically
- Safely handles "already registered" authId scenarios
- Fails deployment on authentication errors
- Validates certificate and key before registration

### 2. AuthId Management
Dynamic environment-specific credential routing:
- Separate authIds per environment (sb1, sb2, prod)
- Automatic selection based on deployment target
- Config file updates with environment-specific authId
- Restoration of original config after deployment

### 3. Certificate Auth
X.509 self-signed certificates with private keys:
- Certificate ID registered in NetSuite
- Private key stored as PEM file
- Asymmetric cryptography for secure authentication
- No password required in CI environments

### 4. Credential Resolution
Multi-layer priority chain for flexible deployment:
- Environment-specific variables (highest priority)
- Shared environment variables
- Configuration file values
- Default path conventions
- Clear error messages when credentials missing

### 5. CI Authentication
CI mode with passkey support:
- `SUITECLOUD_CI=1` enables non-interactive mode
- Optional CI passkey for additional security
- GitHub Actions secrets integration
- Secure credential handling in pipelines

## Authentication Flow (9 Steps)

```
┌─────────────────────────────────────────────────┐
│ 1. Load configuration from twx-sdf.config.json │
└───────────────────┬─────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────┐
│ 2. Extract environment-specific config          │
│    (e.g., "sb1", "sb2", "prod")                 │
└───────────────────┬─────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────┐
│ 3. Resolve credentials via priority chain:      │
│    • Certificate ID (certId)                    │
│    • Private key path (.pem file location)      │
│    • CI passkey (for automated environments)    │
└───────────────────┬─────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────┐
│ 4. Update .sdfcli.json and project.json         │
│    with environment-specific authId             │
└───────────────────┬─────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────┐
│ 5. Execute suitecloud account:setup:ci          │
│    (safely handles "already registered")        │
└───────────────────┬─────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────┐
│ 6. Validate SDF structure                       │
│    (manifest.xml, deploy.xml)                   │
└───────────────────┬─────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────┐
│ 7. Run optional build step                      │
└───────────────────┬─────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────┐
│ 8. Deploy via suitecloud project:deploy         │
│    with CI mode (SUITECLOUD_CI=1)               │
└───────────────────┬─────────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────┐
│ 9. Restore original config files                │
│    (ALWAYS, even on failure)                    │
└─────────────────────────────────────────────────┘
```

## Credential Resolution Priority Chain

### Certificate ID Resolution

**Priority Order:**
1. Environment-specific variable: `TWX_SDF_{ENV}_CERT_ID`
2. Shared environment variable: `TWX_SDF_CERT_ID`
3. Configuration file: `environments.{env}.certificateId`
4. **ERROR** if not found

**Example:**
```bash
# Highest priority - environment-specific
export TWX_SDF_SB1_CERT_ID="cert-id-sb1"

# Medium priority - shared
export TWX_SDF_CERT_ID="cert-id-shared"

# Lowest priority - config file
{
  "environments": {
    "sb1": {
      "certificateId": "cert-id-from-config"
    }
  }
}
```

### Private Key Path Resolution

**Priority Order:**
1. Environment-specific variable: `TWX_SDF_{ENV}_PRIVATE_KEY_PATH`
2. Shared environment variable: `TWX_SDF_PRIVATE_KEY_PATH`
3. Configuration file: `environments.{env}.privateKeyPath`
4. **Default path:** `/home/tchow/NetSuiteBundlet/SDF/keys/{authId}.pem`
5. **ERROR** if file doesn't exist at resolved path

**Example:**
```bash
# Highest priority - environment-specific
export TWX_SDF_SB1_PRIVATE_KEY_PATH="/custom/path/sb1.pem"

# Medium priority - shared
export TWX_SDF_PRIVATE_KEY_PATH="/shared/path/key.pem"

# Lower priority - config file
{
  "environments": {
    "sb1": {
      "privateKeyPath": "/path/from/config.pem"
    }
  }
}

# Lowest priority - default convention
# /home/tchow/NetSuiteBundlet/SDF/keys/my-sb1-auth.pem
```

### CI Passkey Resolution

**Priority Order:**
1. Global environment variable: `TWX_SDF_CI_PASSKEY`
2. Environment-specific variable: `TWX_SDF_{ENV}_CI_PASSKEY`
3. **Optional** (undefined if not provided)

**Example:**
```bash
# Global passkey (highest priority)
export TWX_SDF_CI_PASSKEY="global-passkey"

# Environment-specific passkey
export TWX_SDF_SB1_CI_PASSKEY="sb1-passkey"
```

## Credential Storage in CI Mode

### Browser Mode vs CI Mode

SuiteCloud CLI uses **completely different** authentication storage mechanisms depending on the mode:

| Aspect | Browser Mode | CI Mode (M2M) |
|--------|--------------|---------------|
| **Storage File** | `~/.suitecloud-sdk/credentials_browser_based.p12` | `~/.suitecloud-sdk/credentials_ci.p12` |
| **Additional Storage** | System keychain (macOS Keychain, GNOME Keyring, Windows Credential Manager) | **NONE** - file only |
| **Encryption** | System-managed | `SUITECLOUD_CI_PASSKEY` environment variable |
| **Management Command** | `suitecloud account:manageauth` | **Incompatible** - tries to access keychain |
| **Environment Variable** | None required | `SUITECLOUD_CI=1` required |
| **Use Case** | Interactive development | CI/CD pipelines, automation |

### CI Mode Credential Storage

**File Location:** `~/.suitecloud-sdk/credentials_ci.p12`

**What's Stored:**
When `suitecloud account:setup:ci` registers an authId, it stores **COMPLETE credentials**:
1. **accountId** - Which NetSuite account to deploy to
2. **certificateId** - Which certificate to use for authentication
3. **privateKeyPath** - Where the private key is located
4. **User/Role binding** - NetSuite user and role for the integration

**Critical Insight:**
An authId is NOT just an alias - it's a **complete credential snapshot**. This means:
- ✅ Once registered, the authId contains all authentication info
- ⚠️ Updating config doesn't update cached credentials
- 🔥 Stale credentials can point to wrong account/certificate

### Why account:manageauth Fails in CI Mode

If you try to use `suitecloud account:manageauth --remove authId` in CI mode:

```
Error: Secure storage is inaccessible
```

**This is EXPECTED and NORMAL** in CI mode because:
- `account:manageauth` is designed for browser-based authentication
- It tries to access the system keychain (which doesn't exist in CI environments)
- CI mode uses file-based storage (`credentials_ci.p12`) instead

**Solution:** Manipulate `credentials_ci.p12` file directly (backup → remove → re-register)

See `references/credential-refresh.md` for complete guide on credential refresh.

## Critical Files

### Core Authentication Module
**File:** `/home/tchow/netsuite-deploy/src/auth/credentials.ts` (139 lines)

**Responsibilities:**
- Multi-layer credential resolution
- Environment variable parsing
- Configuration file reading
- Default path generation
- Credential validation

**Key Functions:**
- `resolveCredentials(config, environment)` - Main resolution logic
- `getCertificateId(config, env)` - Certificate ID resolution
- `getPrivateKeyPath(config, env)` - Private key path resolution
- `getCIPasskey(env)` - CI passkey resolution

### Deployment Orchestration
**File:** `/home/tchow/netsuite-deploy/src/core/deployment.ts` (292 lines)

**Responsibilities:**
- Coordinates entire deployment flow
- Manages authentication setup
- Handles config file updates
- Ensures config restoration

**Key Functions:**
- `deploy(environment, options)` - Main deployment orchestrator
- `setupAuthentication(credentials)` - Auth setup wrapper
- `validateCredentials(credentials)` - Pre-deployment validation
- `restoreConfigs()` - Config restoration (always runs)

### SDF CLI Manager
**File:** `/home/tchow/netsuite-deploy/src/core/sdfcli-manager.ts` (165 lines)

**Responsibilities:**
- Manages .sdfcli.json and project.json
- Executes SuiteCloud CLI commands
- Handles "already registered" errors gracefully
- Validates file changes

**Key Functions:**
- `updateConfigs(authId, accountId)` - Update both config files
- `registerAuthId(credentials)` - Execute account:setup:ci
- `backupConfigs()` - Create config backups
- `restoreConfigs()` - Restore from backups

## Key Safety Features

### 1. Fail Closed
**Principle:** Authentication errors halt deployment immediately

**Implementation:**
- All auth errors throw exceptions
- Deployment stops before making changes
- Exception: "Already registered" errors (safe to continue)

**Example:**
```typescript
if (!certificateId) {
  throw new Error('Certificate ID not found in credentials');
}
```

### 2. Always Restore
**Principle:** Config files restored even if deployment fails

**Implementation:**
- try/finally blocks ensure restoration
- Backups created before modifications
- Restoration runs regardless of success/failure

**Example:**
```typescript
try {
  await updateConfigs(authId, accountId);
  await deploy();
} finally {
  await restoreConfigs(); // ALWAYS runs
}
```

### 3. Private Key Validation
**Principle:** Verify file exists before deployment

**Implementation:**
- File system check before auth setup
- Clear error messages for missing files
- Path validation in resolution logic

**Example:**
```typescript
if (!fs.existsSync(privateKeyPath)) {
  throw new Error(`Private key not found: ${privateKeyPath}`);
}
```

### 4. Graceful Deduplication
**Principle:** "Already registered" authIds are safe to continue

**Implementation:**
- Detect "already registered" error pattern
- Log warning instead of failing
- Continue with deployment

**Example:**
```typescript
if (error.message.includes('already registered')) {
  console.warn('AuthId already registered, continuing...');
  return; // Don't throw
}
throw error; // Other errors still fail
```

### 5. File Verification
**Principle:** Confirm config changes were written successfully

**Implementation:**
- Read files after writing
- Verify expected values present
- Throw if verification fails

**Example:**
```typescript
const config = JSON.parse(fs.readFileSync('.sdfcli.json'));
if (config.authId !== expectedAuthId) {
  throw new Error('Config verification failed');
}
```

## Test Coverage

**Test File:** `/home/tchow/netsuite-deploy/src/auth/credentials.test.ts` (335 lines)

**Coverage Scenarios:**
1. Basic credential resolution from environment config
2. Environment variable override behavior
3. Shared vs. project-specific credentials
4. Default key path resolution
5. CI passkey support (optional)
6. Error handling for missing credentials
7. Multiple environments in single config
8. Priority chain verification
9. File system mocking for tests
10. Environment restoration after tests

**Example Test:**
```typescript
describe('Certificate ID Resolution', () => {
  it('prefers environment-specific variable', () => {
    process.env.TWX_SDF_SB1_CERT_ID = 'env-specific';
    process.env.TWX_SDF_CERT_ID = 'shared';

    const certId = getCertificateId(config, 'sb1');
    expect(certId).toBe('env-specific');
  });
});
```

## Environment Variable Reference

### Required Variables

#### TWX_SDF_CERT_ID or TWX_SDF_{ENV}_CERT_ID
**Description:** NetSuite certificate ID for TBA
**Example:** `TWX_SDF_SB1_CERT_ID=abc123xyz`
**Required:** Yes (unless in config file)

#### TWX_SDF_PRIVATE_KEY_PATH or TWX_SDF_{ENV}_PRIVATE_KEY_PATH
**Description:** Path to private key PEM file
**Example:** `TWX_SDF_PRIVATE_KEY_PATH=/path/to/key.pem`
**Required:** Yes (unless in config file or using default path)

### Optional Variables

#### TWX_SDF_CI_PASSKEY
**Description:** CI passkey for account:setup:ci
**Example:** `TWX_SDF_CI_PASSKEY=mypasskey123`
**Required:** No (enhances security in CI)

#### SUITECLOUD_CI
**Description:** Enable SuiteCloud CLI CI mode
**Example:** `SUITECLOUD_CI=1`
**Required:** No (automatically set by tool)

## Best Practices

### 1. Use Environment-Specific Variables in CI
```yaml
env:
  TWX_SDF_SB1_CERT_ID: ${{ secrets.NETSUITE_SB1_CERT_ID }}
  TWX_SDF_PROD_CERT_ID: ${{ secrets.NETSUITE_PROD_CERT_ID }}
```

### 2. Store Private Keys Securely
```bash
# Bad: Hardcoded path in config
{
  "privateKeyPath": "/home/user/keys/prod.pem"
}

# Good: Environment variable
export TWX_SDF_PRIVATE_KEY_PATH="/secure/vault/prod.pem"
```

### 3. Separate Credentials Per Environment
```json
{
  "environments": {
    "sb1": {
      "authId": "myapp-sb1",
      "certificateId": "cert-sb1"
    },
    "prod": {
      "authId": "myapp-prod",
      "certificateId": "cert-prod"
    }
  }
}
```

### 4. Use Descriptive AuthIds
```bash
# Bad: Generic authIds
authId: "auth1", "auth2"

# Good: Descriptive authIds
authId: "myapp-sb1", "myapp-prod"
```

### 5. Validate Credentials Before Deployment
```bash
# Use dry-run to validate without deploying
npx twx-deploy deploy sb1 --dry-run
```

## Common Authentication Errors

### "Auth ID already registered"
**Cause:** AuthId exists in ~/.sdfcli.json
**Solution:** Safe to ignore - tool handles gracefully
**Prevention:** None needed - this is normal behavior

### "Private key not found"
**Cause:** Invalid privateKeyPath or missing file
**Solution:** Verify path and file permissions
**Prevention:** Use absolute paths, verify file exists

### "Invalid certificate ID"
**Cause:** Certificate ID not registered in NetSuite
**Solution:** Verify certificate setup in NetSuite
**Prevention:** Generate and register certificates properly

### "Account ID mismatch"
**Cause:** Wrong accountId in configuration
**Solution:** Check NetSuite account ID (Company > Setup)
**Prevention:** Copy account ID directly from NetSuite

### "Permission denied reading private key"
**Cause:** File permissions too restrictive
**Solution:** `chmod 600 /path/to/key.pem`
**Prevention:** Set proper permissions when generating keys

## Certificate Generation

Use the included script to generate self-signed certificates:

```bash
scripts/generate_cert.sh myapp-sb1
```

This creates:
- `myapp-sb1.pem` - Private key
- `myapp-sb1.crt` - Certificate (upload to NetSuite)

Upload the `.crt` file to NetSuite:
1. Setup > Company > Setup Tasks > Manage Certificates
2. Upload new certificate
3. Note the Certificate ID
4. Configure in twx-sdf.config.json

## Related Documentation

- Configuration reference: `configuration.md`
- Deployment workflow: `deployment-workflow.md`
- CI/CD setup: `ci-cd-setup.md`
- Troubleshooting: `troubleshooting.md`
