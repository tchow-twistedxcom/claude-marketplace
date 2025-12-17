# NetSuite SDF Deployment Troubleshooting Guide

## Common Errors and Solutions

This guide provides comprehensive troubleshooting for common errors encountered when deploying NetSuite SDF projects.

## Authentication Errors

### 🔥 CRITICAL: "Invalid certificate ID" After Sandbox Refresh

**Full Error:**
```
Error: There was an error with the certificate ID used to authenticate.
Verify that certificate ID 4gS-fIf8L-4GTq6qQFZ5H6bRmwYTGbuIbF2qx0wF0nA is invalid...
```

**Symptom:**
- Config file has correct NEW certificate ID
- Deployment fails with OLD certificate ID in error message
- Occurs after NetSuite sandbox refresh from production
- Message says "AuthId already registered - using existing registration"

**Root Cause:**
AuthId has **stale cached credentials** in `~/.suitecloud-sdk/credentials_ci.p12`. When the authId was first registered, it captured the certificate ID at that time. After sandbox refresh, the certificate ID changed but the cached credentials still have the old value.

**CRITICAL SAFETY:**
This is NOT just a deployment failure - stale credentials could point to the **wrong account** (e.g., production instead of sandbox), causing catastrophic mis-deployment.

**Automatic Solution (v0.1.6+):**
✅ **Automatic credential refresh** - The tool now detects this and automatically:
1. Backs up `credentials_ci.p12`
2. Removes the file to clear stale credentials
3. Re-registers authId with fresh credentials from config
4. Restores backup if refresh fails

**Expected Output:**
```
ℹ  AuthId exists - refreshing credentials to ensure they match config...
✓ Backed up existing credentials...
✓ Forcing fresh credential registration...
✓ CI authentication refreshed with updated credentials
```

**Manual Solution (if automatic fails):**
```bash
# 1. Backup credentials
cp ~/.suitecloud-sdk/credentials_ci.p12 ~/.suitecloud-sdk/credentials_ci.p12.backup

# 2. Remove stale credentials
rm ~/.suitecloud-sdk/credentials_ci.p12

# 3. Re-register with fresh credentials
cd /path/to/sdf-project
npx twx-deploy deploy sb2  # Triggers fresh registration

# 4. If successful, remove backup
rm ~/.suitecloud-sdk/credentials_ci.p12.backup
```

**Why NOT to ignore:**
Unlike "Auth ID already registered" (which is safe), stale credentials are DANGEROUS:
- ❌ Could deploy to wrong account (production instead of sandbox)
- ❌ Could use wrong certificate (old/revoked certificate)
- ❌ Could have wrong permissions (stale user/role binding)

**Prevention:**
- Use separate authIds per environment (`myapp-sb1`, `myapp-prod`)
- Document sandbox refresh events and certificate changes
- Test with dry-run after sandbox refresh: `npx twx-deploy deploy sb2 --dry-run`

**See Also:**
- Complete guide: `references/credential-refresh.md`
- Understanding credential storage in CI mode

---

### "Auth ID already registered"

**Full Error:**
```
Error: Auth ID 'myapp-sb1' is already registered
```

**Cause:**
The authId is already present in `~/.suitecloud-sdk/credentials_ci.p12` from a previous registration.

**Solution (v0.1.6+):**
✅ **Automatic credential refresh** - Tool now refreshes credentials to ensure they match config.

**Solution (v0.1.5 and earlier):**
✅ **Safe to ignore** - The deployment tool handles this automatically and continues.

**Important Note:**
As of v0.1.6, the tool **refreshes credentials** instead of skipping setup. This ensures credentials are never stale.

**Prevention:**
None needed - this is now handled automatically with credential refresh.

---

### "Private key not found"

**Full Error:**
```
Error: Private key not found at path: /path/to/key.pem
```

**Cause:**
- Incorrect `privateKeyPath` in configuration
- File doesn't exist at specified path
- File permissions prevent access

**Solution:**
```bash
# 1. Verify file exists
ls -la /path/to/key.pem

# 2. Check file permissions
chmod 600 /path/to/key.pem

# 3. Verify path is absolute, not relative
# Bad:  ./keys/sb1.pem
# Good: /home/user/keys/sb1.pem
```

**Configuration Fix:**
```json
{
  "environments": {
    "sb1": {
      "privateKeyPath": "/absolute/path/to/key.pem"
    }
  }
}
```

**Environment Variable Override:**
```bash
export TWX_SDF_SB1_PRIVATE_KEY_PATH="/absolute/path/to/key.pem"
```

---

### "Invalid certificate ID"

**Full Error:**
```
Error: Certificate with ID 'abc123' not found in NetSuite
```

**Cause:**
- Certificate ID doesn't exist in NetSuite
- Certificate not uploaded to correct NetSuite account
- Typo in certificate ID

