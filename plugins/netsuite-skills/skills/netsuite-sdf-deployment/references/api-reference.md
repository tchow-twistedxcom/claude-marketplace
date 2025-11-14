# API Reference

## Package: @twisted-x/netsuite-deploy

**Version:** 0.1.5 (as of November 2025)
**Type:** ESM Module
**Node:** 18+, npm 9+
**Registry:** GitHub Packages (Private)
**Repository:** `/home/tchow/netsuite-deploy`

## CLI Commands

### twx-deploy init

Initialize a new configuration file.

```bash
npx twx-deploy init
```

**Interactive Prompts:**
- Project name
- Initial version
- First environment setup
  - Environment name
  - Account ID
  - Auth ID

**Output:**
Creates `twx-sdf.config.json` in current directory.

---

### twx-deploy deploy

Deploy to a specific environment.

```bash
npx twx-deploy deploy <environment> [options]
```

**Arguments:**
- `<environment>` (required) - Target environment name (e.g., sb1, sb2, prod)

**Options:**
- `--build` - Run build step before deployment
- `--dry-run` - Validate configuration and credentials without deploying
- `--help` - Show help information
- `--version` - Show version information

**Examples:**
```bash
# Deploy to sb1
npx twx-deploy deploy sb1

# Deploy with build
npx twx-deploy deploy sb2 --build

# Dry-run validation
npx twx-deploy deploy prod --dry-run
```

**Exit Codes:**
- `0` - Success
- `1` - Error (configuration, authentication, or deployment failed)

---

### twx-deploy validate

Validate configuration file (future command).

```bash
npx twx-deploy validate
```

**Status:** Planned for future release

---

## Programmatic API

### Import

```typescript
import { deploy, DeployOptions } from '@twisted-x/netsuite-deploy';
```

### deploy()

Main deployment function.

```typescript
async function deploy(
  environment: string,
  options?: DeployOptions
): Promise<DeployResult>
```

**Parameters:**
- `environment` (string) - Target environment name
- `options` (DeployOptions, optional) - Deployment options

**DeployOptions:**
```typescript
interface DeployOptions {
  build?: boolean;      // Run build step
  dryRun?: boolean;     // Validate only
  configPath?: string;  // Custom config file path
  verbose?: boolean;    // Enable verbose logging
}
```

**Returns:**
```typescript
interface DeployResult {
  success: boolean;
  environment: string;
  timestamp: Date;
  duration: number;     // milliseconds
  errors?: string[];
}
```

**Example:**
```typescript
import { deploy } from '@twisted-x/netsuite-deploy';

const result = await deploy('sb1', {
  build: true,
  dryRun: false,
  verbose: true
});

if (result.success) {
  console.log(`Deployed to ${result.environment} in ${result.duration}ms`);
} else {
  console.error('Deployment failed:', result.errors);
}
```

---

### loadConfig()

Load and validate configuration file.

```typescript
async function loadConfig(
  configPath?: string
): Promise<NetSuiteDeployConfig>
```

**Parameters:**
- `configPath` (string, optional) - Path to config file (default: `./twx-sdf.config.json`)

**Returns:**
```typescript
interface NetSuiteDeployConfig {
  projectName: string;
  version: string;
  environments: {
    [key: string]: EnvironmentConfig;
  };
  build?: BuildConfig;
  paths?: PathsConfig;
  deploy?: DeployConfig;
}
```

**Example:**
```typescript
import { loadConfig } from '@twisted-x/netsuite-deploy';

const config = await loadConfig();
console.log(config.projectName);
console.log(Object.keys(config.environments)); // ['sb1', 'sb2', 'prod']
```

---

### resolveCredentials()

Resolve credentials for a specific environment.

```typescript
async function resolveCredentials(
  config: NetSuiteDeployConfig,
  environment: string
): Promise<Credentials>
```

**Parameters:**
- `config` (NetSuiteDeployConfig) - Loaded configuration
- `environment` (string) - Target environment name

**Returns:**
```typescript
interface Credentials {
  certificateId: string;
  privateKeyPath: string;
  ciPasskey?: string;
}
```

**Example:**
```typescript
import { loadConfig, resolveCredentials } from '@twisted-x/netsuite-deploy';

const config = await loadConfig();
const credentials = await resolveCredentials(config, 'sb1');

console.log(credentials.certificateId);
console.log(credentials.privateKeyPath);
```

---

## Type Definitions

### NetSuiteDeployConfig

```typescript
interface NetSuiteDeployConfig {
  projectName: string;
  version: string;
  environments: {
    [key: string]: EnvironmentConfig;
  };
  build?: BuildConfig;
  paths?: PathsConfig;
  deploy?: DeployConfig;
}
```

