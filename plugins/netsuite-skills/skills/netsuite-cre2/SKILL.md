# NetSuite CRE 2.0 (Content Renderer Engine) Skill

skill_name: netsuite-cre2
version: 1.5.0
description: Complete CRE 2.0 skill for Prolecto's Content Renderer Engine 2 - FreeMarker template development, profile management, and PDF/HTML document generation in NetSuite
trigger_patterns:
  - "CRE2"
  - "CRE 2.0"
  - "Content Renderer"
  - "FreeMarker template"
  - "customer statement"
  - "PDF template"
  - "email template NetSuite"
  - "document generation NetSuite"
  - "Prolecto template"
  - "render PDF"
  - "statement template"
mcp_servers: []
tools_required:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob

---

## Overview

CRE 2.0 (Content Renderer Engine 2) is Prolecto's document generation framework for NetSuite. It enables:

- **PDF Generation**: Customer statements, invoices, credit letters
- **HTML Email Templates**: Shipping notifications, order confirmations
- **Dynamic Data Binding**: Pull data from Saved Searches OR SuiteQL queries
- **FreeMarker Templating**: Industry-standard template engine for data interpolation

### Why CRE 2.0 Over Standard Advanced PDF Templates?

| Feature | Advanced PDF | CRE 2.0 |
|---------|-------------|---------|
| Data Access | Flattened statement lines | Full record access via queries |
| Custom Fields | Limited on statements | Full access via SuiteQL |
| Calculations | Limited | Full FreeMarker logic |
| Data Sources | Fixed | Saved Search OR SuiteQL |
| Flexibility | Low | High |

**Key Advantage**: CRE 2.0 can access invoice-level fields that standard Advanced PDF templates cannot. For example, discount dates and discount amounts require joining the Transaction and Term tables - only possible with CRE 2.0's SuiteQL data sources.

---

## Architecture

### CRE 2.0 Components

```
┌─────────────────────────────────────────────────────────┐
│                    CRE 2.0 System                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │  CRE2 Profile │───►│ Data Sources │───►│ Template  │ │
│  │  (Custom Rec) │    │ (Search/SQL) │    │ (HTML)    │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
│         │                    │                  │       │
│         ▼                    ▼                  ▼       │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │ Record Type  │    │   record.*   │    │ FreeMarker│ │
│  │ (Customer,   │    │   tran.*     │    │  Engine   │ │
│  │  Transaction)│    │   aging.*    │    │           │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
│                              │                          │
│                              ▼                          │
│                      ┌──────────────┐                   │
│                      │ PDF or HTML  │                   │
│                      │   Output     │                   │
│                      └──────────────┘                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Bundle Dependencies

CRE 2.0 requires these Prolecto bundles:

| Bundle ID | Name | Purpose |
|-----------|------|---------|
| 369503 | Prolecto CRE2 | Core engine (`/.bundle/369503/CRE2/PRI_CRE2_Engine`) |
| 413713 | RIEM | Report/Export integration (optional) |

### Profile Record Type

CRE2 profiles are stored in a custom record type:

```
Custom Record Type: customrecord_cre2_profile
Fields:
  - custrecord_cre2_record_type: Record type (Customer, Transaction, etc.)
  - custrecord_cre2_template: File Cabinet path to HTML template
  - custrecord_cre2_output_type: Output format (PDF, HTML, Email)
  - custrecord_cre2_data_sources: Linked data source definitions
