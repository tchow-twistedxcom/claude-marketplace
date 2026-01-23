# NetSuite CRE 2.0 (Content Renderer Engine) Skill

skill_name: netsuite-cre2
version: 1.2.0
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

CRE 2.0 uses FreeMarker for template processing.

### Variable Interpolation

```freemarker
${variable}                          <!-- Simple variable -->
${record.companyname}                <!-- Record field -->
${customer.rows[0].salesrep}         <!-- Saved search result -->
${tran.openbalance?number}           <!-- Type conversion -->
```

### Conditionals

```freemarker
<#if condition>
    content when true
<#elseif other_condition>
    alternate content
<#else>
    default content
</#if>

<!-- Examples -->
<#if tran.openbalance?has_content>
    ${tran.openbalance}
</#if>

<#if (tran.daystodiscount > 0)>
    <span style="color: green;">${tran.daystodiscount} days</span>
<#elseif (tran.daystodiscount == 0)>
    <span style="color: orange;">Today</span>
<#else>
    <span style="color: #999;">Expired</span>
</#if>
```

### List Iteration

```freemarker
<#list collection as item>
    ${item.field}
</#list>

<!-- Example: Transaction lines -->
<#list tran.rows as tran>
    <tr>
        <td>${tran.tranid}</td>
        <td>${tran.amount}</td>
        <td>${tran.openbalance}</td>
    </tr>
</#list>

<!-- Example: Item fulfillment lines -->
<#list itemfulfillment.item as itemline>
    <tr>
        <td>${itemline.item}</td>
        <td>${itemline.description}</td>
        <td>${itemline.quantity}</td>
    </tr>
</#list>
```

### Variable Assignment

```freemarker
<#assign variable_name = value>

<!-- Examples -->
<#assign debug_on = 0>
<#assign currency_symbol = "$">
<#assign running_balance = 0.00>
<#assign company_addr1 = "269 South Beverly Drive">

<!-- Calculations -->
<#assign running_balance = running_balance + tran.openbalance?number>
<#assign band_aging_current_total = band_aging_current_total + tran.current?number>
```

### Built-in Functions

```freemarker
<!-- Content checks -->
${value?has_content}                 <!-- True if not null/empty -->
${value?string}                      <!-- Convert to string -->
${value?number}                      <!-- Convert to number -->

<!-- String operations -->
${value?replace('old', 'new')}       <!-- Replace text -->
${value?upper_case}                  <!-- Uppercase -->
${value?lower_case}                  <!-- Lowercase -->
${value?trim}                        <!-- Trim whitespace -->

<!-- Date/Time -->
<#assign aDateTime = .now>           <!-- Current datetime -->
<#assign aDate = aDateTime?date>     <!-- Extract date -->
${aDate?string.medium}               <!-- Format: Jan 19, 2026 -->
${aDate?string("MM/dd/yyyy")}        <!-- Custom format -->

<!-- Number formatting -->
${value?string["0.00"]}              <!-- Two decimal places -->
${value?string.currency}             <!-- Currency format -->
```

### Macros (Reusable Components)

```freemarker
<macrolist>
    <macro id="nlheader">
        <!-- Header content -->
    </macro>

    <macro id="nlfooter">
        <table class="footer">
            <tr>
                <td>Page <pagenumber/> of <totalpages/></td>
            </tr>
        </table>
    </macro>
</macrolist>

<!-- Use in body -->
<body header="nlheader" header-height="21%"
      footer="nlfooter" footer-height="5%">
```

---

## PDF Template Structure

### Document Type Declaration

```xml
<?xml version="1.0"?>
<!DOCTYPE pdf PUBLIC "-//big.faceless.org//report" "report-1.1.dtd">
<pdf>
<head>
    <macrolist>
        <!-- Macros here -->
    </macrolist>
    <style type="text/css">
        /* CSS styles */
    </style>
</head>
<body header="header_macro" header-height="20%"
      footer="footer_macro" footer-height="5%"
      padding="0.25in 0.15in" size="Letter-landscape">
    <!-- Content -->
</body>
</pdf>
```

### Common CSS Classes

```css
table.itemtable {
    font-family: sans-serif;
    font-size: 9pt;
    table-layout: fixed;
    width: 100%;
}

table.itemtable th {
    font-weight: bold;
    background-color: #3c96d8;
    color: #ffffff;
    padding: 5px;
}

table.itemtable td {
    vertical-align: top;
    padding: 3px;
    border-bottom: 0.5px solid #aad2ee;
}
```

### Page Configuration

| Attribute | Values | Description |
|-----------|--------|-------------|
| `size` | Letter, Letter-landscape, A4, A4-landscape | Page size |
| `header-height` | Percentage or measurement | Header space |
| `footer-height` | Percentage or measurement | Footer space |
| `padding` | CSS padding values | Page margins |

---

## Email Template Structure

### HTML Email Template

