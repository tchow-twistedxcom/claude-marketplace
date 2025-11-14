# NetSuite SDF Configuration Reference

## Configuration File: twx-sdf.config.json

The `twx-sdf.config.json` file is the central configuration for multi-environment NetSuite SDF deployments. It defines project metadata, environment-specific settings, build options, and deployment preferences.

## Complete Configuration Schema

```json
{
  "projectName": "string (required)",
  "version": "string (required, semantic version)",
  "environments": {
    "[environment-name]": {
      "accountId": "string (required)",
      "authId": "string (required)",
      "certificateId": "string (optional)",
      "privateKeyPath": "string (optional)"
    }
  },
  "build": {
    "enabled": "boolean (optional, default: false)",
    "command": "string (optional)",
    "outputDir": "string (optional)"
  },
  "paths": {
    "sdf": "string (optional, default: ./sdf)"
  },
  "deploy": {
    "accountSpecificValues": "ERROR|WARNING|IGNORE (optional, default: ERROR)",
    "validateBeforeDeploy": "boolean (optional, default: true)"
  }
}
```

## Field Reference

### Root Level Fields

#### projectName (required)
**Type:** String
**Description:** Unique identifier for the project
**Example:** `"My NetSuite Project"`
**Best Practice:** Use descriptive, human-readable names

#### version (required)
**Type:** String (Semantic Version)
**Description:** Project version following semantic versioning (MAJOR.MINOR.PATCH)
**Example:** `"1.0.0"`, `"2.1.3"`
**Validation:** Must match pattern `^\d+\.\d+\.\d+$`

### environments (required)

Configuration for each deployment environment (sb1, sb2, prod, etc.)

#### environments.{env}.accountId (required)
**Type:** String
**Description:** NetSuite account ID
**Example:**
- Production: `"1234567"`
- Sandbox: `"1234567_SB1"`, `"1234567_SB2"`
**Best Practice:** Copy directly from NetSuite (Company > Setup)

#### environments.{env}.authId (required)
**Type:** String
**Description:** Token-Based Authentication (TBA) identifier
**Example:** `"myapp-sb1"`, `"myapp-prod"`
**Best Practice:** Use descriptive format `{project}-{env}`

#### environments.{env}.certificateId (optional)
**Type:** String
**Description:** NetSuite certificate ID for TBA
**Example:** `"abc123xyz"`
**Default:** Resolved from environment variables
**Best Practice:** Use environment variables in CI/CD

#### environments.{env}.privateKeyPath (optional)
**Type:** String
**Description:** Path to private key PEM file
**Example:** `"/path/to/keys/sb1.pem"`
**Default:** `/home/tchow/NetSuiteBundlet/SDF/keys/{authId}.pem`
**Best Practice:** Use environment variables for security

### build (optional)

Build configuration for pre-deployment compilation

#### build.enabled (optional)
**Type:** Boolean
**Default:** `false`
**Description:** Enable build step before deployment
**Example:** `true`

#### build.command (optional)
**Type:** String
**Default:** `"npm run build"`
**Description:** Command to execute for building
**Example:** `"npm run build"`, `"gulp build"`

#### build.outputDir (optional)
**Type:** String
**Default:** `"dist"`
**Description:** Build output directory
**Example:** `"dist"`, `"build"`, `"out"`

### paths (optional)

Project path configuration

#### paths.sdf (optional)
**Type:** String
**Default:** `"./sdf"`
**Description:** Path to SDF project directory
**Example:** `"./sdf"`, `"./src/sdf"`

### deploy (optional)

Deployment behavior configuration

#### deploy.accountSpecificValues (optional)
**Type:** Enum: `"ERROR"` | `"WARNING"` | `"IGNORE"`
**Default:** `"ERROR"`
**Description:** How to handle account-specific values during deployment
- `"ERROR"` - Fail deployment if account-specific values detected
- `"WARNING"` - Warn but continue deployment
- `"IGNORE"` - Silently ignore account-specific values

#### deploy.validateBeforeDeploy (optional)
**Type:** Boolean
**Default:** `true`
**Description:** Run SDF validation before deployment
**Example:** `true`

## Example Configurations

### Minimal Configuration

```json
{
  "projectName": "My SDF Project",
  "version": "1.0.0",
  "environments": {
    "sb1": {
      "accountId": "1234567_SB1",
      "authId": "myproject-sb1"
    }
  }
}
```

### Production-Ready Configuration

```json
{
  "projectName": "Enterprise NetSuite Bundle",
  "version": "2.1.0",
  "environments": {
    "sb1": {
      "accountId": "1234567_SB1",
      "authId": "enterprise-sb1",
      "certificateId": "cert-sb1-abc",
      "privateKeyPath": "/secure/keys/sb1.pem"
    },
    "sb2": {
      "accountId": "1234567_SB2",
      "authId": "enterprise-sb2",
      "certificateId": "cert-sb2-xyz"
    },
    "prod": {
      "accountId": "1234567",
      "authId": "enterprise-prod",
      "certificateId": "cert-prod-123",
      "privateKeyPath": "/secure/keys/prod.pem"
    }
  },
  "build": {
    "enabled": true,
    "command": "npm run build",
    "outputDir": "dist"
  },
  "paths": {
    "sdf": "./sdf"
  },
  "deploy": {
    "accountSpecificValues": "ERROR",
    "validateBeforeDeploy": true
  }
}
```

