# NetSuite SDF Credential Refresh & Stale Credential Detection

## Critical Problem: Post-Sandbox-Refresh Deployment Failures

### The Issue

After a NetSuite sandbox refresh from production, certificate IDs change but the SuiteCloud CLI continues using **stale cached credentials** that point to the old certificate. This causes deployment failures with errors like:

```
Error: There was an error with the certificate ID used to authenticate.
Verify that certificate ID 4gS-fIf8L-4GTq6qQFZ5H6bRmwYTGbuIbF2qx0wF0nA is invalid...
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                         ❌ OLD CERTIFICATE - NOT IN CONFIG ANYMORE
```

Even though the configuration file (`twx-sdf.config.json`) has been updated with the new certificate ID, the tool continues using the old one from cached credentials.

### Why This Happens

#### Understanding AuthId Registration

When `suitecloud account:setup:ci` registers an authId, it stores **COMPLETE credentials** in `~/.suitecloud-sdk/credentials_ci.p12`:

1. **accountId** (which NetSuite account to deploy to)
2. **certificateId** (which certificate to use for authentication)
3. **privateKeyPath** (where the private key is located)
4. **User/Role binding** (NetSuite user and role for the integration)

**Critical Insight:** An authId is NOT just an alias - it's a **complete credential snapshot**. When the authId was first registered, it captured all these values. Even if you update your config file, the cached credentials in `credentials_ci.p12` still have the OLD values.

#### The "Already In Use" Trap

The previous implementation had this logic:

```typescript
if (errorMsg.includes('This authentication ID is already in use')) {
  console.log('AuthId already registered - skipping setup');
  return; // ❌ DANGER: Uses potentially stale credentials
}
```

This seemed safe - "the authId exists, so we're good to go." But this is **catastrophically wrong** because:

1. The authId might point to the **wrong certificate** (after sandbox refresh)
2. The authId might point to the **wrong account** (e.g., production instead of sandbox)
3. The authId might have **stale credentials** that no longer work

**Real-World Impact:** This led to a production incident where a deployment intended for SB2 actually deployed to production because the cached authId had production credentials.

## How CI Mode Credential Storage Works

### Browser Mode vs CI Mode

SuiteCloud CLI has two completely different authentication storage mechanisms:

| Aspect | Browser Mode | CI Mode (M2M) |
|--------|--------------|---------------|
| **Storage File** | `~/.suitecloud-sdk/credentials_browser_based.p12` | `~/.suitecloud-sdk/credentials_ci.p12` |
| **Additional Storage** | System keychain (macOS Keychain, GNOME Keyring, Windows Credential Manager) | **NONE** - file only |
| **Encryption** | System-managed | `SUITECLOUD_CI_PASSKEY` environment variable |
| **Management Command** | `suitecloud account:manageauth` | **Incompatible** - tries to access keychain |
| **Environment Variable** | None required | `SUITECLOUD_CI=1` |

### Why account:manageauth Fails in CI Mode

When you try to use `suitecloud account:manageauth --remove authId` in CI mode, you get:

```
Error: Secure storage is inaccessible
```

