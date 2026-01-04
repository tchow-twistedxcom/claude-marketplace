# Claude Code Portable Setup

Complete Claude Code configuration package for easy setup on new servers.

## Quick Start

```bash
# Extract package
tar -xzf claude-code-portable-YYYYMMDD.tar.gz
cd claude-code-portable-YYYYMMDD

# Run setup
chmod +x setup.sh
./setup.sh

# Configure secrets
nano ~/.config/claude-code/.env
nano ~/.npmrc

# Reload shell
source ~/.bashrc

# Verify installation
claude --version
```

## What's Included

### System Configuration
- **Statusline**: Custom powerline-based statusline with usage tracking
- **System Dotfiles**: tmux, git, bash, npm configurations
- **.env template**: Environment variable configuration template
- **Claude Code Settings**: Basic settings.json configuration

### What's NOT Included

The following are user-specific and excluded from the portable package:
- **SuperClaude Framework**: CLAUDE.md, FLAGS.md, PRINCIPLES.md, RULES.md, behavioral modes, MCP guides
- **Custom Agents**: User-specific agent definitions
- **Custom Commands**: User-specific command implementations
- **Custom Hooks**: User-specific automation hooks

This keeps the portable setup minimal and focused on system configuration, allowing you to add your own framework and customizations per installation.

## Prerequisites

### Required
- Ubuntu/Debian Linux (20.04+ or 11+)
- Node.js 18+ and npm 9+
- Python 3.10+
- Git 2.30+
- 4GB RAM minimum (8GB recommended)
- 10GB free disk space

### Optional
- Docker 20+ (for local ntfy notifications)
- Go 1.20+ (for agent-deck development)

## What Gets Configured

```
~/.claude/                      # Claude Code configuration
└── settings.json               # Statusline config

~/.config/claude-code/          # Claude Code configuration
├── config.json                 # Main configuration
└── .env                        # Environment variables

~/                              # System dotfiles
├── .tmux.conf                  # Terminal multiplexer
├── .bashrc                     # Shell additions (Claude Code specific)
├── .npmrc                      # NPM registry + GitHub token
└── .config/git/ignore          # Git ignore patterns
```

**Note**: SuperClaude framework files, custom agents, commands, and hooks are not included. Add your own customizations after installation.

## Installation

### Step 1: Extract Package

```bash
tar -xzf claude-code-portable-YYYYMMDD.tar.gz
cd claude-code-portable-YYYYMMDD
```

### Step 2: Run Setup Script

```bash
chmod +x setup.sh
./setup.sh
```

The setup script will:
1. Check prerequisites
2. Install Claude Code and additional tools
3. Create directory structure
4. Copy all configuration files
5. Set up git configuration
6. Authenticate GitHub CLI
7. Validate installation

### Step 3: Configure Secrets

#### ntfy Topics
Edit `~/.config/claude-code/.env`:
```bash
nano ~/.config/claude-code/.env
```

Replace placeholders:
```bash
NTFY_TOPIC_DEFAULT=your-actual-topic
NTFY_TOPIC_ERRORS=your-errors-topic
```

#### GitHub Personal Access Token
Edit `~/.npmrc`:
```bash
nano ~/.npmrc
```

Generate token at: https://github.com/settings/tokens

Required scopes: `repo`, `read:packages`

Replace `YOUR_GITHUB_TOKEN` with your actual token.

### Step 4: Reload Shell

```bash
source ~/.bashrc
```

### Step 5: Verify Installation

```bash
# Check Claude Code
claude --version

# Run validation
./scripts/validate-setup.sh
```

## Documentation

- **docs/SETUP.md** - Detailed setup guide with troubleshooting
- **docs/DEPENDENCIES.md** - Complete dependency list and installation
- **docs/CUSTOMIZATION.md** - Customization guide for agents, modes, statusline

## Exporting from Current System

To create a new portable package from your current system:

```bash
cd /path/to/scripts
./export-config.sh
```

This will create `claude-code-portable-YYYYMMDD.tar.gz` with all your current configuration.

## Security Notes

### What's Protected
- **Secrets stripped**: All sensitive data removed from templates
- **Template files**: `.env.template` and `.npmrc.template` require manual configuration
- **Re-authentication**: GitHub CLI requires fresh authentication
- **Excluded**: Session data, shell snapshots, SSH keys handled separately

### What's Included
- Framework configuration (no secrets)
- Custom agents and commands
- Hooks and automation scripts
- System configuration templates
- Documentation

## Common Issues

### Claude Code Not Found After Installation
```bash
# Verify global npm installation
npm list -g claude-code

# If missing, reinstall
npm install -g claude-code

# Check PATH
echo $PATH  # Should include npm global bin
```

### Statusline Not Showing
```bash
# Check settings
cat ~/.claude/settings.json

# Verify powerline package
npm list -g @owloops/claude-powerline

# If missing, install
npm install -g @owloops/claude-powerline
```

### GitHub CLI Authentication Failed
```bash
# Re-authenticate
gh auth login

# Follow prompts to authenticate via browser
```

### ntfy Notifications Not Working
```bash
# Verify .env configuration
cat ~/.config/claude-code/.env

# Test notification
curl -d "Test message" ntfy.sh/your-topic
```

## Support

For issues or questions:
1. Check validation output: `./scripts/validate-setup.sh`
2. Review documentation in `docs/`
3. Check VERSION_INFO.txt for system details

## Version Information

Check `VERSION_INFO.txt` for:
- Export date and source system
- Installed version numbers
- Configuration summary
- System information