**Solution:**
```bash
# 1. Verify certificate in NetSuite
# Go to: Setup > Company > Setup Tasks > Manage Certificates
# Copy the exact Certificate ID

# 2. Update configuration
{
  "environments": {
    "sb1": {
      "certificateId": "exact-cert-id-from-netsuite"
    }
  }
}

# 3. Or use environment variable
export TWX_SDF_SB1_CERT_ID="exact-cert-id-from-netsuite"
```

---

### "Account ID mismatch"

**Full Error:**
```
Error: Account ID mismatch. Expected: 1234567, Got: 1234567_SB1
```

**Cause:**
Incorrect accountId format in configuration.

**Solution:**
```bash
# Check actual account ID in NetSuite
# Go to: Company > Setup > Company Information

# Correct format:
# Production: "1234567"
# Sandbox:    "1234567_SB1" or "1234567_SB2"
```

**Configuration Fix:**
```json
{
  "environments": {
    "sb1": {
      "accountId": "1234567_SB1",  // ✅ Include _SB1 for sandbox
      "authId": "myapp-sb1"
    },
    "prod": {
      "accountId": "1234567",  // ✅ No suffix for production
      "authId": "myapp-prod"
    }
  }
}
```

---

### "Permission denied reading private key"

**Full Error:**
```
Error: EACCES: permission denied, open '/path/to/key.pem'
```

**Cause:**
File permissions too restrictive or file owned by different user.

**Solution:**
```bash
# Fix permissions
chmod 600 /path/to/key.pem

# Verify ownership
ls -la /path/to/key.pem

# If owned by different user
sudo chown $USER:$USER /path/to/key.pem
chmod 600 /path/to/key.pem
```

---

## Configuration Errors

### "Configuration file not found"

**Full Error:**
```
Error: twx-sdf.config.json not found in current directory
```

**Cause:**
Running command from wrong directory or config file doesn't exist.

**Solution:**
```bash
# 1. Check current directory
pwd

# 2. List files
ls -la | grep twx-sdf

# 3. Navigate to project root
cd /path/to/project

# 4. Or initialize configuration
npx twx-deploy init
```

---

### "Invalid semantic version format"

**Full Error:**
```
Error: version must match format MAJOR.MINOR.PATCH (e.g., "1.0.0")
```

**Cause:**
Version in config doesn't follow semantic versioning.

**Solution:**
```json
{
  "version": "1.0.0"  // ✅ Must be MAJOR.MINOR.PATCH
}
```

**Invalid Examples:**
```json
"version": "1.0"     // ❌ Missing patch
"version": "1"       // ❌ Missing minor and patch
"version": "v1.0.0"  // ❌ No 'v' prefix
```

---

### "Missing required field"

**Full Error:**
```
Error: environments.sb1.authId is required
```

**Cause:**
Required configuration field is missing.

**Solution:**
```json
{
  "projectName": "My Project",     // ✅ Required
  "version": "1.0.0",              // ✅ Required
  "environments": {
    "sb1": {
      "accountId": "1234567_SB1",  // ✅ Required
      "authId": "myapp-sb1"        // ✅ Required
    }
  }
}
```

---

## Deployment Errors

### "Validation failed"

**Full Error:**
```
Error: SDF validation failed - manifest.xml not found
```

**Cause:**
SDF project structure is invalid or missing required files.

**Solution:**
```bash
# Check SDF structure
ls -la sdf/

# Required files:
sdf/
├── manifest.xml    # ✅ Must exist
├── deploy.xml      # ✅ Must exist
└── src/            # ✅ Must exist
    ├── FileCabinet/
    └── Objects/
```

**Disable Validation (not recommended):**
```json
{
  "deploy": {
    "validateBeforeDeploy": false
  }
}
```

---

### "Build failed"

**Full Error:**
```
Error: Build command exited with code 1
```

**Cause:**
Build command failed or build script has errors.

**Solution:**
```bash
# 1. Run build manually to debug
npm run build

# 2. Check build configuration
{
  "build": {
    "enabled": true,
    "command": "npm run build",  // ✅ Must be valid command
    "outputDir": "dist"
  }
}

# 3. Verify build script exists
cat package.json | grep build
```

---

### "Deployment hangs indefinitely"

**Symptom:**
Deployment runs but never completes.

**Cause:**
SuiteCloud CLI waiting for interactive input.

**Solution:**
```bash
# Ensure CI mode is enabled
export SUITECLOUD_CI=1

# Or verify tool sets it automatically
# (should be automatic with twx-deploy)
```

**Manual Test:**
```bash
# Test with dry-run first
npx twx-deploy deploy sb1 --dry-run
```

---

## CI/CD Errors

### "Secrets not available in workflow"

**Symptom:**
Environment variables are empty in CI.

**Cause:**
Secrets not configured or not accessible in workflow.

