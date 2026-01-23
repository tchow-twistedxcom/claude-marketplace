# CRE2 Template Patterns

Common patterns and complete examples for EDI document PDF templates.

## Document Structure

### Standard EDI Document Layout

```
┌─────────────────────────────────────────────────────┐
│ [Logo Left]      DOCUMENT TITLE       [Logo Right]  │
│                  Partner Name                       │
├─────────────────────────────────────────────────────┤
│                                    ┌──────────────┐ │
│                                    │ Summary Box  │ │
│                                    │ Doc Number   │ │
│                                    │ Date         │ │
│                                    │ PO Number    │ │
│                                    │ Total        │ │
│                                    └──────────────┘ │
├─────────────────────────────────────────────────────┤
│ ┌─────────────────┐  ┌─────────────────┐            │
│ │ Bill To         │  │ Ship To         │            │
│ │ Address...      │  │ Address...      │            │
│ └─────────────────┘  └─────────────────┘            │
├─────────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────────────┐   │
│ │ Line Items Table                              │   │
│ │ Item | Description | Qty | Price | Total     │   │
│ │ ...  | ...         | ... | ...   | ...       │   │
│ └───────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────┤
│                              Subtotal: $X,XXX.XX    │
│                              Discount: $XXX.XX      │
│                              Shipping: $XX.XX       │
│                              Tax:      $XX.XX       │
│                              ───────────────────    │
│                              TOTAL:    $X,XXX.XX    │
├─────────────────────────────────────────────────────┤
│ Payment Terms: Net 30                               │
│ Remittance Address...                               │
├─────────────────────────────────────────────────────┤
│ Control Number: XXXXXXXXX | Test: P                 │
└─────────────────────────────────────────────────────┘
```

## Complete 810 Invoice Template