### EnvironmentConfig

```typescript
interface EnvironmentConfig {
  accountId: string;
  authId: string;
  certificateId?: string;
  privateKeyPath?: string;
}
```

### BuildConfig

```typescript
interface BuildConfig {
  enabled: boolean;
  command?: string;      // Default: "npm run build"
  outputDir?: string;    // Default: "dist"
}
```

### PathsConfig

```typescript
interface PathsConfig {
  sdf: string;          // Default: "./sdf"
}
```

### DeployConfig

```typescript
interface DeployConfig {
  accountSpecificValues?: 'ERROR' | 'WARNING' | 'IGNORE';  // Default: "ERROR"
  validateBeforeDeploy?: boolean;                          // Default: true
}
```

### Credentials

```typescript
interface Credentials {
  certificateId: string;
  privateKeyPath: string;
  ciPasskey?: string;
}
```

### DeployResult

```typescript
interface DeployResult {
  success: boolean;
  environment: string;
  timestamp: Date;
  duration: number;
  errors?: string[];
}
```

## Environment Variables

### Authentication Variables

**TWX_SDF_CERT_ID**
- Type: String
- Description: Shared certificate ID for all environments
- Example: `export TWX_SDF_CERT_ID="abc123"`

**TWX_SDF_{ENV}_CERT_ID**
- Type: String
- Description: Environment-specific certificate ID (highest priority)
- Example: `export TWX_SDF_SB1_CERT_ID="abc123"`

**TWX_SDF_PRIVATE_KEY_PATH**
- Type: String
- Description: Shared private key path for all environments
- Example: `export TWX_SDF_PRIVATE_KEY_PATH="/path/to/key.pem"`

**TWX_SDF_{ENV}_PRIVATE_KEY_PATH**
- Type: String
- Description: Environment-specific private key path (highest priority)
- Example: `export TWX_SDF_SB1_PRIVATE_KEY_PATH="/path/to/sb1.pem"`

**TWX_SDF_CI_PASSKEY**
- Type: String
- Description: CI passkey for account:setup:ci
- Example: `export TWX_SDF_CI_PASSKEY="passkey123"`
- Optional: Yes

**TWX_SDF_{ENV}_CI_PASSKEY**
- Type: String
- Description: Environment-specific CI passkey
- Example: `export TWX_SDF_SB1_CI_PASSKEY="passkey123"`
- Optional: Yes

### SuiteCloud CLI Variables

**SUITECLOUD_CI**
- Type: String
- Description: Enable CI mode for SuiteCloud CLI
- Example: `export SUITECLOUD_CI=1`
- Note: Automatically set by tool

## Error Codes

| Code | Type | Description |
|------|------|-------------|
| `CONFIG_NOT_FOUND` | ConfigError | Configuration file not found |
| `CONFIG_INVALID` | ConfigError | Configuration validation failed |
| `ENV_NOT_FOUND` | ConfigError | Environment not in configuration |
| `CRED_NOT_FOUND` | AuthError | Credentials not resolved |
| `CERT_INVALID` | AuthError | Invalid certificate ID |
| `KEY_NOT_FOUND` | AuthError | Private key file not found |
| `AUTH_FAILED` | AuthError | Authentication failed |
| `VALIDATION_FAILED` | DeployError | SDF validation failed |
| `BUILD_FAILED` | DeployError | Build command failed |
| `DEPLOY_FAILED` | DeployError | Deployment failed |

## Source Code Reference

### Core Modules

**Credentials Management**
- File: `/home/tchow/netsuite-deploy/src/auth/credentials.ts`
- Lines: 139
- Responsibilities: Multi-layer credential resolution

**Deployment Engine**
- File: `/home/tchow/netsuite-deploy/src/core/deployment.ts`
- Lines: 292
- Responsibilities: Orchestrates deployment workflow

**SDF CLI Manager**
- File: `/home/tchow/netsuite-deploy/src/core/sdfcli-manager.ts`
- Lines: 165
- Responsibilities: Manages .sdfcli.json and project.json

**Configuration Schema**
- File: `/home/tchow/netsuite-deploy/src/config/schema.ts`
- Lines: 80
- Responsibilities: Zod schema validation

**Configuration Loader**
- File: `/home/tchow/netsuite-deploy/src/config/loader.ts`
- Lines: 48
- Responsibilities: Load and validate configuration

## Related Documentation

- Authentication reference: `authentication.md`
- Configuration reference: `configuration.md`
- Deployment workflow: `deployment-workflow.md`
- CI/CD setup: `ci-cd-setup.md`
- Troubleshooting: `troubleshooting.md`
