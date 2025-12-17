# ClaudeKit Skills

Curated collection of 20+ specialized skills for Claude Code from the [ClaudeKit repository](https://github.com/mrgoonie/claudekit-skills).

## Overview

ClaudeKit Skills provides expert-level instruction sets for Claude Code across multiple domains. Each skill contains mission briefs, guardrails, and integration hints designed for transparency and easy customization.

## Installation

Install via Claude Code marketplace:
```
/plugin install claudekit-skills
```

Or clone manually to your project:
```bash
git clone https://github.com/mrgoonie/claudekit-skills.git
cp -r claudekit-skills/.claude/skills/* .claude/skills/
```

## Available Skills

### Development Tools

- **nextjs** - Next.js 15+ development with App Router, Server Components, and best practices
- **tailwindcss** - Tailwind CSS styling with modern patterns and optimization
- **shadcn-ui** - shadcn/ui component library integration and customization
- **turborepo** - Turborepo monorepo management and optimization
- **better-auth** - Better-auth authentication framework implementation

### Media Processing

- **ffmpeg** - FFmpeg video/audio processing automation
- **imagemagick** - ImageMagick image manipulation and batch processing

### AI & Agents

- **google-adk-python** - Google AI Development Kit for Python integration
- **mcp-builder** - MCP (Model Context Protocol) server builder guide
- **claude-code** - Claude Code usage patterns and best practices

### Document Processing

- **document-skills** - PDF, Excel, PowerPoint, Word manipulation skills

### Problem-Solving Frameworks

- **problem-solving** - Inversion thinking, pattern recognition frameworks
- **debugging** - Systematic debugging methodologies

### Design & Icons

- **canvas-design** - Canvas design tools and workflows
- **remix-icon** - Remix Icon library integration (3,100+ icons)

### Development Utilities

- **docs-seeker** - Documentation search and integration patterns
- **repomix** - Repository management and optimization
- **shopify** - Shopify development patterns and API integration
- **skill-creator** - Create custom Claude Code skills

## Skill Structure

Each skill contains:
- **Mission Brief** - Clear objectives and scope
- **Guardrails** - Checklists and validation steps
- **Integration Hints** - How to combine with other tools
- **Examples** - Real-world usage patterns

## Usage

After installation, Claude Code automatically detects and uses these skills. You can invoke specific skills by context or explicitly:

```
# Claude will automatically use relevant skills based on your request
"Create a Next.js app with Tailwind and shadcn/ui"

# Or reference skills explicitly
"Use the debugging skill to analyze this error"
```

## Customization

Skills are stored as text files and can be customized:

```bash
# Edit a skill
nano .claude/skills/nextjs/mission-brief.md

# Add custom guardrails
echo "- Custom validation step" >> .claude/skills/nextjs/guardrails.md
```

## Credits

- **Original Author**: [mrgoonie](https://github.com/mrgoonie)
- **Repository**: [claudekit-skills](https://github.com/mrgoonie/claudekit-skills)
- **Marketplace Integration**: tchow-essentials

## License

MIT License - See original repository for details

## Support

- Original Issues: https://github.com/mrgoonie/claudekit-skills/issues
- Marketplace Issues: https://github.com/tchow-twistedxcom/claude-marketplace/issues
