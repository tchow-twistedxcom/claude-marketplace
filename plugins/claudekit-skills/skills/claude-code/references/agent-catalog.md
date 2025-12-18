# Agent Catalog

Complete reference for all 30+ Task subagent types organized by use case.

## How to Use Agents

Invoke agents via the Task tool:
```
Task tool with subagent_type="agent-name"
```

**Key Principles**:
- Launch multiple independent agents in parallel
- Provide clear, detailed prompts
- Agents work autonomously and return results
- Use appropriate model (haiku for fast, sonnet for complex, opus for critical)

---

## Exploration & Research Agents

### Explore
**When**: Codebase discovery, finding files, understanding structure
**Best for**: Unknown codebases, pattern finding, broad searches

```
Use when:
- "Where is X implemented?"
- "How does the codebase structure work?"
- "Find all files related to authentication"
```

### general-purpose
**When**: Complex multi-step research requiring multiple tools
**Best for**: Tasks needing extensive exploration and synthesis

```
Use when:
- Research requiring many file reads
- Complex questions needing investigation
- Tasks where you're unsure what's needed
```

### claude-code-guide
**When**: Questions about Claude Code itself
**Best for**: Feature questions, usage help, troubleshooting

```
Use when:
- "Can Claude Code do X?"
- "How do I configure Y?"
- "What's the best way to Z in Claude Code?"
```

---

## Planning & Architecture Agents

### Plan
**When**: Designing implementation strategy before coding
**Best for**: Multi-file changes, architectural decisions

```
Use when:
- Feature requires multiple components
- Need to identify critical files
- Want step-by-step implementation plan
```

### system-architect
**When**: System-level design decisions
**Best for**: Scalability, maintainability, long-term architecture

```
Use when:
- Designing new system architecture
- Evaluating trade-offs
- Planning major refactors
```

### backend-architect
**When**: Backend system design
**Best for**: API design, data integrity, fault tolerance

```
Use when:
- Designing REST/GraphQL APIs
- Database schema decisions
- Service architecture
```

### frontend-architect
**When**: UI/UX architecture
**Best for**: Component design, accessibility, performance

```
Use when:
- Designing component hierarchy
- State management decisions
- Frontend performance optimization
```

### requirements-analyst
**When**: Transforming vague ideas into specifications
**Best for**: Requirements discovery, structured analysis

```
Use when:
- User request is ambiguous
- Need to clarify scope
- Creating technical specifications
```

---

## Implementation Agents

### feature-dev:code-architect
**When**: Designing feature architecture
**Best for**: Implementation blueprints, component design, data flows

```
Use when:
- Planning a new feature
- Need specific file/component recommendations
- Want build sequence guidance
```

### feature-dev:code-explorer
**When**: Analyzing existing features deeply
**Best for**: Tracing execution paths, mapping dependencies

```
Use when:
- Understanding how existing code works
- Mapping data flow through system
- Documenting architecture patterns
```

### tc-implementation-agent
**When**: Production-ready feature development
**Best for**: Streamlined implementation with MCP integration

```
Use when:
- Implementing features following established patterns
- Need IDE diagnostics integration
- Want efficient, production-ready code
```

### python-expert
**When**: Python-specific tasks
**Best for**: SOLID principles, modern Python best practices

```
Use when:
- Python implementation
- Python performance optimization
- Python-specific patterns
```

### devops-architect
**When**: Infrastructure and deployment
**Best for**: CI/CD, reliability, observability

```
Use when:
- Setting up deployment pipelines
- Infrastructure automation
- Monitoring and alerting setup
```

---

## Quality & Review Agents

### feature-dev:code-reviewer
**When**: Code review and quality assessment
**Best for**: Bug detection, security, code quality

```
Use when:
- Reviewing pull requests
- Code quality assessment
- Finding bugs before merge
```

### quality-engineer
**When**: Comprehensive testing strategy
**Best for**: Test planning, edge case detection

```
Use when:
- Designing test strategy
- Finding edge cases
- Ensuring coverage
```

### security-engineer
**When**: Security vulnerability assessment
**Best for**: OWASP compliance, threat modeling

```
Use when:
- Security audit
- Vulnerability assessment
- Compliance checking
```

### performance-engineer
**When**: Performance optimization
**Best for**: Bottleneck identification, measurement-driven optimization

