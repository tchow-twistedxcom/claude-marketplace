---
description: Install portable setup from included template
---

Install the portable Claude Code configuration from the bundled template tarball. This command extracts the pre-packaged configuration and runs the automated setup process.

## Instructions

1. **Locate the plugin directory:**
   - Use `Bash` to find plugin location: `find ~/.claude/plugins -name "portable-setup" -type d | head -1`
   - Store as `PLUGIN_DIR`

2. **Find the template tarball:**
   - List files: `ls $PLUGIN_DIR/assets/template/*.tar.gz`
   - Should find exactly one tarball (e.g., `claude-code-portable-20260104.tar.gz`)
   - Store path as `TARBALL_PATH`

3. **Determine extraction directory:**
   - Check if user provided `--path` argument
   - Default: `~/claude-portable-setup`
   - If directory exists, warn user and ask for confirmation to overwrite

4. **Extract tarball:**
   - Create extraction directory if needed: `mkdir -p <extraction-dir>`
   - Extract: `tar -xzf $TARBALL_PATH -C <extraction-dir>`
   - Navigate to extracted directory

5. **Run setup script:**
   - Make executable: `chmod +x setup.sh`
   - Execute: `./setup.sh`
   - Show full output to user (includes progress, validation, warnings)

6. **Remind about secrets configuration:**
   - Display message:
     ```
     ⚠️  Important: Configure secrets before using Claude Code

     1. Edit ntfy topics:
        nano ~/.config/claude-code/.env

     2. Add GitHub personal access token:
        nano ~/.npmrc
        Generate token at: https://github.com/settings/tokens
        Required scopes: repo, read:packages

     3. Reload shell:
        source ~/.bashrc
     ```

7. **Run validation:**
   - Execute: `$PLUGIN_DIR/assets/scripts/validate-setup.sh`
   - Show validation results
   - Highlight any errors or warnings

8. **Display next steps:**
   - If validation passed: "✅ Installation complete! Run `claude --version` to verify."
   - If validation has warnings: List specific items needing attention
   - If validation failed: Provide troubleshooting guidance

## Usage Examples

**Basic installation:**
```
/portable:install
```
Extracts to default location `~/claude-portable-setup` and runs setup.

**Custom installation path:**
```
/portable:install --path /opt/claude-setup
```
Extracts to specified directory.

## Notes

- Non-destructive: Won't overwrite existing configurations without confirmation
- Secrets must be manually configured after installation for security
- GitHub CLI authentication happens during setup (follow interactive prompts)
- If plugin is not in expected location, guide user to verify plugin installation