This is **EXPECTED and NORMAL** in CI mode because:
- `account:manageauth` is designed for browser-based authentication
- It tries to access the system keychain (which doesn't exist in CI environments)
- CI mode uses file-based storage (`credentials_ci.p12`) instead

**Important:** This is not a bug - it's by design. CI mode authentication is completely separate from browser-based authentication.

### credentials_ci.p12 File Structure

The `credentials_ci.p12` file:
- Location: `~/.suitecloud-sdk/credentials_ci.p12`
- Format: PKCS#12 encrypted file
- Encryption: Uses `SUITECLOUD_CI_PASSKEY` environment variable
- Contains: All registered authIds with their complete credentials
- Created by: `suitecloud account:setup:ci` command

## The Credential Refresh Solution

### Implementation Strategy

Since we can't use `account:manageauth --remove` in CI mode, we manipulate the `credentials_ci.p12` file directly:

1. **Backup** the credentials file
2. **Remove** the credentials file
3. **Re-register** with fresh credentials from config
4. **Restore backup** if refresh fails (fail-safe)

### Code Implementation

```typescript
private async setupCIAuthentication() {
  const spinner = ora('Setting up CI authentication...').start();
  const sdfPath = resolve(process.cwd(), this.options.config.paths.sdf);

  try {
    // Try to setup CI authentication
    await this.executeAccountSetupCI(sdfPath);
    spinner.succeed('CI authentication setup completed');
  } catch (error) {
    const errorMsg = (error as Error).message;

    // If authId is already registered, refresh credentials to ensure they match config
    if (errorMsg.includes('This authentication ID is already in use')) {
      spinner.info('AuthId exists - refreshing credentials to ensure they match config...');

      try {
        // SAFETY: Backup and remove credentials file to force fresh registration
        const credentialsPath = resolve(homedir(), '.suitecloud-sdk', 'credentials_ci.p12');
        const backupPath = credentialsPath + '.backup';

        if (existsSync(credentialsPath)) {
          copyFileSync(credentialsPath, backupPath);
          spinner.text = 'Backed up existing credentials...';

          unlinkSync(credentialsPath);
          spinner.text = 'Forcing fresh credential registration...';
        }

        // Re-register with fresh credentials from config
        await this.executeAccountSetupCI(sdfPath);
        spinner.succeed('CI authentication refreshed with updated credentials');

        // Clean up backup file on success
        if (existsSync(backupPath)) {
          unlinkSync(backupPath);
        }
      } catch (refreshError) {
        spinner.fail('Failed to refresh credentials');

        // SAFETY: Restore backup if refresh failed
        const credentialsPath = resolve(homedir(), '.suitecloud-sdk', 'credentials_ci.p12');
        const backupPath = credentialsPath + '.backup';
        if (existsSync(backupPath)) {
          copyFileSync(backupPath, credentialsPath);
          console.log(chalk.yellow('✓ Restored original credentials from backup'));
        }

        throw new Error(/* detailed error */);
      }

      return; // Successfully refreshed credentials
    }

    // For all other errors: CRITICAL SAFETY - Never continue if auth setup fails
    throw new Error(/* existing error handling */);
  }
}
```

### Why This Approach Works

1. **Forces Fresh Registration:** Removing `credentials_ci.p12` makes SuiteCloud CLI think no authIds are registered
2. **Uses Config Values:** Re-registration pulls certificateId, accountId, and privateKeyPath from current config
3. **Safe Failure Mode:** If refresh fails, backup is restored so nothing is lost
4. **No Manual Intervention:** Happens automatically during deployment

### Safety Features

🛡️ **CRITICAL SAFETY CHECKS:**

1. **Backup Before Remove:** Always create backup before deleting credentials file
2. **Restore on Failure:** If refresh fails, restore the backup automatically
3. **Fail-Safe Behavior:** Better to fail deployment than use wrong credentials
4. **Clear Error Messages:** Guides user on what went wrong and how to fix

## Common Scenarios

### Scenario 1: Sandbox Refresh from Production

**Problem:**
- SB2 sandbox refreshed from production
- SB2's old certificate ID: `4gS-fIf8L-4GTq6qQFZ5H6bRmwYTGbuIbF2qx0wF0nA`
- After refresh, SB2 now has production's certificate ID: `FJLhl7AtfNIFgz6RBtJ0OHsbRHBJAiWFRGDKymtuUAM`
- Config updated with new certificate ID
- Deployment fails with "invalid certificate" error

**Solution:**
1. Deployment detects authId is already registered
2. Automatically backs up `credentials_ci.p12`
3. Removes `credentials_ci.p12` to clear stale credentials
4. Re-registers authId with new certificate ID from config
5. Deployment proceeds with fresh credentials
6. Success - deployment uses correct certificate

### Scenario 2: Certificate Rotation

**Problem:**
- Security policy requires rotating certificates every 90 days
- New certificate generated and uploaded to NetSuite
- Config updated with new certificate ID and private key path
- Old authId registration still has old certificate

**Solution:**
- Same as Scenario 1 - automatic credential refresh
- No manual intervention required
- Deployment automatically picks up new certificate

### Scenario 3: Wrong Environment Deployment (PREVENTED)

**Problem:**
- Previous bug: SB2 authId had production credentials cached
- User runs `npx twx-deploy deploy sb2`
- Without refresh: Would deploy to production (catastrophic!)
- With refresh: Detects mismatch, refreshes credentials, deploys correctly

**Prevention:**
- Credential refresh ensures authId always matches config
- Config specifies correct accountId for each environment
- Stale credentials can't cause wrong-environment deployment

## Manual Credential Refresh (Advanced)

### When Manual Refresh is Needed

Normally the tool handles this automatically, but manual refresh may be needed when:
- Testing credential refresh behavior
- Debugging authentication issues
- Recovering from corrupted credentials file
- Migrating credentials between machines

### Manual Refresh Process

```bash
# 1. Backup existing credentials
cp ~/.suitecloud-sdk/credentials_ci.p12 ~/.suitecloud-sdk/credentials_ci.p12.backup

# 2. Remove credentials file
rm ~/.suitecloud-sdk/credentials_ci.p12

# 3. Re-register authId with current config
cd /path/to/sdf-project
suitecloud account:setup:ci \
  --authid myapp-sb1 \
  --account 1234567_SB1 \
  --certificateid new-cert-id \
  --privatekeypath /path/to/new-key.pem

# 4. Test deployment
npx twx-deploy deploy sb1 --dry-run

# 5. If successful, delete backup
rm ~/.suitecloud-sdk/credentials_ci.p12.backup
```

### Verify Credential Refresh

After refresh (automatic or manual), verify with:

```bash
# 1. Check credentials file exists
ls -la ~/.suitecloud-sdk/credentials_ci.p12

# 2. Test deployment with dry-run
npx twx-deploy deploy sb1 --dry-run

# 3. Verify config values are correct
cat twx-sdf.config.json | jq '.environments.sb1'
```

## Troubleshooting Credential Refresh

### "Failed to refresh credentials"

**Error:**
```
Failed to refresh CI authentication for authId "myapp-sb1".
Error: [specific error message]
```

**Causes:**
1. Certificate or private key is invalid
2. Account ID is incorrect
3. SUITECLOUD_CI_PASSKEY is missing or wrong
4. Network connectivity issues

**Solution:**
```bash
# 1. Verify certificate ID in NetSuite
# Go to: Setup > Company > Setup Tasks > Manage Certificates
# Copy exact Certificate ID

# 2. Verify private key file exists
ls -la /path/to/key.pem
cat /path/to/key.pem  # Should show -----BEGIN PRIVATE KEY-----

# 3. Verify account ID
# Go to: Company > Setup > Company Information
# Copy exact Account ID (include _SB1, _SB2 suffix for sandboxes)

# 4. Check SUITECLOUD_CI_PASSKEY (if used)
echo $SUITECLOUD_CI_PASSKEY  # Should not be empty

# 5. Test credentials manually
cd /path/to/sdf-project
suitecloud account:setup:ci \
  --authid test-auth \
  --account 1234567_SB1 \
  --certificateid cert-id \
  --privatekeypath /path/to/key.pem
```

### "Original credentials have been restored"

**Message:**
```
✓ Restored original credentials from backup
Original credentials have been restored. Please verify your config and try again.
```

**Meaning:**
- Credential refresh failed
- Backup was automatically restored
- Your original (stale) credentials are back in place
- Nothing was lost, but deployment still won't work

**Next Steps:**
1. Review error message for specific issue
2. Fix the underlying problem (cert ID, key path, account ID)
3. Update config with correct values
4. Try deployment again

### Backup File Left Behind

**Symptom:**
```bash
ls ~/.suitecloud-sdk/
credentials_ci.p12
credentials_ci.p12.backup  # ⚠️ Leftover backup
```

**Cause:**
- Credential refresh was interrupted
- Process was killed mid-refresh
- Cleanup step didn't run

**Solution:**
```bash
# Safe to delete if deployment is working
rm ~/.suitecloud-sdk/credentials_ci.p12.backup

# Or restore it if credentials are broken
mv ~/.suitecloud-sdk/credentials_ci.p12.backup ~/.suitecloud-sdk/credentials_ci.p12
```

## Best Practices

### 1. Document Sandbox Refresh Events

After a sandbox refresh, document:
- Date of refresh
- New certificate IDs
- Changes to accountId format (if any)
- Config updates made

### 2. Test After Sandbox Refresh

Always run a dry-run deployment after sandbox refresh:
```bash
npx twx-deploy deploy sb2 --dry-run
```

This triggers credential refresh without actually deploying.

### 3. Monitor Credential Files

Periodically check credentials file:
```bash
ls -la ~/.suitecloud-sdk/credentials_ci.p12
# Should exist and be recent if you've deployed recently
```

### 4. Keep Backups of Config

Before making credential changes:
```bash
cp twx-sdf.config.json twx-sdf.config.json.backup
# Then make your changes
```

### 5. Use Separate AuthIds Per Environment

```json
{
  "environments": {
    "sb1": {
      "authId": "myapp-sb1",  // ✅ Distinct per environment
      "accountId": "1234567_SB1",
      "certificateId": "sb1-cert-id"
    },
    "prod": {
      "authId": "myapp-prod",  // ✅ Never same as sandbox
      "accountId": "1234567",
      "certificateId": "prod-cert-id"
    }
  }
}
```

This prevents credential cross-contamination between environments.

## Safety Philosophy

### Prioritize Deployment Failure Over Wrong-Environment Deployment

The credential refresh implementation follows this principle:

**Better to have:**
- ❌ Deployment failure with clear error message
- ✅ User investigates, fixes config, tries again

**Never allow:**
- ✅ Deployment "succeeds" by using stale credentials
- ❌ Actually deploys to wrong account (production instead of sandbox)
- 🔥 Catastrophic data corruption or business impact

### Fail-Safe Design

Every step has a rollback path:
- Backup before remove → Restore on failure
- Clear error messages → Guide user to fix
- Halt deployment → Prevent wrong-environment deployment
- Preserve original state → Nothing lost on failure

## Related Documentation

- **Authentication Architecture:** `authentication.md`
- **Common Errors:** `troubleshooting.md`
- **Deployment Workflow:** `deployment-workflow.md`
- **CI/CD Setup:** `ci-cd-setup.md`

## Oracle Documentation References

- [Machine-to-Machine (M2M) Authentication for CI/CD](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/article_94164947835.html)
- [Execution Context for Secure Credentials Storage](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/article_0113125121.html)
- [Token-Based Authentication (TBA) Overview](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_4247337262.html)
