#!/bin/bash
# Export current Claude Code configuration for portable setup
# Creates a tarball with all configuration files, stripping secrets

set -e

EXPORT_DIR="claude-code-portable-$(date +%Y%m%d)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Support both standalone and plugin usage
# In plugin: files are in same directory and docs in ../docs/
# Standalone: files are in portable-templates/ subdirectory
if [ -f "$SCRIPT_DIR/setup.sh" ]; then
    # Plugin mode - files in same directory
    TEMPLATES_DIR="$SCRIPT_DIR"
    DOCS_DIR="$BASE_DIR/docs"
elif [ -d "$SCRIPT_DIR/portable-templates" ]; then
    # Standalone mode - files in portable-templates/
    TEMPLATES_DIR="$SCRIPT_DIR/portable-templates"
    DOCS_DIR="$SCRIPT_DIR/portable-templates"
else
    echo "❌ Error: Cannot find template files"
    echo "Expected setup.sh in $SCRIPT_DIR or $SCRIPT_DIR/portable-templates/"
    exit 1
fi

echo "🚀 Claude Code Configuration Export"
echo "===================================="
echo ""

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p "$EXPORT_DIR"/{config/{claude,claude-code,system},docs,scripts}

# Copy Claude framework files
echo "📋 Copying Claude configuration..."
if [ -d ~/.claude ]; then
    # Skip framework markdown files (SuperClaude framework excluded)
    echo "  ⏭️  Skipping SuperClaude framework files"

    # Skip agents directory (custom agents excluded)
    echo "  ⏭️  Skipping custom agents directory"

    # Skip commands directory (custom commands excluded)
    echo "  ⏭️  Skipping custom commands directory"

    # Copy settings.json
    if [ -f ~/.claude/settings.json ]; then
        cp ~/.claude/settings.json "$EXPORT_DIR/config/claude/"
        echo "  ✅ Copied settings.json"
    fi

    # Copy custom statusline scripts if they exist
    if [ -f ~/.claude/statusline.sh ]; then
        cp ~/.claude/statusline*.sh "$EXPORT_DIR/config/claude/" 2>/dev/null || true
        echo "  ✅ Copied custom statusline scripts"
    fi
else
    echo "  ⚠️  ~/.claude/ directory not found"
fi

# Copy Claude Code configuration (strip secrets)
echo "⚙️  Copying Claude Code configuration..."
if [ -d ~/.config/claude-code ]; then
    # Copy config.json
    if [ -f ~/.config/claude-code/config.json ]; then
        cp ~/.config/claude-code/config.json "$EXPORT_DIR/config/claude-code/"
        echo "  ✅ Copied config.json"
    fi

    # Skip hooks directory (custom hooks excluded)
    echo "  ⏭️  Skipping custom hooks directory"

    # Create .env template (strip secrets)
    if [ -f ~/.config/claude-code/.env ]; then
        sed 's/NTFY_TOPIC=.*/NTFY_TOPIC=YOUR_TOPIC_HERE/g' \
            ~/.config/claude-code/.env > "$EXPORT_DIR/config/claude-code/.env.template"
        echo "  ✅ Created .env.template (secrets stripped)"
    else
        # Create default template if .env doesn't exist
        cat > "$EXPORT_DIR/config/claude-code/.env.template" <<'EOF'
# ntfy.sh notification topics
NTFY_TOPIC_DEFAULT=YOUR_TOPIC_HERE
NTFY_TOPIC_ERRORS=YOUR_ERRORS_TOPIC_HERE

# Features
NTFY_ENABLE_SOUND=true
NTFY_ENABLE_DESKTOP=true
NTFY_DAILY_SUMMARY=true
EOF
        echo "  ✅ Created default .env.template"
    fi
else
    echo "  ⚠️  ~/.config/claude-code/ directory not found"
fi

# Copy system configuration (strip secrets)
echo "🔧 Copying system configuration..."

# tmux configuration
if [ -f ~/.tmux.conf ]; then
    cp ~/.tmux.conf "$EXPORT_DIR/config/system/"
    echo "  ✅ Copied .tmux.conf"
fi

# bashrc additions (extract Claude Code specific sections)
if [ -f ~/.bashrc ]; then
    # Try to find Claude Code additions section
    if grep -q "# Claude Code additions" ~/.bashrc; then
        sed -n '/# Claude Code additions/,$p' ~/.bashrc > "$EXPORT_DIR/config/system/.bashrc.additions"
        echo "  ✅ Extracted .bashrc additions"
    else
        # If no marker, create empty file with instructions
        cat > "$EXPORT_DIR/config/system/.bashrc.additions" <<'EOF'
# Claude Code additions
# Add your custom bash configurations here

# Example: Add aliases
# alias cc='claude'
EOF
        echo "  ⚠️  No Claude Code additions found in .bashrc, created template"
    fi
fi

# npmrc (strip GitHub token)
if [ -f ~/.npmrc ]; then
    sed 's/ghp_[^[:space:]]*/YOUR_GITHUB_TOKEN/g' \
        ~/.npmrc > "$EXPORT_DIR/config/system/.npmrc.template"
    echo "  ✅ Created .npmrc.template (token stripped)"
else
    # Create default template
    cat > "$EXPORT_DIR/config/system/.npmrc.template" <<'EOF'
@owloops:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=YOUR_GITHUB_TOKEN
EOF
    echo "  ✅ Created default .npmrc.template"
fi

# git ignore
if [ -f ~/.config/git/ignore ]; then
    cp ~/.config/git/ignore "$EXPORT_DIR/config/system/git-ignore"
    echo "  ✅ Copied git ignore"
fi