```html
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
  <title>810 Invoice - ${OVERRIDE.EDI.invoiceNumber!""}</title>
</head>
<body style="font-family:Arial,Helvetica,sans-serif; font-size:10px; margin:20px;">

<!-- HEADER WITH LOGOS -->
<table style="width:100%;">
  <tr>
    <td style="width:25%; vertical-align:top;">
      <img src="${OVERRIDE.EDI.twistedXLogo?replace('&', '&amp;')}" dpi="400"/>
    </td>
    <td style="width:50%; text-align:center; vertical-align:middle;">
      <table style="margin:0 auto;">
        <tr><td style="padding-bottom:4px;">
          <span style="font-size:18px; font-weight:bold;">810 INVOICE</span>
        </td></tr>
        <tr><td>
          <span style="font-size:14px;">${OVERRIDE.EDI.partnerName!""}</span>
        </td></tr>
      </table>
    </td>
    <td style="width:25%; text-align:right; vertical-align:top;">
      <#if OVERRIDE.EDI.tradingPartnerLogo?has_content>
        <img src="${OVERRIDE.EDI.tradingPartnerLogo?replace('&', '&amp;')}" dpi="400"/>
      </#if>
    </td>
  </tr>
</table>

<!-- INVOICE SUMMARY BOX -->
<table style="width:100%; margin-top:15px;">
  <tr>
    <td style="width:60%;"></td>
    <td style="width:40%;">
      <table style="border:2px solid #000; width:100%;">
        <tr><td style="padding:8px;">
          <table style="width:100%;">
            <tr>
              <td style="font-weight:bold; padding:2px;">Invoice #:</td>
              <td style="text-align:right; padding:2px;">${OVERRIDE.EDI.invoiceNumber!""}</td>
            </tr>
            <tr>
              <td style="font-weight:bold; padding:2px;">Date:</td>
              <td style="text-align:right; padding:2px;">${OVERRIDE.EDI.invoiceDate!""}</td>
            </tr>
            <tr>
              <td style="font-weight:bold; padding:2px;">PO #:</td>
              <td style="text-align:right; padding:2px;">${OVERRIDE.EDI.invoiceSummary.poNumber!""}</td>
            </tr>
            <tr>
              <td style="font-weight:bold; padding:2px;">Type:</td>
              <td style="text-align:right; padding:2px;">${OVERRIDE.EDI.invoiceSummary.invoiceType!""}</td>
            </tr>
            <tr style="border-top:1px solid #000;">
              <td style="font-weight:bold; padding:4px 2px 2px 2px; font-size:12px;">Total:</td>
              <td style="text-align:right; padding:4px 2px 2px 2px; font-size:12px; font-weight:bold;">
                ${OVERRIDE.EDI.invoiceSummary.totalAmount!""}
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </td>
  </tr>
</table>

<!-- BILLING INFORMATION -->
<table style="width:100%; margin-top:15px;">
  <tr>
    <td colspan="2" style="font-size:12px; font-weight:bold; padding-bottom:8px; border-bottom:1px solid #000;">
      Billing Information
    </td>
  </tr>
</table>

<table style="width:100%; margin-top:10px;">
  <tr>
    <#list OVERRIDE.EDI.partners as partner>
      <#if partner.type == "BILL TO" || partner.type == "SHIP TO">
        <td style="width:50%; vertical-align:top;">
          <table>
            <tr><td style="font-weight:bold; padding-bottom:4px;">${partner.type}</td></tr>
            <tr><td style="padding-bottom:2px;">${partner.name!""}</td></tr>
            <tr><td style="padding-bottom:2px;">${partner.address!""}</td></tr>
            <#if partner.address2?has_content>
              <tr><td style="padding-bottom:2px;">${partner.address2}</td></tr>
            </#if>
            <tr><td>${partner.city!""}, ${partner.state!""} ${partner.zip!""}</td></tr>
          </table>
        </td>
      </#if>
    </#list>
  </tr>
</table>

<!-- LINE ITEMS -->
<table style="width:100%; margin-top:15px;">
  <tr>
    <td style="font-size:12px; font-weight:bold; padding-bottom:8px; border-bottom:1px solid #000;">
      Invoice Line Items
    </td>
  </tr>
</table>

<table style="width:100%; border-collapse:collapse; margin-top:10px;">
  <tr style="background-color:#e0e0e0;">
    <th style="border:1px solid #000; padding:5px; text-align:left; width:10%;">Line</th>
    <th style="border:1px solid #000; padding:5px; text-align:left; width:15%;">Item #</th>
    <th style="border:1px solid #000; padding:5px; text-align:left; width:35%;">Description</th>
    <th style="border:1px solid #000; padding:5px; text-align:right; width:10%;">Qty</th>
    <th style="border:1px solid #000; padding:5px; text-align:right; width:15%;">Unit Price</th>
    <th style="border:1px solid #000; padding:5px; text-align:right; width:15%;">Total</th>
  </tr>
  <#list OVERRIDE.EDI.invoiceDetails as line>
  <tr style="background-color:<#if line?is_odd_item>#ffffff<#else>#f9f9f9</#if>;">
    <td style="border:1px solid #000; padding:5px;">${line.lineNumber!""}</td>
    <td style="border:1px solid #000; padding:5px;">${line.itemNumber!""}</td>
    <td style="border:1px solid #000; padding:5px;">${line.description!""}</td>
    <td style="border:1px solid #000; padding:5px; text-align:right;">${line.quantity!""}</td>
    <td style="border:1px solid #000; padding:5px; text-align:right;">${line.unitPrice!""}</td>
    <td style="border:1px solid #000; padding:5px; text-align:right;">${line.totalPrice!""}</td>
  </tr>
  </#list>
</table>

<!-- TOTALS -->
<table style="width:100%; margin-top:10px;">
  <tr>
    <td style="width:70%;"></td>
    <td style="width:30%;">
      <table style="width:100%;">
        <#if OVERRIDE.EDI.invoiceSummary.subtotal?has_content>
        <tr>
          <td style="padding:3px;">Subtotal:</td>
          <td style="text-align:right; padding:3px;">${OVERRIDE.EDI.invoiceSummary.subtotal}</td>
        </tr>
        </#if>
        <#if OVERRIDE.EDI.invoiceSummary.discount?has_content && OVERRIDE.EDI.invoiceSummary.discount != "$0.00">
        <tr>
          <td style="padding:3px;">Discount:</td>
          <td style="text-align:right; padding:3px;">${OVERRIDE.EDI.invoiceSummary.discount}</td>
        </tr>
        </#if>
        <#if OVERRIDE.EDI.invoiceSummary.shipping?has_content && OVERRIDE.EDI.invoiceSummary.shipping != "$0.00">
        <tr>
          <td style="padding:3px;">Shipping:</td>
          <td style="text-align:right; padding:3px;">${OVERRIDE.EDI.invoiceSummary.shipping}</td>
        </tr>
        </#if>
        <#if OVERRIDE.EDI.invoiceSummary.tax?has_content && OVERRIDE.EDI.invoiceSummary.tax != "$0.00">
        <tr>
          <td style="padding:3px;">Tax:</td>
          <td style="text-align:right; padding:3px;">${OVERRIDE.EDI.invoiceSummary.tax}</td>
        </tr>
        </#if>
        <tr style="border-top:2px solid #000;">
          <td style="padding:5px 3px; font-weight:bold; font-size:12px;">TOTAL:</td>
          <td style="text-align:right; padding:5px 3px; font-weight:bold; font-size:12px;">
            ${OVERRIDE.EDI.invoiceSummary.totalAmount!""}
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>

<!-- PAYMENT TERMS -->
<#if OVERRIDE.EDI.paymentTerms?? && OVERRIDE.EDI.paymentTerms.description?has_content>
<table style="width:100%; margin-top:15px;">
  <tr>
    <td style="font-size:12px; font-weight:bold; padding-bottom:8px; border-bottom:1px solid #000;">
      Payment Terms
    </td>
  </tr>
</table>

<table style="width:100%; margin-top:10px;">
  <tr>
    <td>
      <table>
        <tr><td style="padding-bottom:4px;">${OVERRIDE.EDI.paymentTerms.description!""}</td></tr>
        <#if OVERRIDE.EDI.paymentTerms.netDays??>
        <tr><td style="padding-bottom:4px;">Net ${OVERRIDE.EDI.paymentTerms.netDays} days</td></tr>
        </#if>
        <#if OVERRIDE.EDI.paymentTerms.dueDate?has_content>
        <tr><td>Due Date: ${OVERRIDE.EDI.paymentTerms.dueDate}</td></tr>
        </#if>
      </table>
    </td>
  </tr>
</table>
</#if>

<!-- TECHNICAL DETAILS (FOOTER) -->
<table style="width:100%; margin-top:20px; border-top:1px solid #ccc;">
  <tr>
    <td style="padding-top:5px; font-size:8px; color:#666;">
      Control Number: ${OVERRIDE.EDI.technicalDetails.controlNumber!""}
      <#if OVERRIDE.EDI.technicalDetails.testIndicator?? && OVERRIDE.EDI.technicalDetails.testIndicator == "T">
        | <span style="color:red;">TEST DOCUMENT</span>
      </#if>
    </td>
    <td style="text-align:right; padding-top:5px; font-size:8px; color:#666;">
      Generated by CRE2 Framework
    </td>
  </tr>
</table>

</body>
</html>
```

