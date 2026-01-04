# Dependencies

Complete dependency list for Claude Code portable setup.

## System Requirements

### Minimum
- **OS**: Ubuntu 20.04+ or Debian 11+
- **RAM**: 4GB
- **Disk**: 10GB free space
- **Network**: Internet connection for package installation

### Recommended
- **OS**: Ubuntu 22.04 LTS or Debian 12
- **RAM**: 8GB
- **Disk**: 20GB free space
- **CPU**: 2+ cores

## Required Software

### Core Tools

#### Node.js 18+
- **Purpose**: JavaScript runtime for Claude Code and npm packages
- **Verify**: `node --version` should show v18.0.0 or higher
- **Install**:
  ```bash
  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
  sudo apt install -y nodejs
  ```

#### npm 9+
- **Purpose**: Package manager for Node.js
- **Verify**: `npm --version` should show 9.0.0 or higher
- **Note**: Typically installed with Node.js

#### Python 3.10+
- **Purpose**: Runtime for agent scripts and automation
- **Verify**: `python3 --version` should show Python 3.10.0 or higher
- **Install**:
  ```bash
  sudo apt update
  sudo apt install -y python3 python3-pip python3-venv
  ```

#### Git 2.30+
- **Purpose**: Version control and GitHub integration
- **Verify**: `git --version` should show git version 2.30 or higher
- **Install**:
  ```bash
  sudo apt install -y git
  ```

### Claude Code Tools

#### claude-code (CLI)
- **Purpose**: Main Claude Code interface
- **Install**: `npm install -g claude-code`
- **Verify**: `claude --version`

#### GitHub CLI (gh)
- **Purpose**: GitHub authentication and API access
- **Install**:
  ```bash
  type -p curl >/dev/null || sudo apt install curl -y
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | \
    sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
  sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) \
    signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] \
    https://cli.github.com/packages stable main" | \
    sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
  sudo apt update
  sudo apt install gh -y
  ```
- **Verify**: `gh --version`

#### claudeup
- **Purpose**: Statusline template manager
- **Install**: `npm install -g claudeup`
- **Verify**: `claudeup --version`

#### @owloops/claude-powerline
- **Purpose**: Powerline statusline for Claude Code
- **Install**: `npm install -g @owloops/claude-powerline`
- **Note**: Only needed if using powerline statusline

### System Tools

#### tmux 3.0+
- **Purpose**: Terminal multiplexer for session management
- **Install**: `sudo apt install -y tmux`
- **Verify**: `tmux -V`

#### curl/wget
- **Purpose**: File downloads and HTTP requests
- **Install**: `sudo apt install -y curl wget`

## Optional Software

### Docker 20+
- **Purpose**: Local ntfy.sh server for notifications
- **Install**:
  ```bash
  curl -fsSL https://get.docker.com -o get-docker.sh
  sudo sh get-docker.sh
  sudo usermod -aG docker $USER
  ```
- **Verify**: `docker --version`
- **Note**: Logout and login after adding user to docker group

### Go 1.20+
- **Purpose**: Development of agent-deck and Go tools
- **Install**:
  ```bash
  wget https://go.dev/dl/go1.21.0.linux-amd64.tar.gz
  sudo rm -rf /usr/local/go
  sudo tar -C /usr/local -xzf go1.21.0.linux-amd64.tar.gz
  echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
  source ~/.bashrc
  ```
- **Verify**: `go version`

## Python Packages

### Core Packages (installed with Python)
- `pip` - Python package manager
- `venv` - Virtual environment support

### Project-Specific Packages
Refer to individual project `requirements.txt` files for specific Python dependencies.

Example installation:
```bash
cd /path/to/project
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## NPM Global Packages

### Required
```bash
npm install -g claude-code
npm install -g claudeup
```

### Optional (based on configuration)
```bash
npm install -g @owloops/claude-powerline  # If using powerline statusline
```

## Complete Installation Script

### Ubuntu/Debian
```bash
#!/bin/bash
# Complete dependency installation for Ubuntu/Debian

