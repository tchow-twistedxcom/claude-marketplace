#!/bin/bash
# Sync Claude Code portable configuration across environments

set -e

# Detect plugin directory
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Validate git repository
if ! git -C "$PLUGIN_DIR" rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Plugin must be in a git repository for sync"
    exit 1
fi

# Check for git remote
if ! git -C "$PLUGIN_DIR" remote get-url origin > /dev/null 2>&1; then
    echo "❌ No git remote configured"
    exit 1
fi

# Export current configuration
echo "📤 Exporting current configuration..."
cd /tmp
bash "$PLUGIN_DIR/assets/scripts/export-config.sh"

# Find the newly created tarball
TARBALL=$(ls -t claude-code-portable-*.tar.gz | head -1)

if [ ! -f "$TARBALL" ]; then
    echo "❌ Export failed - no tarball created"
    exit 1
fi

# Replace old template
echo "🔄 Updating plugin template..."
rm -f "$PLUGIN_DIR/assets/template/"*.tar.gz
mv "$TARBALL" "$PLUGIN_DIR/assets/template/"

# Git operations
echo "📦 Committing changes..."
cd "$PLUGIN_DIR"
git add assets/template/

# Use custom message or default
COMMIT_MSG="${1:-Sync portable config - $TIMESTAMP}"
git commit -m "$COMMIT_MSG"

echo "⬆️  Pushing to remote..."
git push

echo ""
echo "✅ Configuration synchronized!"
echo ""
echo "📦 Updated template: assets/template/$(basename "$PLUGIN_DIR/assets/template/"*.tar.gz)"
echo ""
echo "🔄 To update other environments:"
echo "   1. cd ~/.claude/marketplace && git pull"
echo "   2. /portable:install"
