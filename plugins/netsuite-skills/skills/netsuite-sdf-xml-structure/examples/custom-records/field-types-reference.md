# NetSuite Custom Record Field Types Reference

Complete guide to all NetSuite custom record field types with XML examples and usage guidance.

## Table of Contents

- [Text Fields](#text-fields)
  - [TEXT](#text---short-text-255-chars)
  - [TEXTAREA](#textarea---long-text-4000-chars)
  - [CLOBTEXT](#clobtext---very-long-text-1m-chars)
- [Selection Fields](#selection-fields)
  - [SELECT](#select---single-selection)
  - [MULTISELECT](#multiselect---multiple-selections)
  - [CHECKBOX](#checkbox---boolean-yesno)
- [Date & Time Fields](#date--time-fields)
  - [DATE](#date---calendar-date-only)
  - [DATETIME](#datetime---date--time)
- [Numeric Fields](#numeric-fields)
  - [INTEGER](#integer---whole-numbers)
  - [FLOAT](#float---decimal-numbers)
  - [PERCENT](#percent---percentage-values)
  - [CURRENCY](#currency---money-amounts)
- [Specialized Fields](#specialized-fields)
  - [EMAIL](#email---email-addresses)
  - [PHONE](#phone---phone-numbers)
  - [URL](#url---clickable-links)
  - [DOCUMENT](#document---file-attachments)
  - [IMAGE](#image---image-files)
- [Advanced Fields](#advanced-fields)
  - [FORMULA](#formula---calculated-values)
  - [RICHTEXT](#richtext---html-editor)

---

## Text Fields

### TEXT - Short Text (≤ 255 chars)

**Use For**: Names, codes, identifiers, short descriptions

**Key Attributes**:
- `<maxlength>` - REQUIRED (1-255)
- Best for searchable, indexable text

**Example**:
```xml
<customrecordcustomfield scriptid="custrecord_partner_code">
  <fieldtype>TEXT</fieldtype>
  <label>Partner Code</label>
  <maxlength>50</maxlength>
  <ismandatory>T</ismandatory>
  <storevalue>T</storevalue>
  <help>Unique identifier for trading partner</help>
</customrecordcustomfield>
```

**Common Use Cases**:
```xml
<!-- Short identifier -->
<maxlength>20</maxlength>  <!-- Customer number, SKU -->

<!-- Medium text -->
<maxlength>100</maxlength>  <!-- Names, titles -->

<!-- Long identifier -->
<maxlength>255</maxlength>  <!-- Full URLs, long descriptions -->
```

---

### TEXTAREA - Long Text (≤ 4000 chars)

**Use For**: Descriptions, notes, comments, multi-line text

**Key Attributes**:
- `<maxlength>` - REQUIRED (1-4000)
- `<displayheight>` - Number of rows in UI (default: 3)
- Supports line breaks

**Example**:
```xml
<customrecordcustomfield scriptid="custrecord_description">
  <fieldtype>TEXTAREA</fieldtype>
  <label>Description</label>
  <maxlength>4000</maxlength>
  <displayheight>10</displayheight>
  <displaywidth>80</displaywidth>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
  <help>Detailed description of the item</help>
</customrecordcustomfield>
```

**Display Options**:
```xml
<!-- Small text area -->
<displayheight>3</displayheight>
<displaywidth>60</displaywidth>

<!-- Medium text area -->
<displayheight>5</displayheight>
<displaywidth>80</displaywidth>

<!-- Large text area -->
<displayheight>10</displayheight>
<displaywidth>100</displaywidth>
```

**TEXTAREA vs TEXT Decision Guide**:
- **Use TEXT if**: Single line, ≤ 255 chars, needs to be searchable
- **Use TEXTAREA if**: Multi-line, 256-4000 chars, formatting important

---

### CLOBTEXT - Very Long Text (≤ 1M chars)

**Use For**: SuiteQL queries, JSON data, XML content, large text blocks, code snippets

**Key Attributes**:
- `<maxlength>` - MUST BE EMPTY: `<maxlength></maxlength>`
- Supports ~1 million characters
- Not searchable/indexable (use for storage, not searching)

**Example - SuiteQL Query Storage**:
```xml
<customrecordcustomfield scriptid="custrecord_twx_tmpl_query">
  <accesslevel>2</accesslevel>
  <allowquickadd>F</allowquickadd>
  <applyformatting>F</applyformatting>
  <checkspelling>F</checkspelling>
  <defaultchecked>F</defaultchecked>
  <defaultselection></defaultselection>
  <defaultvalue></defaultvalue>
  <description>SuiteQL query returning single row. Column names become template variables.</description>
  <displayheight>10</displayheight>
  <displaytype>NORMAL</displaytype>
  <displaywidth>80</displaywidth>
  <dynamicdefault></dynamicdefault>
  <enabletextenhance>F</enabletextenhance>
  <encryptatrest>F</encryptatrest>
  <fieldtype>CLOBTEXT</fieldtype>
  <globalsearch>F</globalsearch>
  <help>Query should SELECT columns with names matching template {{variables}}. Use {recordId} for parameter substitution.</help>
  <isformula>F</isformula>
  <ismandatory>T</ismandatory>
  <isparent>F</isparent>
  <label>Data Query (SuiteQL)</label>
  <linktext></linktext>
  <maxlength></maxlength>  <!-- CRITICAL: MUST BE EMPTY FOR CLOBTEXT -->
  <maxvalue></maxvalue>
  <minvalue></minvalue>
  <onparentdelete></onparentdelete>
  <parentsubtab></parentsubtab>
  <rolerestrict>F</rolerestrict>
  <searchcomparefield></searchcomparefield>
  <searchdefault></searchdefault>
  <searchlevel>2</searchlevel>
  <selectrecordtype></selectrecordtype>
  <showinlist>F</showinlist>
  <sourcefilterby></sourcefilterby>
  <sourcefrom></sourcefrom>
  <sourcelist></sourcelist>
  <storevalue>T</storevalue>
  <subtab></subtab>
</customrecordcustomfield>
```

**Example - JSON Configuration Storage**:
```xml
<customrecordcustomfield scriptid="custrecord_config_json">
  <fieldtype>CLOBTEXT</fieldtype>
  <label>Configuration (JSON)</label>
  <help>Full configuration in JSON format</help>
  <maxlength></maxlength>  <!-- Empty for CLOBTEXT -->
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
</customrecordcustomfield>
```

**Example - Large Text Block**:
```xml
<customrecordcustomfield scriptid="custrecord_full_query">
  <fieldtype>CLOBTEXT</fieldtype>
  <label>Full Query</label>
  <help>Full query text (up to 1 million characters)</help>
  <maxlength></maxlength>  <!-- Empty for CLOBTEXT -->
  <displayheight>15</displayheight>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
</customrecordcustomfield>
```

**⚠️ CRITICAL DIFFERENCES**:

| Field Type | maxlength Value | Character Limit | Searchable | Use Case |
|------------|----------------|-----------------|------------|----------|
| TEXT | Number (1-255) | 255 | ✅ Yes | Short text, identifiers |
| TEXTAREA | Number (1-4000) | 4,000 | ✅ Yes | Descriptions, notes |
| **CLOBTEXT** | **Empty string** | ~1,000,000 | ❌ No | Queries, JSON, large text |

**Common Mistake**:
```xml
<!-- ❌ WRONG: CLOBTEXT with maxlength number -->
<fieldtype>CLOBTEXT</fieldtype>
<maxlength>10000</maxlength>  <!-- NetSuite will reject this! -->

<!-- ✅ CORRECT: CLOBTEXT with empty maxlength -->
<fieldtype>CLOBTEXT</fieldtype>
<maxlength></maxlength>
```

**CLOBTEXT vs TEXTAREA Decision Guide**:
- **Use TEXTAREA if**: ≤ 4000 chars, needs searching, user-visible descriptions
- **Use CLOBTEXT if**: > 4000 chars, code/data storage, not searched, queries/JSON/XML

---

## Selection Fields

### SELECT - Single Selection

**Use For**: Dropdowns, lookups to other records, single-choice fields

**Key Attributes**:
- `<selectrecordtype>` - Record type to link to
- `<isparent>` - Creates parent-child relationship if 'T'

**Example - Link to Custom Record**:
```xml
<customrecordcustomfield scriptid="custrecord_trading_partner">
  <fieldtype>SELECT</fieldtype>
  <label>Trading Partner</label>
  <selectrecordtype>[scriptid=customrecord_twx_edi_tp]</selectrecordtype>
  <ismandatory>T</ismandatory>
  <storevalue>T</storevalue>
  <help>Link to trading partner record</help>
</customrecordcustomfield>
```

**Example - Link to Custom List**:
```xml
<customrecordcustomfield scriptid="custrecord_status">
  <fieldtype>SELECT</fieldtype>
  <label>Status</label>
  <selectrecordtype>[scriptid=customlist_status_values]</selectrecordtype>
  <ismandatory>T</ismandatory>
  <storevalue>T</storevalue>
</customrecordcustomfield>
```

**Example - Link to Standard NetSuite Record**:
```xml
<customrecordcustomfield scriptid="custrecord_customer">
  <fieldtype>SELECT</fieldtype>
  <label>Customer</label>
  <selectrecordtype>-2</selectrecordtype>  <!-- -2 = Customer -->
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
</customrecordcustomfield>
```

**Common Standard Record Types**:
```xml
<selectrecordtype>-2</selectrecordtype>   <!-- Customer -->
<selectrecordtype>-5</selectrecordtype>   <!-- Item -->
<selectrecordtype>-10</selectrecordtype>  <!-- Vendor -->
<selectrecordtype>-140</selectrecordtype> <!-- Location -->
<selectrecordtype>-112</selectrecordtype> <!-- Employee -->
```

**Parent-Child Relationship** (creates related list on parent):
```xml
<customrecordcustomfield scriptid="custrecord_parent_record">
  <fieldtype>SELECT</fieldtype>
  <label>Parent Record</label>
  <selectrecordtype>[scriptid=customrecord_parent]</selectrecordtype>
  <isparent>T</isparent>  <!-- Creates parent-child relationship -->
  <parentsubtab>[scriptid=customrecord_parent.tab_children]</parentsubtab>
  <onparentdelete>SET_NULL</onparentdelete>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
</customrecordcustomfield>
```

---

### MULTISELECT - Multiple Selections

**Use For**: Many-to-many relationships, selecting multiple items

**Example**:
```xml
<customrecordcustomfield scriptid="custrecord_channels">
  <fieldtype>MULTISELECT</fieldtype>
  <label>Notification Channels</label>
  <selectrecordtype>[scriptid=customrecord_notification_channel]</selectrecordtype>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
  <help>Select one or more notification channels</help>
</customrecordcustomfield>
```

---

### CHECKBOX - Boolean (Yes/No)

**Use For**: True/false flags, enabled/disabled toggles

**Key Attributes**:
- `<defaultchecked>` - T or F (default state)

**Example**:
```xml
<customrecordcustomfield scriptid="custrecord_is_active">
  <fieldtype>CHECKBOX</fieldtype>
  <label>Active</label>
  <checkspelling>F</checkspelling>
  <defaultchecked>T</defaultchecked>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
  <help>Enable or disable this record</help>
</customrecordcustomfield>
```

---

## Date & Time Fields

### DATE - Calendar Date Only

**Use For**: Birth dates, deadlines, dates without time

**Example**:
```xml
<customrecordcustomfield scriptid="custrecord_ship_date">
  <fieldtype>DATE</fieldtype>
  <label>Ship Date</label>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
  <help>Expected shipment date</help>
</customrecordcustomfield>
```

---

### DATETIME - Date + Time

**Use For**: Timestamps, scheduled times, exact moments

**Example**:
```xml
<customrecordcustomfield scriptid="custrecord_timestamp">
  <fieldtype>DATETIME</fieldtype>
  <label>Timestamp</label>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
  <help>Exact date and time of event</help>
</customrecordcustomfield>
```

---

## Numeric Fields

### INTEGER - Whole Numbers

**Use For**: Counts, quantities, IDs

**Example**:
```xml
<customrecordcustomfield scriptid="custrecord_quantity">
  <fieldtype>INTEGER</fieldtype>
  <label>Quantity</label>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
  <help>Whole number quantity</help>
</customrecordcustomfield>
```

---

### FLOAT - Decimal Numbers

**Use For**: Measurements, weights, precise calculations

**Example**:
```xml
<customrecordcustomfield scriptid="custrecord_weight">
  <fieldtype>FLOAT</fieldtype>
  <label>Weight (lbs)</label>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
  <help>Weight in pounds (decimal)</help>
</customrecordcustomfield>
```

---

### PERCENT - Percentage Values

**Use For**: Percentages, ratios

**Example**:
```xml
<customrecordcustomfield scriptid="custrecord_discount_pct">
  <fieldtype>PERCENT</fieldtype>
  <label>Discount %</label>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
  <help>Discount percentage</help>
</customrecordcustomfield>
```

---

### CURRENCY - Money Amounts

**Use For**: Prices, costs, monetary values

**Example**:
```xml
<customrecordcustomfield scriptid="custrecord_amount">
  <fieldtype>CURRENCY</fieldtype>
  <label>Amount</label>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
  <help>Dollar amount with currency symbol</help>
</customrecordcustomfield>
```

---

## Specialized Fields

### EMAIL - Email Addresses

**Use For**: Email addresses with validation

**Example**:
```xml
<customrecordcustomfield scriptid="custrecord_contact_email">
  <fieldtype>EMAIL</fieldtype>
  <label>Contact Email</label>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
  <help>Contact email address</help>
</customrecordcustomfield>
```

---

### PHONE - Phone Numbers

**Use For**: Phone numbers with formatting

**Example**:
```xml
<customrecordcustomfield scriptid="custrecord_phone">
  <fieldtype>PHONE</fieldtype>
  <label>Phone Number</label>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
  <help>Contact phone number</help>
</customrecordcustomfield>
```

---

### URL - Clickable Links

**Use For**: External links, websites

**Example**:
```xml
<customrecordcustomfield scriptid="custrecord_website">
  <fieldtype>URL</fieldtype>
  <label>Website</label>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
  <help>Company website URL</help>
</customrecordcustomfield>
```

---

### DOCUMENT - File Attachments

**Use For**: Attaching files to records

**Example**:
```xml
<customrecordcustomfield scriptid="custrecord_attachment">
  <fieldtype>DOCUMENT</fieldtype>
  <label>Attachment</label>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
  <help>Attach a file to this record</help>
</customrecordcustomfield>
```

---

### IMAGE - Image Files

**Use For**: Photos, logos, images

**Example**:
```xml
<customrecordcustomfield scriptid="custrecord_logo">
  <fieldtype>IMAGE</fieldtype>
  <label>Logo</label>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
  <help>Company logo image</help>
</customrecordcustomfield>
```

---

## Advanced Fields

### FORMULA - Calculated Values

**Use For**: Read-only computed fields

**Key Attributes**:
- `<formula>` - The formula text
- `<formulanumeric>` or `<formulatext>` or `<formuladate>` - Return type

**Example - Text Formula**:
```xml
<customrecordcustomfield scriptid="custrecord_display_name">
  <fieldtype>FORMULA</fieldtype>
  <label>Display Name</label>
  <formulatext>{custrecord_first_name}||' '||{custrecord_last_name}</formulatext>
  <storevalue>F</storevalue>
  <help>Computed full name</help>
</customrecordcustomfield>
```

**Example - Numeric Formula**:
```xml
<customrecordcustomfield scriptid="custrecord_total">
  <fieldtype>FORMULA</fieldtype>
  <label>Total</label>
  <formulanumeric>{custrecord_quantity}*{custrecord_price}</formulanumeric>
  <storevalue>F</storevalue>
  <help>Computed total (qty × price)</help>
</customrecordcustomfield>
```

---

### RICHTEXT - HTML Editor

**Use For**: Formatted text with HTML, rich content

**Example**:
```xml
<customrecordcustomfield scriptid="custrecord_rich_description">
  <fieldtype>RICHTEXT</fieldtype>
  <label>Rich Description</label>
  <ismandatory>F</ismandatory>
  <storevalue>T</storevalue>
  <help>Description with formatting</help>
</customrecordcustomfield>
```

---

## Field Type Decision Tree

```
Need to store text?
├─ ≤ 255 chars, single line → TEXT
├─ 256-4000 chars, multi-line → TEXTAREA
└─ > 4000 chars, large blocks → CLOBTEXT

Need to link records?
├─ Single selection → SELECT
└─ Multiple selections → MULTISELECT

Need date/time?
├─ Date only → DATE
└─ Date + time → DATETIME

Need numbers?
├─ Whole numbers → INTEGER
├─ Decimals → FLOAT
├─ Percentages → PERCENT
└─ Money → CURRENCY

Need specialized input?
├─ Email → EMAIL
├─ Phone → PHONE
├─ Website → URL
├─ File → DOCUMENT
├─ Image → IMAGE
├─ Yes/No → CHECKBOX
├─ Formatted text → RICHTEXT
└─ Calculated value → FORMULA
```

---

## Common Patterns

### Configuration Storage (JSON/XML)
```xml
<!-- Use CLOBTEXT for large configuration -->
<customrecordcustomfield scriptid="custrecord_config">
  <fieldtype>CLOBTEXT</fieldtype>
  <label>Configuration</label>
  <maxlength></maxlength>  <!-- Empty for CLOBTEXT -->
  <storevalue>T</storevalue>
</customrecordcustomfield>
```

### SuiteQL Query Storage
```xml
<!-- Use CLOBTEXT for queries > 4000 chars -->
<customrecordcustomfield scriptid="custrecord_query">
  <fieldtype>CLOBTEXT</fieldtype>
  <label>SuiteQL Query</label>
  <maxlength></maxlength>
  <storevalue>T</storevalue>
</customrecordcustomfield>
```

### Simple Notes/Comments
```xml
<!-- Use TEXTAREA for user comments -->
<customrecordcustomfield scriptid="custrecord_notes">
  <fieldtype>TEXTAREA</fieldtype>
  <label>Notes</label>
  <maxlength>4000</maxlength>
  <displayheight>5</displayheight>
  <storevalue>T</storevalue>
</customrecordcustomfield>
```

### Short Identifiers
```xml
<!-- Use TEXT for codes/IDs -->
<customrecordcustomfield scriptid="custrecord_code">
  <fieldtype>TEXT</fieldtype>
  <label>Code</label>
  <maxlength>50</maxlength>
  <storevalue>T</storevalue>
</customrecordcustomfield>
```

---

## Troubleshooting

### "Value exceeds maximum length" Error

**Cause**: Text too long for field type

**Solution**:
```xml
<!-- If using TEXT and hitting 255 char limit -->
<fieldtype>TEXT</fieldtype>
<maxlength>255</maxlength>  <!-- MAX for TEXT -->

<!-- Upgrade to TEXTAREA if 256-4000 chars needed -->
<fieldtype>TEXTAREA</fieldtype>
<maxlength>4000</maxlength>  <!-- MAX for TEXTAREA -->

<!-- Upgrade to CLOBTEXT if > 4000 chars needed -->
<fieldtype>CLOBTEXT</fieldtype>
<maxlength></maxlength>  <!-- EMPTY for CLOBTEXT -->
```

### "Invalid maxlength value" for CLOBTEXT

**Cause**: Trying to set numeric maxlength on CLOBTEXT

**Solution**:
```xml
<!-- ❌ WRONG -->
<fieldtype>CLOBTEXT</fieldtype>
<maxlength>10000</maxlength>

<!-- ✅ CORRECT -->
<fieldtype>CLOBTEXT</fieldtype>
<maxlength></maxlength>  <!-- Must be empty -->
```

### Field Type Conversion Issues

**Converting from TEXTAREA to CLOBTEXT**:
```xml
<!-- Before -->
<fieldtype>TEXTAREA</fieldtype>
<maxlength>4000</maxlength>

<!-- After -->
<fieldtype>CLOBTEXT</fieldtype>
<maxlength></maxlength>  <!-- Change to empty -->
```

**Warning**: NetSuite may show "Type conversion will take significant time" - this is expected for existing records.

---

## Quick Reference Table

| Field Type | Character Limit | maxlength Value | Searchable | Common Use |
|------------|----------------|-----------------|------------|------------|
| TEXT | 255 | 1-255 | ✅ | Names, codes, IDs |
| TEXTAREA | 4,000 | 1-4000 | ✅ | Descriptions, notes |
| **CLOBTEXT** | ~1,000,000 | **Empty** | ❌ | Queries, JSON, large text |
| SELECT | N/A | N/A | ✅ | Dropdowns, lookups |
| MULTISELECT | N/A | N/A | ✅ | Multiple choices |
| CHECKBOX | N/A | N/A | ✅ | Yes/No, enabled/disabled |
| DATE | N/A | N/A | ✅ | Calendar dates |
| DATETIME | N/A | N/A | ✅ | Timestamps |
| INTEGER | N/A | N/A | ✅ | Whole numbers |
| FLOAT | N/A | N/A | ✅ | Decimals |
| PERCENT | N/A | N/A | ✅ | Percentages |
| CURRENCY | N/A | N/A | ✅ | Money amounts |
| EMAIL | 255 | N/A | ✅ | Email addresses |
| PHONE | 50 | N/A | ✅ | Phone numbers |
| URL | 255 | N/A | ✅ | Web links |
| DOCUMENT | N/A | N/A | ❌ | File attachments |
| IMAGE | N/A | N/A | ❌ | Images |
| FORMULA | N/A | N/A | ✅ | Calculated values |
| RICHTEXT | Large | N/A | ⚠️ | HTML content |

---

**Related Documentation**:
- [Parent-Child Patterns](parent-child-patterns.md)
- [Subtab Configuration](../../skill.md#subtab-configuration)
- [Custom List Structure](../custom-lists/list-structure.md)
