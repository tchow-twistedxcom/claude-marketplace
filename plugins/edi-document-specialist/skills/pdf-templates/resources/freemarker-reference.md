# FreeMarker Reference for CRE2 Templates

CRE2 templates use Apache FreeMarker syntax for dynamic content. This reference covers the most common patterns for EDI document templates.

## Variable Access

### Basic Variable Output

```html
<!-- Direct output -->
${variableName}

<!-- From OVERRIDE object (CRE2 JS hook output) -->
${OVERRIDE.EDI.invoiceNumber}
${OVERRIDE.EDI.invoiceSummary.totalAmount}

<!-- From query data source -->
${edi.invoiceNumber}
${record.name}
```

### Nested Object Access

```html
<!-- Dot notation -->
${OVERRIDE.EDI.invoiceSummary.poNumber}

<!-- Square bracket notation (for special characters) -->
${OVERRIDE.EDI["invoice-summary"]["po-number"]}
```

### Default Values

```html
<!-- If variable might be null -->
${variableName!"Default Value"}
${OVERRIDE.EDI.optionalField!"N/A"}

<!-- Empty string as default -->
${variableName!""}

<!-- Check if exists before using -->
<#if variableName??>
  ${variableName}
</#if>
```

## Conditionals

### Basic If/Else

```html
<#if condition>
  Content when true
</#if>

<#if condition>
  Content when true
<#else>
  Content when false
</#if>

<#if condition1>
  First condition
<#elseif condition2>
  Second condition
<#else>
  Default
</#if>
```

### Comparison Operators

```html
<!-- Equality -->
<#if status == "Shipped">Shipped</#if>

<!-- Inequality -->
<#if status != "Pending">Not Pending</#if>

<!-- Numeric comparisons -->
<#if quantity gt 0>Has items</#if>
<#if quantity gte 10>10 or more</#if>
<#if quantity lt 5>Less than 5</#if>
<#if quantity lte 100>100 or less</#if>

<!-- String checks -->
<#if name?starts_with("A")>Starts with A</#if>
<#if name?ends_with("Inc")>Ends with Inc</#if>
<#if name?contains("Brands")>Contains Brands</#if>
```

### Boolean Logic

```html
<!-- AND -->
<#if status == "Shipped" && quantity gt 0>
  Shipped with items
</#if>

<!-- OR -->
<#if status == "Pending" || status == "Processing">
  In progress
</#if>

<!-- NOT -->
<#if !cancelled>
  Active
</#if>
```

### Null/Exists Checks

```html
<!-- Check if variable exists -->
<#if variableName??>
  Variable exists: ${variableName}
</#if>

<!-- Check if variable has content -->
<#if variableName?has_content>
  Variable has content
</#if>

<!-- Check if list is not empty -->
<#if items?? && items?size gt 0>
  Has items
</#if>
```

## Loops

### List Iteration

```html
<#list invoiceDetails as line>
  <tr>
    <td>${line.itemNumber}</td>
    <td>${line.quantity}</td>
  </tr>
</#list>
```

### Loop with Index

```html
<#list items as item>
  ${item?index + 1}. ${item.name}
  <!-- item?index is 0-based -->
</#list>
```

### Loop Variables

```html
<#list items as item>
  <#if item?is_first>First item</#if>
  <#if item?is_last>Last item</#if>
  <#if item?is_odd_item>Odd row</#if>
  <#if item?is_even_item>Even row</#if>
  Item ${item?counter} of ${items?size}
</#list>
```

### Alternating Row Colors

```html
<#list items as item>
  <tr style="background-color:<#if item?is_odd_item>#ffffff<#else>#f5f5f5</#if>;">
    <td>${item.name}</td>
  </tr>
</#list>
```

### Loop with Separator

```html
<#list items as item>${item.name}<#sep>, </#sep></#list>
<!-- Output: Item1, Item2, Item3 -->
```

### Empty List Handling

```html
<#list items as item>
  ${item.name}
<#else>
  No items found
</#list>
```

## String Operations

### Case Conversion

```html
${name?upper_case}  <!-- UPPERCASE -->
${name?lower_case}  <!-- lowercase -->
${name?cap_first}   <!-- First letter capitalized -->
```

### Trimming

```html
${text?trim}        <!-- Remove leading/trailing whitespace -->
${text?left_pad(10)}  <!-- Pad left to 10 chars -->
${text?right_pad(10)} <!-- Pad right to 10 chars -->
```

### Substring

```html
${text?substring(0, 5)}  <!-- First 5 characters -->
${text?substring(5)}     <!-- From position 5 to end -->
```

### Replace

```html
${text?replace("old", "new")}
${text?replace("\n", "<br/>")}  <!-- Newlines to HTML breaks -->
```

### Length Check

```html
<#if text?length gt 50>
  ${text?substring(0, 47)}...
<#else>
  ${text}
</#if>
```

## Number Formatting

### Basic Number Format

```html
${number?string("0.00")}      <!-- 1234.56 -->
${number?string("#,##0.00")}  <!-- 1,234.56 -->
${number?string("0")}         <!-- Round to integer -->
```

### Currency Formatting

```html
<!-- Manual currency format -->
$${amount?string("#,##0.00")}

<!-- With null check -->
$${(amount!0)?string("#,##0.00")}
```