```html
<?xml version="1.0"?>
<!DOCTYPE pdf PUBLIC "-//big.faceless.org//report" "report-1.1.dtd">
<pdf>
<head>
    <style type="text/css">
        @media screen and (max-width: 480px) {
            .mobile-hide { display: none !important; }
            .mobile-center { text-align: center !important; }
        }
    </style>
</head>
<body style="background-color: #eeeeee; margin: 0; padding: 0;">
    <!-- Email content -->
</body>
</pdf>
```

### Data Access in Emails

```freemarker
<!-- Customer info -->
<#if customer[0].isperson>
    ${customer[0].firstname} ${customer[0].lastname}
<#else>
    ${customer[0].companyname}
</#if>

<!-- Transaction data -->
${itemfulfillment.tranid}
${itemfulfillment.shipAddress}
${itemfulfillment.shipMethod}

<!-- Related records -->
${salesorder[0].trackingnumbers}
${salesorder[0].trackingLink}

<!-- Preferences -->
${preferences.naming_customer}
```

---

## CRE 2.0 Engine API

### JavaScript API Usage

```javascript
/**
 * @NApiVersion 2.1
 * @NModuleScope SameAccount
 */
define(['/.bundle/369503/CRE2/PRI_CRE2_Engine'], (creEngine) => {

    function renderDocument(profileId, recordId, outputFolder) {
        // Create CRE2 engine instance
        const CRE2 = creEngine.createCRE2Engine(profileId);

        // Load record data
        CRE2.Load({ recordId: recordId });

        // Optional: Set output folder
        if (outputFolder) {
            CRE2.fileFolder.originalValue = outputFolder;
        }

        // Render and save quietly (no email)
        CRE2.TranslateAndSendQuietly();

        return CRE2.getGeneratedFileId();
    }

    return { renderDocument };
});
```

### API Methods

| Method | Description |
|--------|-------------|
| `createCRE2Engine(profileId)` | Create engine instance for profile |
| `CRE2.Load({recordId})` | Load record data into engine |
| `CRE2.TranslateAndSendQuietly()` | Render document without sending |
| `CRE2.TranslateAndSend()` | Render and send via configured delivery |
| `CRE2.getGeneratedFileId()` | Get File Cabinet ID of output |

### Engine Properties

```javascript
// File output location
CRE2.fileFolder.originalValue = '/SuiteScripts/Output/';

// Access rendered content
const pdfContent = CRE2.getRenderedContent();
const fileId = CRE2.getGeneratedFileId();
```

---

## Lifecycle Hooks

CRE 2.0 provides lifecycle hooks that allow custom logic at different stages of document generation. These are configured on the CRE2 Profile record.

### Hook Types

| Hook | Timing | Use Case |
|------|--------|----------|
| `beforeLoad` | Before data sources execute | Validate record, set parameters |
| `afterLoad` | After data loaded, before template | Transform data, add computed fields |
| `beforeTranslate` | Before FreeMarker processing | Final data adjustments |
| `afterTranslate` | After rendering complete | Post-processing, notifications |

### Configuring Hooks

Hooks are configured on the CRE2 Profile record using script references:

```javascript
// Example: afterLoad hook to add computed fields
/**
 * @NApiVersion 2.1
 * @NModuleScope SameAccount
 */
define(['N/log'], (log) => {

    function afterLoad(context) {
        // context.data contains loaded data sources
        // context.record contains the base record

        // Add computed field
        if (context.data.tran && context.data.tran.rows) {
            let totalAmount = 0;
            context.data.tran.rows.forEach(row => {
                totalAmount += parseFloat(row.amount || 0);
            });
            context.data.computedTotal = totalAmount;
        }

        return context;
    }

    return { afterLoad };
});
```

### Hook Context Object

```javascript
{
    record: {          // Base record being rendered
        id: 12345,
        type: 'customer',
        // ... record fields
    },
    data: {            // Loaded data sources
        tran: { rows: [...] },
        aging: { rows: [...] },
        // ... other data sources
    },
    profile: {         // CRE2 profile settings
        id: 15,
        outputType: 'pdf',
        // ...
    },
    params: {}         // Custom parameters passed to engine
}
```

### Common Hook Patterns

**beforeLoad - Validation**
```javascript
function beforeLoad(context) {
    // Validate record before processing
    if (!context.record.email) {
        throw new Error('Customer has no email address');
    }
    return context;
}
```

**afterLoad - Data Transformation**
```javascript
function afterLoad(context) {
    // Add discount eligibility flag to each transaction
    context.data.tran.rows.forEach(row => {
        row.discountEligible = row.daystodiscount > 0;
    });
    return context;
}
```

**afterTranslate - Notification**
```javascript
function afterTranslate(context) {
    // Log successful generation
    log.audit('PDF Generated', {
        recordId: context.record.id,
        fileId: context.generatedFileId
    });
    return context;
}
```

---

## Query Linking Strategy

CRE2 supports linking queries to reference data from parent or related queries using FreeMarker syntax in WHERE clauses.

