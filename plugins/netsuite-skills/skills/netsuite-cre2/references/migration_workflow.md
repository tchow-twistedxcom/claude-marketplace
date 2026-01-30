# Native Template to CRE2 Migration Workflow

This document provides a step-by-step workflow for migrating existing NetSuite native email templates to CRE2. Following this workflow prevents common mistakes like design mismatches and wrong branding assets.

---

## The Golden Rule

**ALWAYS examine the existing template FIRST before building a CRE2 replacement.**

Don't assume what the template should look like. Query it, extract it, understand it.

---

## Step 1: Query Existing Native Template

### Find the Template

```bash
# Find email template by scriptid
python3 query_netsuite.py "
  SELECT id, name, scriptid, subject, recordtype
  FROM emailtemplate
  WHERE scriptid LIKE '%so_confirmation%'
" --env prod --format table
```

### Get Full Content

```bash
# Get template content
python3 query_netsuite.py "
  SELECT id, name, scriptid, subject, content
  FROM emailtemplate
  WHERE id = 433
" --env prod --format json
```

### Export for Analysis

Save the content to a local file for detailed analysis:

```bash
python3 query_netsuite.py "
  SELECT content FROM emailtemplate WHERE id = 433
" --env prod --format json > native_template.json
```

---

## Step 2: Extract Design Elements

Analyze the native template and document:

### Branding Assets Checklist

- [ ] **Logo image ID(s)** - Extract from `<img>` tags
- [ ] **Banner image ID(s)** - Check for hero/header images
- [ ] **Social media icons** - Footer icons (Instagram, Facebook, etc.)
- [ ] **Background colors** - Header, footer, content areas
- [ ] **Text colors** - Headers, body text, links
- [ ] **Font family** - Usually Open Sans, Helvetica, Arial

### Content Structure Checklist

- [ ] **Header section** - Logo placement, background color
- [ ] **Greeting pattern** - How customer name is displayed
- [ ] **Main content** - What information is shown
- [ ] **Footer section** - Contact info, social links
- [ ] **Design philosophy** - Detailed tables vs simple text

### Example Extraction (SO Confirmation)

From native template `custemailtmpl_so_confirmation`:

| Element | Value | Notes |
|---------|-------|-------|
| Main Logo | 20634688 | White on dark navy header |
| Banner | 47017000 | "The Original Driving Moc" |
| Header BG | #242f46 | Dark navy |
| Content BG | #ffffff | White |
| Instagram | 57140 | Footer icon |
| Facebook | 57139 | Footer icon |
| Design | Simple | "See attached PDF" approach |

---

## Step 3: Map Variables to CRE2 Syntax

Create a mapping table for all native variables:

### Common Mappings

| Native Variable | CRE2 Query | CRE2 Variable |
|-----------------|-----------|---------------|
| `${transaction.entity.companyname}` | Customer | `${customer.rows[0].companyname}` |
| `${transaction.entity.firstname}` | Customer | `${customer.rows[0].firstname}` |
| `${transaction.entity.lastname}` | Customer | `${customer.rows[0].lastname}` |
| `${transaction.entity.email}` | Customer | `${customer.rows[0].email}` |
| `${transaction.tranid}` | Transaction | `${salesorder.rows[0].tranid}` |
| `${transaction.total}` | Transaction | `${salesorder.rows[0].total}` |
| `${transaction.trandate}` | Transaction | `${salesorder.rows[0].trandate}` |
| `${transaction@title}` | N/A | Hard-code "Sales Order" |
| `${companyinformation.legalname}` | Company | `${company.rows[0].legalname}` |

### Required CRE2 Queries

Based on the mappings, create data source queries:

**Customer Query:**
```sql
SELECT id, email, firstname, lastname, companyname, isperson
FROM Customer
WHERE id = ${record.entity}
```

**Transaction Query:**
```sql
SELECT id, tranid, total, trandate, terms, status,
       custbody_8qp_paylink
FROM Transaction
WHERE id = ${record.id}
```

---

## Step 4: Assess Design Philosophy

### Key Question

**Does the existing email show detailed data OR reference an attachment?**

| Design Type | Characteristics | When to Use |
|-------------|-----------------|-------------|
| **Detailed** | Line items table, totals, calculations | Invoices, statements, quotes |
| **Reference** | Simple text + "see attached PDF" | Order confirmations with PDF |

