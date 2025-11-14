# NetSuite SDF Deployment Workflow

## Overview

This document details the complete deployment workflow for NetSuite SDF projects using the `@twisted-x/netsuite-deploy` package. Understanding this workflow is essential for successful deployments and troubleshooting.

## Deployment Flow Diagram

```
┌─────────────────────────────────────────┐
│ START: npx twx-deploy deploy {env}      │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│ Step 1: Load & Validate Configuration   │
│ • Read twx-sdf.config.json              │
│ • Validate with Zod schema              │
│ • Extract environment config            │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│ Step 2: Resolve Credentials             │
│ • Certificate ID (via priority chain)   │
│ • Private key path (via priority chain) │
│ • CI passkey (optional)                 │
│ • Validate private key file exists      │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│ Step 3: Backup Config Files             │
│ • Copy .sdfcli.json → .sdfcli.json.bak  │
│ • Copy project.json → project.json.bak  │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│ Step 4: Update Config Files             │
│ • Set authId in .sdfcli.json            │
│ • Set defaultAuthId in project.json     │
│ • Verify changes written successfully   │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│ Step 5: Register AuthId (CI Mode)       │
│ • Execute: suitecloud account:setup:ci  │
│ • Handle "already registered" gracefully│
│ • Fail on other authentication errors   │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│ Step 6: Validate SDF Structure          │
│ • Check manifest.xml exists & valid     │
│ • Check deploy.xml exists & valid       │
│ • Validate project directory structure  │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│ Step 7: Optional Build Step             │
│ • If build.enabled && --build flag      │
│ • Execute build command                 │
│ • Verify build output                   │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│ Step 8: Execute Deployment              │
│ • Set SUITECLOUD_CI=1                   │
│ • Execute: suitecloud project:deploy    │
│ • Stream deployment output              │
│ • Capture exit code                     │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│ Step 9: Restore Config Files            │
│ • Restore .sdfcli.json from backup      │
│ • Restore project.json from backup      │
│ • ALWAYS runs (even on failure)         │
│ • Delete backup files                   │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│ END: Deployment Complete                │
│ • Exit code 0 = Success                 │
│ • Exit code 1 = Failure                 │
└─────────────────────────────────────────┘
```

## Step-by-Step Workflow

### Step 1: Load & Validate Configuration

**Purpose:** Load project configuration and validate structure

**Actions:**
1. Search for `twx-sdf.config.json` in current directory
2. Parse JSON content
3. Validate against Zod schema
4. Extract environment-specific configuration
5. Verify environment exists in config

**Error Handling:**
- Configuration file not found → Exit with error
- Invalid JSON syntax → Exit with parse error
- Schema validation failed → Exit with validation errors
- Environment not found → Exit with error

**Example:**
```bash
npx twx-deploy deploy sb1
# Loads environments.sb1 from config
```

### Step 2: Resolve Credentials

**Purpose:** Determine authentication credentials for deployment

**Actions:**
1. Resolve certificate ID via priority chain:
   - `TWX_SDF_{ENV}_CERT_ID` environment variable
   - `TWX_SDF_CERT_ID` environment variable
   - `environments.{env}.certificateId` from config
2. Resolve private key path via priority chain:
   - `TWX_SDF_{ENV}_PRIVATE_KEY_PATH` environment variable
   - `TWX_SDF_PRIVATE_KEY_PATH` environment variable
   - `environments.{env}.privateKeyPath` from config
   - Default: `/home/tchow/NetSuiteBundlet/SDF/keys/{authId}.pem`
3. Resolve optional CI passkey:
   - `TWX_SDF_CI_PASSKEY` environment variable
   - `TWX_SDF_{ENV}_CI_PASSKEY` environment variable
4. Validate private key file exists at resolved path

**Error Handling:**
- Certificate ID not found → Exit with error
- Private key file not found → Exit with error
- Invalid file permissions → Exit with error

**Example:**
```bash
export TWX_SDF_SB1_CERT_ID="abc123"
export TWX_SDF_SB1_PRIVATE_KEY_PATH="/path/to/key.pem"
npx twx-deploy deploy sb1
```

### Step 3: Backup Config Files

**Purpose:** Create backups for restoration after deployment

**Actions:**
1. Copy `.sdfcli.json` to `.sdfcli.json.bak`
2. Copy `project.json` to `project.json.bak` (if exists)
3. Verify backup files created successfully

**Error Handling:**
- File read error → Exit with error
- Write permission denied → Exit with error

**Files Backed Up:**
- `.sdfcli.json` (SuiteCloud CLI configuration)
- `project.json` (Legacy SDF configuration)

### Step 4: Update Config Files

**Purpose:** Set environment-specific authId for deployment

**Actions:**
1. Update `.sdfcli.json`:
   ```json
   {
     "authId": "environment-specific-auth-id"
   }
   ```
2. Update `project.json` (if exists):
   ```json
   {
     "defaultAuthId": "environment-specific-auth-id"
   }
   ```
3. Read files back to verify changes

**Error Handling:**
- Write failed → Exit with error
- Verification failed → Exit with error

**Dual Format Support:**
- Modern: `.sdfcli.json`
- Legacy: `project.json`
- Both updated for backward compatibility

### Step 5: Register AuthId (CI Mode)

**Purpose:** Register authentication credentials with SuiteCloud CLI

**Command:**
```bash
suitecloud account:setup:ci \
  --accountId {accountId} \
  --authId {authId} \
  --certId {certificateId} \
  --privateKeyPath {privateKeyPath}
```

**Actions:**
1. Set `SUITECLOUD_CI=1` environment variable
2. Add `--passkey` if CI passkey provided
3. Execute account:setup:ci command
4. Capture stdout and stderr
5. Parse output for success/failure