### Linking to Base Record

Use `${record.id}` to filter by the base record:

```sql
-- In a Customer-based profile, filter transactions by customer
SELECT T.ID, T.TranID, T.Amount
FROM Transaction T
WHERE T.Entity = ${record.id}
  AND T.Type = 'CustInvc'
```

### Cross-Query Linking

Reference values from other data sources in WHERE clauses:

```sql
-- Link to a parent query's results
SELECT TL.ID, TL.Item, TL.Quantity
FROM TransactionLine TL
WHERE TL.Transaction = ${parent_tran.id}
```

### Dynamic Parameter Substitution

FreeMarker variables are evaluated before query execution:

```sql
-- Use computed values from hooks
SELECT * FROM Transaction
WHERE TranDate >= '${params.startDate}'
  AND TranDate <= '${params.endDate}'
```

### Query Linking Rules

1. **Single Quotes for Strings**: Wrap FreeMarker string variables in single quotes
   ```sql
   WHERE Status = '${record.status}'
   ```

2. **No Quotes for Numbers**: Numeric values don't need quotes
   ```sql
   WHERE Entity = ${record.id}
   ```

3. **List Expansion**: For IN clauses with arrays
   ```sql
   WHERE ID IN (${childIds?join(",")})
   ```

4. **Default Values**: Handle nulls to prevent SQL errors
   ```sql
   WHERE Parent = ${record.parent!0}
   ```

---

## Anonymous Rendering

CRE2 supports anonymous (unauthenticated) document rendering using GUID-based security. This enables external access to generated documents without requiring NetSuite login.

### How It Works

1. **GUID Generation**: When enabled, CRE2 generates a unique GUID for each document
2. **Secure URL**: A URL with the GUID provides one-time or time-limited access
3. **No Authentication**: External users can access the document via the GUID URL

### Enabling Anonymous Rendering

On the CRE2 Profile:
1. Enable **Allow Anonymous Access**
2. Set **GUID Expiration** (optional, in hours)
3. Configure **Access Limit** (optional, number of times)

### API Usage

```javascript
// Render with anonymous access
const CRE2 = creEngine.createCRE2Engine(profileId);
CRE2.Load({ recordId: recordId });

// Enable anonymous mode
CRE2.enableAnonymousAccess({
    expirationHours: 24,    // Link expires after 24 hours
    accessLimit: 5          // Allow 5 downloads
});

CRE2.TranslateAndSendQuietly();

// Get the anonymous access URL
const anonymousUrl = CRE2.getAnonymousUrl();
log.debug('Anonymous URL', anonymousUrl);
```

### Security Considerations

- GUIDs should be sufficiently random (CRE2 handles this)
- Set appropriate expiration times for sensitive documents
- Use access limits for single-use documents
- Audit anonymous access for compliance

---

## Workflow Integration

CRE2 can be triggered from NetSuite Workflows and Action scripts for automated document generation.

### Workflow Action Script

```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType WorkflowActionScript
 */
define(['/.bundle/369503/CRE2/PRI_CRE2_Engine', 'N/log'], (creEngine, log) => {

    function onAction(context) {
        const record = context.newRecord;
        const profileId = 15;  // Your CRE2 profile ID

        try {
            const CRE2 = creEngine.createCRE2Engine(profileId);
            CRE2.Load({ recordId: record.id });
            CRE2.TranslateAndSend();  // Generate and send via profile settings

            log.audit('Document Generated', {
                recordId: record.id,
                recordType: record.type
            });

            return 'success';
        } catch (e) {
            log.error('CRE2 Generation Failed', e.message);
            return 'error';
        }
    }

    return { onAction };
});
```

### Workflow Configuration

1. Create **Custom Action** pointing to the Workflow Action Script
2. Add to Workflow at desired state transition
3. Configure trigger conditions (e.g., on Approval, on Fulfillment)

### Scheduled Script Integration

For batch document generation:

```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType ScheduledScript
 */
define(['/.bundle/369503/CRE2/PRI_CRE2_Engine', 'N/search', 'N/log'],
    (creEngine, search, log) => {

    function execute(context) {
        const profileId = 15;

        // Find records needing documents
        const results = search.create({
            type: 'customer',
            filters: [
                ['custentity_statement_pending', 'is', 'T']
            ],
            columns: ['internalid']
        }).run().getRange({ start: 0, end: 100 });

        results.forEach(result => {
            try {
                const CRE2 = creEngine.createCRE2Engine(profileId);
                CRE2.Load({ recordId: result.id });
                CRE2.TranslateAndSendQuietly();
            } catch (e) {
                log.error('Failed for ' + result.id, e.message);
            }
        });
    }

    return { execute };
});
```

---

## Background Processing & Queue Management

For large batch operations or when generating documents for many recipients, CRE2 supports background processing with queue management.

### When to Use Queue Management

