'use strict';
// launcher.cjs — Cross-platform MCP server launcher with uv prerequisite check.
// Node.js is always available in Claude Code, making this the most reliable
// way to provide a helpful install message when uv is missing.

const { spawn, execFileSync } = require('child_process');
const path = require('path');
const os = require('os');

function uvAvailable() {
  try {
    execFileSync('uv', ['--version'], { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

function installInstructions() {
  switch (os.platform()) {
    case 'win32':
      return [
        '  PowerShell : powershell -c "irm https://astral.sh/uv/install.ps1 | iex"',
        '  winget     : winget install --id=astral-sh.uv -e',
      ].join('\n');
    case 'darwin':
      return [
        '  Homebrew : brew install uv',
        '  curl     : curl -LsSf https://astral.sh/uv/install.sh | sh',
      ].join('\n');
    default:
      return '  curl -LsSf https://astral.sh/uv/install.sh | sh';
  }
}

if (!uvAvailable()) {
  process.stderr.write([
    '',
    '╔══════════════════════════════════════════════════════════╗',
    '║  NetSuite SuiteQL MCP — missing prerequisite: uv        ║',
    '╚══════════════════════════════════════════════════════════╝',
    '',
    '  "uv" (Python package manager) is required but not found in PATH.',
    '  Install it for your platform, then restart Claude Code:',
    '',
    installInstructions(),
    '',
    '  Docs: https://docs.astral.sh/uv/getting-started/installation/',
    '',
  ].join('\n') + '\n');
  process.exit(1);
}

const serverPath = path.join(__dirname, 'src', 'server.py');
const proc = spawn(
  'uv',
  ['run', '--with', 'mcp>=1.0.0', '--with', 'httpx>=0.27.0', serverPath],
  { stdio: 'inherit', env: process.env, windowsHide: true }
);

proc.on('error', (err) => {
  process.stderr.write(`[NetSuite SuiteQL] Failed to start server: ${err.message}\n`);
  process.exit(1);
});

proc.on('exit', (code, signal) => {
  process.exit(signal ? 1 : (code ?? 0));
});