set -e

echo "Installing Claude Code dependencies..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js
echo "Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install Python
echo "Installing Python..."
sudo apt install -y python3 python3-pip python3-venv

# Install Git
echo "Installing Git..."
sudo apt install -y git

# Install GitHub CLI
echo "Installing GitHub CLI..."
type -p curl >/dev/null || sudo apt install curl -y
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | \
  sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] \
  https://cli.github.com/packages stable main" | \
  sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh -y

# Install tmux
echo "Installing tmux..."
sudo apt install -y tmux

# Install system utilities
sudo apt install -y curl wget build-essential

# Install Claude Code and tools
echo "Installing Claude Code and tools..."
npm install -g claude-code
npm install -g claudeup
npm install -g @owloops/claude-powerline

echo "✅ All dependencies installed!"
echo ""
echo "Verify installation:"
echo "  node --version"
echo "  npm --version"
echo "  python3 --version"
echo "  git --version"
echo "  gh --version"
echo "  claude --version"
echo "  tmux -V"
```

## Verification

### Quick Check
```bash
# Core tools
node --version      # v18.0.0+
npm --version       # 9.0.0+
python3 --version   # Python 3.10+
git --version       # git version 2.30+

# Claude Code tools
claude --version    # Latest version
gh --version        # gh version 2.0+
claudeup --version  # Latest version

# System tools
tmux -V             # tmux 3.0+
```

### Detailed Check
Run the validation script included in the portable package:
```bash
./scripts/validate-setup.sh
```

## Troubleshooting

### Node.js Version Too Old
```bash
# Remove old version
sudo apt remove nodejs

# Install Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### npm Permission Errors
```bash
# Fix npm global install permissions
mkdir -p ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

### Python pip Not Found
```bash
sudo apt install -y python3-pip
```

### GitHub CLI Not Authenticating
```bash
# Clear existing auth
gh auth logout

# Re-authenticate
gh auth login

# Follow browser prompts
```

### tmux Command Not Found
```bash
sudo apt update
sudo apt install -y tmux
```

## Platform-Specific Notes

### Ubuntu 20.04
- Default Python is 3.8, may need to install python3.10 separately:
  ```bash
  sudo add-apt-repository ppa:deadsnakes/ppa
  sudo apt update
  sudo apt install python3.10 python3.10-venv
  ```

### Ubuntu 22.04
- All dependencies available in default repositories
- Recommended platform for easiest setup

### Debian 11
- Similar to Ubuntu 20.04, may need newer Python
- Install from backports or build from source

### Debian 12
- All dependencies available in default repositories
- Recommended Debian version

## Network Requirements

### Package Sources
- **Node.js**: https://deb.nodesource.com
- **GitHub CLI**: https://cli.github.com/packages
- **npm packages**: https://registry.npmjs.org
- **Python packages**: https://pypi.org

### Firewall Considerations
If behind a firewall, ensure access to:
- Port 443 (HTTPS) for all package downloads
- Port 80 (HTTP) for some package repositories
- GitHub.com for authentication and package downloads

## Disk Space Requirements

### Installation
- Node.js + npm: ~200MB
- Python: ~100MB
- Git: ~50MB
- Claude Code + tools: ~100MB
- Configuration files: ~50MB
- **Total**: ~500MB

### Runtime
- Project dependencies (varies): 500MB - 2GB
- npm global packages: ~100MB
- Session data and logs: ~100MB
- **Total**: ~1-3GB

### Recommended
- Keep 10GB free for development work
- Additional space for Docker images if using containerized ntfy

## Update Strategy

### System Packages
```bash
sudo apt update && sudo apt upgrade -y
```

### Node.js Packages
```bash
npm update -g claude-code
npm update -g claudeup
npm update -g @owloops/claude-powerline
```

### Python Packages
```bash
# Per-project virtual environments
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### Configuration Updates
Re-run export script to capture latest configuration:
```bash
./scripts/export-config.sh
```