```

---

## Prerequisites

### Required Bundles

1. Navigate to **Customization > SuiteBundler > Search & Install Bundles**
2. Install Prolecto CRE2 bundle (369503)
3. Verify installation: Check for `/.bundle/369503/CRE2/` in File Cabinet

### Required Permissions

- Administrator or CRE2 Administrator role
- Access to Customization > Printing & Branding > CRE2 Profiles
- File Cabinet access for templates

---

## CRE 2.0 Profiles

### Creating a Profile

1. Navigate to **Customization > Printing & Branding > CRE2 Profiles**
2. Click **New**
3. Configure:
   - **Name**: Descriptive name (e.g., "Customer Statement with Discounts")
   - **Record Type**: Base record (Customer, Transaction, etc.)
   - **Template**: File Cabinet path to HTML template
   - **Output Type**: PDF, HTML, or Email

### Profile Configuration Example

```
Profile ID: 15
Name: TXGB: Customer Statement (Draft)
Record Type: Customer
Template: SuiteScripts/CRE2 Credit Letter Template.html
Output Type: PDF
```

### Data Sources

Each profile can have multiple data sources:

| Source Type | Description | Use Case |
|------------|-------------|----------|
| **Saved Search** | Existing NetSuite saved search | Standard reports |
| **SuiteQL** | Direct SQL-like queries | Complex joins, calculations |
| **Record Fields** | Direct record access | Header information |

### Example Data Sources for Customer Statement

| Name | Type | Purpose |
|------|------|---------|
| `customer` | Saved Search | Customer header data |
| `tran` | Saved Search | AR transaction lines |
| `aging` | Saved Search | Aging bucket summaries |
| `discount_lines` | SuiteQL | Discount calculations |

---

## FreeMarker Template Syntax

CRE 2.0 uses FreeMarker for template processing. Key constructs: `${variable}`, `<#if>`, `<#list>`, `<#assign>`, `?has_content`, `?number`, `?string["0.00"]`.

See **[freemarker_syntax.md](references/freemarker_syntax.md)** for full syntax reference with examples.

---

## PDF Template Structure

PDF templates use BFO engine with XML doctype declaration, `<macrolist>` for header/footer macros, inline `<style>`, and `<body>` with `header`, `header-height`, `footer`, `footer-height`, `padding`, and `size` attributes. Use `table-layout: fixed` and `<colgroup>` for item tables.

See **[freemarker_syntax.md](references/freemarker_syntax.md)** and **[bfo_freemarker_gotchas.md](references/bfo_freemarker_gotchas.md)** for full syntax and BFO-specific rules.

---

## Email Template Structure

Email templates use the same BFO XML wrapper but with email-specific patterns: inline CSS, `@media` queries for mobile, and data access via `${customer[0].field}`, `${transaction.field}`, `${preferences.field}`. See **[common_patterns.md](references/common_patterns.md)** for examples.

---

## CRE 2.0 Engine API

Bundle: `/.bundle/369503/CRE2/PRI_CRE2_Engine`. Core pattern:

```javascript
const CRE2 = creEngine.createCRE2Engine(profileId);
CRE2.Load({ recordId: recordId });
CRE2.TranslateAndSendQuietly();  // Render without sending
const fileId = CRE2.getGeneratedFileId();
```

| Method | Description |
|--------|-------------|
| `createCRE2Engine(profileId)` | Create engine instance |
| `CRE2.Load({recordId})` | Load record data |
| `CRE2.TranslateAndSendQuietly()` | Render without sending |
| `CRE2.TranslateAndSend()` | Render and send |
| `CRE2.getGeneratedFileId()` | Get output file ID |
| `CRE2.enableAnonymousAccess({expirationHours, accessLimit})` | Enable GUID-based anonymous access |
| `CRE2.getAnonymousUrl()` | Get anonymous access URL |

---

## Lifecycle Hooks

CRE 2.0 provides lifecycle hooks for custom logic at different render stages:

| Hook | Timing | Use Case |
|------|--------|----------|
| `beforeLoad` | Before data sources execute | Validate record, set parameters |
| `afterLoad` | After data loaded, before template | Transform data, add computed fields |
| `beforeTranslate` | Before FreeMarker processing | Final data adjustments |
| `afterTranslate` | After rendering complete | Post-processing, notifications |

Hooks receive a `context` object with `record`, `data`, `profile`, and `params` properties. See **[js_override_hooks.md](references/js_override_hooks.md)** for full patterns and examples.

---

## Query Linking Strategy

CRE2 queries support FreeMarker variables in WHERE clauses for dynamic linking:

