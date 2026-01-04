---
name: export
description: Export current Claude Code configuration to tarball
argument-hint: "[--output-dir <path>]"
allowed-tools: ["Bash", "Read"]
---

Export the current Claude Code configuration to a portable tarball. Creates a timestamped package suitable for transfer to other servers or updating the plugin template.

## Instructions

1. **Locate the plugin directory:**
   - Use `Bash`: `find ~/.claude/plugins -name "portable-setup" -type d | head -1`
   - Store as `PLUGIN_DIR`

2. **Locate export script:**
   - Path: `$PLUGIN_DIR/assets/scripts/export-config.sh`
   - Verify exists: `[ -f $PLUGIN_DIR/assets/scripts/export-config.sh ] && echo "Found" || echo "Missing"`

3. **Determine output directory:**
   - Check if user provided `--output-dir` argument
   - Default: current working directory
   - Verify directory exists and is writable

4. **Run export script:**
   - Navigate to output directory: `cd <output-dir>`
   - Execute: `bash $PLUGIN_DIR/assets/scripts/export-config.sh`
   - Capture and show full output

5. **Find created tarball:**
   - List newest tarball: `ls -t claude-code-portable-*.tar.gz | head -1`
   - Get file size: `du -h <tarball-name>`
   - Store tarball path and name

6. **Show export summary:**
   - Display:
     ```
     ✅ Configuration exported successfully!

     📦 Package: <tarball-name>
     📊 Size: <size>
     📁 Location: <full-path>

     📋 What's included:
     - Claude Code settings.json and statusline scripts
     - System dotfiles (tmux, bash, git, npm)
     - Configuration templates (secrets stripped)

     🚫 What's excluded:
     - SuperClaude framework files
     - Custom agents, commands, hooks
     - Secrets and authentication tokens

     📝 Next steps:
     ```

7. **Provide next step options:**
   - **Option 1: Transfer to new server:**
     ```
     1. Transfer tarball: scp <tarball> user@server:/path/
     2. On server: tar -xzf <tarball>
     3. On server: cd <extracted-dir> && ./setup.sh
     ```

   - **Option 2: Update plugin template:**
     ```
     1. Move to plugin: mv <tarball> $PLUGIN_DIR/assets/template/
     2. Remove old template: rm $PLUGIN_DIR/assets/template/claude-code-portable-[old-date].tar.gz
     3. Commit changes: cd $PLUGIN_DIR && git add assets/template/ && git commit -m "Update template"
     4. Push to remote: git push
     ```

   - **Option 3: Use sync command (recommended):**
     ```
     Instead of manual export and update, use:
     /portable:sync

     This automatically exports, updates template, commits, and pushes.
     ```

8. **Verify tarball contents (if user asks):**
   - List contents: `tar -tzf <tarball> | head -20`
   - Check for secrets: `tar -xzf <tarball> -O | grep -E "(ghp_|github_pat_|NTFY_TOPIC=(?!YOUR_TOPIC_HERE))"`
   - If secrets found: ⚠️ Warning and recommend reviewing export-config.sh

## Usage Examples

**Export to current directory:**
```
/portable:export
```
Creates tarball in current working directory.

**Export to specific location:**
```
/portable:export --output-dir /tmp/exports
```
Creates tarball in specified directory.

## Notes

- Export script automatically strips secrets from configuration files
- Tarball is timestamped for version tracking
- Typically 20-30KB in size
- Can inspect tarball before transferring: `tar -tzf <file>.tar.gz`
- Use `/portable:sync` for automatic template updates and git synchronization