- **>10 Recipients**: Bulk email operations
- **Large Documents**: Complex PDFs that take time to render
- **Rate Limiting**: When hitting NetSuite governance limits
- **Reliability**: When failures shouldn't stop the batch

### Queue Manager API

```javascript
/**
 * @NApiVersion 2.1
 * @NModuleScope SameAccount
 */
define(['/.bundle/369503/CRE2/PRI_CRE2_QueueManager', 'N/log'],
    (queueManager, log) => {

    function queueDocuments(recordIds, profileId) {
        // Create queue for bulk processing
        const queue = queueManager.createQueue({
            profileId: profileId,
            batchSize: 10,              // Process 10 at a time
            retryOnFailure: true,       // Auto-retry failures
            maxRetries: 3,
            notifyOnComplete: true      // Send summary when done
        });

        // Add records to queue
        recordIds.forEach(id => {
            queue.add({ recordId: id });
        });

        // Start background processing
        const queueId = queue.submit();

        log.audit('Queue Submitted', {
            queueId: queueId,
            recordCount: recordIds.length
        });

        return queueId;
    }

    function checkQueueStatus(queueId) {
        const status = queueManager.getStatus(queueId);
        return {
            total: status.totalRecords,
            completed: status.completedRecords,
            failed: status.failedRecords,
            pending: status.pendingRecords,
            isComplete: status.isComplete
        };
    }

    return { queueDocuments, checkQueueStatus };
});
```

### Queue Status Tracking

Queues create records in `customrecord_pri_cre2_queue` for tracking:

| Field | Description |
|-------|-------------|
| `custrecord_pri_cre2q_status` | Pending, Processing, Complete, Failed |
| `custrecord_pri_cre2q_total` | Total records in queue |
| `custrecord_pri_cre2q_completed` | Successfully processed count |
| `custrecord_pri_cre2q_failed` | Failed record count |
| `custrecord_pri_cre2q_errors` | Error details for failed records |

### Bulk Emailer Logic

When sending to >10 recipients, CRE2 automatically uses queue management:

```javascript
// Automatic queue management for bulk email
const CRE2 = creEngine.createCRE2Engine(profileId);

// When sending to multiple recipients
CRE2.bulkSend({
    recordIds: customerIds,     // Array of record IDs
    batchSize: 50,             // Optional: override default batch size
    useQueue: true             // Force queue even for < 10 recipients
});
```

---

## Email Template Features

### File Attachments

CRE2 supports attaching the generated PDF to emails using the `{fileAttachment}` placeholder:

```html
<!-- In email template -->
<p>Please find your statement attached.</p>

<!-- The {fileAttachment} placeholder tells CRE2 to attach the PDF -->
<!-- It's configured on the profile, not in the template HTML -->
```

### Profile Email Configuration

| Field | Description |
|-------|-------------|
| `custrecord_pri_cre2_email_to` | Recipient field (e.g., `${record.email}`) |
| `custrecord_pri_cre2_email_cc` | CC recipients |
| `custrecord_pri_cre2_email_bcc` | BCC recipients |
| `custrecord_pri_cre2_email_subject` | Email subject with FreeMarker |
| `custrecord_pri_cre2_email_body` | Email body template |
| `custrecord_pri_cre2_email_attach` | Attach generated PDF (checkbox) |
| `custrecord_pri_cre2_email_from` | Sender email/employee ID |

### Dynamic Email Subject

```freemarker
<!-- Email subject template -->
Statement for ${record.companyname} - ${.now?string["MMMM yyyy"]}

<!-- Result: "Statement for Acme Corp - January 2026" -->
```

### Email Body with Personalization

```freemarker
<!-- Email body template -->
Dear ${record.companyname},

Please find your account statement attached for the period ending ${.now?string["MM/dd/yyyy"]}.

Your current balance is: ${currency_symbol}${total_balance?string["0.00"]}

<#if aging_over90 gt 0>
IMPORTANT: You have ${currency_symbol}${aging_over90?string["0.00"]} past due over 90 days.
Please contact us to discuss payment arrangements.
</#if>

Thank you for your business.

Best regards,
Accounts Receivable
```

### Multiple Attachments

For templates that need multiple file attachments:

```javascript
// Attach additional files programmatically
const CRE2 = creEngine.createCRE2Engine(profileId);
CRE2.Load({ recordId: recordId });

// Add extra attachments
CRE2.addAttachment({ fileId: termsFileId });    // Terms & Conditions
CRE2.addAttachment({ fileId: catalogFileId });  // Product catalog

CRE2.TranslateAndSend();
```

---

## SuiteQL Data Sources

### Adding SuiteQL to Profile

1. Open CRE2 Profile
2. Add new Data Source
3. Select Type: **SuiteQL**
4. Name the data source (e.g., `discount_lines`)
5. Enter query with `{record.id}` placeholder

### Example: Discount Information Query