| Pattern | Example | Use Case |
|---------|---------|----------|
| Base record | `WHERE T.Entity = ${record.id}` | Filter by profile's base record |
| Cross-query | `WHERE TL.Transaction = ${parent_tran.id}` | Reference another data source |
| String params | `WHERE Status = '${record.status}'` | Strings need single quotes |
| Numeric params | `WHERE Entity = ${record.id}` | Numbers: no quotes |
| List expansion | `WHERE ID IN (${childIds?join(",")})` | Arrays for IN clauses |
| Null defaults | `WHERE Parent = ${record.parent!0}` | Prevent SQL errors |

See **[cre2_data_sources.md](references/cre2_data_sources.md)** for full data source configuration.

---

## Anonymous Rendering

GUID-based unauthenticated document access. Enable on CRE2 Profile (Allow Anonymous Access, set expiration/access limit). API: `CRE2.enableAnonymousAccess({expirationHours, accessLimit})` → `CRE2.getAnonymousUrl()`. See Engine API table above.

---

## Workflow Integration

CRE2 can be triggered from Workflows (`WorkflowActionScript`) and Scheduled Scripts for automated/batch document generation. Pattern: `creEngine.createCRE2Engine(profileId)` → `CRE2.Load({recordId})` → `CRE2.TranslateAndSend()`.

---

## Background Processing & Queue Management

For >10 recipients or large batch operations, use `PRI_CRE2_QueueManager`:
- `queueManager.createQueue({profileId, batchSize, retryOnFailure, maxRetries})`
- Queue status tracked in `customrecord_pri_cre2_queue`
- `CRE2.bulkSend({recordIds, batchSize, useQueue: true})` for bulk email

---

## Email Template Features

Profile email fields: `custrecord_pri_cre2_email_to/cc/bcc/subject/body/attach/from`. Supports FreeMarker in subject/body, PDF attachments, and multiple file attachments via `CRE2.addAttachment({fileId})`.

---

## Email Profile Configuration

### ⚠️ CRITICAL: Email Body Precedence Rules

CRE2 has **TWO fields** for email body content:

| Field | Purpose | Precedence |
|-------|---------|------------|
| `custrecord_pri_cre2_email_body` | Inline HTML body | **1st (highest)** |
| `custrecord_pri_cre2_gen_file_tmpl_doc` | Template file reference | 2nd (fallback) |

**Rule**: If `custrecord_pri_cre2_email_body` has ANY content, it is used. Template file is ONLY used when inline body is NULL/empty.

This is the #1 source of confusion when working with CRE2 email profiles.

### When to Use Each

| Approach | Use When |
|----------|----------|
| **Inline body only** | Simple emails, no conditional logic |
| **Template file only** | Complex templates, conditional sections, reusability |
| **Both** | **AVOID** - Creates confusion |

### Clearing Inline Body to Use Template File

```bash
python3 update_record.py customrecord_pri_cre2_profile <ID> \
  --field 'custrecord_pri_cre2_email_body=' --env sb2
```

### Email vs PDF Profile Differences

| Aspect | Email Profile | PDF Profile |
|--------|--------------|-------------|
| Output | HTML email sent to recipient | PDF file generated |
| Rendering Engine | Email client (Outlook, Gmail) | BFO PDF engine |
| Body Source | Inline body OR template file | Template file only |
| CSS Support | Limited (inline only) | BFO subset |
| Images | External URLs **required** | Can embed or use URLs |
| Testing | Send test email | `render_pdf.py` script |

### Migration Checklist (Native → CRE2)

When migrating native email templates to CRE2:

1. [ ] **Query existing template** - Don't assume design, examine it first
2. [ ] **Extract branding assets** - Logo IDs, colors, icons
3. [ ] **Map variables to CRE2 syntax** - `${transaction.field}` → `${datasource.rows[0].field}`
4. [ ] **Preserve design philosophy** - Don't add complexity native doesn't have
5. [ ] **Leave inline body empty** - Use template file for complex templates
6. [ ] **Test with/without conditions** - If using conditional sections

See **[email_profiles.md](references/email_profiles.md)** for full documentation including FreeMarker syntax differences and common issues.

See **[migration_workflow.md](references/migration_workflow.md)** for step-by-step migration process.

