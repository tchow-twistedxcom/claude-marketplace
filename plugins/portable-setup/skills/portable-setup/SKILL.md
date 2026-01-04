---
name: portable-setup
description: Guides users in creating portable Claude Code configurations, transferring setups across servers, and synchronizing environments using git-based workflows
---

This skill teaches users about portable Claude Code configuration management. Use it when users ask about transferring their Claude Code setup to new servers, exporting their configuration, keeping multiple environments synchronized, or maintaining consistent setups across machines.

**Common trigger phrases:**
- "portable setup"
- "transfer configuration"
- "move claude code to another server"
- "export my setup"
- "install on new server"
- "synchronize setup"
- "sync configuration across environments"
- "keep environments in sync"

# Portable Claude Code Configuration

## What Makes a Setup Portable

Create portable configurations by separating system-level settings from project-specific customizations:

**Include in portable setup:**
- Claude Code settings.json and statusline customizations
- System dotfiles (.tmux.conf, .bashrc additions, .npmrc, git ignore patterns)
- Configuration templates with placeholder secrets
- Documentation and setup automation scripts

**Exclude from portable setup:**
- Project-specific agents, commands, and hooks
- Framework customizations (CLAUDE.md, custom modes)
- Secrets, API keys, and authentication tokens
- Session data and temporary files

This separation keeps packages small (typically 20-30KB), prevents conflicts between environments, and allows per-project customization while maintaining consistent system configuration.

## Security Considerations

Protect sensitive data when creating portable configurations:

**Secret Stripping:**
- Replace actual values with placeholders (e.g., `NTFY_TOPIC=YOUR_TOPIC_HERE`)
- Use `.template` suffix for files requiring manual configuration
- Document required secrets in setup instructions

**Validation:**
- Check exported packages for accidentally included secrets
- Validate configurations detect placeholder values
- Require manual secret entry during installation

**Best Practices:**
- Never commit secrets to version control
- Use separate .env files for environment-specific values
- Implement validation gates to catch misconfiguration

## Transfer Strategies

Choose the right transfer method based on your workflow:

**Git-Based (Recommended):**
- Store portable setup as plugin in personal marketplace repository
- Use `/portable:sync` to export, commit, and push configuration changes
- Pull marketplace updates on other machines and run `/portable:install`
- Provides version history, rollback capability, and familiar workflow

**Manual Transfer:**
- Export configuration to tarball with `/portable:export`
- Transfer via scp, rsync, or file sharing
- Extract and run setup.sh on target machine
- Suitable for one-time transfers or air-gapped environments

**Team Distribution:**
- Create team marketplace with standardized configurations
- Team members clone marketplace and install shared setup
- Customize per-developer preferences in .local.md files

## Git-Based Synchronization Workflow

Maintain synchronized environments using git as the transport layer:

**Initial Setup:**
1. Create plugin in personal marketplace repository
2. Export current configuration to bundled template
3. Commit and push to remote repository
4. Clone marketplace on other machines

**Making Changes (Machine A):**
1. Modify Claude Code configuration (settings, statusline, dotfiles)
2. Run `/portable:sync` to export, update template, commit, and push
3. Git handles version control and distribution

**Receiving Changes (Machines B, C, D):**
1. `cd ~/.claude/marketplace && git pull` to fetch updates
2. `/portable:install` to apply synchronized configuration
3. Configure environment-specific secrets if needed

**Benefits:**
- Automatic versioning and rollback via git history
- Familiar workflow using standard git operations
- Works with any git hosting (GitHub, GitLab, self-hosted)
- No custom sync infrastructure required

**Optional Auto-Pull:**
Set up cron job or git hook to periodically pull marketplace updates for near-real-time synchronization.

## Multi-Environment Management Patterns

Effective strategies for managing multiple Claude Code installations:

**Environment Tiers:**
- **Development**: Experimental features, frequent updates
- **Staging**: Stable configurations for testing
- **Production**: Verified setups for critical work

Use git branches to maintain different configuration versions per tier.

**Machine-Specific Overrides:**
- Use `.claude/*.local.md` files for machine-specific settings
- Add `.local.md` to .gitignore to prevent sync conflicts
- Document override patterns in README

**Incremental Rollout:**
1. Test configuration changes on development machine
2. Sync to staging environment for validation
3. Deploy to production machines after confirmation

**Conflict Resolution:**
- Avoid simultaneous configuration changes on multiple machines
- Designate primary machine for configuration updates
- Use git merge strategies for intentional divergence

## Troubleshooting Common Issues

### Export Creates Large Tarball

**Symptom:** Tarball exceeds 50KB

**Causes:**
- Including project-specific customizations
- Framework files not excluded properly
- Binary files or logs accidentally included

**Solution:**
- Verify exclusion patterns in export-config.sh
- Check for `.claude/` subdirectories with large files
- Use `tar -tzf package.tar.gz` to inspect contents

### Secrets Leak into Export

**Symptom:** Actual API keys or tokens in exported files

**Causes:**
- Secret stripping patterns incomplete
- New secret location not covered by export script
- Manual edits to templates after generation

**Solution:**
- Update export-config.sh secret stripping patterns
- Search exported tarball: `tar -xzf package.tar.gz && grep -r "ghp_" .`
- Add validation step to export workflow

### Sync Push Fails

**Symptom:** Git push rejected during `/portable:sync`

**Causes:**
- No write access to remote repository
- Divergent history (remote has commits you don't)
- Network connectivity issues

**Solution:**
- Verify repository permissions and authentication
- Pull remote changes before syncing: `git pull --rebase`
- Check network connection and remote URL

### Installation Validation Warnings

**Symptom:** validate-setup.sh shows configuration warnings

**Causes:**
- Placeholder values not replaced with actual secrets
- Missing optional tools (gh, tmux, etc.)
- File permissions issues

**Solution:**
- Edit `~/.config/claude-code/.env` with actual ntfy topics
- Edit `~/.npmrc` with GitHub personal access token
- Run `chmod` to fix permission issues
- Use `--strict` flag only when all optional features required

## Commands Available

The portable-setup plugin provides these commands:

- `/portable:install` - Install bundled template on current machine
- `/portable:export` - Create new export of current configuration
- `/portable:sync` - Synchronize configuration across all environments via git
- `/portable:validate` - Validate installation completeness
- `/portable:docs` - View setup, dependency, and customization documentation

Use these commands to manage your portable Claude Code configuration efficiently.