```sql
SELECT
    T.ID,
    T.TranID AS DocNo,
    T.TranDate AS InvoiceDate,
    T.DueDate,
    (SELECT SUM(TAL.Debit)
     FROM TransactionAccountingLine TAL
     WHERE TAL.Transaction = T.ID) AS OriginalAmount,
    BUILTIN.DF(T.Terms) AS Terms,
    Trm.DiscountPercent,
    T.TranDate + Trm.DaysUntilExpiry AS DiscountDate,
    TRUNC(T.TranDate + Trm.DaysUntilExpiry) - TRUNC(SYSDATE) AS DaysToDiscount,
    CASE
        WHEN Trm.DiscountPercent IS NOT NULL
        THEN ROUND(
            (SELECT SUM(TAL.Debit)
             FROM TransactionAccountingLine TAL
             WHERE TAL.Transaction = T.ID) * Trm.DiscountPercent / 100, 2)
        ELSE NULL
    END AS DiscountAmount
FROM Transaction T
LEFT JOIN Term Trm ON T.Terms = Trm.ID
WHERE T.Type = 'CustInvc'
  AND T.Entity = {record.id}
ORDER BY T.TranDate DESC
```

### SuiteQL Variables in Templates

```freemarker
<!-- Access SuiteQL results -->
<#if discount_lines?has_content>
    <#list discount_lines.rows as disc>
        <tr>
            <td>${disc.docno}</td>
            <td>${disc.terms}</td>
            <td>${disc.discountpercent}%</td>
            <td>${disc.discountamount}</td>
            <td>
                <#if (disc.daystodiscount > 0)>
                    ${disc.daystodiscount} days
                <#else>
                    Expired
                </#if>
            </td>
        </tr>
    </#list>
</#if>
```

### SuiteQL Field Limitations

Some fields are NOT exposed in SuiteQL:

| Field | Status | Workaround |
|-------|--------|------------|
| `discountamount` | ❌ Not available | Calculate from Term table |
| `discountdate` | ❌ Not available | `TranDate + Term.DaysUntilExpiry` |
| `foreignamountremaining` | ❌ Not available | Use TransactionAccountingLine |
| `total` | ❌ Not available | `SUM(TAL.Debit)` |

---

## Common Template Patterns

### Running Balance Calculation

```freemarker
<#assign running_balance = 0.00>

<#list tran.rows as tran>
    <#if tran.openbalance?has_content>
        <#assign running_balance = running_balance + tran.openbalance?number>
    </#if>
    <tr>
        <td>${tran.tranid}</td>
        <td>${tran.amount}</td>
        <td>${currency_symbol}${running_balance}</td>
    </tr>
</#list>
```

### Aging Bucket Accumulators

```freemarker
<#assign band_aging_current_total = 0.00>
<#assign band_aging_1_30_total = 0.00>
<#assign band_aging_31_60_total = 0.00>
<#assign band_aging_61_90_total = 0.00>
<#assign band_aging_over90_total = 0.00>

<#list tran.rows as tran>
    <#assign band_aging_current_total = band_aging_current_total + tran.current?number>
    <#assign band_aging_1_30_total = band_aging_1_30_total + tran.due130?number>
    <#assign band_aging_31_60_total = band_aging_31_60_total + tran.due3160?number>
    <#assign band_aging_61_90_total = band_aging_61_90_total + tran.due6190?number>
    <#assign band_aging_over90_total = band_aging_over90_total + tran.due91plus?number>
</#list>
```

### Customer Group Breaks

```freemarker
<#assign current_customer_id = "">
<#assign previous_customer_id = "">
<#assign first_time_through = 1>

<#list tran.rows as tran>
    <#assign current_customer_id = tran.custname?string>

    <#if first_time_through == 1>
        <#assign previous_customer_id = current_customer_id>
    </#if>

    <#if current_customer_id != previous_customer_id>
        <!-- Display subtotal for previous customer -->
        <tr class="subtotal">
            <td colspan="5">Subtotal for ${previous_customer_id}</td>
            <td>${currency_symbol}${customer_total}</td>
        </tr>

        <!-- Reset accumulators -->
        <#assign customer_total = 0.00>
    </#if>

    <!-- Process current row -->
    <tr>
        <td>${tran.tranid}</td>
        <td>${tran.amount}</td>
    </tr>

    <#assign previous_customer_id = current_customer_id>
    <#assign first_time_through = 0>
</#list>
```

### Conditional Styling

```freemarker
<td colspan="4" align="center">
    <#if tran.daystodiscount?has_content>
        <#if (tran.daystodiscount > 0)>
            <p style="text-align: center; color: green;">${tran.daystodiscount} days</p>
        <#elseif (tran.daystodiscount == 0)>
            <p style="text-align: center; color: orange;">Today</p>
        <#else>
            <p style="text-align: center; color: #999;">Expired</p>
        </#if>
    <#else>
        <p style="text-align: center;">-</p>
    </#if>
</td>
```

### Debug Mode Toggle