# GitHub CLI config (may contain auth, so strip)
if [ -f ~/.config/gh/config.yml ]; then
    # Copy but note that user needs to re-auth
    cp ~/.config/gh/config.yml "$EXPORT_DIR/config/system/gh-config.yml.example"
    echo "  ✅ Copied gh config (requires re-authentication)"
fi

# Document agent-deck (will be cloned during installation)
echo "🎯 Documenting agent-deck..."
if [ -d ~/agent-deck/.git ]; then
    cd ~/agent-deck
    AGENT_DECK_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    AGENT_DECK_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    AGENT_DECK_REMOTE=$(git remote get-url origin 2>/dev/null || echo "https://github.com/tchow-twistedxcom/agent-deck.git")
    cd - > /dev/null
    echo "  📌 Current version: $AGENT_DECK_BRANCH @ $AGENT_DECK_COMMIT"
    echo "  📍 Repository: $AGENT_DECK_REMOTE"
    echo "  ⏭️  Will be cloned during installation (not included in tarball)"

    # Store repo URL in a config file for installation
    mkdir -p "$EXPORT_DIR/config/agent-deck"
    echo "$AGENT_DECK_REMOTE" > "$EXPORT_DIR/config/agent-deck/repo.txt"
else
    echo "  ⚠️  ~/agent-deck/.git not found, using default repo"
    mkdir -p "$EXPORT_DIR/config/agent-deck"
    echo "https://github.com/tchow-twistedxcom/agent-deck.git" > "$EXPORT_DIR/config/agent-deck/repo.txt"
fi

# Copy setup scripts
echo "📜 Copying setup scripts..."
cp "$SCRIPT_DIR/export-config.sh" "$EXPORT_DIR/scripts/" 2>/dev/null || true

# Copy setup and validation templates
# Copy setup.sh to root of package
if [ -f "$TEMPLATES_DIR/setup.sh" ]; then
    cp "$TEMPLATES_DIR/setup.sh" "$EXPORT_DIR/"
    chmod +x "$EXPORT_DIR/setup.sh"
    echo "  ✅ Copied setup.sh"
fi

# Copy validate-setup.sh to scripts directory
if [ -f "$TEMPLATES_DIR/validate-setup.sh" ]; then
    cp "$TEMPLATES_DIR/validate-setup.sh" "$EXPORT_DIR/scripts/"
    chmod +x "$EXPORT_DIR/scripts/validate-setup.sh"
    echo "  ✅ Copied validate-setup.sh"
fi

# Copy documentation files
echo "📚 Copying documentation..."
if [ -f "$DOCS_DIR/README.md" ]; then
    cp "$DOCS_DIR/README.md" "$EXPORT_DIR/"
    echo "  ✅ Copied README.md"
fi

if [ -f "$DOCS_DIR/DEPENDENCIES.md" ]; then
    cp "$DOCS_DIR/DEPENDENCIES.md" "$EXPORT_DIR/docs/"
    echo "  ✅ Copied DEPENDENCIES.md"
fi

if [ -f "$DOCS_DIR/CUSTOMIZATION.md" ]; then
    cp "$DOCS_DIR/CUSTOMIZATION.md" "$EXPORT_DIR/docs/"
    echo "  ✅ Copied CUSTOMIZATION.md"
fi

# Document versions
echo "📊 Documenting versions..."
cat > "$EXPORT_DIR/VERSION_INFO.txt" <<EOF
Claude Code Portable Configuration
Exported: $(date)
Exported from: $(hostname)

System Information:
- OS: $(lsb_release -d 2>/dev/null | cut -f2 || echo "Unknown")
- Kernel: $(uname -r)

Installed Versions:
- Node.js: $(node --version 2>/dev/null || echo "Not installed")
- npm: $(npm --version 2>/dev/null || echo "Not installed")
- Python: $(python3 --version 2>/dev/null || echo "Not installed")
- Git: $(git --version 2>/dev/null || echo "Not installed")
- Claude Code: $(claude --version 2>/dev/null || echo "Not installed")
- GitHub CLI: $(gh --version 2>/dev/null | head -1 || echo "Not installed")
- tmux: $(tmux -V 2>/dev/null || echo "Not installed")

Configuration Summary:
- System configuration files: $(find "$EXPORT_DIR/config" -type f 2>/dev/null | wc -l)
- SuperClaude framework: Excluded (user-specific)
- Custom agents: Excluded (user-specific)
- Custom hooks: Excluded (user-specific)
- Custom commands: Excluded (user-specific)
- Agent-deck: Will be cloned from $(cat "$EXPORT_DIR/config/agent-deck/repo.txt" 2>/dev/null || echo "default repo")
EOF

# Create tarball
echo ""
echo "📦 Creating tarball..."
tar -czf "${EXPORT_DIR}.tar.gz" "$EXPORT_DIR"

# Calculate size
SIZE=$(du -h "${EXPORT_DIR}.tar.gz" | cut -f1)

echo ""
echo "✅ Configuration exported successfully!"
echo ""
echo "📦 Package: ${EXPORT_DIR}.tar.gz"
echo "📊 Size: $SIZE"
echo "📁 Location: $(pwd)/${EXPORT_DIR}.tar.gz"
echo ""
echo "⚠️  Security Note:"
echo "  - Secrets have been stripped from configuration files"
echo "  - .env.template and .npmrc.template need manual configuration"
echo "  - GitHub CLI will require re-authentication"
echo ""
echo "📝 Next Steps:"
echo "  1. Transfer ${EXPORT_DIR}.tar.gz to new server"
echo "  2. Extract: tar -xzf ${EXPORT_DIR}.tar.gz"
echo "  3. Run: cd ${EXPORT_DIR} && chmod +x setup.sh && ./setup.sh"
echo ""