## Partner-Specific Templates

When creating templates for specific trading partners, consider:

### 1. Logo DPI Differences

```html
<!-- Generic template: standard logo size -->
<img src="${tradingPartnerLogo}" dpi="400" />

<!-- Rocky Brands: large source image needs higher DPI -->
<img src="${tradingPartnerLogo}" dpi="2000" />

<!-- Small partner logo: lower DPI -->
<img src="${tradingPartnerLogo}" dpi="200" />
```

### 2. Custom Branding

```html
<!-- Partner-specific colors -->
<#if OVERRIDE.EDI.partnerName?contains("Rocky")>
  <tr style="background-color:#8B4513;">  <!-- Brown for Rocky -->
<#else>
  <tr style="background-color:#1a3a5c;">  <!-- Default blue -->
</#if>
```

### 3. Additional Fields

Some partners require extra information:

```html
<!-- Vendor number (some partners require this) -->
<#if OVERRIDE.EDI.vendorNumber?has_content>
<tr>
  <td style="font-weight:bold; padding:2px;">Vendor #:</td>
  <td style="text-align:right; padding:2px;">${OVERRIDE.EDI.vendorNumber}</td>
</tr>
</#if>

<!-- Department number -->
<#if OVERRIDE.EDI.departmentNumber?has_content>
<tr>
  <td style="font-weight:bold; padding:2px;">Dept #:</td>
  <td style="text-align:right; padding:2px;">${OVERRIDE.EDI.departmentNumber}</td>
</tr>
</#if>
```

