# CRE2 Email Profile Configuration

This document covers CRE2 email profile configuration, including critical precedence rules, syntax differences from PDF profiles, and migration guidance.

---

## Email Body Precedence Rules (CRITICAL)

CRE2 has **TWO fields** for email body content:

| Field | Purpose | Precedence |
|-------|---------|------------|
| `custrecord_pri_cre2_email_body` | Inline HTML body | **1st (highest)** |
| `custrecord_pri_cre2_gen_file_tmpl_doc` | Template file reference | 2nd (fallback) |

### The Critical Rule

**If `custrecord_pri_cre2_email_body` has ANY content, it is used.**
Template file is ONLY used when inline body is NULL/empty.

This is the #1 source of confusion when working with CRE2 email profiles.

### Common Mistake

Creating both an inline body AND a template file reference:
```
custrecord_pri_cre2_email_body = "<html>Old design...</html>"  ← Used!
custrecord_pri_cre2_gen_file_tmpl_doc = 52801458              ← Ignored!
```

Result: Old design shows instead of uploaded template.

### When to Use Each

| Approach | Use When |
|----------|----------|
| **Inline body only** | Simple emails, no conditional logic, quick prototyping |
| **Template file only** | Complex templates, conditional sections, version control |
| **Both** | **AVOID** - Creates confusion and maintenance issues |

### Clearing Inline Body to Use Template File

```bash
# Clear the inline body so CRE2 uses the template file
python3 update_record.py customrecord_pri_cre2_profile <ID> \
  --field 'custrecord_pri_cre2_email_body=' --env sb2
```

### Verifying Configuration

```bash
# Check what a profile is using
python3 query_netsuite.py "
  SELECT id, name,
    custrecord_pri_cre2_gen_file_tmpl_doc as template_file,
    CASE
      WHEN custrecord_pri_cre2_email_body IS NULL THEN 'NULL'
      WHEN LENGTH(custrecord_pri_cre2_email_body) = 0 THEN 'EMPTY'
      ELSE 'HAS_CONTENT'
    END as email_body_status
  FROM customrecord_pri_cre2_profile
  WHERE id = <PROFILE_ID>
" --env sb2 --format table
```

---

## Email vs PDF Profile Differences

| Aspect | Email Profile | PDF Profile |
|--------|--------------|-------------|
| **Output** | HTML email sent to recipient | PDF file generated |
| **Rendering Engine** | Email client (Outlook, Gmail, etc.) | BFO PDF engine |
| **CSS Support** | Limited (inline styles only) | BFO CSS subset |
| **Images** | External URLs **required** | Can embed or use URLs |
| **Testing Method** | Send test email | `render_pdf.py` script |
| **Body Source** | Inline body OR template file | Template file only |
| **Page Breaks** | N/A | Supported via BFO |
| **Headers/Footers** | N/A | Supported via BFO |

---

## Email-Specific FreeMarker Syntax

### Data Source Access

CRE2 email templates access data from query results:

```freemarker
<!-- Single-row data source -->
${customer.rows[0].companyname}
${salesorder.rows[0].tranid}
${salesorder.rows[0].total}

<!-- Multi-row data source -->
<#list salesorderlines.rows as line>
  ${line.item} - ${line.quantity} @ ${line.rate}
</#list>
```

### Native vs CRE2 Variable Mapping

When migrating from native NetSuite email templates to CRE2:

| Native Email Syntax | CRE2 Equivalent | Notes |
|--------------------|-----------------|-------|
| `${transaction.entity.companyname}` | `${customer.rows[0].companyname}` | Requires customer query |
| `${transaction.tranid}` | `${salesorder.rows[0].tranid}` | Requires SO query |
| `${transaction.total}` | `${salesorder.rows[0].total}` | Requires SO query |
| `${transaction@title}` | Hard-coded "Sales Order" | Or query record type |
| `${companyinformation.legalname}` | Query from company record | Requires company query |
| `${transaction.entity.email}` | `${customer.rows[0].email}` | Requires customer query |

### Required Queries for SO Confirmation

**Customer Query:**
```sql
SELECT id, email, firstname, lastname, companyname, isperson
FROM Customer
WHERE id = ${record.entity}
```

**Sales Order Query:**
```sql
SELECT id, tranid, total, trandate, custbody_8qp_paylink,
       BUILTIN.DF(terms) as terms, BUILTIN.DF(status) as status
FROM Transaction
WHERE id = ${record.id}
```

---

## Conditional Sections

### Pay Link Example (IT-20459 Pattern)

Show pay link section only when the field has content:

```freemarker
<#if (salesorder.rows[0].custbody_8qp_paylink)?has_content>
  <!-- IMPORTANT NOTICE BOX -->
  <table style="border: 2px solid #c41e3a; background-color: #fff5f5; width: 100%;">
    <tr>
      <td style="padding: 15px; text-align: center; color: #c41e3a; font-weight: bold;">
        IMPORTANT NOTICE<br/>
        For PCI compliance, we no longer accept credit card information
        over phone or email. Please use the secure payment link below.
      </td>
    </tr>
  </table>

  <!-- PAY NOW BUTTON -->
  <table style="width: 100%; margin-top: 15px;">
    <tr>
      <td style="text-align: center;">
        <a href="${salesorder.rows[0].custbody_8qp_paylink}"
           style="background-color: #c41e3a; color: #ffffff;
                  padding: 15px 40px; text-decoration: none;
                  display: inline-block; border-radius: 5px; font-weight: bold;">
          PAY NOW - $${salesorder.rows[0].total!'0.00'}
        </a>
      </td>
    </tr>
  </table>
</#if>
```

### Customer Name Pattern (Person vs Company)

```freemarker
<#if customer.rows[0].isperson == 'T' &&
     ((customer.rows[0].firstname)?has_content || (customer.rows[0].lastname)?has_content)>
  Dear ${customer.rows[0].firstname!''} ${customer.rows[0].lastname!''},
<#elseif customer.rows[0].isperson == 'F' && (customer.rows[0].companyname)?has_content>
  Dear ${customer.rows[0].companyname},
<#else>
  Dear Valued Customer,
</#if>
```

---

## Email Image Requirements

### External URLs Required

Images in CRE2 emails **MUST** use external NetSuite URLs:

```html
<!-- CORRECT - External URL with hash -->
<img src="https://4138030.app.netsuite.com/core/media/media.nl?id=20634688&c=4138030&h=JMQE5iAkIjWMFFjcIAPJZhvSC9sFSlCEkSEgk3KW5u8-pZD6" />

<!-- WRONG - Internal path (won't work in email clients) -->
<img src="/core/media/media.nl?id=20634688" />
```

### URL Format

```
https://4138030.app.netsuite.com/core/media/media.nl?id=<FILE_ID>&c=4138030&h=<HASH>
```

| Parameter | Value | Description |
|-----------|-------|-------------|
| `id` | File internal ID | e.g., 20634688 |
| `c` | Company ID | Always 4138030 for Twisted X |
| `h` | Security hash | Required for external access |

### Getting Image Hash

```bash
# Query file cabinet for URL with hash
python3 query_netsuite.py "
  SELECT id, name, url
  FROM file
  WHERE id = 20634688
" --env prod
```

---

## Email CSS Limitations

Email clients have limited CSS support. Follow these rules:

### DO Use

- Inline styles (`style="..."` attributes)
- `<table>` for layout
- Basic colors and fonts
- Padding and margins on table cells
- `border-collapse: collapse` for tables

### DON'T Use

- External stylesheets (`<link>`)
- `<style>` blocks (unreliable)
- CSS Grid or Flexbox
- `float` layout
- CSS variables
- Media queries (limited support)
- `position: absolute/relative`

### Email-Safe Layout Pattern

```html
<!-- Outer wrapper for background -->
<table border="0" cellpadding="0" cellspacing="0" width="100%" bgcolor="#eeeeee">
  <tr>
    <td align="center">
      <!-- Content container -->
      <table border="0" cellpadding="0" cellspacing="0" width="600" bgcolor="#ffffff">
        <tr>
          <td style="padding: 20px; font-family: Arial, sans-serif;">
            Content here
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
```

---

## Testing Email Profiles

Unlike PDF profiles, email profiles cannot be tested with `render_pdf.py`.

### Testing Options

1. **Send Test Email** - Configure test recipient and trigger profile
2. **Preview in NetSuite** - Use CRE2 profile test/preview feature
3. **Check Data Sources** - Verify queries return expected data:

```bash
# Test customer query
python3 query_netsuite.py "
  SELECT id, email, companyname, isperson
  FROM Customer
  WHERE id = 27959
" --env sb2 --format table

# Test sales order query
python3 query_netsuite.py "
  SELECT id, tranid, total, custbody_8qp_paylink
  FROM Transaction
  WHERE id = 22791151
" --env sb2 --format table
```

---

## Common Issues and Solutions

### Issue: Email uses old design
**Cause**: Inline body taking precedence over template file
**Solution**: Clear `custrecord_pri_cre2_email_body` field

### Issue: Images not displaying
**Cause**: Using internal paths instead of external URLs with hash
**Solution**: Use full external URL format with security hash

### Issue: Layout broken in Outlook
**Cause**: Using CSS not supported by Outlook (flexbox, grid)
**Solution**: Use table-based layout with inline styles

### Issue: Variables not resolving
**Cause**: Wrong data source syntax (native vs CRE2)
**Solution**: Use `${datasource.rows[0].field}` pattern

---

## Related Documentation

- `migration_workflow.md` - Steps for migrating native templates to CRE2
- `branding_assets.md` - Logo and image file IDs by context
- `common_patterns.md` - Reusable FreeMarker patterns
- `cre2_data_sources.md` - Query configuration reference
