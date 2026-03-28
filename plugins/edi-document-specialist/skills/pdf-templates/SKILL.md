---
name: pdf-templates
description: BFO PDF renderer compatibility and CRE2 template patterns. Use when creating or debugging PDF templates for NetSuite CRE2 Framework, especially for BFO rendering issues (logo distortion, layout overlap).
triggers:
  keywords:
    - bfo
    - pdf template
    - cre2 template
    - freemarker
    - pdf rendering
    - logo distortion
    - layout overlap
    - pdf spacing
  file_patterns:
    - "*_PDF.html"
    - "*.ftl"
---

# PDF Templates Skill

BFO PDF renderer compatibility and CRE2 template patterns for NetSuite.

## Resources

- [BFO Compatibility Guide](resources/bfo-compatibility.md)
- [FreeMarker Reference](resources/freemarker-reference.md)
- [Template Patterns](resources/template-patterns.md)

## Key BFO Rules

- Use `dpi` attribute for images (not height/width) — higher DPI = smaller image
- Use tables for layout (not divs with CSS margins)
- Use `padding-bottom` for line spacing (not `<br/>`)
- Escape `&` as `&amp;` in URLs
- Inline styles only (no CSS classes)

## Examples

**Logo is distorted in PDF**
Use dpi attribute instead of height — see bfo-compatibility.md.

**Text is overlapping in PDF**
Use tables with padding-bottom instead of `<br/>` tags.

**How do I iterate over line items?**
Use `<#list>` directive — see freemarker-reference.md.

**How do I format currency?**
Use formatCurrency() or string interpolation — see template-patterns.md.