### CI/CD Configuration (with environment variables)

```json
{
  "projectName": "Automated Deployment",
  "version": "1.5.0",
  "environments": {
    "sb1": {
      "accountId": "1234567_SB1",
      "authId": "auto-sb1"
    },
    "prod": {
      "accountId": "1234567",
      "authId": "auto-prod"
    }
  },
  "build": {
    "enabled": true
  },
  "deploy": {
    "validateBeforeDeploy": true
  }
}
```

**Note:** Certificate ID and private key path resolved from environment variables:
```bash
export TWX_SDF_SB1_CERT_ID="cert-id"
export TWX_SDF_SB1_PRIVATE_KEY_PATH="/path/to/key.pem"
```

## Environment Variable Integration

Configuration values can be overridden or supplemented with environment variables:

### Certificate ID Override
```bash
# Environment-specific (highest priority)
export TWX_SDF_SB1_CERT_ID="cert-override"

# Shared (medium priority)
export TWX_SDF_CERT_ID="cert-shared"

# Config file (lowest priority)
{
  "environments": {
    "sb1": {
      "certificateId": "cert-from-config"
    }
  }
}
```

### Private Key Path Override
```bash
# Environment-specific (highest priority)
export TWX_SDF_SB1_PRIVATE_KEY_PATH="/override/path.pem"

# Shared (medium priority)
export TWX_SDF_PRIVATE_KEY_PATH="/shared/path.pem"

# Config file (lower priority)
{
  "environments": {
    "sb1": {
      "privateKeyPath": "/config/path.pem"
    }
  }
}

# Default (lowest priority)
# /home/tchow/NetSuiteBundlet/SDF/keys/{authId}.pem
```

## Zod Schema Validation

The configuration is validated using Zod schemas for type safety:

**Location:** `/home/tchow/netsuite-deploy/src/config/schema.ts` (80 lines)

**Validation Rules:**
- `projectName` must be non-empty string
- `version` must match semantic version format
- `environments` must have at least one environment
- Each environment must have `accountId` and `authId`
- `certificateId` and `privateKeyPath` are optional
- `build.enabled` must be boolean if present
- `deploy.accountSpecificValues` must be valid enum value

**Example Validation Error:**
```
Invalid configuration:
- version: Invalid semantic version format
- environments.sb1.accountId: Required field missing
```

## Configuration Loading

**File:** `/home/tchow/netsuite-deploy/src/config/loader.ts` (48 lines)

**Loading Process:**
1. Search for `twx-sdf.config.json` in current directory
2. Parse JSON and validate against schema
3. Throw clear error if validation fails
4. Return typed configuration object

**Usage:**
```typescript
import { loadConfig } from './config/loader';

const config = await loadConfig();
console.log(config.projectName); // Type-safe access
```

## Configuration Best Practices

### 1. Separate Credentials by Environment
```json
{
  "environments": {
    "sb1": {
      "authId": "myapp-sb1",  // Sandbox-specific
      "certificateId": "cert-sb1"
    },
    "prod": {
      "authId": "myapp-prod",  // Production-specific
      "certificateId": "cert-prod"
    }
  }
}
```

### 2. Use Environment Variables for Secrets
```bash
# Don't hardcode in config
{
  "certificateId": "abc123"  // ❌ Bad
}

# Use environment variables
export TWX_SDF_CERT_ID="abc123"  # ✅ Good
```

### 3. Enable Validation
```json
{
  "deploy": {
    "validateBeforeDeploy": true  // ✅ Always validate
  }
}
```

### 4. Semantic Versioning
```json
{
  "version": "1.2.3"  // ✅ MAJOR.MINOR.PATCH
}
```

### 5. Descriptive AuthIds
```json
{
  "authId": "myapp-sb1"  // ✅ Clear and descriptive
}
```

## Common Configuration Errors

### Missing Required Fields
```json
{
  "projectName": "My Project"
  // ❌ Missing "version" and "environments"
}
```
**Fix:** Add all required fields

### Invalid Semantic Version
```json
{
  "version": "1.0"  // ❌ Missing patch version
}
```
**Fix:** Use format `"1.0.0"`

### Empty Environments
```json
{
  "environments": {}  // ❌ Must have at least one
}
```
**Fix:** Add at least one environment configuration

### Invalid Account ID Format
```json
{
  "accountId": "1234567-SB1"  // ❌ Use underscore, not hyphen
}
```
**Fix:** Use `"1234567_SB1"`

### Missing AuthId
```json
{
  "environments": {
    "sb1": {
      "accountId": "1234567_SB1"
      // ❌ Missing "authId"
    }
  }
}
```
**Fix:** Add `"authId": "myapp-sb1"`

## Configuration Testing

Test your configuration before deployment:

```bash
# Validate configuration
npx twx-deploy validate

# Dry-run deployment (validates config and credentials)
npx twx-deploy deploy sb1 --dry-run
```

## Related Documentation

- Authentication reference: `authentication.md`
- Deployment workflow: `deployment-workflow.md`
- CI/CD setup: `ci-cd-setup.md`
- Troubleshooting: `troubleshooting.md`
