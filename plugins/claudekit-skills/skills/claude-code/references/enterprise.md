# Enterprise Features Reference

Guide for enterprise deployment, security, and team workflows.

---

## Authentication & SSO

### SSO Integration
Enterprise plans support SAML/OIDC single sign-on:
- Azure AD
- Okta
- Google Workspace
- Custom SAML providers

### API Key Management
```bash
# Set API key
export ANTHROPIC_API_KEY="your-key"

# Or use config
claude config set apiKey "your-key"
```

### Organization Policies
Administrators can enforce:
- Allowed/blocked tools
- Model restrictions
- Data handling policies
- Session limits

---

## Security Configuration

### Permission Model

Claude Code uses a tiered permission system:

| Level | Description | Example |
|-------|-------------|---------|
| Allow | Always permitted | Read files |
| Ask | Prompt before execute | Write files |
| Deny | Never permitted | Destructive operations |

### Tool Restrictions
```json
{
  "permissions": {
    "allow": ["Read", "Grep", "Glob"],
    "deny": ["Bash"],
    "ask": ["Write", "Edit"]
  }
}
```

### Sandbox Mode
Enable sandbox for restricted execution:
```bash
claude --sandbox "query"
```

Sandbox restrictions:
- No network access
- Limited file system
- Restricted shell commands

---

## Cost Management

### Token Usage Monitoring
```bash
# Check usage
claude usage

# Verbose output shows tokens
claude --verbose "query"
```

### Cost Optimization Strategies

1. **Model Selection**
   - Use `haiku` for simple tasks (fastest, cheapest)
   - Use `sonnet` for standard tasks (balanced)
   - Use `opus` for critical tasks (most capable)

2. **Context Management**
   - Keep prompts concise
   - Use targeted file reads
   - Leverage session continuation

3. **Caching**
   - Enable prompt caching for repeated patterns
   - Use session continuation vs new sessions

### Budget Controls
Set spending limits per user/team:
```json
{
  "limits": {
    "daily_tokens": 1000000,
    "monthly_cost": 500
  }
}
```

---

## Team Workflows

### Shared Configuration
Team settings in `.mcp.json` and `CLAUDE.md`:
```
project/
├── .mcp.json          # Shared MCP servers
├── CLAUDE.md          # Project conventions
└── .claude/
    └── settings.json  # Local overrides
```

### Code Review Integration
```bash
# Review PR changes
claude "review the changes in this PR"

# With specific focus
claude "security review PR #123"
```

### CI/CD Integration
```yaml
# GitHub Actions example
- name: Claude Code Review
  run: |
    claude -p "review changes for security issues" \
      --output-format json > review.json
```

---

## Compliance Features

### Audit Logging
Enterprise plans include:
- Session transcripts
- Tool usage logs
- Model selection history
- Permission decisions

### Data Handling
Configure data policies:
```json
{
  "dataHandling": {
    "logRetention": "30d",
    "excludePatterns": ["*.env", "*.key"],
    "piiDetection": true
  }
}
```

### Compliance Modes
- HIPAA mode
- SOC 2 compliance
- GDPR data handling

---

## Deployment Options

### Self-Hosted
On-premises deployment for maximum control:
- Private model hosting
- Network isolation
- Custom security policies

### Cloud Options
- Anthropic API (default)
- AWS Bedrock
- Google Cloud Vertex AI

### Hybrid Configuration
```json
{
  "deployment": {
    "primary": "anthropic",
    "fallback": "bedrock",
    "routing": {
      "sensitive": "self-hosted",
      "standard": "cloud"
    }
  }
}
```

---

## Monitoring & Observability

### Metrics Collection
Track key metrics:
- Response latency
- Token usage
- Error rates
- Tool invocation frequency

### Integration with Monitoring Tools
```json
{
  "observability": {
    "metrics": "prometheus",
    "tracing": "opentelemetry",
    "logging": "cloudwatch"
  }
}
```

### Alerting
Configure alerts for:
- High error rates
- Budget thresholds
- Unusual activity patterns

---

## Multi-Environment Setup

### Environment Separation
```
environments/
├── development/
│   └── .mcp.json
├── staging/
│   └── .mcp.json
└── production/
    └── .mcp.json
```

### Environment-Specific Config
```bash
# Development
CLAUDE_ENV=development claude "query"

# Production (restricted)
CLAUDE_ENV=production claude --safe-mode "query"
```

---

## Access Control

### Role-Based Access
| Role | Capabilities |
|------|--------------|
| Viewer | Read-only, no tool execution |
| Developer | Standard tools, code editing |
| Admin | Full access, configuration |
| Security | Audit logs, policy management |

### Project-Level Permissions
```json
{
  "projectAccess": {
    "team-a": ["read", "write"],
    "team-b": ["read"],
    "contractors": ["read"]
  }
}
```

---

## Disaster Recovery

### Session Recovery
```bash
# Continue interrupted session
claude -c

# Resume specific session
claude -r "session-name" "continue"
```

### State Persistence
- Automatic checkpoint every 30 minutes
- Session state saved on clean exit
- Recovery from crashes

### Backup Strategies
- Export important sessions
- Version control for configurations
- Regular audit log backups

---

## Performance Tuning

### Concurrency Settings
```json
{
  "performance": {
    "maxConcurrentTools": 10,
    "requestTimeout": 30000,
    "retryAttempts": 3
  }
}
```

### Caching Configuration
```json
{
  "caching": {
    "promptCache": true,
    "responseCache": false,
    "ttl": 3600
  }
}
```

### Resource Limits
```json
{
  "limits": {
    "maxContextTokens": 200000,
    "maxResponseTokens": 16000,
    "maxFileSize": "10MB"
  }
}
```

---

## Getting Enterprise Support

### Support Channels
- Enterprise Slack channel
- Priority email support
- Dedicated account manager

### Documentation
- Private enterprise docs portal
- Custom integration guides
- Security whitepapers

### Training
- Onboarding sessions
- Best practices workshops
- Custom training programs

---

*See also: [CLI reference](cli-reference.md) for command-line options*