### Why This Matters

If the native template says "Please find the attached PDF containing details of your order" - then **DON'T** add elaborate order tables in the CRE2 version.

Match the existing design philosophy. Don't over-engineer.

### Red Flags (Over-Engineering)

- Adding order line items when native doesn't have them
- Adding pricing tables when native references PDF
- Adding multiple sections when native is simple
- Creating elaborate headers when native is minimal

---

## Step 5: Build CRE2 Template

### Template Structure

Follow the native template structure exactly:

```html
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="UTF-8">
    <title>Sales Order Confirmation</title>
</head>
<body style="background-color: #eeeeee; margin: 0; padding: 0;">

<!-- HEADER - Match native exactly -->
<table>...</table>

<!-- CONTENT - Match native structure -->
<table>...</table>

<!-- NEW: Conditional sections (if needed) -->
<#if (salesorder.rows[0].custbody_8qp_paylink)?has_content>
  <!-- Pay link section -->
</#if>

<!-- FOOTER - Match native exactly -->
<table>...</table>

</body>
</html>
```

### Adding New Features

When adding features the native template doesn't have (like pay link):
1. Keep them **visually consistent** with existing design
2. Use **conditional logic** so they don't appear when not applicable
3. **Insert at logical points** (after greeting, before footer)

---

## Step 6: Configure CRE2 Profile

### Profile Settings

| Field | Value | Notes |
|-------|-------|-------|
| Name | TWX \| SO Confirmation Email | Clear naming |
| Record Type | TRANSACTION | Sales Order |
| Send Email | Yes | Enable email sending |
| Email Body | **LEAVE EMPTY** | Use template file |
| Template File | Upload and reference | Stores template |

### Critical: Email Body Field

**Leave `custrecord_pri_cre2_email_body` empty** if using a template file.

If this field has content, it overrides the template file.

### Data Sources

Create query records for:
1. Customer data
2. Transaction data
3. Line items (if needed)

---

## Step 7: Test Both Scenarios

If adding conditional sections:

### Test Case 1: Condition Met

```bash
# Find record WITH pay link
python3 query_netsuite.py "
  SELECT id, tranid, custbody_8qp_paylink
  FROM Transaction
  WHERE type = 'SalesOrd' AND custbody_8qp_paylink IS NOT NULL
  FETCH FIRST 5 ROWS ONLY
" --env sb2 --format table
```

Test with this record - conditional section should appear.

### Test Case 2: Condition Not Met

```bash
# Find record WITHOUT pay link
python3 query_netsuite.py "
  SELECT id, tranid
  FROM Transaction
  WHERE type = 'SalesOrd' AND custbody_8qp_paylink IS NULL
  FETCH FIRST 5 ROWS ONLY
" --env sb2 --format table
```

Test with this record - conditional section should NOT appear.

---

## Migration Checklist

Before marking migration complete:

- [ ] Native template content extracted and analyzed
- [ ] All branding assets identified (logos, colors, icons)
- [ ] All variables mapped to CRE2 syntax
- [ ] Design philosophy preserved (detailed vs simple)
- [ ] CRE2 queries created and tested
- [ ] Template file uploaded (not inline body)
- [ ] `custrecord_pri_cre2_email_body` is EMPTY
- [ ] Tested with condition met (if applicable)
- [ ] Tested without condition (if applicable)
- [ ] Visual comparison to native template done
- [ ] Stakeholder approval received

---

## Common Migration Mistakes

### Mistake 1: Not examining native template first

**Result**: CRE2 template looks completely different from what users expect.

**Prevention**: Always query and analyze native template before writing any code.

### Mistake 2: Using both inline body and template file

**Result**: Inline body takes precedence, template file ignored.

**Prevention**: Clear inline body field when using template file.

### Mistake 3: Using wrong branding assets

**Result**: Different logo, wrong colors, inconsistent look.

**Prevention**: Extract exact file IDs from native template.

### Mistake 4: Over-engineering simple templates

**Result**: Added complexity that native template didn't have.

**Prevention**: Match native design philosophy exactly.

---

## Related Documentation

- `email_profiles.md` - Email body precedence rules
- `branding_assets.md` - Logo and image file IDs
- `common_patterns.md` - FreeMarker template patterns
