---
name: n8n-validate
description: "Validate n8n workflow configuration and optionally auto-fix issues"
---

# /n8n:validate - Validate Workflow Configuration

Comprehensive validation of workflow structure, nodes, connections, and expressions with optional auto-fix.

## Usage

```
/n8n:validate <workflow-id> [options]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `workflow-id` | ID of the workflow to validate |

## Flags

| Flag | Description |
|------|-------------|
| `--account <id>` | Use specific n8n account (default: from config) |
| `--fix` | Automatically fix common issues |
| `--fix-preview` | Preview fixes without applying them |
| `--strict` | Use strict validation profile |
| `--verbose` | Show detailed validation output |
| `--nodes-only` | Validate only node configurations |
| `--connections-only` | Validate only workflow connections |
| `--expressions-only` | Validate only expression syntax |

## Workflow

### Full Validation (Default)

1. **Fetch Workflow**
   - Call `mcp__n8n__n8n_get_workflow` to retrieve workflow JSON

2. **Validate Structure**
   - Call `mcp__n8n__validate_workflow` with full validation
   - Check nodes, connections, and expressions

3. **Analyze Results**
   - Categorize errors vs warnings
   - Identify fixable issues

4. **Report Findings**
   - Show errors with severity
   - Provide fix recommendations
   - Offer auto-fix if applicable

### Auto-Fix Mode

1. **Run Validation**
   - Identify all fixable issues

2. **Preview Fixes** (if --fix-preview)
   - Show what would be changed
   - Ask for confirmation

3. **Apply Fixes** (if --fix)
   - Call `mcp__n8n__n8n_autofix_workflow`
   - Report changes made

4. **Re-validate**
   - Confirm issues resolved
   - Report remaining issues

## Output Format

### Clean Validation
```
Workflow Validation: Customer Sync (abc123)
================================
Status: ✅ Valid

Checks Passed:
  ✓ Node configurations (8 nodes)
  ✓ Workflow connections (7 connections)
  ✓ Expression syntax (12 expressions)
  ✓ Trigger node present
  ✓ No circular dependencies

Workflow is ready for activation.
```

### Validation with Issues
```
Workflow Validation: Data Import (def456)
================================
Status: ⚠️ Issues Found

Errors (2):
  ❌ Node "HTTP Request" (node_3)
     - Missing required field: url
     - Authentication not configured

  ❌ Expression Error (node_5)
     - Invalid expression: {{ $json.data.items }
     - Missing closing bracket

Warnings (3):
  ⚠️ Node "Set" (node_4)
     - Deprecated property: keepOnlySet
     - Recommendation: Use "Options" instead

  ⚠️ Connection Warning
     - Node "IF" has unconnected output
     - Consider adding error handling

  ⚠️ Best Practice
     - No error handling node detected
     - Consider adding Error Trigger

Fixable Issues: 2 of 5
Run with --fix to auto-repair common issues.
```

### Auto-Fix Preview
```
Workflow Auto-Fix Preview: Data Import (def456)
================================
The following fixes can be applied:

1. Expression Format Fix (node_5)
   Before: {{ $json.data.items }
   After:  {{ $json.data.items }}
   Confidence: High

2. TypeVersion Correction (node_3)
   Before: typeVersion: 3
   After:  typeVersion: 4.2
   Confidence: Medium

3. Deprecated Property Update (node_4)
   Before: keepOnlySet: true
   After:  options: { dotNotation: true }
   Confidence: High

Cannot Auto-Fix (1):
  ❌ Missing URL in HTTP Request
     Manual configuration required

Apply these fixes? Use --fix to proceed.
```

### After Auto-Fix
```
Workflow Auto-Fix Applied: Data Import (def456)
================================
Fixes Applied: 3

✓ Expression format corrected (node_5)
✓ TypeVersion updated (node_3)
✓ Deprecated property migrated (node_4)

Remaining Issues: 1
  ❌ HTTP Request URL still needs manual configuration

Re-validation Status: ⚠️ Needs Attention
```

## Validation Profiles

| Profile | Description | Use Case |
|---------|-------------|----------|
| `runtime` | Default, catches execution issues | General validation |
| `strict` | All rules, including style | Pre-production review |
| `ai-friendly` | Optimized for AI agent use | AI workflow validation |
| `minimal` | Required fields only | Quick checks |

## API Limitations

**Note**: The n8n REST API does not provide built-in validation endpoints. Validation is performed locally by:

1. **Fetching workflow JSON** via API
2. **Analyzing structure** (nodes, connections, expressions)
3. **Checking for common issues** programmatically

Auto-fix capabilities are limited to what can be done via the `workflows update` endpoint.

## CLI Tools Used

| Script | Purpose |
|--------|---------|
| `scripts/n8n_api.py workflows get` | Fetch workflow JSON for analysis |
| `scripts/n8n_api.py workflows update` | Apply fixes via workflow update |

### Example CLI Commands

```bash
# Get workflow to inspect structure
python3 scripts/n8n_api.py workflows get <workflow-id>

# Get workflow as JSON for analysis
python3 scripts/n8n_api.py workflows get <workflow-id> --json

# Update workflow after manual fixes
python3 scripts/n8n_api.py workflows update <workflow-id> --file fixed_workflow.json
```

## Validation Approach

Since the API doesn't have validation endpoints, validation involves:

1. **Fetch**: Get workflow JSON via `workflows get`
2. **Analyze**: Check nodes have required fields, connections are valid
3. **Report**: Show errors, warnings, and recommendations
4. **Fix**: Apply fixes via `workflows update` (limited to JSON structure changes)

## Examples

### Basic Validation
```
/n8n:validate abc123
```

### Strict Validation
```
/n8n:validate abc123 --strict
```

### Preview Fixes
```
/n8n:validate abc123 --fix-preview
```

### Apply Fixes
```
/n8n:validate abc123 --fix
```

### Validate Only Expressions
```
/n8n:validate abc123 --expressions-only
```

### Verbose Output
```
/n8n:validate abc123 --verbose

# Shows detailed node-by-node validation results
```

### Validate on Specific Account
```
/n8n:validate abc123 --account production
```

## Common Validation Errors

### Node Errors
| Error | Cause | Fix |
|-------|-------|-----|
| Missing required field | Node not fully configured | Configure in n8n UI |
| Invalid credential | Credential deleted/renamed | Update credential reference |
| Unknown node type | Node package not installed | Install required package |
| TypeVersion mismatch | Outdated node version | Auto-fixable with --fix |

### Connection Errors
| Error | Cause | Fix |
|-------|-------|-----|
| Orphan node | Node not connected | Connect to workflow |
| Invalid connection | Type mismatch | Fix connection types |
| Circular dependency | Loop without merge | Restructure workflow |
| Missing trigger | No start node | Add trigger node |

### Expression Errors
| Error | Cause | Fix |
|-------|-------|-----|
| Syntax error | Invalid expression | Fix brackets/syntax |
| Unknown variable | Referenced non-existent data | Check data path |
| Invalid function | Using unsupported function | Use n8n functions |

## Auto-Fix Capabilities

The auto-fix feature can repair:

✓ Expression format issues (brackets, syntax)
✓ TypeVersion corrections
✓ Error output configuration
✓ Webhook missing path
✓ Deprecated property migration

Cannot auto-fix:
✗ Missing required configuration
✗ Invalid credentials
✗ Logic errors
✗ Complex expression errors

## Related Commands

- `/n8n:list workflows` - Find workflow IDs
- `/n8n:run` - Execute validated workflow
- `/n8n:status` - Check n8n health
- `/n8n:help expressions` - Expression syntax guide
