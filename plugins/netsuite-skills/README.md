# NetSuite Skills Plugin

Specialized skills for NetSuite ERP customization, diagnostics, and advanced SuiteScript development.

## Current Skills

### PRI Container Tracking (v1.1)
Comprehensive expertise for debugging, diagnosing, and understanding the Prolecto PRI Container Tracking system (Bundle 125246).

**Capabilities:**
- **Application Settings Configuration** (NEW v1.1) - 23+ settings for field mappings, workflows, and behavior control
- Diagnostic troubleshooting for container workflow issues
- System architecture understanding (10 custom records, 35 scripts)
- Modification planning for customizations and upgrades
- Manual remediation with deployable diagnostic scripts

**Use Cases:**
- Configure field mappings via Application Settings (Setting 250 for TO line dates)
- Troubleshoot why field mappings aren't applying (status gates, JSON errors)
- Debug date synchronization issues across Container → Transfer Order → Item Fulfillment
- Understand landed cost allocation methods
- Analyze Production PO Line locking scenarios
- Plan Bundle 132118 (Infrastructure) upgrades
- Modify PRI system behavior through JSON configuration

**Documentation:** 11 reference files (~390KB) including 3 new Application Settings guides

### NetSuite SDF Deployment (v1.2)
Comprehensive expertise for NetSuite SuiteCloud Development Framework (SDF) deployment, CI/CD automation, and certificate-based authentication.

**Capabilities:**
- **Certificate-Based M2M Authentication** - X.509 certificates with Token-Based Authentication (TBA)
- **Multi-Environment Deployment** - Sandbox (SB1, SB2) and production workflows
- **CI/CD Integration** - GitHub Actions templates and automated deployment pipelines
- **AuthId Management** - Registration, refresh, and credential resolution
- **Configuration System** - Type-safe Zod validation with environment variables
- **Deployment Workflows** - Automated validation, build, deploy, and config restoration

**Use Cases:**
- Set up certificate-based TBA for machine-to-machine deployments
- Configure multi-environment deployments (sb1, sb2, prod)
- Implement GitHub Actions workflows for automated NetSuite deployments
- Refresh authIds after certificate rotation
- Troubleshoot authentication and deployment errors
- Manage credential resolution across environments
- Validate SDF project structure before deployment

**Documentation:** 6 comprehensive reference files + 3 asset templates + certificate generation script

## Future Skills

This plugin will expand to include additional NetSuite customization expertise:
- [ ] Item Receipt to Transfer Order linking workflows
- [ ] Advanced Inventory Management customizations
- [ ] NetSuite SuiteCommerce Advanced (SCA) development
- [ ] RESTlet API design patterns
- [ ] SuiteTalk integration expertise
- [ ] Saved Search optimization techniques
- [ ] User Event Script performance patterns
- [ ] Client Script best practices
- [ ] NetSuite Analytics Workbook development

## Adding New Skills

To add a new NetSuite skill:

1. Create skill directory in `skills/`
2. Add `SKILL.md` with YAML frontmatter
3. Include `references/` for documentation
4. Include `scripts/` for diagnostic tools
5. Update `plugin.json` skills array
6. Test with sample NetSuite scenarios

## Version History

- **1.2.0** (2025-11-14) - Added NetSuite SDF Deployment skill
  - New skill: NetSuite SDF Deployment Expert
  - 6 comprehensive reference documents (authentication, configuration, deployment, CI/CD, troubleshooting, API)
  - 3 asset templates (config, GitHub Actions, environment variables)
  - Certificate generation script (generate_cert.sh)
  - Multi-environment deployment support (sb1, sb2, prod)
  - Certificate-based M2M authentication with TBA
  - CI/CD integration guide for GitHub Actions
- **1.1.0** (2025-11-12) - Enhanced PRI Container Tracking skill with Application Settings knowledge
  - Added 3 new reference documents (Application Settings Catalog, Architecture, Field Mapping Analysis)
  - Enhanced SKILL.md with Application Settings configuration capability
  - Added 23+ settings documentation with JSON examples
  - Added field mapping engine deep-dive (PRI_AS_Engine, SYNCSRCDEF)
  - Updated troubleshooting guides with configuration-based solutions
- **1.0.0** (2025-11-12) - Initial release with PRI Container Tracking skill
