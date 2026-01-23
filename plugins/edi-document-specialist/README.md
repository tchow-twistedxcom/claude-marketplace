# EDI Document Specialist Plugin

Knowledge base and tooling for EDI document mapping, PDF template generation, and notification workflows in the B2B Dashboard.

## Purpose

This plugin provides:
- **X12 EDI Segment References**: Field mappings for 810, 850, 855, 856, 860 documents
- **BFO PDF Compatibility Guide**: NetSuite's PDF renderer quirks and workarounds
- **FreeMarker Template Patterns**: CRE2 template syntax and best practices
- **EDI Document Agent**: Subagent for complex EDI workflows

## Skills

### edi-mapping
X12 EDI segment references with field-to-template variable mappings.

**Resources**:
- `x12-segments-810.md` - Invoice segments (BIG, N1, IT1, ITD, TDS)
- `x12-segments-850.md` - Purchase Order segments
- `x12-segments-855.md` - PO Acknowledgment segments
- `x12-segments-856.md` - Advance Ship Notice segments
- `x12-segments-860.md` - PO Change segments

### pdf-templates
BFO PDF renderer compatibility and CRE2 template patterns.

**Resources**:
- `bfo-compatibility.md` - BFO quirks, image handling, layout rules
- `freemarker-reference.md` - FreeMarker syntax for CRE2 templates
- `template-patterns.md` - Common template patterns and examples

## Agent

### edi-document-agent
Use this subagent for complex EDI workflows:
- Creating or modifying CRE2 PDF templates
- Mapping X12 EDI segments to template fields
- Setting up notification rules for EDI events
- Debugging PDF rendering issues

## Dependencies

Requires the `netsuite-skills` plugin for:
- `netsuite-cre2` skill - Profile management, template testing
- `netsuite-file-cabinet` skill - File operations

## Usage Examples

### Creating a New Trading Partner Template

```bash
# 1. Clone existing profile for new trading partner
python3 ~/.claude/plugins/.../netsuite-cre2/scripts/clone_profile.py 17 \
  --name "TWX-EDI-810-NEWPARTNER-PDF" \
  --template 52794300 \
  --env sb2

# 2. Compare local template with NetSuite version
python3 ~/.claude/plugins/.../netsuite-file-cabinet/scripts/compare_file.py \
  ./template.html --file-id 52794300 --env sb2

# 3. Validate template before upload
python3 ~/.claude/plugins/.../netsuite-cre2/scripts/validate_template.py \
  ./template.html

# 4. Upload template to NetSuite
python3 ~/.claude/plugins/.../netsuite-file-cabinet/scripts/upload_file.py \
  ./template.html --folder 1285029 --env sb2

# 5. Test profile rendering
python3 ~/.claude/plugins/.../netsuite-cre2/scripts/cre2_render.py debug \
  --profile-id 118 --record-id 12345 --env sb2
```

### Debugging PDF Layout Issues

1. Check `resources/bfo-compatibility.md` for known quirks
2. Use `dpi` attribute (not `height`) for images
3. Use tables (not `<br/>`) for vertical spacing
4. Escape `&` as `&amp;` in URLs

## Lessons Learned (from Rocky 810 PDF Work)

1. **BFO Image Handling**: Higher DPI = smaller rendered image (inverse relationship)
2. **Layout Spacing**: Tables with `padding-bottom` work better than `<br/>` tags
3. **URL Escaping**: Always escape `&` as `&amp;` for XML/BFO compatibility
4. **Profile Cloning**: Need to clone both profile AND data sources with new parent reference
5. **File Verification**: Always compare local vs NetSuite file to ensure correct version