See **[branding_assets.md](references/branding_assets.md)** for Twisted X logo IDs and colors by context.

---

## SuiteQL Data Sources

Add SuiteQL data sources to CRE2 profiles: type **SuiteQL**, name becomes the FreeMarker variable, use `${record.id}` for dynamic filtering. Access results via `datasource.rows`.

Key limitations: `discountamount`, `discountdate`, `foreignamountremaining`, `total` not directly available — must be calculated from Term/TransactionAccountingLine tables.

See **[cre2_data_sources.md](references/cre2_data_sources.md)** for full examples including discount queries and SuiteQL field workarounds.

---

## Common Template Patterns

Common patterns: running balance calculation, aging bucket accumulators, customer group breaks, conditional styling, debug mode toggle.

See **[common_patterns.md](references/common_patterns.md)** for full examples.

---

## Testing and Debugging

**NetSuite UI**: Customization > Printing & Branding > CRE2 Profiles > Open profile > Test/Preview.

**Debug data**: Add `<#if debug_on == 1><pre>${record?keys?join(", ")}</pre></#if>` before `</body>`.

**SuiteQL testing**: `python3 $SQL_SCRIPTS/query_netsuite.py "<query>" --env sb2 --format table`

**EDI PDF testing**: `python3 $CRE2_SCRIPTS/render_pdf.py --profile-id <ID> --record-id <ID> --env sb2 --open-browser`

| Error | Fix |
|-------|-----|
| `${var}` blank | Check data source query |
| `?number` fails | Add `?has_content` check |
| Empty iteration | Verify query returns data, use `datasource.rows` |
| PDF render fails | Check unclosed XML/HTML tags |

---

## Common Pitfalls and Troubleshooting

Critical pitfalls that cause silent failures in CRE2 templates:

| # | Pitfall | Quick Fix |
|---|---------|-----------|
| 1 | `{record.id}` missing `$` in SuiteQL | Use `${record.id}` |
| 2 | `T.Status = 'A'` returns 0 rows | Use `T.Status <> 'B'` |
| 3 | Iterating on data source directly | Use `datasource.rows` |
| 4 | Row objects don't serialize in FreeMarker hashes | Store explicit field values |
| 5 | Conditionals fail on lookup map values | Use direct output with `!default` |
| 6 | `<tr>` before `<thead>` | Proper thead/tbody/tr ordering |
| 7 | Debug output in middle of doc | Place before `</body>` |
| 8 | `!=` in SuiteQL | Use `<>` |
| 9 | Entity ID ≠ Internal ID | Use `${record.id}` for internal ID |
| 10 | Hardcoded AR account IDs | Verify per environment |
| 11 | Query record misconfigured | `querytype=1`, `parent=profile ID` |
| 12 | Nested subqueries timeout | Simplify or use separate data source |
| 13 | Currency/date formatting | `?number?string["0.00"]`, `white-space: nowrap` |

**BFO-specific pitfalls** (empty strings, `?trim` on numeric strings, CSS limitations, numeric zero guards):
See **[bfo_freemarker_gotchas.md](references/bfo_freemarker_gotchas.md)** for full details with code examples.

### Quick Troubleshooting Checklist

1. Check FreeMarker syntax: `${variable}` not `{variable}`
2. Verify data source returns data (add row count debug)
3. Access `datasource.rows` not just `datasource`
4. Store explicit field values in lookup maps
5. Use direct output with `!default` for lookup values
6. Validate table structure (thead/tbody order)
7. Debug output goes before `</body>`
8. Test SuiteQL separately via `query_netsuite.py`
9. Verify customer internal ID (not entity ID)

---

## File Organization

### Template Location

Templates stored in File Cabinet:
- `/SuiteScripts/Prolecto/CRE/` - Standard CRE templates
- `/SuiteScripts/` - Custom templates (e.g., `CRE2 Credit Letter Template.html`)

### Naming Conventions

| Pattern | Example | Description |
|---------|---------|-------------|
| `CRE2_<type>_<purpose>.html` | `CRE2_Customer_Statement.html` | PDF templates |
| `<record>_<action>.html` | `item_fulfillment.html` | Email templates |

