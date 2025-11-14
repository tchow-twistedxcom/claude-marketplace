# CI/CD Setup Guide for NetSuite SDF Deployments

## Overview

This guide covers setting up continuous integration and continuous deployment (CI/CD) for NetSuite SDF projects using GitHub Actions and the `@twisted-x/netsuite-deploy` package.

## Quick Start

1. Configure GitHub Secrets
2. Add GitHub Actions workflow file
3. Test with manual dispatch
4. Enable automated deployments

## GitHub Secrets Configuration

### Required Secrets

Navigate to: **Repository Settings > Secrets and variables > Actions**

#### NETSUITE_CERT_ID
**Description:** NetSuite certificate ID for TBA authentication
**Example Value:** `abc123xyz`
**How to get:**
1. NetSuite: Setup > Company > Setup Tasks > Manage Certificates
2. Note the Certificate ID after uploading your certificate

#### NETSUITE_PRIVATE_KEY
**Description:** Private key content (PEM format)
**Example Value:**
```
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...
(full key content)
-----END PRIVATE KEY-----
```
**How to get:**
1. Generate with `scripts/generate_cert.sh`
2. Copy entire contents of `.pem` file
3. Paste into GitHub secret

#### NETSUITE_CI_PASSKEY (Optional)
**Description:** CI passkey for additional security
**Example Value:** `mySecurePasskey123`
**Recommended:** Use for production deployments

### Environment-Specific Secrets (Multi-Environment)

For different credentials per environment:

- `NETSUITE_SB1_CERT_ID` - Sandbox 1 certificate ID
- `NETSUITE_SB1_PRIVATE_KEY` - Sandbox 1 private key
- `NETSUITE_SB2_CERT_ID` - Sandbox 2 certificate ID
- `NETSUITE_SB2_PRIVATE_KEY` - Sandbox 2 private key
- `NETSUITE_PROD_CERT_ID` - Production certificate ID
- `NETSUITE_PROD_PRIVATE_KEY` - Production private key

## GitHub Actions Workflow

See `assets/github-actions-template.yml` for a complete example.

### Basic Workflow Structure

```yaml
name: Deploy to NetSuite

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        type: choice
        options:
          - sb1
          - sb2
          - prod

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Install SuiteCloud CLI
        run: npm install -g @oracle/suitecloud-cli

      - name: Deploy to NetSuite
        env:
          TWX_SDF_CERT_ID: ${{ secrets.NETSUITE_CERT_ID }}
          TWX_SDF_PRIVATE_KEY_PATH: /tmp/key.pem
          TWX_SDF_CI_PASSKEY: ${{ secrets.NETSUITE_CI_PASSKEY }}
        run: |
          echo "${{ secrets.NETSUITE_PRIVATE_KEY }}" > /tmp/key.pem
          chmod 600 /tmp/key.pem
          npx twx-deploy deploy ${{ github.event.inputs.environment || 'sb1' }}
          rm /tmp/key.pem
```

### Automated Deployment Workflow

```yaml
name: Auto Deploy to Sandbox

on:
  push:
    branches:
      - main
      - develop

jobs:
  deploy-sandbox:
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Install SuiteCloud CLI
        run: npm install -g @oracle/suitecloud-cli

      - name: Determine environment
        id: env
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "environment=sb1" >> $GITHUB_OUTPUT
          else
            echo "environment=sb2" >> $GITHUB_OUTPUT
          fi

      - name: Deploy to NetSuite
        env:
          TWX_SDF_CERT_ID: ${{ secrets.NETSUITE_CERT_ID }}
          TWX_SDF_PRIVATE_KEY_PATH: /tmp/key.pem
          TWX_SDF_CI_PASSKEY: ${{ secrets.NETSUITE_CI_PASSKEY }}
        run: |
          echo "${{ secrets.NETSUITE_PRIVATE_KEY }}" > /tmp/key.pem
          chmod 600 /tmp/key.pem
          npx twx-deploy deploy ${{ steps.env.outputs.environment }} --build
          rm /tmp/key.pem
```

### Production Deployment with Approval

```yaml
name: Deploy to Production

on:
  workflow_dispatch:
    inputs:
      confirm:
        description: 'Type "DEPLOY" to confirm production deployment'
        required: true

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Validate confirmation
        run: |
          if [[ "${{ github.event.inputs.confirm }}" != "DEPLOY" ]]; then
            echo "❌ Deployment cancelled - confirmation not provided"
            exit 1
          fi

  deploy-production:
    needs: validate
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Install SuiteCloud CLI
        run: npm install -g @oracle/suitecloud-cli

      - name: Deploy to Production
        env:
          TWX_SDF_CERT_ID: ${{ secrets.NETSUITE_PROD_CERT_ID }}
          TWX_SDF_PRIVATE_KEY_PATH: /tmp/key.pem
          TWX_SDF_CI_PASSKEY: ${{ secrets.NETSUITE_CI_PASSKEY }}
        run: |
          echo "${{ secrets.NETSUITE_PROD_PRIVATE_KEY }}" > /tmp/key.pem
          chmod 600 /tmp/key.pem
          npx twx-deploy deploy prod --build
          rm /tmp/key.pem
```