### Percentage

```html
${percentage?string("0.0")}%
```

## Date Formatting

### Date Output

```html
${date?string("MM/dd/yyyy")}      <!-- 01/15/2026 -->
${date?string("yyyy-MM-dd")}      <!-- 2026-01-15 -->
${date?string("MMMM d, yyyy")}    <!-- January 15, 2026 -->
${date?string("EEE, MMM d")}      <!-- Wed, Jan 15 -->
```

### Date/Time Combined

```html
${datetime?string("MM/dd/yyyy HH:mm")}  <!-- 01/15/2026 14:30 -->
${datetime?string("yyyy-MM-dd'T'HH:mm:ss")}  <!-- ISO format -->
```

### Date Parsing

```html
<!-- Parse string to date -->
<#assign parsedDate = dateString?date("yyyyMMdd")>
${parsedDate?string("MM/dd/yyyy")}
```

## CRE2-Specific Patterns

### Accessing OVERRIDE Data

The JavaScript hook (`twx_CRE2_EDI_DataExtractor.js`) sets data on `OVERRIDE.EDI`:

```html
<!-- Document header -->
<span>${OVERRIDE.EDI.documentType}</span>
<span>${OVERRIDE.EDI.partnerName}</span>

<!-- Summary data -->
<td>${OVERRIDE.EDI.invoiceSummary.totalAmount}</td>
<td>${OVERRIDE.EDI.invoiceSummary.poNumber}</td>

<!-- Technical details -->
<span>Control: ${OVERRIDE.EDI.technicalDetails.controlNumber}</span>
```

### Iterating Partners

```html
<#list OVERRIDE.EDI.partners as partner>
  <#if partner.type == "BILL TO">
    <table>
      <tr><td style="font-weight:bold;">Bill To:</td></tr>
      <tr><td>${partner.name}</td></tr>
      <tr><td>${partner.address}</td></tr>
      <tr><td>${partner.city}, ${partner.state} ${partner.zip}</td></tr>
    </table>
  </#if>
</#list>
```

### Finding Specific Partner

```html
<#assign billTo = "">
<#list OVERRIDE.EDI.partners as partner>
  <#if partner.type == "BILL TO">
    <#assign billTo = partner>
  </#if>
</#list>

<#if billTo?has_content>
  ${billTo.name}
</#if>
```

### Line Items with Totals

```html
<#assign lineTotal = 0>
<#list OVERRIDE.EDI.invoiceDetails as line>
  <tr>
    <td>${line.itemNumber}</td>
    <td>${line.description}</td>
    <td style="text-align:right;">${line.quantity}</td>
    <td style="text-align:right;">${line.unitPrice}</td>
    <td style="text-align:right;">${line.totalPrice}</td>
  </tr>
  <#-- Note: Calculating totals in FreeMarker is limited -->
  <#-- Better to pre-calculate in JavaScript hook -->
</#list>
```

### Conditional Sections

```html
<!-- Show payment terms only if present -->
<#if OVERRIDE.EDI.paymentTerms?? && OVERRIDE.EDI.paymentTerms.description?has_content>
  <table style="margin-top:15px;">
    <tr><td style="font-weight:bold;">Payment Terms</td></tr>
    <tr><td>${OVERRIDE.EDI.paymentTerms.description}</td></tr>
    <#if OVERRIDE.EDI.paymentTerms.netDays??>
      <tr><td>Net ${OVERRIDE.EDI.paymentTerms.netDays} days</td></tr>
    </#if>
  </table>
</#if>
```

### Logo URLs

```html
<!-- Twisted X logo (always present) -->
<img src="${OVERRIDE.EDI.twistedXLogo?replace('&', '&amp;')}" dpi="400" />

<!-- Trading partner logo (may be missing) -->
<#if OVERRIDE.EDI.tradingPartnerLogo?has_content>
  <img src="${OVERRIDE.EDI.tradingPartnerLogo?replace('&', '&amp;')}" dpi="400" />
</#if>
```

## Template Includes

### Including Shared Components

```html
<!-- Include another template file -->
<#include "/templates/header.ftl">
<#include "/templates/footer.ftl">
```

### Macros for Reusable Components

```html
<!-- Define macro -->
<#macro addressBlock partner>
  <table>
    <tr><td style="font-weight:bold;">${partner.type}</td></tr>
    <tr><td>${partner.name}</td></tr>
    <tr><td>${partner.address}</td></tr>
    <tr><td>${partner.city}, ${partner.state} ${partner.zip}</td></tr>
  </table>
</#macro>

<!-- Use macro -->
<@addressBlock partner=billToPartner />
<@addressBlock partner=shipToPartner />
```

## Debugging

### Output Variable Type

```html
<!-- Check what a variable is -->
<#if variable?is_string>String</#if>
<#if variable?is_number>Number</#if>
<#if variable?is_boolean>Boolean</#if>
<#if variable?is_sequence>List/Array</#if>
<#if variable?is_hash>Object/Map</#if>
```

### Debug Output

```html
<!-- Temporarily show raw data (remove in production) -->
<div style="background:yellow; padding:5px;">
  DEBUG: ${OVERRIDE.EDI?string}
</div>
```
