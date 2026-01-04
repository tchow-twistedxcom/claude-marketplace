---
description: View portable setup documentation
argument-hint: "<readme|dependencies|customization|all>"
allowed-tools: ["Read"]
---

View documentation bundled with the portable setup plugin. Provides quick access to setup guides, dependency information, and customization instructions without leaving Claude Code.

## Instructions

1. **Locate the plugin directory:**
   - Use `Bash`: `find ~/.claude/plugins -name "portable-setup" -type d | head -1`
   - Store as `PLUGIN_DIR`

2. **Parse the topic argument:**
   - Expected values: `readme`, `dependencies`, `customization`, `all`
   - If no argument or invalid: Show usage help and available topics

3. **Map topic to file:**
   - `readme` → `$PLUGIN_DIR/assets/docs/README.md`
   - `dependencies` → `$PLUGIN_DIR/assets/docs/DEPENDENCIES.md`
   - `customization` → `$PLUGIN_DIR/assets/docs/CUSTOMIZATION.md`
   - `all` → Read all three files

4. **Read and display documentation:**

   **For single topic:**
   - Read the file using `Read` tool
   - Display with clear header:
     ```
     ═══════════════════════════════════════════
     📚 Portable Setup - [Topic Name]
     ═══════════════════════════════════════════

     [file contents]
     ```

   **For "all" topic:**
   - Create table of contents:
     ```
     ═══════════════════════════════════════════
     📚 Portable Setup - Complete Documentation
     ═══════════════════════════════════════════

     Table of Contents:
     1. README - Quick start guide and overview
     2. DEPENDENCIES - System requirements and installation
     3. CUSTOMIZATION - Customization options and patterns

     ───────────────────────────────────────────
     ```
   - Read and display each file in sequence with separators
   - Between files, show:
     ```
     ───────────────────────────────────────────
     Next: [Topic Name]
     ───────────────────────────────────────────
     ```

5. **Handle missing files:**
   - If file doesn't exist:
     ```
     ❌ Documentation file not found: [filename]

     This might indicate an incomplete plugin installation.
     Try reinstalling the plugin or check:
     $PLUGIN_DIR/assets/docs/
     ```

6. **Offer search capability (if user asks):**
   - If user asks to search for specific term:
     - Read all three doc files
     - Search for term (case-insensitive)
     - Display matching sections with context
     - Format:
       ```
       🔍 Search results for "[term]":

       In README.md:
       - [Line X]: [matching line with context]

       In DEPENDENCIES.md:
       - [Line Y]: [matching line with context]
       ```

7. **Display usage help if needed:**
   ```
   📚 Portable Setup Documentation

   Usage: /portable:docs <topic>

   Available topics:
   - readme        Quick start guide and overview
   - dependencies  System requirements and installation
   - customization Customization options and patterns
   - all           View all documentation

   Examples:
     /portable:docs readme
     /portable:docs dependencies
     /portable:docs all
   ```

8. **Suggest related commands:**
   - After displaying docs, suggest:
     ```
     💡 Related commands:
     - /portable:install  - Install portable setup
     - /portable:export   - Export current configuration
     - /portable:sync     - Synchronize across environments
     - /portable:validate - Validate installation
     ```

## Usage Examples

**View quick start guide:**
```
/portable:docs readme
```
Displays README.md with setup instructions.

**View dependency information:**
```
/portable:docs dependencies
```
Shows system requirements and installation commands.

**View customization guide:**
```
/portable:docs customization
```
Displays customization options for statusline, agents, hooks.

**View all documentation:**
```
/portable:docs all
```
Displays complete documentation in sequence.

## Documentation Contents

**README.md:**
- Quick start installation instructions
- What gets packaged vs excluded
- Prerequisites and system requirements
- Common issues and solutions

**DEPENDENCIES.md:**
- Required system packages
- Optional tools and features
- Installation commands per OS
- Version compatibility information

**CUSTOMIZATION.md:**
- Statusline customization patterns
- Adding custom agents and commands
- Hook development examples
- MCP server integration

## Notes

- Documentation is read-only and bundled with the plugin
- Same content as running `cat $PLUGIN_DIR/assets/docs/<file>.md`
- Provides quick reference without leaving Claude Code
- All docs are in Markdown format for easy reading
- Can copy-paste commands directly from documentation
- For most up-to-date docs, use the plugin's built-in versions
