# tchow-essentials Marketplace Integration Process

Personal process for integrating new skills into the tchow-essentials marketplace. This ensures proper discovery, documentation, and maintainability.

## Post-Creation Integration Checklist

After creating a new skill, complete these integration steps:

### Step 1: Update Skill Router

**File**: `scripts/skill-router.py`

Add pattern matching for the new skill to enable automatic activation.

```python
"<skill-name>": {
    "patterns": [
        r"\b(<keyword1>)\b.*\b(<keyword2>)\b",
        r"\b(<keyword3>)\b.*\b(<action>)\b",
        # Add 2-4 patterns that capture different ways users might request the skill
    ],
    "skill_name": "<plugin-name>:<skill-name>",
    "priority": 3,  # 1=highest, 5=lowest
},
```

**Pattern Guidelines**:
- Use word boundaries (`\b`) to avoid false positives
- Create patterns for different phrasings (e.g., "create confluence page" vs "write to confluence")
- Include action verbs relevant to the skill's purpose
- Test patterns with `python3 scripts/skill-router.py --test "<user query>"`

### Step 2: Update Documentation

#### USAGE.md (`docs/USAGE.md`)

Add a section for the new skill/plugin under the appropriate category:

```markdown
## <Plugin Name>

<Brief description of what the plugin does.>

### Skills

#### <Skill Name>
<What the skill does.>

**Activates when:**
- <Trigger 1>
- <Trigger 2>

**Example:**
```
<Example user query>
[<skill-name> skill activates]
```

**Capabilities:**
- <Capability 1>
- <Capability 2>
```

#### README.md (Root)

1. Update the tagline if adding a major category
2. Add to "What's Included" section under appropriate category
3. Add to "Plugin Details" section with commands/skills/capabilities
4. Update version number if significant

#### INSTALLATION.md (`docs/INSTALLATION.md`)

If the skill requires setup:
1. Add prerequisites if new dependencies
2. Add setup section with configuration steps
3. Update "Verifying Installation" section with new commands

### Step 3: Update Marketplace Registry

**File**: `.claude-plugin/marketplace.json`

If adding a new plugin (not just a skill to existing plugin):

```json
{
  "name": "<plugin-name>",
  "source": "./plugins/<plugin-name>",
  "description": "<Comprehensive description with key features>",
  "version": "1.0.0",
  "category": "<skills|integration|ecommerce|security|framework>",
  "keywords": ["<keyword1>", "<keyword2>", "<keyword3>"]
}
```

If updating an existing plugin:
1. Update `version` field
2. Update `description` if capabilities changed significantly

### Step 4: Update Plugin Manifest

**File**: `plugins/<plugin-name>/plugin.json`

Ensure the skill is registered:

```json
{
  "skills": [
    "./skills/<skill-name>"
  ]
}
```

Update version to match marketplace.json.

## Skill Router Pattern Examples

### API Integration Skills

```python
"<service>-api": {
    "patterns": [
        r"\b(<service>)\b.*\b(api|endpoint|request)\b",
        r"\b(<service>)\b.*\b(authenticate|oauth|token)\b",
        r"\b(list|get|create|update|delete)\b.*\b(<service>)\b.*\b(<resource>)\b",
    ],
    "skill_name": "<plugin>:<service>-api",
    "priority": 2,
},
```

### Document Processing Skills

```python
"document-<format>": {
    "patterns": [
        r"\b(<format>)\b.*\b(create|edit|read|write)\b",
        r"\b(create|edit|read|write)\b.*\b(<format>)\b",
        r"\b(<format>)\b\s+(file|document)\b",
    ],
    "skill_name": "document-skills:<format>",
    "priority": 3,
},
```

### Debugging/Methodology Skills

```python
"debugging-<method>": {
    "patterns": [
        r"\b(debug|troubleshoot)\b.*\b(<symptom>)\b",
        r"\b(<method>)\b.*\b(analysis|approach)\b",
        r"\b(help|how)\b.*\b(debug|fix|trace)\b.*\b(<focus>)\b",
    ],
    "skill_name": "claudekit-skills:<method>",
    "priority": 4,
},
```

## Documentation Templates

### For API Integration Skills

```markdown
## <Service Name> Skills

<Service> integration via REST/GraphQL API.

### Skills

#### <Service> API
Full coverage for <service> operations.

| Category | Operations |
|----------|------------|
| <Resource1> | List, get, create, update, delete |
| <Resource2> | List, get, create |

**Authentication:**
- <Auth type> (OAuth 2.0 / API Key / etc.)
- <Special notes>

**Activates when:**
```
<Example query>
[<service>-api skill activates]
```
```

### For Methodology/Framework Skills

```markdown
### <Methodology Name>

<Number> <type> for <purpose>:

| <Type> | When to Use |
|--------|-------------|
| `<name1>` | <Description> |
| `<name2>` | <Description> |

**Activates when:**
```
<Example query>
[<methodology> skill activates]
```
```

## Version Bump Guidelines

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| New skill added | Patch (x.x.+1) | 1.2.0 → 1.2.1 |
| New plugin added | Minor (x.+1.0) | 1.2.0 → 1.3.0 |
| Major feature/API change | Major (+1.0.0) | 1.2.0 → 2.0.0 |
| Documentation only | No bump | - |
| Bug fix | Patch (x.x.+1) | 1.2.0 → 1.2.1 |

## Quick Reference: Files to Update

| Adding... | skill-router.py | USAGE.md | README.md | INSTALLATION.md | marketplace.json | plugin.json |
|-----------|-----------------|----------|-----------|-----------------|------------------|-------------|
| New skill to existing plugin | ✓ | ✓ | Optional | If setup needed | Update version | ✓ |
| New plugin | ✓ | ✓ | ✓ | ✓ | ✓ (add entry) | Create new |
| Updating existing skill | If patterns change | If capabilities change | If major | If setup changed | Update version | Update version |

---

*This is a personal process document for tchow-essentials marketplace maintenance.*