**Solution:**
```yaml
# ✅ Correct usage
env:
  TWX_SDF_CERT_ID: ${{ secrets.NETSUITE_CERT_ID }}

# ❌ Wrong - won't work in run
run: echo ${{ secrets.NETSUITE_CERT_ID }}
```

**Verify Secrets:**
1. Go to Repository Settings
2. Secrets and variables > Actions
3. Verify secret exists and is spelled correctly

---

### "Private key format invalid"

**Full Error:**
```
Error: Invalid PEM formatted message
```

**Cause:**
Private key in GitHub secret has incorrect format or line breaks.

**Solution:**
```bash
# When copying to GitHub secret, ensure:
# 1. Include -----BEGIN PRIVATE KEY-----
# 2. Include -----END PRIVATE KEY-----
# 3. Preserve line breaks
# 4. No extra whitespace

# Correct format:
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...
(more lines)
-----END PRIVATE KEY-----
```

---

## Network Errors

### "Connection timeout"

**Full Error:**
```
Error: connect ETIMEDOUT
```

**Cause:**
Network connectivity issues or NetSuite is down.

**Solution:**
```bash
# 1. Check NetSuite status
# Visit: https://status.netsuite.com

# 2. Test network connectivity
ping netsuite.com

# 3. Check proxy settings (if applicable)
echo $HTTP_PROXY
echo $HTTPS_PROXY

# 4. Retry deployment
npx twx-deploy deploy sb1
```

---

### "SSL certificate error"

**Full Error:**
```
Error: unable to verify the first certificate
```

**Cause:**
SSL certificate verification failed.

**Solution:**
```bash
# Not recommended for production:
export NODE_TLS_REJECT_UNAUTHORIZED=0

# Better: Update Node.js or system certificates
brew upgrade node  # macOS
sudo apt update && sudo apt upgrade nodejs  # Linux
```

---

## Debugging Tips

### Enable Debug Mode

```bash
# Enable detailed logging
DEBUG=twx-deploy:* npx twx-deploy deploy sb1

# SuiteCloud CLI debug mode
suitecloud project:deploy --log debug
```

### Check SuiteCloud CLI Version

```bash
# Verify SuiteCloud CLI is installed
suitecloud --version

# Update if outdated
npm install -g @oracle/suitecloud-cli@latest
```

### Validate Configuration

```bash
# Use dry-run to validate without deploying
npx twx-deploy deploy sb1 --dry-run

# This checks:
# ✅ Configuration file
# ✅ Credentials resolution
# ✅ Private key file existence
# ✅ SDF project structure
```

### Check File Permissions

```bash
# Config files
ls -la twx-sdf.config.json
chmod 644 twx-sdf.config.json

# Private key
ls -la /path/to/key.pem
chmod 600 /path/to/key.pem

# SDF files
ls -la sdf/manifest.xml
chmod 644 sdf/manifest.xml
```

### Review Logs

```bash
# Tool logs (if enabled)
cat ~/.twx-deploy/logs/latest.log

# SuiteCloud CLI logs
cat ~/.suitecl loud/logs/latest.log
```

## Error Message Reference

| Error Pattern | Category | Severity | Quick Fix |
|---------------|----------|----------|-----------|
| "already registered" | Authentication | Low | Ignore - automatic |
| "not found" | Configuration | High | Check paths |
| "permission denied" | File System | High | Fix permissions (chmod) |
| "invalid" | Validation | High | Check format/syntax |
| "mismatch" | Configuration | High | Verify values match NetSuite |
| "timeout" | Network | Medium | Retry or check connectivity |
| "failed" | Deployment | High | Check SDF structure |

## Getting Help

### 1. Check Documentation
- Authentication: `authentication.md`
- Configuration: `configuration.md`
- Workflow: `deployment-workflow.md`
- CI/CD: `ci-cd-setup.md`

### 2. Review Test Files
- Credential tests: `/home/tchow/netsuite-deploy/src/auth/credentials.test.ts`
- Config tests: `/home/tchow/netsuite-deploy/src/config/schema.test.ts`

### 3. Examine Source Code
- Credentials: `/home/tchow/netsuite-deploy/src/auth/credentials.ts`
- Deployment: `/home/tchow/netsuite-deploy/src/core/deployment.ts`
- CLI Manager: `/home/tchow/netsuite-deploy/src/core/sdfcli-manager.ts`

### 4. Check Package Documentation
- README: `/home/tchow/netsuite-deploy/README.md`
- Changelog: `/home/tchow/netsuite-deploy/CHANGELOG.md`
- Getting Started: `/home/tchow/netsuite-deploy/docs/GETTING_STARTED.md`

## Related Documentation

- Authentication reference: `authentication.md`
- Configuration reference: `configuration.md`
- Deployment workflow: `deployment-workflow.md`
- CI/CD setup: `ci-cd-setup.md`