```freemarker
<#assign debug_on = 0>

<#if debug_on == 1>
    <td colspan="3" style="background-color: #ffe6e6;">
        <p>Debug: ${tran.internalid}</p>
    </td>
</#if>
```

---

## Testing and Debugging

### Test in NetSuite UI

1. Navigate to **Customization > Printing & Branding > CRE2 Profiles**
2. Open your profile
3. Click **Test** or **Preview**
4. Select a test record
5. View rendered output

### Debug Data Sources

Add debug output to see available data:

```freemarker
<#if debug_on == 1>
    <h3>Available Data Sources</h3>
    <pre>
    record: ${record?keys?join(", ")}
    customer: ${customer?has_content?string("yes", "no")}
    tran: ${tran?has_content?string("yes", "no")} (${tran.rows?size} rows)
    </pre>
</#if>
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `${variable}` shows blank | Variable not in data source | Check data source query |
| `?number` fails | Value is null/empty | Add `?has_content` check first |
| List iteration empty | No rows returned | Verify query returns data |
| PDF rendering fails | Invalid XML/HTML | Check for unclosed tags |

### SuiteQL Query Testing

Test queries before adding to profile:

```bash
cd ~/.claude/plugins/marketplaces/tchow-essentials/plugins/netsuite-skills/skills/netsuite-suiteql
python3 scripts/query_netsuite.py "<query>" --env sb1 --format table
```

---

## Common Pitfalls and Troubleshooting

Critical lessons learned from production debugging. These issues often produce cryptic errors or silent failures.

### 1. FreeMarker Parameter Syntax in SuiteQL

**Problem**: Using `{record.id}` instead of `${record.id}` in SuiteQL data source queries.

```sql
-- WRONG: Causes SQL parse error
WHERE T.Entity = {record.id}

-- CORRECT: Proper FreeMarker interpolation
WHERE T.Entity = ${record.id}
```

**Symptom**: SQL parse error, data source returns no results, or template fails to render.

### 2. SuiteQL Status Filter Quirk

**Problem**: Filtering by `T.Status = 'A'` (Open/Approved) returns 0 rows even when matching records exist.

```sql
-- WRONG: Returns 0 rows unexpectedly
WHERE T.Type = 'CustInvc' AND T.Status = 'A'

-- CORRECT: Use negative filter or remove entirely
WHERE T.Type = 'CustInvc' AND T.Status <> 'B'

-- ALSO CORRECT: Remove status filter, filter in template
WHERE T.Type = 'CustInvc'
```

**Symptom**: Empty data source despite confirmed matching records in NetSuite.

### 3. CRE2 Data Source Access Pattern

**Problem**: Forgetting that data sources have a `.rows` property for iteration.

```freemarker
<!-- WRONG: Iterating directly on data source -->
<#list discount_lines as dl>

<!-- CORRECT: Access the .rows property -->
<#list discount_lines.rows as dl>
```

**Symptom**: Empty loop, no output, or FreeMarker error about iteration.

### 4. CRITICAL: Row Objects Do Not Serialize in FreeMarker Hashes

**Problem**: When building lookup maps from CRE2 data sources, storing the row object reference does NOT work. The row object does not transfer properly when assigned to a hash.

```freemarker
<!-- WRONG: Row object reference doesn't transfer -->
<#assign discount_map = {}>
<#list discount_lines.rows as dl>
    <#assign discount_map = discount_map + {dl.docno: dl}>
</#list>
<!-- Later access fails silently: discount_map[key].discountamount returns nothing -->

<!-- CORRECT: Store explicit field values as a new hash -->
<#assign discount_map = {}>
<#list discount_lines.rows as dl>
    <#assign discount_map = discount_map + {dl.docno: {
        "discountamount": dl.discountamount!0,
        "daystodiscount": dl.daystodiscount!0,
        "discountdate": dl.discountdate!""
    }}>
</#list>
<!-- Now discount_map[key].discountamount works correctly -->
```

**Symptom**: Silent failure - lookup appears to work but all values are empty/null. No error message.

### 5. CRITICAL: Avoid Conditionals with CRE2 Lookup Values

**Problem**: FreeMarker conditionals (`?has_content`, `??`, comparisons) do not work reliably with values retrieved from lookup maps built from CRE2 data sources. The values may appear to exist but conditionals evaluate incorrectly.

```freemarker
<!-- WRONG: Conditionals fail silently with CRE2 lookup values -->
<#assign disc = discount_map[docno]!{}>
<#if disc.discountamount?? && disc.discountamount != 0>
    ${disc.discountamount}
</#if>
<!-- Often shows nothing even when discountamount has a value -->