## Reusable Macros

### Address Block Macro

```html
<#macro addressBlock partner showType=true>
<table>
  <#if showType>
  <tr><td style="font-weight:bold; padding-bottom:4px;">${partner.type}</td></tr>
  </#if>
  <tr><td style="padding-bottom:2px;">${partner.name!""}</td></tr>
  <tr><td style="padding-bottom:2px;">${partner.address!""}</td></tr>
  <#if partner.address2?has_content>
  <tr><td style="padding-bottom:2px;">${partner.address2}</td></tr>
  </#if>
  <tr><td>${partner.city!""}, ${partner.state!""} ${partner.zip!""}</td></tr>
  <#if partner.country?has_content && partner.country != "US">
  <tr><td>${partner.country}</td></tr>
  </#if>
</table>
</#macro>

<!-- Usage -->
<@addressBlock partner=billTo />
<@addressBlock partner=shipTo showType=false />
```

### Summary Row Macro

```html
<#macro summaryRow label value bold=false showIfZero=false>
<#if value?has_content && (showIfZero || value != "$0.00")>
<tr>
  <td style="padding:3px;<#if bold>font-weight:bold;</#if>">${label}:</td>
  <td style="text-align:right; padding:3px;<#if bold>font-weight:bold;</#if>">${value}</td>
</tr>
</#if>
</#macro>

<!-- Usage -->
<@summaryRow label="Subtotal" value=invoiceSummary.subtotal />
<@summaryRow label="Discount" value=invoiceSummary.discount />
<@summaryRow label="TOTAL" value=invoiceSummary.totalAmount bold=true />
```

### Badge/Status Macro

```html
<#macro statusBadge status>
<span style="
  padding:2px 6px;
  border-radius:3px;
  font-size:9px;
  font-weight:bold;
  <#if status == "Accepted">
    background-color:#d4edda; color:#155724;
  <#elseif status == "Rejected">
    background-color:#f8d7da; color:#721c24;
  <#elseif status == "Backordered">
    background-color:#fff3cd; color:#856404;
  <#else>
    background-color:#e2e3e5; color:#383d41;
  </#if>
">${status}</span>
</#macro>

<!-- Usage in 855 Acknowledgment -->
<td><@statusBadge status=line.status /></td>
```

## Template Validation Checklist

Before deploying a template:

- [ ] All `&` in URLs escaped as `&amp;`
- [ ] All images use `dpi` attribute (not `height`)
- [ ] All styles are inline (no CSS classes)
- [ ] All tables have proper closing tags
- [ ] All `<br>` tags are self-closing `<br/>`
- [ ] All variables have null checks or defaults
- [ ] Template renders without FreeMarker errors
- [ ] PDF opens without BFO errors
- [ ] Logo aspect ratios are correct
- [ ] Text doesn't overlap
- [ ] Tables don't overflow page width
- [ ] Debug elements removed for production

## Testing Templates

### Using CRE2 Debug Mode

```bash
# Show what data the template receives
python3 cre2_render.py debug --profile-id 17 --record-id 12345 --env sb2

# Validate template syntax
python3 validate_template.py ./template.html
```

### Common Test Cases

1. **Missing optional fields** - Verify null checks work
2. **Long text** - Check truncation/wrapping
3. **Many line items** - Verify pagination
4. **Zero amounts** - Check conditional display
5. **Missing logos** - Verify fallback behavior
6. **Special characters** - Test `&`, `<`, `>` handling