## CI/CD Pipeline Architecture

### Multi-Stage Pipeline

```
┌─────────────────────┐
│   Code Push/PR      │
└──────────┬──────────┘
           │
    ┌──────▼─────┐
    │   Build    │
    │   & Test   │
    └──────┬─────┘
           │
    ┌──────▼─────────┐
    │  Deploy to SB2 │
    │  (Auto)        │
    └──────┬─────────┘
           │
    ┌──────▼─────────┐
    │  Merge to Main │
    └──────┬─────────┘
           │
    ┌──────▼─────────┐
    │  Deploy to SB1 │
    │  (Auto)        │
    └──────┬─────────┘
           │
    ┌──────▼─────────────┐
    │  Deploy to PROD    │
    │  (Manual Approval) │
    └────────────────────┘
```

## Environment Strategy

### Development → Sandbox 2 (SB2)
- **Trigger:** Push to `develop` branch
- **Frequency:** Automatic on every push
- **Purpose:** Active development testing

### Staging → Sandbox 1 (SB1)
- **Trigger:** Push to `main` branch
- **Frequency:** Automatic on merge
- **Purpose:** Pre-production validation

### Production → Production Account
- **Trigger:** Manual workflow dispatch
- **Frequency:** Manual approval required
- **Purpose:** Live environment

## Security Best Practices

### 1. Protect Secrets
```yaml
# ❌ Bad: Hardcoded secrets
env:
  TWX_SDF_CERT_ID: "abc123"

# ✅ Good: Use GitHub Secrets
env:
  TWX_SDF_CERT_ID: ${{ secrets.NETSUITE_CERT_ID }}
```

### 2. Temporary Key Files
```yaml
# ✅ Create temporary file
echo "${{ secrets.NETSUITE_PRIVATE_KEY }}" > /tmp/key.pem
chmod 600 /tmp/key.pem

# ✅ Always cleanup
rm /tmp/key.pem
```

### 3. Use Specific Permissions
```yaml
permissions:
  contents: read
  # Don't grant unnecessary permissions
```

### 4. Environment Protection
```yaml
environment: production  # Requires approval
```

### 5. Branch Protection
- Require pull request reviews
- Require status checks
- Restrict who can push to protected branches

## Monitoring & Notifications

### Slack Notifications

```yaml
- name: Notify Slack
  if: always()
  uses: slackapi/slack-github-action@v1
  with:
    webhook: ${{ secrets.SLACK_WEBHOOK }}
    payload: |
      {
        "text": "Deployment ${{ job.status }}: ${{ github.event.inputs.environment }}"
      }
```

### Email Notifications

Configure in: **Repository Settings > Notifications**

## Troubleshooting CI/CD Issues

### Authentication Fails in CI
**Symptom:** "Invalid credentials" error
**Solution:**
1. Verify secrets are set correctly
2. Check certificate is uploaded to NetSuite
3. Validate private key format (PEM)

### Deployment Hangs
**Symptom:** Workflow runs indefinitely
**Solution:**
1. Ensure `SUITECLOUD_CI=1` is set
2. Use `--dry-run` to test without deploying
3. Check SuiteCloud CLI version compatibility

### Private Key Permission Denied
**Symptom:** "Permission denied" reading key
**Solution:**
```bash
chmod 600 /tmp/key.pem  # Add before deployment
```

### Environment Variable Not Available
**Symptom:** Variables are empty/undefined
**Solution:**
```yaml
env:
  TWX_SDF_CERT_ID: ${{ secrets.NETSUITE_CERT_ID }}
  # Must be in env block, not run command
```

## Testing Your CI/CD Setup

### 1. Test Workflow Locally (with act)
```bash
# Install act
brew install act

# Run workflow
act workflow_dispatch -e event.json
```

### 2. Dry-Run Deployment
```yaml
run: npx twx-deploy deploy sb1 --dry-run
```

### 3. Manual Dispatch Test
1. Go to Actions tab
2. Select workflow
3. Click "Run workflow"
4. Choose environment
5. Monitor output

## Related Documentation

- Authentication reference: `authentication.md`
- Configuration reference: `configuration.md`
- Deployment workflow: `deployment-workflow.md`
- Troubleshooting: `troubleshooting.md`