<!-- CORRECT: Use direct output with default values -->
<#assign disc = discount_map[docno]!{}>
${disc.discountamount!"-"}
```

**Symptom**: Conditionals always evaluate to false even when data exists. Values display when you remove the conditional wrapper.

**Workaround Pattern for Optional Display**:
```freemarker
<!-- If you must show different content based on value, output with defaults -->
<td align="right">${disc.discountamount!"-"}</td>
<td align="center">${disc.daystodiscount!"-"}</td>
```

### 6. PDF Table Structure Errors

**Problem**: Placing `<tr>` elements before `<thead>` breaks PDF rendering.

```html
<!-- WRONG: Breaks PDF with UNEXPECTED_ERROR -->
<table>
    <tr>...</tr>           <!-- TR before THEAD -->
    <thead>...</thead>
    <tbody>...</tbody>
</table>

<!-- CORRECT: Proper table structure -->
<table>
    <thead>
        <tr>...</tr>
    </thead>
    <tbody>
        <tr>...</tr>
    </tbody>
</table>
```

**Symptom**: Cryptic `UNEXPECTED_ERROR` during PDF generation with no useful details.

### 7. Debug Output Placement

**Problem**: Placing debug output in the middle of the document can break PDF structure.

```freemarker
<!-- WRONG: Debug in middle can break table/structure -->
<table>
    <#-- Debug here breaks rendering -->
    <tr><td>${debug_info}</td></tr>
</table>

<!-- CORRECT: Add debug section at END of document, before </body> -->
</table>

<!-- Debug Section (before </body>) -->
<#if debug_on == 1>
    <div style="page-break-before: always;">
        <h3>Debug Information</h3>
        <pre>
        discount_lines count: ${(discount_lines.rows)?size}
        <#list discount_lines.rows as dl>
            ${dl.docno}: ${dl.discountamount!"-"}
        </#list>
        </pre>
    </div>
</#if>

</body>
```

**Symptom**: PDF rendering fails when debug is enabled; works when disabled.

### 8. SuiteQL Inequality Operator

**Problem**: SuiteQL does not support `!=` for inequality. Use `<>` instead.

```sql
-- WRONG: SuiteQL syntax error
WHERE Tran.status != 'CustInvc:B'

-- CORRECT: Use SQL standard inequality
WHERE Tran.status <> 'CustInvc:B'
```

**Symptom**: Query fails with syntax error or returns no results.

### 9. Customer Internal ID vs Entity ID

**Problem**: NetSuite customer records have both an Entity ID (e.g., "CUST8428") and an Internal ID (e.g., 27959). SuiteQL filters require the Internal ID.

```sql
-- WRONG: Using entity ID number
WHERE TRL.entity = 8428

-- CORRECT: Use internal ID
WHERE TRL.entity = 27959

-- CORRECT: In CRE2 template, ${record.id} gives internal ID
WHERE TRL.entity = ${record.id}
```

**How to find Internal ID**: Query the Customer table:
```sql
SELECT id, entityid, companyname FROM Customer WHERE entityid LIKE '%8428%'
-- Returns: id=27959, entityid='CUST8428', companyname='Dodds Shoe Co - HQ'
```

### 10. AR Account Numbers Vary by NetSuite Instance

**Problem**: Different NetSuite accounts use different internal IDs for the same GL account. Hardcoding account IDs will fail in different environments.

```sql
-- WRONG: Hardcoded account ID (may not exist in target environment)
WHERE TRA.account = 7

-- CORRECT: Verify account ID for your environment
-- Query: SELECT id, accountsearchdisplayname FROM Account WHERE accountsearchdisplayname LIKE '%A/R%'
-- SB1 Result: id=514, name='11001 A/R - Trade'
WHERE TRA.account = 514
```

**Best Practice**: Document account IDs per environment or use account number/name lookup.

### 11. CRE2 Query Record Configuration

**Problem**: CRE2 SuiteQL data sources require proper configuration in `customrecord_pri_cre2_query`:

| Field | Required Value | Description |
|-------|---------------|-------------|
| `custrecord_pri_cre2q_querytype` | `1` | Must be 1 for SuiteQL (not Saved Search) |
| `custrecord_pri_cre2q_parent` | Profile ID | Links query to CRE2 profile |
| `custrecord_pri_cre2q_name` | Variable name | How template accesses data (e.g., `aging`) |

**Symptom**: Data source is defined but returns nothing in template; no error message.

### 12. Nested Subqueries Can Timeout in CRE2

**Problem**: Complex subqueries in WHERE clauses can cause CRE2 rendering to timeout, especially when evaluated per-row.

```sql
-- WRONG: Subquery runs for every row - causes timeout
WHERE (Trl.entity = ${record.id}
   OR Trl.entity IN (SELECT id FROM Customer WHERE parent = ${record.id}))

-- CORRECT: Simple direct filter (for single customer without children)
WHERE Trl.entity = ${record.id}
```

**Symptom**: PDF generation runs for a long time then stops/times out with no output.

**Workaround for Parent/Child Customers**: Use a separate `cus_children` data source that runs once and caches results, then reference it via FreeMarker.

### 13. Currency and Date Formatting

**Problem**: Currency values display without proper formatting; dates wrap in narrow columns.

```freemarker
<!-- WRONG: No formatting -->
<td>${tran.amount}</td>
<td>${tran.trandate}</td>

