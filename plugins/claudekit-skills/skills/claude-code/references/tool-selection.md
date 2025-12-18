# Native Tool Selection Guide

Complete decision matrix for choosing the right Claude Code tool for each task.

## Tool Categories

### File Reading

| Tool | Use When | Avoid When |
|------|----------|------------|
| `Read` | Reading file content, viewing code, examining configs | File doesn't exist |
| `Glob` | Finding files by pattern (*.ts, **/*.md) | Searching file content |
| `Grep` | Searching content within files | Finding files by name |

**Decision Tree**:
```
Need file content? → Read
Need to find files? → Glob
Need to search content? → Grep
```

### File Writing

| Tool | Use When | Avoid When |
|------|----------|------------|
| `Write` | Creating new files, complete file replacement | Modifying existing files |
| `Edit` | Targeted changes to 1-2 files | Creating new files, 3+ files |
| `MultiEdit` | Modifying 3+ files, batch operations | Single file changes |

**Decision Tree**:
```
New file? → Write
Existing file, 1-2 files? → Edit
Existing files, 3+ files? → MultiEdit
```

### Search Operations

| Tool | Use When | Avoid When |
|------|----------|------------|
| `Grep` | Known patterns, specific searches | Complex codebase exploration |
| `Glob` | File name patterns, directory scanning | Content search |
| `Task` (Explore) | Unknown structure, broad exploration | Simple known queries |

**Grep vs Task Decision**:
```
Know what you're looking for? → Grep
Exploring unknown codebase? → Task (Explore agent)
Need multiple search rounds? → Task (Explore agent)
```

### System Operations

| Tool | Use When | Avoid When |
|------|----------|------------|
| `Bash` | Git commands, npm/yarn, system tools | File reading/writing |
| `WebFetch` | Fetching URL content | Searching the web |
| `WebSearch` | Finding information online | Known URLs |

**Anti-pattern Alert**:
```
# AVOID: Using Bash for file operations
bash: cat file.txt
bash: grep pattern file.txt
bash: find . -name "*.ts"

# PREFER: Specialized tools
Read: file.txt
Grep: pattern in files
Glob: **/*.ts
```

### User Interaction

| Tool | Use When | Avoid When |
|------|----------|------------|
| `AskUserQuestion` | Need clarification, multiple choices | Information is clear |
| `TodoWrite` | Multi-step tasks, progress tracking | Simple single operations |
| `EnterPlanMode` | Complex implementations, architectural decisions | Simple changes |

## Detailed Tool Reference

### Read Tool

**Best for**: Viewing file content, code review, understanding structure

```
Parameters:
- file_path: Absolute path to file
- offset: Start line (optional)
- limit: Number of lines (optional)
```

**Capabilities**:
- Read text files
- View images (PNG, JPG)
- Read PDFs
- Read Jupyter notebooks

### Edit Tool

**Best for**: Targeted modifications to existing files

```
Parameters:
- file_path: Absolute path
- old_string: Exact text to replace
- new_string: Replacement text
- replace_all: Replace all occurrences (default: false)
```

**Rules**:
- Must read file first
- old_string must be unique (or use replace_all)
- Preserve exact indentation from file

### MultiEdit Tool

**Best for**: Batch operations across multiple files

**When to use**:
- Renaming across codebase
- Updating imports everywhere
- Applying consistent changes

### Grep Tool

**Best for**: Content search with regex support

```
Parameters:
- pattern: Regex pattern
- path: Directory or file to search
- output_mode: "files_with_matches" | "content" | "count"
- glob: File pattern filter (e.g., "*.ts")
```

**Tips**:
- Use `output_mode: "content"` with `-A`, `-B`, `-C` for context
- Use `glob` to limit search scope
- Use `head_limit` for large result sets

### Glob Tool

**Best for**: Finding files by name pattern

```
Parameters:
- pattern: Glob pattern (e.g., "**/*.tsx")
- path: Base directory (optional)
```

**Pattern Examples**:
- `*.ts` - TypeScript files in current dir
- `**/*.test.ts` - All test files
- `src/**/*.{ts,tsx}` - TS/TSX in src/

### Bash Tool

**Best for**: System commands, git operations

**Do use for**:
- `git status`, `git diff`, `git commit`
- `npm install`, `npm run build`
- `docker`, `kubectl`
- Environment commands

**Don't use for**:
- `cat`, `head`, `tail` → Use Read
- `grep`, `rg` → Use Grep
- `find` → Use Glob
- `echo` for output → Direct response

### Task Tool (Agents)

**Best for**: Complex multi-step operations

```
Parameters:
- subagent_type: Agent specialization
- prompt: Task description
- model: Optional model override
```

**Agent Selection**:
- `Explore` - Codebase discovery
- `Plan` - Implementation design
- `general-purpose` - Complex research

### WebFetch Tool

**Best for**: Retrieving URL content

```
Parameters:
- url: Full URL to fetch
- prompt: What to extract from content
```

**Features**:
- Converts HTML to markdown
- Follows redirects (inform user)
- 15-minute cache

### WebSearch Tool

**Best for**: Finding information online

```
Parameters:
- query: Search query
- allowed_domains: Optional domain filter
- blocked_domains: Optional block list
```

**Requirement**: Always include Sources section in response

## Common Anti-Patterns

### 1. Bash for File Operations

```
# BAD
Bash: cat src/index.ts
Bash: grep "function" src/*.ts

# GOOD
Read: src/index.ts
Grep: "function" in src/*.ts
```

### 2. Sequential Edits for Multiple Files

```
# BAD
Edit: file1.ts
Edit: file2.ts
Edit: file3.ts

# GOOD
MultiEdit: [file1.ts, file2.ts, file3.ts]
```

### 3. Direct Grep for Complex Exploration

```
# BAD (unknown codebase)
Grep: "auth"
Grep: "login"
Grep: "session"

# GOOD
Task (Explore): "Find how authentication is implemented"
```

### 4. Assumptions Instead of Questions

```
# BAD
Assume user wants React implementation

# GOOD
AskUserQuestion: "Which framework should I use?"
```

## Tool Combinations

### Code Review Workflow
1. `Glob` - Find relevant files
2. `Read` - Examine content
3. `Grep` - Search for patterns
4. `Task` (code-reviewer) - Deep analysis

### Implementation Workflow
1. `Task` (Explore) - Understand codebase
2. `Read` - Study specific files
3. `Edit`/`MultiEdit` - Make changes
4. `Bash` - Run tests

### Research Workflow
1. `WebSearch` - Find information
2. `WebFetch` - Get specific docs
3. `Task` (general-purpose) - Synthesize

---

*See also: [agent-catalog.md](agent-catalog.md) for agent selection*