---

## Existing CRE2 Profiles (Twisted X)

| Profile ID | Name | Record Type | Purpose |
|------------|------|-------------|---------|
| 15 | TXGB: Customer Statement (Landscape) | Customer | Customer statement PDF (11" x 8.5") - Digital/Email |
| 16 | TXGB: Customer Statement (Portrait) | Customer | Customer statement PDF (8.5" x 11") - Print/Mail |

### Existing Saved Searches

| Search ID | Name | Purpose |
|-----------|------|---------|
| `customsearch_cre_cust_stmt_head` | CRE Customer Header | Customer header data |
| `customsearch_cre_cust_stmt_ar_line` | CRE AR Lines | AR transaction lines |
| `customsearch_cre_cust_stmt_aging` | CRE Aging | Aging bucket summaries |

---

## EDI Consolidated Template Architecture

### Overview

EDI PDF templates were consolidated from ~80 partner-specific templates to **1 template per document type** (~14 total). Partner-specific differences (logo DPI) are now data-driven.

### How It Works

1. **Data Extractor** (`twx_CRE2_EDI_DataExtractor.js`, file ID 52794157) populates `tpLogoDpi` based on a hardcoded map:

```javascript
var TP_LOGO_DPI_MAP = {
    'Runnings': '200',     // Small source image
    'Buchheit': '200',
    'Academy': '800',      // Medium source image
    'Bomgaars': '800',
    // ... others at 800
};
var DEFAULT_LOGO_DPI = '2000';  // Large source images (most partners)

ediResult.tpLogoDpi = TP_LOGO_DPI_MAP[tpName] || DEFAULT_LOGO_DPI;
```

2. **Templates** use data-driven DPI on the trading partner logo:

```freemarker
<img src="${OVERRIDE.EDI.tradingPartnerLogo}" dpi="${OVERRIDE.EDI.tpLogoDpi!'2000'}" />
```

3. **CRE2 Profiles** all point to the consolidated generic template file ID per doc type.

### Consolidated Template File IDs (sb2)

| Doc Type | Template File Name | File ID |
|----------|-------------------|---------|
| 810 | TWX_EDI_810_PDF.html | 52794158 |
| 850 | TWX_EDI_850_PDF.html | 52794159 |
| 855 | TWX_EDI_855_PDF.html | 52794160 |
| 856 | TWX_EDI_856_PDF.html | 52794161 |
| 860 | TWX_EDI_860_PDF.html | 52794162 |
| 820 | TWX_EDI_820_PDF.html | 52800858 |
| 824 | TWX_EDI_824_PDF.html | 52800859 |
| 846 | TWX_EDI_846_PDF.html | 52800958 |

### Gold Standard Pattern

All consolidated templates follow this pattern (derived from the Runnings 850 template):

- **Header**: Pure `<table>` with 3 columns: Twisted X logo (`dpi="400"`) | Document title + TP name | TP logo (`dpi="${OVERRIDE.EDI.tpLogoDpi!'2000'}"`)
- **Body**: `header-height="75px"`, `padding="0.5in"`, `size="Letter"`
- **Layout**: Pure `<table>` elements (no `<div>` wrappers)
- **Color scheme**: `#1B4F72` accent, `#2C3E50` headings
- **Guards**: `?? && ?has_content` for strings, `> 0` for numeric fields
- **Variables**: `tpDisplayName` (not `partner_name`)
- **Date fields**: `deliveryRequestedDate` and `cancelAfterDate` in summary (850/855/856/860)

### Adding a New Trading Partner

No template changes needed. If the partner's logo needs non-default DPI:

1. Add entry to `TP_LOGO_DPI_MAP` in the data extractor
2. Upload data extractor with `--file-id 52794157`
3. The consolidated template automatically picks up the new DPI

---

## Scripts Reference

Key scripts (all under CRE2 scripts dir). See **[cli_reference.md](references/cli_reference.md)** for complete flags and workflows.

