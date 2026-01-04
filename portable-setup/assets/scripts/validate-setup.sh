#!/bin/bash
# Validate Claude Code portable setup installation

echo "🔍 Validating Claude Code Setup"
echo "================================"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} $1 installed"
        return 0
    else
        echo -e "${RED}❌${NC} $1 not found"
        ((ERRORS++))
        return 1
    fi
}

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅${NC} $2"
        return 0
    else
        echo -e "${RED}❌${NC} $2 missing"
        ((ERRORS++))
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✅${NC} $2"
        return 0
    else
        echo -e "${RED}❌${NC} $2 missing"
        ((ERRORS++))
        return 1
    fi
}

check_warning() {
    if [ "$1" = "true" ]; then
        echo -e "${YELLOW}⚠️${NC}  $2"
        ((WARNINGS++))
    else
        echo -e "${GREEN}✅${NC} $2"
    fi
}

# Check core tools
echo "Core Tools:"
check_command "claude"
check_command "git"
check_command "node"
check_command "npm"
check_command "python3"

echo ""
echo "Additional Tools:"
check_command "gh"
check_command "claudeup"
check_command "tmux"

# Check Claude configuration
echo ""
echo "Claude Configuration:"
check_file ~/.claude/settings.json "Settings.json"

echo -e "  ${YELLOW}ℹ️${NC}  SuperClaude framework not included in portable setup (user-specific)"
echo -e "  ${YELLOW}ℹ️${NC}  Custom agents not included in portable setup (user-specific)"
echo -e "  ${YELLOW}ℹ️${NC}  Custom commands not included in portable setup (user-specific)"

# Check Claude Code config
echo ""
echo "Claude Code Configuration:"
check_file ~/.config/claude-code/config.json "config.json"

echo -e "  ${YELLOW}ℹ️${NC}  Custom hooks not included in portable setup (user-specific)"

# Check .env configuration
echo ""
echo "Environment Configuration:"
if [ -f ~/.config/claude-code/.env ]; then
    if grep -q "YOUR_TOPIC_HERE" ~/.config/claude-code/.env; then
        check_warning "true" ".env exists but needs configuration"
    else
        check_warning "false" ".env configured"
    fi
else
    echo -e "${RED}❌${NC} .env file missing"
    ((ERRORS++))
fi

# Check system configuration
echo ""
echo "System Configuration:"
check_file ~/.tmux.conf "tmux configuration"
check_file ~/.npmrc "npm configuration"

if [ -f ~/.npmrc ]; then
    if grep -q "YOUR_GITHUB_TOKEN" ~/.npmrc; then
        check_warning "true" "npmrc exists but needs GitHub token"
    else
        check_warning "false" "npmrc configured with token"
    fi
fi

# Check git configuration
echo ""
echo "Git Configuration:"
if git config --global user.name >/dev/null 2>&1; then
    NAME=$(git config --global user.name)
    EMAIL=$(git config --global user.email)
    echo -e "${GREEN}✅${NC} Git user configured"
    echo -e "  ${GREEN}ℹ️${NC}  Name: $NAME"
    echo -e "  ${GREEN}ℹ️${NC}  Email: $EMAIL"
else
    echo -e "${YELLOW}⚠️${NC}  Git user not configured"
    ((WARNINGS++))
fi

# Check GitHub CLI authentication
echo ""
echo "GitHub CLI:"
if command -v gh >/dev/null 2>&1; then
    if gh auth status >/dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} GitHub CLI authenticated"
    else
        echo -e "${YELLOW}⚠️${NC}  GitHub CLI not authenticated"
        ((WARNINGS++))
    fi
else
    echo -e "${YELLOW}⚠️${NC}  GitHub CLI not installed"
    ((WARNINGS++))
fi

# Check statusline package
echo ""
echo "Statusline:"
if [ -f ~/.claude/settings.json ]; then
    if grep -q "@owloops/claude-powerline" ~/.claude/settings.json; then
        if npm list -g @owloops/claude-powerline >/dev/null 2>&1; then
            echo -e "${GREEN}✅${NC} @owloops/claude-powerline installed"
        else
            echo -e "${YELLOW}⚠️${NC}  @owloops/claude-powerline not installed (required by settings.json)"
            ((WARNINGS++))
        fi
    else
        echo -e "${GREEN}ℹ️${NC}  Custom statusline configuration"
    fi
fi

# Version information
echo ""
echo "Version Information:"
echo -e "${GREEN}ℹ️${NC}  Claude Code: $(claude --version 2>/dev/null || echo 'unknown')"
echo -e "${GREEN}ℹ️${NC}  Node.js: $(node --version 2>/dev/null || echo 'unknown')"
echo -e "${GREEN}ℹ️${NC}  npm: $(npm --version 2>/dev/null || echo 'unknown')"
echo -e "${GREEN}ℹ️${NC}  Python: $(python3 --version 2>/dev/null || echo 'unknown')"
echo -e "${GREEN}ℹ️${NC}  Git: $(git --version 2>/dev/null || echo 'unknown')"

# Summary
echo ""
echo "════════════════════════════════════════"
echo "Validation Summary"
echo "════════════════════════════════════════"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ Perfect!${NC} Setup is complete and fully configured."
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Warnings:${NC} $WARNINGS items need attention (optional)"
    echo ""
    echo "Setup is functional but some optional items need configuration."
    exit 0
else
    echo -e "${RED}❌ Errors:${NC} $ERRORS critical items missing"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Warnings:${NC} $WARNINGS items need attention"
    fi
    echo ""
    echo "Please review errors above and re-run setup if needed."
    exit 1
fi
