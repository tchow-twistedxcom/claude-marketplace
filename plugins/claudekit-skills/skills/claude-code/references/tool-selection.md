# Tool Selection

> Native tool decision matrices

*Auto-generated from Claude Code documentation on 2025-12-20*
*Source: github.com/ericbuess/claude-code-docs*

---

# Claude Code overview

> Learn about Claude Code, Anthropic's agentic coding tool that lives in your terminal and helps you turn ideas into code faster than ever before.

## Get started in 30 seconds

Prerequisites:

* A [Claude.ai](https://claude.ai) (recommended) or [Claude Console](https://console.anthropic.com/) account

**Install Claude Code:**

To install Claude Code, use one of the following methods:

<Tabs>
  <Tab title="Native Install (Recommended)">
    **macOS, Linux, WSL:**

    ```bash  theme={null}
    curl -fsSL https://claude.ai/install.sh | bash
    ```

    **Windows PowerShell:**

    ```powershell  theme={null}
    irm https://claude.ai/install.ps1 | iex
    ```

    **Windows CMD:**

    ```batch  theme={null}
    curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
    ```
  </Tab>

  <Tab title="Homebrew">
    ```sh  theme={null}
    brew install --cask claude-code
    ```
  </Tab>

  <Tab title="NPM">
    If you have [Node.js 18 or newer installed](https://nodejs.org/en/download/):

    ```sh  theme={null}
    npm install -g @anthropic-ai/claude-code
    ```
  </Tab>
</Tabs>

**Start using Claude Code:**

```bash  theme={null}
cd your-project
claude
```

You'll be prompted to log in on first use. That's it! [Continue with Quickstart (5 minutes) →](/en/quickstart)

<Tip>
  Claude Code automatically keeps itself up to date. See [advanced setup](/en/setup) for installation options, manual updates, or uninstallation instructions. Visit [troubleshooting](/en/troubleshooting) if you hit issues.
</Tip>

## What Claude Code does for you

* **Build features from descriptions**: Tell Claude what you want to build in plain English. It will make a plan, write the code, and ensure it works.
* **Debug and fix issues**: Describe a bug or paste an error message. Claude Code will analyze your codebase, identify the problem, and implement a fix.
* **Navigate any codebase**: Ask anything about your team's codebase, and get a thoughtful answer back. Claude Code maintains awareness of your entire project structure, can find up-to-date information from the web, and with [MCP](/en/mcp) can pull from external data sources like Google Drive, Figma, and Slack.
* **Automate tedious tasks**: Fix fiddly lint issues, resolve merge conflicts, and write release notes. Do all this in a single command from your developer machines, or automatically in CI.

## Why developers love Claude Code

* **Works in your terminal**: Not another chat window. Not another IDE. Claude Code meets you where you already work, with the tools you already love.
* **Takes action**: Claude Code can directly edit files, run commands, and create commits. Need more? [MCP](/en/mcp) lets Claude read your design docs in Google Drive, update your tickets in Jira, or use *your* custom developer tooling.
* **Unix philosophy**: Claude Code is composable and scriptable. `tail -f app.log | claude -p "Slack me if you see any anomalies appear in this log stream"` *works*. Your CI can run `claude -p "If there are new text strings, translate them into French and raise a PR for @lang-fr-team to review"`.
* **Enterprise-ready**: Use the Claude API, or host on AWS or GCP. Enterprise-grade [security](/en/security), [privacy](/en/data-usage), and [compliance](https://trust.anthropic.com/) is built-in.

## Next steps

<CardGroup>
  <Card title="Quickstart" icon="rocket" href="/en/quickstart">
    See Claude Code in action with practical examples
  </Card>

  <Card title="Common workflows" icon="graduation-cap" href="/en/common-workflows">
    Step-by-step guides for common workflows
  </Card>

  <Card title="Troubleshooting" icon="wrench" href="/en/troubleshooting">
    Solutions for common issues with Claude Code
  </Card>

  <Card title="IDE setup" icon="laptop" href="/en/vs-code">
    Add Claude Code to your IDE
  </Card>
</CardGroup>

## Additional resources

<CardGroup>
  <Card title="About Claude Code" icon="sparkles" href="https://claude.com/product/claude-code">
    Learn more about Claude Code on claude.com
  </Card>

  <Card title="Build with the Agent SDK" icon="code-branch" href="https://docs.claude.com/en/docs/agent-sdk/overview">
    Create custom AI agents with the Claude Agent SDK
  </Card>

  <Card title="Host on AWS or GCP" icon="cloud" href="/en/third-party-integrations">
    Configure Claude Code with Amazon Bedrock or Google Vertex AI
  </Card>

  <Card title="Settings" icon="gear" href="/en/settings">
    Customize Claude Code for your workflow
  </Card>

  <Card title="Commands" icon="terminal" href="/en/cli-reference">
    Learn about CLI commands and controls
  </Card>

  <Card title="Reference implementation" icon="code" href="https://github.com/anthropics/claude-code/tree/main/.devcontainer">
    Clone our development container reference implementation
  </Card>

  <Card title="Security" icon="shield" href="/en/security">
    Discover Claude Code's safeguards and best practices for safe usage
  </Card>

  <Card title="Privacy and data usage" icon="lock" href="/en/data-usage">
    Understand how Claude Code handles your data
  </Card>
</CardGroup>

---

> To find navigation and other pages in this documentation, fetch the llms.txt file at: https://code.claude.com/docs/llms.txt

---

# CLI reference

> Complete reference for Claude Code command-line interface, including commands and flags.

## CLI commands

| Command                         | Description                                    | Example                                           |
| :------------------------------ | :--------------------------------------------- | :------------------------------------------------ |
| `claude`                        | Start interactive REPL                         | `claude`                                          |
| `claude "query"`                | Start REPL with initial prompt                 | `claude "explain this project"`                   |
| `claude -p "query"`             | Query via SDK, then exit                       | `claude -p "explain this function"`               |
| `cat file \| claude -p "query"` | Process piped content                          | `cat logs.txt \| claude -p "explain"`             |
| `claude -c`                     | Continue most recent conversation              | `claude -c`                                       |
| `claude -c -p "query"`          | Continue via SDK                               | `claude -c -p "Check for type errors"`            |
| `claude -r "<session>" "query"` | Resume session by ID or name                   | `claude -r "auth-refactor" "Finish this PR"`      |
| `claude update`                 | Update to latest version                       | `claude update`                                   |
| `claude mcp`                    | Configure Model Context Protocol (MCP) servers | See the [Claude Code MCP documentation](/en/mcp). |

## CLI flags

Customize Claude Code's behavior with these command-line flags:

| Flag                             | Description                                                                                                                                                                                             | Example                                                                                            |
| :------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------- |
| `--add-dir`                      | Add additional working directories for Claude to access (validates each path exists as a directory)                                                                                                     | `claude --add-dir ../apps ../lib`                                                                  |
| `--agent`                        | Specify an agent for the current session (overrides the `agent` setting)                                                                                                                                | `claude --agent my-custom-agent`                                                                   |
| `--agents`                       | Define custom [subagents](/en/sub-agents) dynamically via JSON (see below for format)                                                                                                                   | `claude --agents '{"reviewer":{"description":"Reviews code","prompt":"You are a code reviewer"}}'` |
| `--allowedTools`                 | Tools that execute without prompting for permission. To restrict which tools are available, use `--tools` instead                                                                                       | `"Bash(git log:*)" "Bash(git diff:*)" "Read"`                                                      |
| `--append-system-prompt`         | Append custom text to the end of the default system prompt (works in both interactive and print modes)                                                                                                  | `claude --append-system-prompt "Always use TypeScript"`                                            |
| `--betas`                        | Beta headers to include in API requests (API key users only)                                                                                                                                            | `claude --betas interleaved-thinking`                                                              |
| `--chrome`                       | Enable [Chrome browser integration](/en/chrome) for web automation and testing                                                                                                                          | `claude --chrome`                                                                                  |
| `--continue`, `-c`               | Load the most recent conversation in the current directory                                                                                                                                              | `claude --continue`                                                                                |
| `--dangerously-skip-permissions` | Skip permission prompts (use with caution)                                                                                                                                                              | `claude --dangerously-skip-permissions`                                                            |
| `--debug`                        | Enable debug mode with optional category filtering (for example, `"api,hooks"` or `"!statsig,!file"`)                                                                                                   | `claude --debug "api,mcp"`                                                                         |
| `--disallowedTools`              | Tools that are removed from the model's context and cannot be used                                                                                                                                      | `"Bash(git log:*)" "Bash(git diff:*)" "Edit"`                                                      |
| `--enable-lsp-logging`           | Enable verbose LSP logging for debugging language server issues. Logs are written to `~/.claude/debug/`                                                                                                 | `claude --enable-lsp-logging`                                                                      |
| `--fallback-model`               | Enable automatic fallback to specified model when default model is overloaded (print mode only)                                                                                                         | `claude -p --fallback-model sonnet "query"`                                                        |
| `--fork-session`                 | When resuming, create a new session ID instead of reusing the original (use with `--resume` or `--continue`)                                                                                            | `claude --resume abc123 --fork-session`                                                            |
| `--ide`                          | Automatically connect to IDE on startup if exactly one valid IDE is available                                                                                                                           | `claude --ide`                                                                                     |
| `--include-partial-messages`     | Include partial streaming events in output (requires `--print` and `--output-format=stream-json`)                                                                                                       | `claude -p --output-format stream-json --include-partial-messages "query"`                         |
| `--input-format`                 | Specify input format for print mode (options: `text`, `stream-json`)                                                                                                                                    | `claude -p --output-format json --input-format stream-json`                                        |
| `--json-schema`                  | Get validated JSON output matching a JSON Schema after agent completes its workflow (print mode only, see [Agent SDK Structured Outputs](https://docs.claude.com/en/docs/agent-sdk/structured-outputs)) | `claude -p --json-schema '{"type":"object","properties":{...}}' "query"`                           |
| `--max-turns`                    | Limit the number of agentic turns in non-interactive mode                                                                                                                                               | `claude -p --max-turns 3 "query"`                                                                  |
| `--mcp-config`                   | Load MCP servers from JSON files or strings (space-separated)                                                                                                                                           | `claude --mcp-config ./mcp.json`                                                                   |
| `--model`                        | Sets the model for the current session with an alias for the latest model (`sonnet` or `opus`) or a model's full name                                                                                   | `claude --model claude-sonnet-4-5-20250929`                                                        |
| `--no-chrome`                    | Disable [Chrome browser integration](/en/chrome) for this session                                                                                                                                       | `claude --no-chrome`                                                                               |
| `--output-format`                | Specify output format for print mode (options: `text`, `json`, `stream-json`)                                                                                                                           | `claude -p "query" --output-format json`                                                           |
| `--permission-mode`              | Begin in a specified [permission mode](/en/iam#permission-modes)                                                                                                                                        | `claude --permission-mode plan`                                                                    |
| `--permission-prompt-tool`       | Specify an MCP tool to handle permission prompts in non-interactive mode                                                                                                                                | `claude -p --permission-prompt-tool mcp_auth_tool "query"`                                         |
| `--plugin-dir`                   | Load plugins from directories for this session only (repeatable)                                                                                                                                        | `claude --plugin-dir ./my-plugins`                                                                 |
| `--print`, `-p`                  | Print response without interactive mode (see [SDK documentation](https://docs.claude.com/en/docs/agent-sdk) for programmatic usage details)                                                             | `claude -p "query"`                                                                                |
| `--resume`, `-r`                 | Resume a specific session by ID or name, or show an interactive picker to choose a session                                                                                                              | `claude --resume auth-refactor`                                                                    |
| `--session-id`                   | Use a specific session ID for the conversation (must be a valid UUID)                                                                                                                                   | `claude --session-id "550e8400-e29b-41d4-a716-446655440000"`                                       |
| `--setting-sources`              | Comma-separated list of setting sources to load (`user`, `project`, `local`)                                                                                                                            | `claude --setting-sources user,project`                                                            |
| `--settings`                     | Path to a settings JSON file or a JSON string to load additional settings from                                                                                                                          | `claude --settings ./settings.json`                                                                |
| `--strict-mcp-config`            | Only use MCP servers from `--mcp-config`, ignoring all other MCP configurations                                                                                                                         | `claude --strict-mcp-config --mcp-config ./mcp.json`                                               |
| `--system-prompt`                | Replace the entire system prompt with custom text (works in both interactive and print modes)                                                                                                           | `claude --system-prompt "You are a Python expert"`                                                 |
| `--system-prompt-file`           | Load system prompt from a file, replacing the default prompt (print mode only)                                                                                                                          | `claude -p --system-prompt-file ./custom-prompt.txt "query"`                                       |
| `--tools`                        | Specify the list of available tools from the built-in set (use `""` to disable all, `"default"` for all, or tool names like `"Bash,Edit,Read"`)                                                         | `claude -p --tools "Bash,Edit,Read" "query"`                                                       |
| `--verbose`                      | Enable verbose logging, shows full turn-by-turn output (helpful for debugging in both print and interactive modes)                                                                                      | `claude --verbose`                                                                                 |
| `--version`, `-v`                | Output the version number                                                                                                                                                                               | `claude -v`                                                                                        |

<Tip>
  The `--output-format json` flag is particularly useful for scripting and
  automation, allowing you to parse Claude's responses programmatically.
</Tip>

### Agents flag format

The `--agents` flag accepts a JSON object that defines one or more custom subagents. Each subagent requires a unique name (as the key) and a definition object with the following fields:

| Field         | Required | Description                                                                                                            |
| :------------ | :------- | :--------------------------------------------------------------------------------------------------------------------- |
| `description` | Yes      | Natural language description of when the subagent should be invoked                                                    |
| `prompt`      | Yes      | The system prompt that guides the subagent's behavior                                                                  |
| `tools`       | No       | Array of specific tools the subagent can use (for example, `["Read", "Edit", "Bash"]`). If omitted, inherits all tools |
| `model`       | No       | Model alias to use: `sonnet`, `opus`, or `haiku`. If omitted, uses the default subagent model                          |

Example:

```bash  theme={null}
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer. Use proactively after code changes.",
    "prompt": "You are a senior code reviewer. Focus on code quality, security, and best practices.",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  },
  "debugger": {
    "description": "Debugging specialist for errors and test failures.",
    "prompt": "You are an expert debugger. Analyze errors, identify root causes, and provide fixes."
  }
}'
```

For more details on creating and using subagents, see the [subagents documentation](/en/sub-agents).

### System prompt flags

Claude Code provides three flags for customizing the system prompt, each serving a different purpose:

| Flag                     | Behavior                           | Modes               | Use Case                                                             |
| :----------------------- | :--------------------------------- | :------------------ | :------------------------------------------------------------------- |
| `--system-prompt`        | **Replaces** entire default prompt | Interactive + Print | Complete control over Claude's behavior and instructions             |
| `--system-prompt-file`   | **Replaces** with file contents    | Print only          | Load prompts from files for reproducibility and version control      |
| `--append-system-prompt` | **Appends** to default prompt      | Interactive + Print | Add specific instructions while keeping default Claude Code behavior |

**When to use each:**

* **`--system-prompt`**: Use when you need complete control over Claude's system prompt. This removes all default Claude Code instructions, giving you a blank slate.
  ```bash  theme={null}
  claude --system-prompt "You are a Python expert who only writes type-annotated code"
  ```

* **`--system-prompt-file`**: Use when you want to load a custom prompt from a file, useful for team consistency or version-controlled prompt templates.
  ```bash  theme={null}
  claude -p --system-prompt-file ./prompts/code-review.txt "Review this PR"
  ```

* **`--append-system-prompt`**: Use when you want to add specific instructions while keeping Claude Code's default capabilities intact. This is the safest option for most use cases.
  ```bash  theme={null}
  claude --append-system-prompt "Always use TypeScript and include JSDoc comments"
  ```

<Note>
  `--system-prompt` and `--system-prompt-file` are mutually exclusive. You cannot use both flags simultaneously.
</Note>

<Tip>
  For most use cases, `--append-system-prompt` is recommended as it preserves Claude Code's built-in capabilities while adding your custom requirements. Use `--system-prompt` or `--system-prompt-file` only when you need complete control over the system prompt.
</Tip>

For detailed information about print mode (`-p`) including output formats,
streaming, verbose logging, and programmatic usage, see the
[SDK documentation](https://docs.claude.com/en/docs/agent-sdk).

## See also

* [Chrome extension](/en/chrome) - Browser automation and web testing
* [Interactive mode](/en/interactive-mode) - Shortcuts, input modes, and interactive features
* [Slash commands](/en/slash-commands) - Interactive session commands
* [Quickstart guide](/en/quickstart) - Getting started with Claude Code
* [Common workflows](/en/common-workflows) - Advanced workflows and patterns
* [Settings](/en/settings) - Configuration options
* [SDK documentation](https://docs.claude.com/en/docs/agent-sdk) - Programmatic usage and integrations

---

> To find navigation and other pages in this documentation, fetch the llms.txt file at: https://code.claude.com/docs/llms.txt
