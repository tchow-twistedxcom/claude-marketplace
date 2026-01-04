---
description: Validate portable setup configuration
---

Validate that portable setup configuration has been properly applied. Checks for placeholder secrets that need manual configuration, verifies configuration files are in place, and ensures the portable setup was installed correctly.

**Note**: This validates the portable setup configuration, not Claude Code itself (which must already be working for you to run this command).

## Instructions

1. **Check for --strict flag:**
   - If `--strict` provided, fail on any warnings
   - Without flag, warnings are informational only

2. **Run validation checks using Bash:**

   **Check 1: Secret Placeholders in .env**
   ```bash
   if [ -f ~/.config/claude-code/.env ]; then
       if grep -q "YOUR_TOPIC_HERE\|YOUR_.*_HERE\|PLACEHOLDER" ~/.config/claude-code/.env; then
           echo "⚠️  .env contains placeholder values - needs manual configuration"
           echo "   Edit: ~/.config/claude-code/.env"
           echo "   Replace placeholder values with actual secrets"
       else
           echo "✅ .env configured with actual values"
       fi
   else
       echo "ℹ️  .env not present (optional for some setups)"
   fi
   ```

   **Check 2: GitHub Token in .npmrc**
   ```bash
   if [ -f ~/.npmrc ]; then
       if grep -q "YOUR_TOKEN_HERE\|<TOKEN>\|PLACEHOLDER" ~/.npmrc; then
           echo "⚠️  .npmrc contains placeholder token - needs manual configuration"
           echo "   Edit: ~/.npmrc"
           echo "   Add GitHub personal access token"
           echo "   Generate at: https://github.com/settings/tokens"
       else
           echo "✅ .npmrc configured with GitHub token"
       fi
   else
       echo "ℹ️  .npmrc not present"
   fi
   ```

   **Check 3: Statusline Scripts**
   ```bash
   if [ -f ~/.claude/statusline.sh ]; then
       if [ -x ~/.claude/statusline.sh ]; then
           echo "✅ Statusline script installed and executable"
       else
           echo "⚠️  Statusline script exists but not executable"
           echo "   Fix: chmod +x ~/.claude/statusline.sh"
       fi
   else
       echo "ℹ️  Statusline script not installed (optional)"
   fi
   ```

   **Check 4: Claude Configuration Files**
   ```bash
   if [ -f ~/.claude/settings.json ]; then
       echo "✅ Claude settings.json present"
   else
       echo "⚠️  Claude settings.json missing"
       echo "   This should have been copied during portable setup"
   fi

   if [ -f ~/.config/claude-code/config.json ]; then
       echo "✅ Claude Code config.json present"
   else
       echo "⚠️  Claude Code config.json missing"
       echo "   This should have been copied during portable setup"
   fi
   ```

   **Check 5: System Dotfiles**
   ```bash
   if [ -f ~/.tmux.conf ]; then
       echo "✅ tmux configuration present"
   else
       echo "ℹ️  tmux configuration not installed (optional)"
   fi

   if grep -q "Claude Code additions" ~/.bashrc 2>/dev/null; then
       echo "✅ Bash configuration includes Claude Code additions"
   else
       echo "ℹ️  No Claude Code additions in .bashrc (optional)"
   fi
   ```

   **Check 6: Git User Configuration**
   ```bash
   if git config user.name >/dev/null 2>&1 && git config user.email >/dev/null 2>&1; then
       echo "✅ Git user configured: $(git config user.name) <$(git config user.email)>"
   else
       echo "⚠️  Git user not configured"
       echo "   Fix: git config --global user.name \"Your Name\""
       echo "        git config --global user.email \"your@email.com\""
   fi
   ```

3. **Count issues:**
   - Track number of ⚠️ warnings
   - Track number of ❌ errors (currently we don't have critical errors, only warnings)
   - Track number of ℹ️ informational items

4. **Display summary:**

   ```
   🔍 Portable Setup Configuration Validation
   ══════════════════════════════════════════

   Configuration Files:
   [Results from checks above]

   Secrets Configuration:
   [Results from checks above]

   System Integration:
   [Results from checks above]

   ──────────────────────────────────────────
   Summary: X warnings, Y informational notes
   ```

5. **Provide summary message:**

   - If no warnings:
     ```
     ✅ Perfect! Portable setup is fully configured.
     All secrets have been set and configuration files are in place.
     ```

   - If warnings found (not strict mode):
     ```
     ⚠️  Configuration needs attention: X items

     Your portable setup is functional but some items need manual configuration.
     Review warnings above for specific actions needed.

     Most common fixes:
     - Edit ~/.config/claude-code/.env to replace YOUR_TOPIC_HERE
     - Edit ~/.npmrc to add GitHub personal access token
     - Run: git config --global user.name "Your Name"
     ```

   - If --strict mode with warnings:
     ```
     ❌ Strict validation failed

     Strict mode requires all optional items to be configured.
     Fix warnings above or run without --strict flag.
     ```

6. **Exit with appropriate code:**
   - If --strict AND warnings exist: Exit code 1
   - Otherwise: Exit code 0

## Usage Examples

**Normal validation:**
```
/portable:validate
```
Checks portable setup configuration, reports warnings, passes if configuration is functional.

**Strict validation:**
```
/portable:validate --strict
```
Fails if any configuration items need attention. Useful for automation or ensuring complete setup.

## What This Validates

✅ **Configuration files copied**: settings.json, config.json
✅ **Secrets configured**: .env and .npmrc have actual values, not placeholders
✅ **Statusline installed**: Custom statusline script present and executable
✅ **Dotfiles applied**: tmux, bash configurations in place
✅ **Git configured**: User name and email set for commits

## What This Does NOT Validate

❌ Claude Code installation (must be working to run this command)
❌ Required system tools (node, npm, python, git)
❌ GitHub CLI installation
❌ Network connectivity

For full system validation (checking if tools are installed), use the standalone `validate-setup.sh` script that comes in the extracted portable setup tarball.

## Notes

- This command is meant to validate portable setup CONFIGURATION, not system prerequisites
- Warnings indicate configuration that needs manual attention (secrets, tokens)
- Informational notes are expected (not all optional features are required)
- Re-run after fixing warnings to confirm resolution
- Validation is read-only and makes no changes to your system
