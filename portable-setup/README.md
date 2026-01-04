# Portable Setup Plugin

Portable Claude Code configuration system - export, transfer, install, and synchronize your setup across all servers.

## Features

- 🎁 **Pre-packaged Template**: Includes a ready-to-use Claude Code setup (24KB)
- 📤 **Export Tool**: Create portable tarballs of your current configuration
- 📥 **Install Tool**: One-command installation on new servers
- 🔄 **Synchronization**: Git-based sync across all environments
- ✅ **Validation**: Verify setup completeness and troubleshoot issues
- 📚 **Documentation**: Comprehensive guides built-in

## Quick Start

### Install Template on New Server

```bash
/portable:install
```

This extracts and installs the included configuration template.

### Export Your Current Setup

```bash
/portable:export
```

Creates a timestamped tarball (24KB) of your current Claude Code configuration.

### Synchronize Across Environments

```bash
/portable:sync
```

**Automatically synchronizes your configuration across all environments:**
1. Exports current configuration
2. Updates bundled template in plugin
3. Commits and pushes to git
4. Other environments pull and install

### Validate Installation

```bash
/portable:validate
```

Checks for missing dependencies, configuration issues, and provides fix suggestions.

### View Documentation

```bash
/portable:docs readme
/portable:docs dependencies
/portable:docs customization
```

## What Gets Packaged

**Included** (Portable):
- Claude Code settings.json and statusline scripts
- System dotfiles (tmux, bash, git, npm)
- Configuration templates (secrets stripped)

**Excluded** (User-Specific):
- SuperClaude framework files
- Custom agents, commands, hooks
- SSH keys and secrets

## Use Cases

1. **New Server Setup**: Quickly replicate your configuration
2. **Team Sharing**: Distribute standardized setups
3. **Backup**: Version-controlled configuration snapshots
4. **Multi-Server**: Maintain consistent setups across machines
5. **Configuration Sync**: Keep all environments synchronized automatically

## Synchronization Workflow

**On Machine A** (where you made changes):
```bash
# Make changes to your Claude Code configuration
# (edit settings, statusline, dotfiles, etc.)

# Synchronize across all environments
/portable:sync

# ✅ Changes now committed and pushed to git
```

**On Machines B, C, D** (other environments):
```bash
# Pull latest plugin changes
cd ~/.claude/plugins/marketplaces/<marketplace-name> && git pull

# Install updated configuration
/portable:install

# ✅ Configuration now synchronized
```

**Or use auto-pull** (optional):
Set up a git pull hook or cron job to automatically pull marketplace updates.

## Security

- All secrets are stripped and replaced with placeholders
- GitHub tokens require manual entry
- ntfy topics require configuration
- Non-destructive (never overwrites existing configs)

## Prerequisites

- Ubuntu/Debian Linux (20.04+ or 11+)
- Node.js 18+, npm 9+
- Python 3.10+
- Git 2.30+

## Installation

### From Personal Marketplace

1. **Clone or update marketplace**:
   ```bash
   cd ~/.claude/plugins/marketplaces/<your-marketplace>
   git pull  # If already cloned
   ```

2. **Verify plugin loaded**:
   ```bash
   claude /help
   # Should see /portable:* commands
   ```

3. **Use on new server**:
   ```bash
   # Clone marketplace first
   git clone <your-marketplace-repo> ~/.claude/plugins/marketplaces/<marketplace-name>

   # Then run install
   /portable:install
   ```

## Commands

- `/portable:install [--path <dir>]` - Install from included template
- `/portable:export [--output-dir <dir>]` - Export current configuration
- `/portable:sync [--message <msg>]` - Synchronize via git
- `/portable:validate [--strict]` - Validate installation
- `/portable:docs <topic>` - View documentation

## Troubleshooting

### Installation Issues

**Claude Code not found after installation:**
```bash
# Verify installation
npm list -g claude-code

# If missing, reinstall
npm install -g claude-code

# Reload shell
source ~/.bashrc
```

### Sync Issues

**Git push fails during sync:**
```bash
# Check repository permissions
cd ~/.claude/plugins/marketplaces/<marketplace>
git remote -v

# Pull remote changes first
git pull --rebase

# Try sync again
/portable:sync
```

### Validation Warnings

**Configuration needs attention:**
```bash
# Edit ntfy topics
nano ~/.config/claude-code/.env

# Add GitHub token
nano ~/.npmrc

# Re-validate
/portable:validate
```

## Learn More

Use the `/portable:docs` command or activate the portable-setup skill to learn about portability and synchronization best practices.

For detailed documentation:
- `/portable:docs readme` - Quick start guide
- `/portable:docs dependencies` - System requirements
- `/portable:docs customization` - Customization options

## Version

- **Plugin Version**: 1.0.0
- **Template Version**: Check `assets/template/` for current tarball timestamp
