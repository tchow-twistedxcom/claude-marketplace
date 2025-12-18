# Common Workflow Patterns

Step-by-step patterns for frequent Claude Code tasks.

---

## Debugging Workflow

**When**: Bug investigation, error resolution, unexpected behavior

### Pattern: Understand → Investigate → Fix → Verify

```
1. UNDERSTAND
   │
   ├─ Read error messages carefully
   ├─ Reproduce the issue
   └─ Gather context (recent changes, environment)

2. INVESTIGATE
   │
   ├─ Use Explore agent for unknown codebases
   ├─ Use root-cause-analyst for complex bugs
   ├─ Read relevant files with Read tool
   └─ Search for patterns with Grep

3. FIX
   │
   ├─ Use Edit for targeted changes
   ├─ Keep changes minimal
   └─ Don't fix unrelated issues

4. VERIFY
   │
   ├─ Run tests with Bash
   ├─ Test the specific scenario
   └─ Check for regressions
```

### Tool Selection
| Step | Tool | When |
|------|------|------|
| Read stack trace | Read | Known file location |
| Find error source | Grep | Pattern search |
| Explore codebase | Task (Explore) | Unknown structure |
| Deep analysis | Task (root-cause-analyst) | Complex bug |
| Apply fix | Edit | 1-2 files |
| Run tests | Bash | Test execution |

---

## Implementation Workflow

**When**: Building new features, adding functionality

### Pattern: Plan → Design → Implement → Review → Test

```
1. PLAN
   │
   ├─ Use EnterPlanMode for non-trivial features
   ├─ Identify affected files
   └─ Break into subtasks with TodoWrite

2. DESIGN
   │
   ├─ Use Plan agent for architecture
   ├─ Use feature-dev:code-architect for blueprints
   └─ Consider existing patterns

3. IMPLEMENT
   │
   ├─ Use Edit for 1-2 files
   ├─ Use MultiEdit for 3+ files
   └─ Follow existing conventions

4. REVIEW
   │
   ├─ Use feature-dev:code-reviewer agent
   ├─ Check for security issues
   └─ Verify code quality

5. TEST
   │
   ├─ Run existing tests
   ├─ Add new tests if needed
   └─ Verify integration
```

### Tool Selection
| Step | Tool | When |
|------|------|------|
| Complex planning | EnterPlanMode | Multi-file, architectural |
| Track progress | TodoWrite | 3+ steps |
| Architecture | Task (Plan) | Strategy design |
| Blueprint | Task (code-architect) | Feature design |
| Code changes | Edit/MultiEdit | Based on file count |
| Quality check | Task (code-reviewer) | After implementation |
| Test execution | Bash | npm test, pytest, etc. |

---

## Research Workflow

**When**: Understanding codebases, answering questions, exploring options

### Pattern: Explore → Read → Synthesize → Report

```
1. EXPLORE
   │
   ├─ Use Explore agent for broad search
   ├─ Use Glob to find relevant files
   └─ Use Grep for specific patterns

2. READ
   │
   ├─ Read identified files
   ├─ Parallel reads for efficiency
   └─ Focus on relevant sections

3. SYNTHESIZE
   │
   ├─ Connect findings
   ├─ Identify patterns
   └─ Note gaps or uncertainties

4. REPORT
   │
   ├─ Summarize findings clearly
   ├─ Include file references
   └─ Suggest next steps
```

### Tool Selection
| Step | Tool | When |
|------|------|------|
| Find files | Glob | Known patterns |
| Search content | Grep | Specific terms |
| Broad exploration | Task (Explore) | Unknown structure |
| Read files | Read | Multiple in parallel |
| Deep analysis | Task (general-purpose) | Complex research |

---

## Code Review Workflow

**When**: Reviewing changes, pull requests, code quality

### Pattern: Identify → Analyze → Report

```
1. IDENTIFY
   │
   ├─ Get changed files (git diff)
   ├─ Understand scope of changes
   └─ Prioritize critical files

2. ANALYZE
   │
   ├─ Read changed files
   ├─ Use code-reviewer agent
   ├─ Check for common issues:
   │  ├─ Security vulnerabilities
   │  ├─ Performance problems
   │  ├─ Code style violations
   │  └─ Logic errors

3. REPORT
   │
   ├─ List findings by severity
   ├─ Provide specific line references
   └─ Suggest improvements
```

### Tool Selection
| Step | Tool | When |
|------|------|------|
| Get changes | Bash (git) | git diff, git status |
| Read files | Read | Parallel for efficiency |
| Deep review | Task (code-reviewer) | Thorough analysis |
| Security check | Task (security-engineer) | Security focus |
| Performance | Task (performance-engineer) | Performance focus |

---

## Refactoring Workflow

**When**: Improving code structure, reducing technical debt

### Pattern: Assess → Plan → Execute → Validate

```
1. ASSESS
   │
   ├─ Identify refactoring targets
   ├─ Understand dependencies
   └─ Estimate impact scope

2. PLAN
   │
   ├─ Use refactoring-expert agent
   ├─ Break into safe steps
   └─ Ensure each step is testable

3. EXECUTE
   │
   ├─ Make one change at a time
   ├─ Use MultiEdit for related changes
   ├─ Preserve behavior

4. VALIDATE
   │
   ├─ Run tests after each step
   ├─ Verify no regressions
   └─ Check performance impact
```

---

## Session Management Patterns

### Starting a Session
```
1. Review context
2. Understand current state
3. Set up TodoWrite for tracking
```

### Continuing Work
```
1. claude -c (continue last session)
2. Review previous progress
3. Update todos and continue
```

### Complex Multi-Session Work
```
Session 1: Plan → Implement part 1
Session 2: claude -c → Continue implementation
Session 3: claude -c → Review and test
```

---

## Parallel Execution Patterns

### Independent File Reads
```
# Good: Read multiple files in parallel
Read: src/auth.ts
Read: src/user.ts
Read: src/api.ts
(all in same request)
```

### Independent Searches
```
# Good: Multiple searches in parallel
Grep: "TODO" in src/
Grep: "FIXME" in src/
Grep: "deprecated" in src/
(all in same request)
```

### Independent Agents
```
# Good: Multiple agents in parallel
Task (security-engineer): "Audit authentication"
Task (performance-engineer): "Profile API endpoints"
(all in same request)
```

---

## Anti-Patterns to Avoid

### Sequential When Parallel Is Possible
```
# Bad: Sequential reads
Read file1 → wait → Read file2 → wait → Read file3

# Good: Parallel reads
Read file1, file2, file3 (same request)
```

### Wrong Tool for Job
```
# Bad: Bash for file content
Bash: cat src/index.ts

# Good: Read tool
Read: src/index.ts
```

### Skipping Planning
```
# Bad: Jump to implementation
User: "Add authentication"
→ Immediately start coding

# Good: Plan first
User: "Add authentication"
→ EnterPlanMode → Design → Then implement
```

---

*See also: [agent-catalog.md](agent-catalog.md) for agent selection*