```
Use when:
- Performance issues
- Optimization analysis
- Scalability assessment
```

### tc-quality-reviewer
**When**: Enterprise-grade quality review
**Best for**: Production standards, architectural excellence

```
Use when:
- Critical code review
- Enterprise compliance
- Architecture validation
```

---

## Debugging & Analysis Agents

### root-cause-analyst
**When**: Complex bug investigation
**Best for**: Evidence-based analysis, hypothesis testing

```
Use when:
- Bug cause is unclear
- Multiple possible causes
- Need systematic investigation
```

### refactoring-expert
**When**: Code improvement
**Best for**: Technical debt reduction, clean code

```
Use when:
- Improving code quality
- Reducing complexity
- Modernizing patterns
```

### tc-codex-critic
**When**: External validation
**Best for**: Unbiased expert critique, final assessment

```
Use when:
- Want second opinion
- Final quality check
- External validation needed
```

---

## Documentation & Learning Agents

### technical-writer
**When**: Documentation creation
**Best for**: Clear, comprehensive docs for specific audiences

```
Use when:
- Creating documentation
- API documentation
- User guides
```

### learning-guide
**When**: Educational explanations
**Best for**: Teaching concepts, practical examples

```
Use when:
- User needs to learn concept
- Explaining complex code
- Tutorial creation
```

### socratic-mentor
**When**: Discovery-based learning
**Best for**: Strategic questioning, guided discovery

```
Use when:
- Teaching through questions
- Want user to discover answer
- Building understanding
```

---

## Testing Agents

### tc-frontend-tester
**When**: UI/UX testing
**Best for**: Browser-based testing, user experience validation

```
Use when:
- Frontend testing needed
- UI validation
- User flow testing
```

### plugin-dev:plugin-validator
**When**: Plugin validation
**Best for**: Checking plugin structure, manifest, components

```
Use when:
- Created/modified plugin
- Want to verify plugin correctness
- Pre-publish validation
```

### plugin-dev:skill-reviewer
**When**: Skill quality review
**Best for**: Skill best practices, description quality

```
Use when:
- Created/modified skill
- Want quality review
- Ensure skill follows patterns
```

### plugin-dev:agent-creator
**When**: Creating new agents
**Best for**: Agent definition, triggering configuration

```
Use when:
- Need to create new agent
- Defining agent behavior
- Agent configuration
```

---

## Context & Planning Agents

### tc-context-gatherer
**When**: Task-specific context analysis
**Best for**: Focused implementation guidance

```
Use when:
- Need targeted context for task
- Starting new implementation
- Understanding task scope
```

### tc-task-planner
**When**: Strategic implementation planning
**Best for**: Production-ready roadmaps

```
Use when:
- Complex task planning
- Multi-phase implementations
- Production planning
```

---

## Agent Selection Decision Tree

```
What do you need?
│
├─ Explore/Research
│  ├─ Unknown codebase → Explore
│  ├─ Complex research → general-purpose
│  └─ Claude Code help → claude-code-guide
│
├─ Plan/Design
│  ├─ Implementation plan → Plan
│  ├─ System design → system-architect
│  ├─ API design → backend-architect
│  └─ UI design → frontend-architect
│
├─ Implement
│  ├─ Feature blueprint → feature-dev:code-architect
│  ├─ Production code → tc-implementation-agent
│  └─ Python specific → python-expert
│
├─ Review/Quality
│  ├─ Code review → feature-dev:code-reviewer
│  ├─ Security audit → security-engineer
│  ├─ Performance → performance-engineer
│  └─ Enterprise review → tc-quality-reviewer
│
├─ Debug
│  ├─ Complex bugs → root-cause-analyst
│  └─ Code cleanup → refactoring-expert
│
└─ Document/Learn
   ├─ Write docs → technical-writer
   ├─ Explain code → learning-guide
   └─ Teach concepts → socratic-mentor
```

## Parallel Agent Execution

Launch independent agents simultaneously:
```
# Good: Multiple independent searches
Task(Explore): "Find authentication code"
Task(Explore): "Find database models"
Task(Explore): "Find API routes"

# Good: Different analysis types
Task(security-engineer): "Audit authentication"
Task(performance-engineer): "Profile API endpoints"
```

---

*See also: [tool-selection.md](tool-selection.md) for tool decisions*
