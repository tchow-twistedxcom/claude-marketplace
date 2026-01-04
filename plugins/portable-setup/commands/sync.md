---
description: Synchronize configuration across all environments
---

Synchronize your Claude Code configuration across all environments using git. This command exports your current configuration, updates the bundled template in the plugin, commits the changes, and pushes to your marketplace repository.

## Instructions

1. **Locate the plugin directory:**
   - Use `Bash`: `find ~/.claude/plugins -name "portable-setup" -type d | head -1`
   - Store as `PLUGIN_DIR`

2. **Validate git repository:**
   - Check if plugin is in git repo: `git -C $PLUGIN_DIR rev-parse --git-dir`
   - If fails with error:
     ```
     ❌ Plugin must be in a git repository for sync to work

     The portable-setup plugin needs to be in a git repository
     (typically your personal marketplace) to enable synchronization.

     Current location: $PLUGIN_DIR

     If this is your marketplace, initialize git:
       cd $PLUGIN_DIR/.. && git init && git remote add origin <your-repo-url>
     ```
   - Exit with error if not in git repo

3. **Check for git remote:**
   - Verify remote exists: `git -C $PLUGIN_DIR remote get-url origin`
   - If fails:
     ```
     ❌ No git remote configured

     Add a remote to enable synchronization:
       cd $PLUGIN_DIR/.. && git remote add origin <your-marketplace-repo-url>
     ```
   - Exit with error if no remote

4. **Check git status:**
   - Run: `git -C $PLUGIN_DIR status --porcelain`
   - If output contains files outside `assets/template/`:
     ```
     ⚠️  Warning: Uncommitted changes in plugin directory

     The following files have uncommitted changes:
     <list files>

     These will NOT be included in the sync.
     Only the updated template will be committed.

     Continue? (y/n)
     ```
   - Wait for user confirmation if uncommitted changes exist

5. **Locate sync script:**
   - Path: `$PLUGIN_DIR/assets/scripts/sync-config.sh`
   - Verify exists

6. **Extract custom commit message (if provided):**
   - Check for `--message` argument
   - If provided, extract message text
   - If not provided, script will use default timestamp message

7. **Run sync script:**
   - If custom message: `bash $PLUGIN_DIR/assets/scripts/sync-config.sh "<custom-message>"`
   - If default: `bash $PLUGIN_DIR/assets/scripts/sync-config.sh`
   - Show full output including:
     - Export progress
     - Template update status
     - Git commit details
     - Git push confirmation

8. **Handle errors:**
   - **Export fails:** Show error, suggest checking configuration files
   - **Git commit fails:** Show git error, suggest resolving conflicts
   - **Git push fails:**
     ```
     ❌ Git push failed

     Common causes:
     - No write access to remote repository
     - Divergent history (remote has commits you don't have)
     - Network connectivity issues

     Troubleshooting:
     1. Check repository permissions and authentication
     2. Pull remote changes: cd $PLUGIN_DIR/.. && git pull --rebase
     3. Verify network connection and remote URL
     4. Try manual push: cd $PLUGIN_DIR/.. && git push
     ```

9. **Display success message:**
   ```
   ✅ Configuration synchronized!

   📦 Updated template: assets/template/<new-tarball-name>
   📝 Commit: <commit-hash> - <commit-message>
   ⬆️  Pushed to: <remote-url>

   🔄 To update other environments:

   Method 1 (Marketplace symlink):
   1. cd ~/.claude/plugins/marketplaces/<marketplace-name> && git pull
   2. /portable:install

   Method 2 (Direct plugin link):
   1. cd ~/.claude/plugins/portable-setup/.. && git pull
   2. /portable:install

   ✨ Other machines will receive these changes on their next pull.
   ```

10. **Show git log entry:**
    - Display last commit: `git -C $PLUGIN_DIR log -1 --oneline`
    - Show file changes: `git -C $PLUGIN_DIR show --stat HEAD`

## Usage Examples

**Basic sync with default message:**
```
/portable:sync
```
Creates commit: "Sync portable config - 20260104-143022"

**Sync with custom commit message:**
```
/portable:sync --message "Update statusline configuration"
```
Creates commit with your custom message.

## Workflow

**On Machine A (where you made changes):**
1. Edit Claude Code configuration (settings, statusline, dotfiles)
2. Run `/portable:sync`
3. Changes are exported, committed, and pushed automatically

**On Machines B, C, D (other environments):**
1. Pull marketplace updates: `cd ~/.claude/marketplace && git pull`
2. Install synchronized config: `/portable:install`
3. Environments now have your latest configuration

## Notes

- Requires plugin to be in a git repository with remote configured
- Only updates the template tarball (assets/template/)
- Other uncommitted plugin changes are NOT included in sync
- Each sync creates a git commit for version history
- Can rollback by reverting commits: `git -C $PLUGIN_DIR/.. revert HEAD`
- For conflicts, resolve manually before syncing again
- Use specific commit messages for better version tracking
