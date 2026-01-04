#!/bin/bash
# Claude Code Portable Setup
# Automated installation script for new servers

set -e

echo "🚀 Claude Code Portable Setup"
echo "=============================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Check prerequisites
echo "📋 Checking prerequisites..."

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅${NC} $1 installed: $($1 --version 2>&1 | head -1 || echo 'version unknown')"
        return 0
    else
        echo -e "  ${RED}❌${NC} $1 not found"
        return 1
    fi
}

MISSING_DEPS=0

check_command "git" || MISSING_DEPS=1
check_command "node" || MISSING_DEPS=1
check_command "npm" || MISSING_DEPS=1
check_command "python3" || MISSING_DEPS=1

if [ $MISSING_DEPS -eq 1 ]; then
    echo ""
    echo -e "${RED}❌ Missing required dependencies!${NC}"
    echo "Please install missing packages and try again."
    echo ""
    echo "See docs/DEPENDENCIES.md for installation instructions."
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites met${NC}"
echo ""

# 2. Install Claude Code if not present
if ! command -v claude >/dev/null 2>&1; then
    echo "📦 Installing Claude Code..."
    npm install -g claude-code
    echo -e "${GREEN}✅ Claude Code installed${NC}"
else
    echo -e "${GREEN}✅ Claude Code already installed${NC}"
fi

# 3. Install additional tools
echo ""
echo "📦 Installing additional tools..."

# Install GitHub CLI if not present
if ! command -v gh >/dev/null 2>&1; then
    echo "  Installing GitHub CLI..."
    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        type -p curl >/dev/null || sudo apt install curl -y
        curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
        sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
        sudo apt update
        sudo apt install gh -y
    else
        echo -e "${YELLOW}⚠️  Please install GitHub CLI manually for your OS${NC}"
    fi
else
    echo -e "  ${GREEN}✅ GitHub CLI already installed${NC}"
fi

# Install claudeup if not present
if ! command -v claudeup >/dev/null 2>&1; then
    echo "  Installing claudeup..."
    npm install -g claudeup
else
    echo -e "  ${GREEN}✅ claudeup already installed${NC}"
fi

# 4. Create directory structure
echo ""
echo "📁 Creating directories..."
mkdir -p ~/.claude
mkdir -p ~/.config/claude-code
mkdir -p ~/.config/git

echo -e "${GREEN}✅ Directories created${NC}"

# 5. Copy Claude configuration
echo ""
echo "📋 Installing Claude configuration..."

if [ -d "config/claude" ]; then
    # Copy settings.json
    if [ -f "config/claude/settings.json" ]; then
        cp config/claude/settings.json ~/.claude/
        echo -e "  ${GREEN}✅${NC} Installed settings.json"
    fi

    # Copy custom statusline scripts
    if [ -f "config/claude/statusline.sh" ]; then
        cp config/claude/statusline*.sh ~/.claude/ 2>/dev/null || true
        chmod +x ~/.claude/statusline*.sh 2>/dev/null || true
        echo -e "  ${GREEN}✅${NC} Installed custom statusline scripts"
    fi

    # Note about excluded custom content
    echo -e "  ${YELLOW}ℹ️${NC}  SuperClaude framework not included (add your own if needed)"
    echo -e "  ${YELLOW}ℹ️${NC}  Custom agents and commands not included (add your own as needed)"
else
    echo -e "  ${YELLOW}⚠️${NC} config/claude directory not found"
fi

# 6. Copy Claude Code config
echo ""
echo "⚙️  Installing Claude Code configuration..."

if [ -d "config/claude-code" ]; then
    # Copy config.json
    if [ -f "config/claude-code/config.json" ]; then
        cp config/claude-code/config.json ~/.config/claude-code/
        echo -e "  ${GREEN}✅${NC} Installed config.json"
    fi

    # Copy .env template
    if [ ! -f ~/.config/claude-code/.env ]; then
        if [ -f "config/claude-code/.env.template" ]; then
            cp config/claude-code/.env.template ~/.config/claude-code/.env
            echo -e "  ${YELLOW}⚠️${NC} Created .env from template - ${RED}REQUIRES CONFIGURATION${NC}"
        fi
    else
        echo -e "  ${GREEN}✅${NC} .env already exists (not overwriting)"
    fi

    # Note about excluded custom content
    echo -e "  ${YELLOW}ℹ️${NC}  Custom hooks not included (add your own as needed)"
