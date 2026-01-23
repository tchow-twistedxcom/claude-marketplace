# NetSuite CRE 2.0 Skill - Quick Start

Prolecto's Content Renderer Engine 2 for PDF/HTML document generation in NetSuite.

## Quick Reference

### What is CRE 2.0?

CRE 2.0 generates dynamic PDFs and HTML emails using:
- **FreeMarker Templates**: Industry-standard templating with `${variable}`, `<#if>`, `<#list>`
- **Multiple Data Sources**: Saved Searches OR SuiteQL queries
- **Flexible Output**: PDF documents, HTML emails, or both

### When to Use CRE 2.0

| Scenario | Use CRE 2.0? |
|----------|--------------|
| Customer statements with custom fields | ✅ Yes |
| Invoices with discount calculations | ✅ Yes |
| Shipping notification emails | ✅ Yes |
| Standard transaction PDF | ❌ Use Advanced PDF |
| Simple record printout | ❌ Use Advanced PDF |

### Key Components

```
CRE2 Profile → Data Sources → FreeMarker Template → PDF/HTML Output
```

## FreeMarker Cheat Sheet

### Variables
```freemarker
${record.companyname}              <!-- Record field -->
${customer.rows[0].salesrep}       <!-- Saved search result -->
${tran.openbalance?number}         <!-- Convert to number -->
```

### Conditionals
```freemarker
<#if value?has_content>
    ${value}
<#else>
    N/A
</#if>
```

### Lists
```freemarker
<#list tran.rows as line>
    <tr>
        <td>${line.tranid}</td>
        <td>${line.amount}</td>
    </tr>
</#list>
```

### Assignments
```freemarker
<#assign total = 0>
<#assign total = total + item.amount?number>
```

## Common Commands

### List Profiles
```bash
python3 scripts/cre2_profile.py list --env sb1
```

### Test Render
```bash
python3 scripts/cre2_profile.py test 15 12345 --env sb1
```

### Validate Template
```bash
python3 scripts/validate_template.py template.html
```

## Example: Add Discount Column to Statement

1. **Create SuiteQL data source** with discount query (see SKILL.md)
2. **Add template columns**:
```freemarker
<th>Discount</th>
<th>Disc. By</th>
```
3. **Add data cells**:
```freemarker
<td>${disc.discountamount}</td>
<td>
    <#if (disc.daystodiscount > 0)>
        ${disc.daystodiscount} days
    <#else>
        Expired
    </#if>
</td>
```

## File Locations

| Item | Path |
|------|------|
| Templates | `/SuiteScripts/Prolecto/CRE/` or `/SuiteScripts/` |
| Profiles | Customization > Printing & Branding > CRE2 Profiles |
| Bundle | `/.bundle/369503/CRE2/` |

## JavaScript Override Hooks

For custom data transformation before template rendering, use a JS Override hook:

```javascript
// beforeTranslate hook - data becomes ${OVERRIDE} in template
function beforeTranslate(cre2) {
    var rows = cre2.dataSources.myQuery.data;  // Access data sources
    return {
        myData: { field1: rows[0].value }      // Available as ${OVERRIDE.myData}
    };
}
```

**Common Pitfalls:**
- Use `cre2.dataSources.<name>.data` (NOT `context.data`)
- Return plain object (NOT the `cre2` object - causes cyclic reference)
- Always null-check data sources and rows

See **[references/js_override_hooks.md](references/js_override_hooks.md)** for complete patterns.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Variable blank | Check `?has_content` and data source query |
| Number error | Add `?number` conversion and null check |
| List empty | Verify data source returns rows |
| PDF fails | Check XML/HTML for unclosed tags |
| OVERRIDE empty | Check JS hook returns object, not cre2 |
| Cyclic reference | Return plain object, not cre2 engine |

## Next Steps

- Read full documentation: `SKILL.md`
- See examples: `templates/` directory
- FreeMarker reference: `references/freemarker_syntax.md`