**Special Handling:**
- "Already registered" error → Log warning, continue
- Other errors → Fail deployment

**Error Handling:**
- Invalid credentials → Exit with error
- Network errors → Exit with error
- Permission errors → Exit with error
- Already registered → Continue (not an error)

### Step 6: Validate SDF Structure

**Purpose:** Verify SDF project structure before deployment

**Validation Checks:**
1. `manifest.xml` exists and is valid XML
2. `deploy.xml` exists and is valid XML
3. `src/` directory exists
4. Required object dependencies declared

**Optional:** Can be disabled with:
```json
{
  "deploy": {
    "validateBeforeDeploy": false
  }
}
```

**Error Handling:**
- Missing manifest.xml → Exit with error
- Invalid XML → Exit with parse error
- Missing dependencies → Exit with error

### Step 7: Optional Build Step

**Purpose:** Compile/transpile code before deployment

**Conditions:**
- `build.enabled` is `true` in config
- `--build` flag provided on command line

**Actions:**
1. Execute build command (default: `npm run build`)
2. Stream build output to console
3. Check build exit code
4. Verify output directory exists

**Configuration:**
```json
{
  "build": {
    "enabled": true,
    "command": "npm run build",
    "outputDir": "dist"
  }
}
```

**Error Handling:**
- Build command not found → Exit with error
- Build failed (non-zero exit) → Exit with error
- Output directory not created → Exit with error

**Example:**
```bash
npx twx-deploy deploy sb1 --build
```

### Step 8: Execute Deployment

**Purpose:** Deploy SDF project to NetSuite

**Command:**
```bash
SUITECLOUD_CI=1 suitecloud project:deploy
```

**Actions:**
1. Set `SUITECLOUD_CI=1` for non-interactive mode
2. Execute `suitecloud project:deploy`
3. Stream deployment output to console
4. Monitor for errors or warnings
5. Capture final exit code

**Deployment Options (from config):**
```json
{
  "deploy": {
    "accountSpecificValues": "ERROR|WARNING|IGNORE"
  }
}
```

**Error Handling:**
- Deployment failed → Exit with SuiteCloud exit code
- Network errors → Exit with error
- Permission errors → Exit with error

**Dry-Run Mode:**
```bash
npx twx-deploy deploy sb1 --dry-run
# Validates but doesn't deploy
```

### Step 9: Restore Config Files

**Purpose:** Return config files to original state

**Actions:**
1. Copy `.sdfcli.json.bak` back to `.sdfcli.json`
2. Copy `project.json.bak` back to `project.json` (if exists)
3. Delete backup files
4. Verify restoration successful

**Critical:** This step ALWAYS runs, even if:
- Deployment failed
- Validation failed
- Build failed
- Authentication failed

**Implementation:**
```typescript
try {
  // All deployment steps
} finally {
  await restoreConfigs(); // ALWAYS runs
}
```

**Error Handling:**
- Restoration failed → Log error but don't fail deployment
- Backup not found → Log warning

## Command Reference

### Basic Deployment
```bash
npx twx-deploy deploy {environment}
```

### Deployment with Build
```bash
npx twx-deploy deploy {environment} --build
```

### Dry-Run (Validation Only)
```bash
npx twx-deploy deploy {environment} --dry-run
```

### Multiple Environments
```bash
npx twx-deploy deploy sb1
npx twx-deploy deploy sb2
npx twx-deploy deploy prod
```

## Environment-Specific Behavior

### Sandbox Deployments (SB1, SB2, etc.)
- Less strict validation
- Faster iteration cycle
- Test mode enabled

### Production Deployments
- Full validation required
- Account-specific value handling: ERROR
- Recommended: manual approval gate in CI/CD

## Deployment Safety Features

### 1. Pre-Deployment Validation
- Configuration schema validation
- Credential verification
- Private key file existence check
- SDF structure validation

### 2. Fail-Fast Behavior
- Stop immediately on authentication errors
- Exit before making changes on validation errors
- Clear error messages for quick troubleshooting

### 3. Always-Restore Configs
- Config files restored even on failure
- Uses try/finally blocks
- Prevents accidental config pollution

### 4. Graceful Error Handling
- "Already registered" authIds handled safely
- Clear error messages with actionable solutions
- Non-zero exit codes for CI/CD integration

### 5. Dual Configuration Support
- Updates both modern and legacy formats
- Ensures backward compatibility
- Verifies both files after update

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | Deployment completed successfully |
| 1 | Configuration error | Fix twx-sdf.config.json |
| 1 | Credential error | Check environment variables or config |
| 1 | Validation error | Fix SDF project structure |
| 1 | Build error | Debug build command |
| 1 | Deployment error | Check SuiteCloud CLI output |

## Troubleshooting Common Issues

### Deployment Hangs
**Symptom:** Deployment doesn't progress
**Cause:** Interactive prompt in CI mode
**Solution:** Ensure `SUITECLOUD_CI=1` is set

### "Already Registered" Error
**Symptom:** AuthId registration fails
**Cause:** AuthId already in ~/.sdfcli.json
**Solution:** Safe to ignore - tool handles automatically

### Config Not Restored
**Symptom:** .sdfcli.json has wrong authId
**Cause:** Unexpected error in restoration
**Solution:** Manually restore from .sdfcli.json.bak

### Build Fails
**Symptom:** Build command exits with error
**Cause:** Build configuration or code error
**Solution:** Run build command manually to debug

### Validation Fails
**Symptom:** SDF structure validation error
**Cause:** Missing or invalid manifest.xml/deploy.xml
**Solution:** Fix SDF project structure

## Related Documentation

- Authentication reference: `authentication.md`
- Configuration reference: `configuration.md`
- CI/CD setup: `ci-cd-setup.md`
- Troubleshooting: `troubleshooting.md`