else
    echo -e "  ${YELLOW}⚠️${NC} config/claude-code directory not found"
fi

# 7. Copy system config
echo ""
echo "🔧 Installing system configuration..."

# tmux
if [ -f "config/system/.tmux.conf" ]; then
    cp config/system/.tmux.conf ~/
    echo -e "  ${GREEN}✅${NC} Installed .tmux.conf"
fi

# bashrc additions
if [ -f "config/system/.bashrc.additions" ]; then
    if ! grep -q "# Claude Code additions" ~/.bashrc 2>/dev/null; then
        cat config/system/.bashrc.additions >> ~/.bashrc
        echo -e "  ${GREEN}✅${NC} Added Claude Code additions to .bashrc"
    else
        echo -e "  ${GREEN}✅${NC} .bashrc already has Claude Code additions"
    fi
fi

# npmrc
if [ ! -f ~/.npmrc ]; then
    if [ -f "config/system/.npmrc.template" ]; then
        cp config/system/.npmrc.template ~/.npmrc
        echo -e "  ${YELLOW}⚠️${NC} Created .npmrc from template - ${RED}REQUIRES GITHUB TOKEN${NC}"
    fi
else
    echo -e "  ${GREEN}✅${NC} .npmrc already exists (not overwriting)"
fi

# git ignore
if [ -f "config/system/git-ignore" ]; then
    cp config/system/git-ignore ~/.config/git/ignore
    echo -e "  ${GREEN}✅${NC} Installed git ignore patterns"
fi

# 8. Configure git
echo ""
echo "🔧 Configuring git..."

if ! git config --global user.name >/dev/null 2>&1; then
    echo "Git user configuration needed:"
    read -p "Enter your name: " git_name
    read -p "Enter your email: " git_email
    git config --global user.name "$git_name"
    git config --global user.email "$git_email"
    echo -e "${GREEN}✅ Git user configured${NC}"
else
    echo -e "${GREEN}✅ Git already configured${NC}"
    echo "  Name: $(git config --global user.name)"
    echo "  Email: $(git config --global user.email)"
fi

# Set HTTPS protocol
git config --global git_protocol https 2>/dev/null || true
git config --global url."https://github.com/".insteadOf git@github.com: 2>/dev/null || true
echo -e "${GREEN}✅ Git protocol set to HTTPS${NC}"

# 9. Install agent-deck
echo ""
echo "🎯 Installing agent-deck..."

# Get repository URL from config
if [ -f "config/agent-deck/repo.txt" ]; then
    AGENT_DECK_REPO=$(cat config/agent-deck/repo.txt)
    echo -e "  📍 Repository: $AGENT_DECK_REPO"
else
    AGENT_DECK_REPO="https://github.com/tchow-twistedxcom/agent-deck.git"
    echo -e "  📍 Using default repository: $AGENT_DECK_REPO"
fi

# Install Go if not present (required for agent-deck)
if ! command -v go >/dev/null 2>&1; then
    echo -e "  ${YELLOW}⚠️${NC} Go not installed - attempting to install..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Download and install latest Go
        GO_VERSION="1.24.0"
        wget -q "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -O /tmp/go.tar.gz
        sudo rm -rf /usr/local/go
        sudo tar -C /usr/local -xzf /tmp/go.tar.gz
        rm /tmp/go.tar.gz

        # Add Go to PATH
        if ! grep -q "/usr/local/go/bin" ~/.bashrc; then
            echo 'export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin' >> ~/.bashrc
        fi
        export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin
        echo -e "  ${GREEN}✅${NC} Installed Go ${GO_VERSION}"
    else
        echo -e "  ${RED}❌${NC} Please install Go manually: https://go.dev/dl/"
        echo -e "  ${YELLOW}⚠️${NC} Skipping agent-deck installation"
        SKIP_AGENT_DECK=1
    fi
fi

