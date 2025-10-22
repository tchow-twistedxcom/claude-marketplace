---
name: sdf-bundle-creation
description: "Best practices for creating and managing NetSuite SDF bundles. Use when creating custom NetSuite objects, SuiteScripts, or bundle packages."
license: MIT
---

# NetSuite SDF Bundle Creation

## Bundle Structure

### Standard Bundle Layout
```
bundle-name/
├── src/
│   ├── FileCabinet/
│   │   └── SuiteScripts/
│   │       └── [your-namespace]/
│   │           ├── client-scripts/
│   │           ├── user-event-scripts/
│   │           ├── restlets/
│   │           └── library/
│   ├── Objects/
│   │   ├── customrecord_[type].xml
│   │   ├── customfield_[field].xml
│   │   └── workflow_[name].xml
│   └── Templates/
│       └── [email-templates]/
├── manifest.xml
└── deploy.xml
```

## Object Naming Conventions

### Script IDs
- **Custom Records**: `customrecord_[namespace]_[name]`
- **Custom Fields**: `custbody_[namespace]_[name]` or `custrecord_[namespace]_[name]`
- **Scripts**: `customscript_[namespace]_[name]`
- **Deployments**: `customdeploy_[namespace]_[name]`

### File Paths
- Use namespace folders: `/SuiteScripts/[company]/[project]/`
- Organize by script type: `client-scripts/`, `user-event-scripts/`
- Keep related files together

## SuiteScript Best Practices

### Script Structure (SuiteScript 2.x)
```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType UserEventScript
 * @NModuleScope SameAccount
 */
define(['N/record', 'N/log'], function(record, log) {

    function beforeSubmit(context) {
        // Implementation
    }

    return {
        beforeSubmit: beforeSubmit
    };
});
```

### Error Handling
```javascript
try {
    // Script logic
} catch (e) {
    log.error({
        title: 'Script Error',
        details: e.message + ' | ' + e.stack
    });
    throw e; // Rethrow if critical
}
```

## Manifest Configuration

### manifest.xml Template
```xml
<?xml version="1.0" encoding="UTF-8"?>
<manifest projecttype="ACCOUNTCUSTOMIZATION">
    <projectname>Your Bundle Name</projectname>
    <frameworkversion>1.0</frameworkversion>
    <dependencies>
        <!-- List dependencies here -->
    </dependencies>
</manifest>
```

## Deployment Configuration

### deploy.xml Best Practices
```xml
<deploy>
    <configuration>
        <!-- Specify objects to deploy -->
        <path>~/Objects/*</path>
        <path>~/FileCabinet/SuiteScripts/**/*.js</path>
    </configuration>
    <excludes>
        <!-- Exclude test files -->
        <path>~/FileCabinet/SuiteScripts/**/test/**</path>
    </excludes>
</deploy>
```

## Development Workflow

### 1. Local Development
```bash
# Create new object
suitecloud object:create

# Import existing objects
suitecloud object:import

# Validate locally
suitecloud project:validate
```

### 2. Version Control
- Commit all XML files (Objects)
- Commit all scripts (FileCabinet)
- Include manifest.xml and deploy.xml
- Use `.gitignore` for credentials

### 3. Deployment Process
```bash
# Validate first
suitecloud project:validate

# Deploy to sandbox
suitecloud project:deploy --accountid DEV

# Test in sandbox
[Run validation tests]

# Deploy to production (after approval)
suitecloud project:deploy --accountid PROD
```

## Common Customizations

### Custom Record Type
```xml
<customrecordtype scriptid="customrecord_mycompany_widget">
    <label>Widget</label>
    <permissions>
        <permission>
            <accesslevel>VIEW</accesslevel>
            <role>ADMINISTRATOR</role>
        </permission>
    </permissions>
</customrecordtype>
```

### Custom Field
```xml
<customfield scriptid="custbody_mycompany_approval_date">
    <label>Approval Date</label>
    <type>DATE</type>
    <appliestorecord>transaction</appliestorecord>
    <displaytype>NORMAL</displaytype>
</customfield>
```

### Client Script
```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType ClientScript
 */
define(['N/ui/message'], function(message) {

    function pageInit(context) {
        // Client-side initialization
    }

    function fieldChanged(context) {
        var fieldId = context.fieldId;
        // Handle field changes
    }

    return {
        pageInit: pageInit,
        fieldChanged: fieldChanged
    };
});
```

## Testing Strategy

### Unit Testing
- Test scripts in isolation
- Mock NetSuite modules
- Use SuiteCloud Development Framework testing tools

### Integration Testing
- Deploy to sandbox environment
- Test user workflows end-to-end
- Verify integrations with external systems

### Validation Checklist
- [ ] All script IDs follow naming convention
- [ ] All scripts have proper error handling
- [ ] All objects have correct permissions
- [ ] Dependencies are declared in manifest
- [ ] Test coverage for critical paths
- [ ] Documentation for custom objects
- [ ] Deployment instructions updated

## Bundle Versioning

### Version Strategy
```
Version Format: MAJOR.MINOR.PATCH
Example: 1.2.3

MAJOR: Breaking changes
MINOR: New features (backwards compatible)
PATCH: Bug fixes
```

### Release Notes Template
```markdown
## Version 1.2.0

### Added
- New custom field: Approval Date
- Client script for validation

### Changed
- Improved error handling in user event script

### Fixed
- Resolved issue with date formatting
```

## Troubleshooting

### Common Issues

**Script Deployment Errors**
- Verify script ID uniqueness
- Check function entry points match deployment
- Ensure all dependencies are defined

**Object Import Failures**
- Validate XML syntax
- Check object dependencies exist
- Verify permissions are correctly set

**Validation Warnings**
- Address all errors before deployment
- Resolve warnings when possible
- Document known warnings in README

## Security Considerations

1. **Restrict Script Permissions**: Only grant necessary access
2. **Validate User Input**: Always sanitize data
3. **Use Secure Communication**: HTTPS for external calls
4. **Audit Logging**: Log security-relevant events
5. **Regular Updates**: Keep SuiteCloud CLI updated