<!-- CORRECT: Currency formatting with 2 decimals -->
<td>${currency_symbol}${tran.amount?number?string["0.00"]}</td>

<!-- CORRECT: Prevent date wrapping -->
<td style="white-space: nowrap;">${tran.trandate}</td>
```

**Symptom**: Amounts show as "1234.5" instead of "$1,234.50"; dates wrap mid-value.

### Troubleshooting Checklist

When CRE2 templates fail silently or produce unexpected output:

1. **Check FreeMarker syntax**: `${variable}` not `{variable}`
2. **Verify data source returns data**: Add row count debug output
3. **Check .rows access**: `datasource.rows` not just `datasource`
4. **Avoid row object references in hashes**: Store explicit field values
5. **Remove conditionals around lookup values**: Use direct output with defaults
6. **Validate table structure**: Proper thead/tbody/tr ordering
7. **Move debug output to end**: Before `</body>` tag
8. **Test SuiteQL separately**: Use netsuite-suiteql skill to verify query
9. **Use `<>` not `!=`**: SuiteQL uses SQL standard inequality operator
10. **Verify customer internal ID**: Entity ID ≠ Internal ID
11. **Check AR account IDs**: They vary by NetSuite instance
12. **Verify query record config**: querytype=1, parent=profile ID
13. **Simplify complex subqueries**: Avoid per-row subqueries that timeout

### Quick Debug Template

Add this at the end of your template (before `</body>`) to diagnose data issues:

```freemarker
<#assign debug_on = 1>

<#if debug_on == 1>
<div style="page-break-before: always; font-family: monospace; font-size: 8pt;">
    <h3>CRE2 Debug Output</h3>

    <h4>Record Info</h4>
    <p>Record ID: ${record.id!"-"}</p>
    <p>Company: ${record.companyname!"-"}</p>

    <h4>Data Source: discount_lines</h4>
    <#if discount_lines?? && discount_lines.rows??>
        <p>Row count: ${discount_lines.rows?size}</p>
        <table border="1" cellpadding="3">
            <tr><th>DocNo</th><th>DiscountAmt</th><th>DaysToDisc</th></tr>
            <#list discount_lines.rows as dl>
                <tr>
                    <td>${dl.docno!"-"}</td>
                    <td>${dl.discountamount!"-"}</td>
                    <td>${dl.daystodiscount!"-"}</td>
                </tr>
            </#list>
        </table>
    <#else>
        <p style="color: red;">discount_lines is null or has no rows</p>
    </#if>

    <h4>Lookup Map Test</h4>
    <#if discount_map??>
        <p>Map keys: ${discount_map?keys?join(", ")}</p>
    <#else>
        <p style="color: red;">discount_map not defined</p>
    </#if>
</div>
</#if>
```

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

## Scripts Reference

### Profile Management

```bash
# List CRE2 profiles
python3 scripts/cre2_profile.py list --env sb1

# Get profile details
python3 scripts/cre2_profile.py get 15 --env sb1

# Test render for customer
python3 scripts/cre2_profile.py test 15 12345 --env sb1
```

### Template Validation

```bash
# Validate FreeMarker syntax
python3 scripts/validate_template.py path/to/template.html

# Extract variables from template
python3 scripts/validate_template.py --extract-vars path/to/template.html
```

### Render Document

```bash
# Render PDF for record
python3 scripts/cre2_render.py render 15 12345 --env sb1

# Preview in browser
python3 scripts/cre2_render.py preview 15 12345 --env sb1

# Debug mode (show data)
python3 scripts/cre2_render.py debug 15 12345 --env sb1
```

---

## Best Practices

### Template Development

1. **Start Simple**: Build basic template, add complexity incrementally
2. **Use Debug Mode**: Add `debug_on` flag for development
3. **Test Data**: Verify data sources return expected data before template work
4. **Handle Nulls**: Always check `?has_content` before using values
5. **CSS Inline**: Use inline styles for email templates

### Data Sources

1. **SuiteQL for Joins**: Use SuiteQL when joining multiple tables
2. **Saved Search for Standard**: Use existing saved searches when possible
3. **Parameterize**: Use `{record.id}` for dynamic filtering
4. **Test Queries**: Validate queries in SuiteQL workbench first

### Performance

1. **Limit Rows**: Add filters to prevent large data sets
2. **Optimize Queries**: Index filtering columns
3. **Cache Static Data**: Assign constants to variables once

### Maintenance

1. **Version Templates**: Include version in template comments
2. **Document Data Sources**: Comment what each data source provides
3. **Backup Before Changes**: Copy template before modifications

---

## Related Skills

- **netsuite-suiteql**: SuiteQL query development and testing
- **netsuite-file-cabinet**: File Cabinet operations for templates
- **netsuite-sdf-deployment**: Deploy CRE2 profiles via SDF

---

*Last updated: 2026-01-20*
*Skill version: 1.2.0*