if [ -z "$SKIP_AGENT_DECK" ]; then
    # Clone agent-deck from repository
    if [ -d ~/agent-deck ]; then
        echo -e "  ${YELLOW}ℹ️${NC}  ~/agent-deck already exists"
        read -p "  Update existing installation? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cd ~/agent-deck
            git pull
            echo -e "  ${GREEN}✅${NC} Updated agent-deck from repository"
        else
            echo -e "  ${YELLOW}⚠️${NC} Skipping agent-deck update"
            SKIP_AGENT_DECK=1
        fi
    else
        git clone "$AGENT_DECK_REPO" ~/agent-deck
        echo -e "  ${GREEN}✅${NC} Cloned agent-deck from repository"
    fi

    if [ -z "$SKIP_AGENT_DECK" ]; then
        # Build agent-deck
        cd ~/agent-deck
        if go build -o agent-deck .; then
            echo -e "  ${GREEN}✅${NC} Built agent-deck binary"

            # Add to PATH if not already there
            if ! grep -q "$HOME/agent-deck" ~/.bashrc; then
                echo 'export PATH=$PATH:$HOME/agent-deck' >> ~/.bashrc
            fi
            export PATH=$PATH:$HOME/agent-deck

            cd - > /dev/null
            echo -e "  ${GREEN}✅${NC} agent-deck installed successfully"
            echo -e "  ${YELLOW}ℹ️${NC}  Run 'agent-deck' to start the AI agent manager"
            echo -e "  ${YELLOW}ℹ️${NC}  Update anytime with: cd ~/agent-deck && git pull && go build"
        else
            echo -e "  ${RED}❌${NC} Failed to build agent-deck"
        fi
    fi
fi

# 10. GitHub CLI authentication
echo ""
echo "🔑 GitHub CLI authentication..."

if command -v gh >/dev/null 2>&1; then
    if ! gh auth status >/dev/null 2>&1; then
        echo "GitHub CLI needs authentication:"
        gh auth login
    else
        echo -e "${GREEN}✅ GitHub CLI already authenticated${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ GitHub CLI not installed, skipping authentication${NC}"
fi

# 11. Install @owloops/claude-powerline if using it
echo ""
echo "📦 Installing statusline package..."

if grep -q "@owloops/claude-powerline" ~/.claude/settings.json 2>/dev/null; then
    npm install -g @owloops/claude-powerline
    echo -e "${GREEN}✅ Installed @owloops/claude-powerline${NC}"
else
    echo -e "${YELLOW}⚠️ Statusline package not needed for current configuration${NC}"
fi

# 12. Validate installation
echo ""
echo "✅ Running validation..."

if [ -f "scripts/validate-setup.sh" ]; then
    chmod +x scripts/validate-setup.sh
    ./scripts/validate-setup.sh
else
    echo -e "${YELLOW}⚠️ Validation script not found${NC}"
fi

# 13. Final summary
echo ""
echo "════════════════════════════════════════"
echo "✨ Setup Complete!"
echo "════════════════════════════════════════"
echo ""

# Check what needs configuration
NEEDS_CONFIG=0

if grep -q "YOUR_TOPIC_HERE" ~/.config/claude-code/.env 2>/dev/null; then
    echo -e "${RED}⚠️  Action Required:${NC} Configure ~/.config/claude-code/.env"
    echo "   Edit ntfy topics: nano ~/.config/claude-code/.env"
    NEEDS_CONFIG=1
fi

if grep -q "YOUR_GITHUB_TOKEN" ~/.npmrc 2>/dev/null; then
    echo -e "${RED}⚠️  Action Required:${NC} Configure ~/.npmrc"
    echo "   Add GitHub PAT: nano ~/.npmrc"
    echo "   Generate token at: https://github.com/settings/tokens"
    NEEDS_CONFIG=1
fi

if [ $NEEDS_CONFIG -eq 0 ]; then
    echo -e "${GREEN}✅ Configuration complete!${NC}"
fi

echo ""
echo "📝 Next Steps:"
echo "  1. Reload shell: source ~/.bashrc"
echo "  2. Test Claude Code: claude --version"
echo "  3. Check statusline: claude (in any directory)"

if [ $NEEDS_CONFIG -eq 1 ]; then
    echo "  4. Complete configuration as noted above"
fi

echo ""
echo "📚 Documentation:"
echo "  - docs/SETUP.md - Detailed setup guide"
echo "  - docs/DEPENDENCIES.md - Dependency information"
echo "  - docs/CUSTOMIZATION.md - Customization options"
echo ""