| Script | Purpose | Example |
|--------|---------|---------|
| `cre2_profile.py` | List/get/test profiles | `list --env sb1` |
| `validate_template.py` | Check FreeMarker syntax | `--extract-vars template.html` |
| `render_pdf.py` | Render PDF for record | `--profile-id 16 --record-id 9425522 --env sb2` |
| `find_test_records.py` | Find test records by TP/doc | `--tp-id 22 --doc-type 850` |
| `render_test_matrix.py` | Batch render across TPs | `--doc-type 850 --env sb2 --open-browser` |

---

## Best Practices

### BFO PDF Template Checklist

Before uploading any PDF template, verify:

1. [ ] Empty string properties `delete`d in JS extractor
2. [ ] No `?trim` in conditional guards
3. [ ] No CSS `max-width`/`max-height` on `<img>` (use `dpi` only)
4. [ ] Pure `<table>` layout (no `<div>` wrappers)
5. [ ] No `display: table/table-cell/flex/grid` CSS
6. [ ] `header-height="75px"` for dual-logo headers
7. [ ] Numeric guards use `> 0` (not just `??`)
8. [ ] `<colgroup>` with `table-layout: fixed` for multi-column tables
9. [ ] Test with sparse, rich, and small-logo partners

See **[bfo_freemarker_gotchas.md](references/bfo_freemarker_gotchas.md)** for full details.

### General

- Start simple, add complexity incrementally
- Verify data sources return data before template work
- Use SuiteQL for joins, saved searches for standard queries
- Use `${record.id}` for dynamic filtering (not entity ID)
- Version templates, document data sources, backup before changes

---

## Reference Files

For detailed information on specific topics, see:

### Email Profiles (NEW)
- **[email_profiles.md](references/email_profiles.md)** - Email body precedence rules, native-to-CRE2 variable mapping, conditional sections, CSS limitations. **Read this before creating email profiles.**
- **[migration_workflow.md](references/migration_workflow.md)** - Step-by-step process for migrating native NetSuite email templates to CRE2. **Read this before rebuilding existing email templates.**
- **[branding_assets.md](references/branding_assets.md)** - Twisted X logo IDs, social icons, colors by context (email vs PDF vs EDI). **Reference this for correct branding assets.**

### Core References
- **[cli_reference.md](references/cli_reference.md)** - Complete CLI reference for all CRE2, SuiteQL, and File Cabinet scripts with exact flags, argument order, and common workflows
- **[edi_json_structures.md](references/edi_json_structures.md)** - Actual JSON structures for each EDI document type (850, 810, 855, 856, 824, 860, 852, 864). **Read this before writing extraction code.**
- **[upload_safety.md](references/upload_safety.md)** - Pre-upload checklist, duplicate prevention, and troubleshooting when changes don't appear. **Read this before uploading files.**
- **[bfo_freemarker_gotchas.md](references/bfo_freemarker_gotchas.md)** - BFO PDF engine quirks: empty string handling, `?trim` failures on numeric strings, the Delete Pattern, layout rules, image DPI. **Read this before writing or debugging PDF templates.**
- **[common_patterns.md](references/common_patterns.md)** - Common FreeMarker template patterns
- **[cre2_data_sources.md](references/cre2_data_sources.md)** - Data source configuration
- **[freemarker_syntax.md](references/freemarker_syntax.md)** - FreeMarker syntax reference
- **[js_override_hooks.md](references/js_override_hooks.md)** - JavaScript override hook patterns

### ⚠️ Critical: File Upload Rules

**Data Extractor:** Always use `--file-id 52794157` (NEVER `--folder-id`).
**Templates:** Use `--file-id <ID>` for existing, `--folder-id 1285029` for new.
See [upload_safety.md](references/upload_safety.md) and the `CRE2_NetSuite_Folders` Serena memory.

## Related Skills

- **netsuite-suiteql**: SuiteQL query development and testing
- **netsuite-file-cabinet**: File Cabinet operations for templates
- **netsuite-sdf-deployment**: Deploy CRE2 profiles via SDF

---

*Last updated: 2026-01-30*
*Skill version: 1.5.0*
