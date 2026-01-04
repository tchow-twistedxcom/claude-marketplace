---
description: Validate portable setup installation
argument-hint: "[--strict]"
allowed-tools: ["Bash", "Read"]
---

Validate the current Claude Code installation for completeness. Checks for required tools, configuration files, and proper setup. Provides actionable recommendations for any issues found.

## Instructions

1. **Locate the plugin directory:**
   - Use `Bash`: `find ~/.claude/plugins -name "portable-setup" -type d | head -1`
   - Store as `PLUGIN_DIR`

2. **Locate validation script:**
   - Path: `$PLUGIN_DIR/assets/scripts/validate-setup.sh`
   - Verify exists

3. **Check for --strict flag:**
   - If `--strict` provided, validation will fail on warnings (exit code 1)
   - Without flag, warnings are informational only (exit code 0)

4. **Run validation script:**
   - With strict mode: `bash $PLUGIN_DIR/assets/scripts/validate-setup.sh --strict`
   - Normal mode: `bash $PLUGIN_DIR/assets/scripts/validate-setup.sh`
   - Capture both output and exit code

5. **Parse validation output:**
   - Look for these markers:
     - `✅` - Check passed
     - `⚠️` - Warning (optional item)
     - `❌` - Error (critical item)
     - `ℹ️` - Informational note

6. **Categorize results:**
   - **Critical Errors** (❌): Missing required tools or configuration
   - **Warnings** (⚠️): Missing optional features or configuration needs
   - **Informational** (ℹ️): Notes about excluded items (agents, hooks, etc.)

7. **Present organized results:**
   ```
   🔍 Portable Setup Validation Results
   ═══════════════════════════════════

   Core Tools: [✅ all passed / ⚠️ X warnings / ❌ X errors]
   - List status of each tool

   Claude Configuration: [status]
   - Settings.json: [status]
   - Note: SuperClaude framework excluded (user-specific)
   - Note: Custom agents excluded (user-specific)

   Claude Code Configuration: [status]
   - config.json: [status]
   - .env: [status with details]
   - Note: Custom hooks excluded (user-specific)

   System Configuration: [status]
   - tmux: [status]
   - npmrc: [status with token check]
   - git: [status with user info]

   GitHub CLI: [status]

   Statusline: [status]

   Version Information:
   - Claude Code: [version]
   - Node.js: [version]
   - Python: [version]
   - Git: [version]
   ```

8. **Provide actionable recommendations:**

   For each error/warning, include fix suggestion:

   **Missing tool:**
   ```
   ❌ claude not found
   Fix: npm install -g claude-code
   Verify: claude --version
   ```

   **Placeholder secrets:**
   ```
   ⚠️  .env exists but needs configuration
   Fix: Edit ~/.config/claude-code/.env
        Replace YOUR_TOPIC_HERE with actual ntfy topic
   Verify: grep -v "YOUR_TOPIC_HERE" ~/.config/claude-code/.env
   ```

   **Missing GitHub token:**
   ```
   ⚠️  npmrc exists but needs GitHub token
   Fix: Edit ~/.npmrc
        Add your GitHub personal access token
        Generate at: https://github.com/settings/tokens
        Required scopes: repo, read:packages
   ```

   **Git not configured:**
   ```
   ⚠️  Git user not configured
   Fix: git config --global user.name "Your Name"
        git config --global user.email "your@email.com"
   ```

9. **Display summary:**
   - If exit code 0 and no errors:
     ```
     ✅ Perfect! Setup is complete and fully configured.
     ```

   - If exit code 0 with warnings:
     ```
     ⚠️  Warnings: X items need attention (optional)

     Setup is functional but some optional items need configuration.
     Review warnings above for details.
     ```

   - If exit code 1:
     ```
     ❌ Errors: X critical items missing
     ⚠️  Warnings: Y items need attention

     Please review errors above and re-run setup or fix manually.
     ```

   - If --strict mode failed on warnings:
     ```
     ⚠️  Strict mode: Failed due to warnings

     All optional features must be configured in strict mode.
     Fix warnings above or run without --strict flag.
     ```

10. **Suggest next steps:**
    - If errors: "Fix errors and run `/portable:validate` again"
    - If warnings only: "Configuration is functional. Fix warnings for complete setup."
    - If perfect: "Setup complete! Run `claude` to start using Claude Code."

## Usage Examples

**Normal validation:**
```
/portable:validate
```
Checks setup, reports errors and warnings, passes if no critical errors.

**Strict validation:**
```
/portable:validate --strict
```
Fails if any warnings exist. Useful for CI/CD or ensuring complete setup.

## Notes

- Validation is read-only and makes no changes to your system
- Exit codes: 0 = success (or warnings only), 1 = critical errors (or strict mode failures)
- Run after installation to verify setup completeness
- Re-run after fixing issues to confirm resolution
- Informational notes about excluded items are normal and expected
- Color-coded output helps identify priority of issues
- Can be automated in scripts using exit code checking
