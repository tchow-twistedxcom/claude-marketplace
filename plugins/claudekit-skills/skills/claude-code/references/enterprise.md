# Enterprise

> Enterprise deployment guide

*Auto-generated from Claude Code documentation on 2025-12-20*
*Source: github.com/ericbuess/claude-code-docs*

---

# Enterprise deployment overview

> Learn how Claude Code can integrate with various third-party services and infrastructure to meet enterprise deployment requirements.

This page provides an overview of available deployment options and helps you choose the right configuration for your organization.

## Provider comparison

<table>
  <thead>
    <tr>
      <th>Feature</th>
      <th>Anthropic</th>
      <th>Amazon Bedrock</th>
      <th>Google Vertex AI</th>
      <th>Microsoft Foundry</th>
    </tr>
  </thead>

  <tbody>
    <tr>
      <td>Regions</td>
      <td>Supported [countries](https://www.anthropic.com/supported-countries)</td>
      <td>Multiple AWS [regions](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html)</td>
      <td>Multiple GCP [regions](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations)</td>
      <td>Multiple Azure [regions](https://azure.microsoft.com/en-us/explore/global-infrastructure/products-by-region/)</td>
    </tr>

    <tr>
      <td>Prompt caching</td>
      <td>Enabled by default</td>
      <td>Enabled by default</td>
      <td>Enabled by default</td>
      <td>Enabled by default</td>
    </tr>

    <tr>
      <td>Authentication</td>
      <td>API key</td>
      <td>API key or AWS credentials</td>
      <td>GCP credentials</td>
      <td>API key or Microsoft Entra ID</td>
    </tr>

    <tr>
      <td>Cost tracking</td>
      <td>Dashboard</td>
      <td>AWS Cost Explorer</td>
      <td>GCP Billing</td>
      <td>Azure Cost Management</td>
    </tr>

    <tr>
      <td>Enterprise features</td>
      <td>Teams, usage monitoring</td>
      <td>IAM policies, CloudTrail</td>
      <td>IAM roles, Cloud Audit Logs</td>
      <td>RBAC policies, Azure Monitor</td>
    </tr>
  </tbody>
</table>

## Cloud providers

<CardGroup cols={3}>
  <Card title="Amazon Bedrock" icon="aws" href="/en/amazon-bedrock">
    Use Claude models through AWS infrastructure with API key or IAM-based authentication and AWS-native monitoring
  </Card>

  <Card title="Google Vertex AI" icon="google" href="/en/google-vertex-ai">
    Access Claude models via Google Cloud Platform with enterprise-grade security and compliance
  </Card>

  <Card title="Microsoft Foundry" icon="microsoft" href="/en/microsoft-foundry">
    Access Claude through Azure with API key or Microsoft Entra ID authentication and Azure billing
  </Card>
</CardGroup>

## Corporate infrastructure

<CardGroup cols={2}>
  <Card title="Enterprise Network" icon="shield" href="/en/network-config">
    Configure Claude Code to work with your organization's proxy servers and SSL/TLS requirements
  </Card>

  <Card title="LLM Gateway" icon="server" href="/en/llm-gateway">
    Deploy centralized model access with usage tracking, budgeting, and audit logging
  </Card>
</CardGroup>

## Configuration overview

Claude Code supports flexible configuration options that allow you to combine different providers and infrastructure:

<Note>
  Understand the difference between:

  * **Corporate proxy**: An HTTP/HTTPS proxy for routing traffic (set via `HTTPS_PROXY` or `HTTP_PROXY`)
  * **LLM Gateway**: A service that handles authentication and provides provider-compatible endpoints (set via `ANTHROPIC_BASE_URL`, `ANTHROPIC_BEDROCK_BASE_URL`, or `ANTHROPIC_VERTEX_BASE_URL`)

  Both configurations can be used in tandem.
</Note>

### Using Bedrock with corporate proxy

Route Bedrock traffic through a corporate HTTP/HTTPS proxy:

```bash  theme={null}
# Enable Bedrock
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_REGION=us-east-1

# Configure corporate proxy
export HTTPS_PROXY='https://proxy.example.com:8080'
```

### Using Bedrock with LLM Gateway

Use a gateway service that provides Bedrock-compatible endpoints:

```bash  theme={null}
# Enable Bedrock
export CLAUDE_CODE_USE_BEDROCK=1

# Configure LLM gateway
export ANTHROPIC_BEDROCK_BASE_URL='https://your-llm-gateway.com/bedrock'
export CLAUDE_CODE_SKIP_BEDROCK_AUTH=1  # If gateway handles AWS auth
```

### Using Foundry with corporate proxy

Route Azure traffic through a corporate HTTP/HTTPS proxy:

```bash  theme={null}
# Enable Microsoft Foundry
export CLAUDE_CODE_USE_FOUNDRY=1
export ANTHROPIC_FOUNDRY_RESOURCE=your-resource
export ANTHROPIC_FOUNDRY_API_KEY=your-api-key  # Or omit for Entra ID auth

# Configure corporate proxy
export HTTPS_PROXY='https://proxy.example.com:8080'
```

### Using Foundry with LLM Gateway

Use a gateway service that provides Azure-compatible endpoints:

```bash  theme={null}
# Enable Microsoft Foundry
export CLAUDE_CODE_USE_FOUNDRY=1

# Configure LLM gateway
export ANTHROPIC_FOUNDRY_BASE_URL='https://your-llm-gateway.com'
export CLAUDE_CODE_SKIP_FOUNDRY_AUTH=1  # If gateway handles Azure auth
```

### Using Vertex AI with corporate proxy

Route Vertex AI traffic through a corporate HTTP/HTTPS proxy:

```bash  theme={null}
# Enable Vertex
export CLAUDE_CODE_USE_VERTEX=1
export CLOUD_ML_REGION=us-east5
export ANTHROPIC_VERTEX_PROJECT_ID=your-project-id

# Configure corporate proxy
export HTTPS_PROXY='https://proxy.example.com:8080'
```

### Using Vertex AI with LLM Gateway

Combine Google Vertex AI models with an LLM gateway for centralized management:

```bash  theme={null}
# Enable Vertex
export CLAUDE_CODE_USE_VERTEX=1

# Configure LLM gateway
export ANTHROPIC_VERTEX_BASE_URL='https://your-llm-gateway.com/vertex'
export CLAUDE_CODE_SKIP_VERTEX_AUTH=1  # If gateway handles GCP auth
```

### Authentication configuration

Claude Code uses the `ANTHROPIC_AUTH_TOKEN` for the `Authorization` header when needed. The `SKIP_AUTH` flags (`CLAUDE_CODE_SKIP_BEDROCK_AUTH`, `CLAUDE_CODE_SKIP_VERTEX_AUTH`) are used in LLM gateway scenarios where the gateway handles provider authentication.

## Choosing the right deployment configuration

Consider these factors when selecting your deployment approach:

### Direct provider access

Best for organizations that:

* Want the simplest setup
* Have existing AWS or GCP infrastructure
* Need provider-native monitoring and compliance

### Corporate proxy

Best for organizations that:

* Have existing corporate proxy requirements
* Need traffic monitoring and compliance
* Must route all traffic through specific network paths

### LLM Gateway

Best for organizations that:

* Need usage tracking across teams
* Want to dynamically switch between models
* Require custom rate limiting or budgets
* Need centralized authentication management

## Debugging

When debugging your deployment:

* Use the `claude /status` [slash command](/en/slash-commands). This command provides observability into any applied authentication, proxy, and URL settings.
* Set environment variable `export ANTHROPIC_LOG=debug` to log requests.

## Best practices for organizations

### 1. Invest in documentation and memory

We strongly recommend investing in documentation so that Claude Code understands your codebase. Organizations can deploy CLAUDE.md files at multiple levels:

* **Organization-wide**: Deploy to system directories like `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS) for company-wide standards
* **Repository-level**: Create `CLAUDE.md` files in repository roots containing project architecture, build commands, and contribution guidelines. Check these into source control so all users benefit

  [Learn more](/en/memory).

### 2. Simplify deployment

If you have a custom development environment, we find that creating a "one click" way to install Claude Code is key to growing adoption across an organization.

### 3. Start with guided usage

Encourage new users to try Claude Code for codebase Q\&A, or on smaller bug fixes or feature requests. Ask Claude Code to make a plan. Check Claude's suggestions and give feedback if it's off-track. Over time, as users understand this new paradigm better, then they'll be more effective at letting Claude Code run more agentically.

### 4. Configure security policies

Security teams can configure managed permissions for what Claude Code is and is not allowed to do, which cannot be overwritten by local configuration. [Learn more](/en/security).

### 5. Leverage MCP for integrations

MCP is a great way to give Claude Code more information, such as connecting to ticket management systems or error logs. We recommend that one central team configures MCP servers and checks a `.mcp.json` configuration into the codebase so that all users benefit. [Learn more](/en/mcp).

At Anthropic, we trust Claude Code to power development across every Anthropic codebase. We hope you enjoy using Claude Code as much as we do.

## Next steps

* [Set up Amazon Bedrock](/en/amazon-bedrock) for AWS-native deployment
* [Configure Google Vertex AI](/en/google-vertex-ai) for GCP deployment
* [Set up Microsoft Foundry](/en/microsoft-foundry) for Azure deployment
* [Configure Enterprise Network](/en/network-config) for network requirements
* [Deploy LLM Gateway](/en/llm-gateway) for enterprise management
* [Settings](/en/settings) for configuration options and environment variables

---

> To find navigation and other pages in this documentation, fetch the llms.txt file at: https://code.claude.com/docs/llms.txt

---

# Security

> Learn about Claude Code's security safeguards and best practices for safe usage.

## How we approach security

### Security foundation

Your code's security is paramount. Claude Code is built with security at its core, developed according to Anthropic's comprehensive security program. Learn more and access resources (SOC 2 Type 2 report, ISO 27001 certificate, etc.) at [Anthropic Trust Center](https://trust.anthropic.com).

### Permission-based architecture

Claude Code uses strict read-only permissions by default. When additional actions are needed (editing files, running tests, executing commands), Claude Code requests explicit permission. Users control whether to approve actions once or allow them automatically.

We designed Claude Code to be transparent and secure. For example, we require approval for bash commands before executing them, giving you direct control. This approach enables users and organizations to configure permissions directly.

For detailed permission configuration, see [Identity and Access Management](/en/iam).

### Built-in protections

To mitigate risks in agentic systems:

* **Sandboxed bash tool**: [Sandbox](/en/sandboxing) bash commands with filesystem and network isolation, reducing permission prompts while maintaining security. Enable with `/sandbox` to define boundaries where Claude Code can work autonomously
* **Write access restriction**: Claude Code can only write to the folder where it was started and its subfolders—it cannot modify files in parent directories without explicit permission. While Claude Code can read files outside the working directory (useful for accessing system libraries and dependencies), write operations are strictly confined to the project scope, creating a clear security boundary
* **Prompt fatigue mitigation**: Support for allowlisting frequently used safe commands per-user, per-codebase, or per-organization
* **Accept Edits mode**: Batch accept multiple edits while maintaining permission prompts for commands with side effects

### User responsibility

Claude Code only has the permissions you grant it. You're responsible for reviewing proposed code and commands for safety before approval.

## Protect against prompt injection

Prompt injection is a technique where an attacker attempts to override or manipulate an AI assistant's instructions by inserting malicious text. Claude Code includes several safeguards against these attacks:

### Core protections

* **Permission system**: Sensitive operations require explicit approval
* **Context-aware analysis**: Detects potentially harmful instructions by analyzing the full request
* **Input sanitization**: Prevents command injection by processing user inputs
* **Command blocklist**: Blocks risky commands that fetch arbitrary content from the web like `curl` and `wget` by default. When explicitly allowed, be aware of [permission pattern limitations](/en/iam#tool-specific-permission-rules)

### Privacy safeguards

We have implemented several safeguards to protect your data, including:

* Limited retention periods for sensitive information (see the [Privacy Center](https://privacy.anthropic.com/en/articles/10023548-how-long-do-you-store-my-data) to learn more)
* Restricted access to user session data
* User control over data training preferences. Consumer users can change their [privacy settings](https://claude.ai/settings/privacy) at any time.

For full details, please review our [Commercial Terms of Service](https://www.anthropic.com/legal/commercial-terms) (for Team, Enterprise, and API users) or [Consumer Terms](https://www.anthropic.com/legal/consumer-terms) (for Free, Pro, and Max users) and [Privacy Policy](https://www.anthropic.com/legal/privacy).

### Additional safeguards

* **Network request approval**: Tools that make network requests require user approval by default
* **Isolated context windows**: Web fetch uses a separate context window to avoid injecting potentially malicious prompts
* **Trust verification**: First-time codebase runs and new MCP servers require trust verification
  * Note: Trust verification is disabled when running non-interactively with the `-p` flag
* **Command injection detection**: Suspicious bash commands require manual approval even if previously allowlisted
* **Fail-closed matching**: Unmatched commands default to requiring manual approval
* **Natural language descriptions**: Complex bash commands include explanations for user understanding
* **Secure credential storage**: API keys and tokens are encrypted. See [Credential Management](/en/iam#credential-management)

<Warning>
  **Windows WebDAV security risk**: When running Claude Code on Windows, we recommend against enabling WebDAV or allowing Claude Code to access paths such as `\\*` that may contain WebDAV subdirectories. [WebDAV has been deprecated by Microsoft](https://learn.microsoft.com/en-us/windows/whats-new/deprecated-features#:~:text=The%20Webclient%20\(WebDAV\)%20service%20is%20deprecated) due to security risks. Enabling WebDAV may allow Claude Code to trigger network requests to remote hosts, bypassing the permission system.
</Warning>

**Best practices for working with untrusted content**:

1. Review suggested commands before approval
2. Avoid piping untrusted content directly to Claude
3. Verify proposed changes to critical files
4. Use virtual machines (VMs) to run scripts and make tool calls, especially when interacting with external web services
5. Report suspicious behavior with `/bug`

<Warning>
  While these protections significantly reduce risk, no system is completely
  immune to all attacks. Always maintain good security practices when working
  with any AI tool.
</Warning>

## MCP security

Claude Code allows users to configure Model Context Protocol (MCP) servers. The list of allowed MCP servers is configured in your source code, as part of Claude Code settings engineers check into source control.

We encourage either writing your own MCP servers or using MCP servers from providers that you trust. You are able to configure Claude Code permissions for MCP servers. Anthropic does not manage or audit any MCP servers.

## IDE security

See [here](/en/vs-code#security) for more information on the security of running Claude Code in an IDE.

## Cloud execution security

When using [Claude Code on the web](/en/claude-code-on-the-web), additional security controls are in place:

* **Isolated virtual machines**: Each cloud session runs in an isolated, Anthropic-managed VM
* **Network access controls**: Network access is limited by default and can be configured to be disabled or allow only specific domains
* **Credential protection**: Authentication is handled through a secure proxy that uses a scoped credential inside the sandbox, which is then translated to your actual GitHub authentication token
* **Branch restrictions**: Git push operations are restricted to the current working branch
* **Audit logging**: All operations in cloud environments are logged for compliance and audit purposes
* **Automatic cleanup**: Cloud environments are automatically terminated after session completion

For more details on cloud execution, see [Claude Code on the web](/en/claude-code-on-the-web).

## Security best practices

### Working with sensitive code

* Review all suggested changes before approval
* Use project-specific permission settings for sensitive repositories
* Consider using [devcontainers](/en/devcontainer) for additional isolation
* Regularly audit your permission settings with `/permissions`

### Team security

* Use [enterprise managed settings](/en/iam#enterprise-managed-settings) to enforce organizational standards
* Share approved permission configurations through version control
* Train team members on security best practices
* Monitor Claude Code usage through [OpenTelemetry metrics](/en/monitoring-usage)

### Reporting security issues

If you discover a security vulnerability in Claude Code:

1. Do not disclose it publicly
2. Report it through our [HackerOne program](https://hackerone.com/anthropic-vdp/reports/new?type=team\&report_type=vulnerability)
3. Include detailed reproduction steps
4. Allow time for us to address the issue before public disclosure

## Related resources

* [Sandboxing](/en/sandboxing) - Filesystem and network isolation for bash commands
* [Identity and Access Management](/en/iam) - Configure permissions and access controls
* [Monitoring usage](/en/monitoring-usage) - Track and audit Claude Code activity
* [Development containers](/en/devcontainer) - Secure, isolated environments
* [Anthropic Trust Center](https://trust.anthropic.com) - Security certifications and compliance

---

> To find navigation and other pages in this documentation, fetch the llms.txt file at: https://code.claude.com/docs/llms.txt
