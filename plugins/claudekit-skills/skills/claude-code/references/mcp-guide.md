# MCP Server Selection Guide

Complete reference for choosing and configuring MCP servers in Claude Code.

## MCP Overview

Model Context Protocol (MCP) extends Claude Code with external tool servers. Each server provides specialized capabilities beyond native tools.

---

## Server Selection Matrix

| Task Domain | MCP Server | Transport | Best For |
|-------------|------------|-----------|----------|
| Library documentation | Context7 | stdio | Official docs, framework patterns |
| Complex reasoning | Sequential | stdio | Multi-step analysis, debugging |
| UI components | Magic | stdio | React/Vue components from 21st.dev |
| Browser testing | Playwright | stdio | E2E tests, visual validation |
| Browser inspection | Chrome DevTools | stdio | Live debugging, performance |
| Symbol operations | Serena | stdio | Refactoring, project memory |
| Bulk edits | Morphllm | stdio | Pattern-based transformations |
| Cloud services | HTTP servers | http | OAuth, external APIs |

---

## Server Profiles

### Context7
**Purpose**: Official library documentation lookup

**Use when**:
- Need version-specific API documentation
- Implementing framework-specific patterns
- Following official best practices

**Example queries**:
```
"implement React useEffect correctly"
"add authentication with Auth0"
"migrate to Vue 3 composition API"
```

**Configuration**:
```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
```

---

### Sequential Thinking
**Purpose**: Multi-step reasoning for complex analysis

**Use when**:
- Debugging multi-component issues
- Architectural analysis
- Root cause investigation
- Problems with 3+ interconnected components

**Example queries**:
```
"why is this API endpoint slow?"
"design microservices architecture"
"debug authentication flow failure"
```

**Configuration**:
```json
{
  "mcpServers": {
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    }
  }
}
```

---

### Magic (21st.dev)
**Purpose**: Modern UI component generation

**Use when**:
- Creating React/Vue components
- Building accessible UI patterns
- Need production-ready frontend code

**Example queries**:
```
"create a login form with validation"
"build responsive navigation bar"
"add data table with sorting"
```

**Configuration**:
```json
{
  "mcpServers": {
    "magic": {
      "command": "npx",
      "args": ["-y", "@21st-dev/magic-mcp"]
    }
  }
}
```

---

### Playwright
**Purpose**: Browser automation and E2E testing

**Use when**:
- Testing user flows
- Visual regression testing
- Accessibility validation
- Cross-browser compatibility

**Example queries**:
```
"test the checkout flow"
"validate form submission works"
"check responsive design breakpoints"
```

**Configuration**:
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-playwright"]
    }
  }
}
```

---

### Chrome DevTools
**Purpose**: Live browser inspection and debugging

**Use when**:
- Debugging running web applications
- Performance profiling
- Network inspection
- Console log analysis

**Example queries**:
```
"inspect this page's network requests"
"check for console errors"
"profile page load performance"
```

---

### Serena
**Purpose**: Semantic code understanding with memory

**Use when**:
- Renaming symbols across codebase
- Finding all references to a function
- Project-wide refactoring
- Session persistence needed

**Example queries**:
```
"rename getUserData everywhere"
"find all references to AuthService"
"extract this method to utility"
```

---

### Morphllm
**Purpose**: Pattern-based bulk code transformations

**Use when**:
- Updating many files with same pattern
- Style guide enforcement
- Framework migration
- Bulk text replacements

**Example queries**:
```
"convert all class components to hooks"
"update imports to new path"
"add error handling to all API calls"
```

---

## Transport Types

### stdio (Recommended for Local)
- Direct process communication
- Best for local tools
- Fast, no network overhead
- Used by most MCP servers

### http (Recommended for Cloud)
- REST-based communication
- Required for OAuth flows
- Cloud service integration
- Supports authentication headers

### sse (Deprecated)
- Server-sent events
- Legacy support only
- Use `http` instead for new servers

---

## Configuration Locations

### Project-Level (Recommended)
`.mcp.json` in project root:
```json
{
  "mcpServers": {
    "server-name": {
      "command": "...",
      "args": ["..."]
    }
  }
}
```

### User-Level
`~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "global-server": {
      "command": "...",
      "args": ["..."]
    }
  }
}
```

### Environment Variables
Some servers need environment variables:
```json
{
  "mcpServers": {
    "server-with-env": {
      "command": "node",
      "args": ["server.js"],
      "env": {
        "API_KEY": "${API_KEY}"
      }
    }
  }
}
```

---

## Decision Framework

```
What do you need?
│
├─ Documentation/patterns
│  └─ Context7
│
├─ Complex analysis
│  └─ Sequential Thinking
│
├─ UI components
│  └─ Magic
│
├─ Browser testing
│  ├─ E2E tests → Playwright
│  └─ Live debugging → Chrome DevTools
│
├─ Code refactoring
│  ├─ Symbol operations → Serena
│  └─ Pattern replacement → Morphllm
│
└─ External services
   └─ HTTP MCP servers
```

---

## Troubleshooting

### Server Not Connecting
1. Run `/mcp` to check server status
2. Verify command path exists
3. Check for missing dependencies
4. Review server logs

### Permission Errors
1. Ensure MCP server has file access
2. Check working directory
3. Verify environment variables

### Timeout Issues
1. Increase timeout in config
2. Check network connectivity
3. Verify server is not blocked

---

*See also: [tool-selection.md](tool-selection.md) for native tools*
