# BFO FreeMarker Gotchas (NetSuite PDF Engine)

NetSuite uses Big Faceless Organization (BFO) as its PDF rendering engine. BFO's FreeMarker implementation differs from Apache FreeMarker in several critical ways that cause silent failures.

**Last updated**: 2026-01-27
**Source**: Empirically discovered during CRE2 EDI template consolidation (850, 855, 860 debugging)

---

## Table of Contents

1. [Empty String Handling](#1-empty-string-handling)
2. [?trim Fails on Numeric-Looking Strings](#2-trim-fails-on-numeric-looking-strings)
3. [The Delete Pattern (Recommended Solution)](#3-the-delete-pattern-recommended-solution)
4. [Layout Rules](#4-layout-rules)
5. [Logo and Image Sizing](#5-logo-and-image-sizing)
6. [Conditional Guard Patterns](#6-conditional-guard-patterns)
7. [Unsupported CSS Properties](#7-unsupported-css-properties)
8. [Numeric Zero Guard Trap](#8-numeric-zero-guard-trap)
9. [Table Column Width Control](#9-table-column-width-control)
10. [Clickable Image Links](#10-clickable-image-links)
11. [Quick Reference Table](#11-quick-reference-table)

---

## 1. Empty String Handling

**BFO behavior**: `?has_content` on an empty string `""` returns **TRUE**.

In standard Apache FreeMarker, `?has_content` returns false for null, undefined, and empty strings. BFO treats empty strings as "having content."

```freemarker
<#-- Apache FreeMarker: FALSE (correct) -->
<#-- BFO FreeMarker:   TRUE  (unexpected) -->
<#assign val = "">
<#if val?has_content>
    This WILL render in BFO even though val is ""
</#if>
```

**Impact**: Sections guarded by `?has_content` still render when the value is an empty string, showing empty fields or empty section headings.

**Workaround**: Don't rely on `?has_content` to filter empty strings. Use the Delete Pattern (Section 3) instead.

---

## 2. ?trim Fails on Numeric-Looking Strings

**BFO behavior**: `?trim` silently fails on strings that look numeric (e.g., `"006"`, `"123"`), causing the entire conditional expression to evaluate as **false**.

```freemarker
<#-- This works in Apache FreeMarker but FAILS SILENTLY in BFO -->
<#assign code = "006">
<#if code?? && code?trim?length gt 0>
    This will NOT render in BFO! "006" causes ?trim to fail silently.
</#if>
```

**Impact**: Legitimate values like carrier codes (`"006"`), zip codes (`"00601"`), or any numeric-looking string become invisible.

**Why it happens**: BFO likely attempts numeric coercion on the trimmed result before checking length, and the coercion path loses the string.

**Workaround**: Never use `?trim?length > 0` as a conditional guard. Use the Delete Pattern (Section 3) instead.

---

## 3. The Delete Pattern (Recommended Solution)

The definitive solution for empty value handling in BFO is to **delete empty properties from the JavaScript data object** in the data extractor, so FreeMarker's `??` (exists check) returns false for truly empty values.

### In the Data Extractor (JavaScript)

```javascript
// After populating an object, delete any empty string properties
var fields = ['fobMethod', 'fobOrigin', 'fobDestination', 'carrierCode', 'routingCode'];
for (var i = 0; i < fields.length; i++) {
    if (!result.shippingDetails[fields[i]]) {
        delete result.shippingDetails[fields[i]];
    }
}
```

This converts `{ carrierCode: "006", fobMethod: "" }` into `{ carrierCode: "006" }`.

### In the FreeMarker Template

```freemarker
<#-- Now ?? reliably returns false for deleted properties -->
<#if OVERRIDE.EDI.shippingDetails.fobMethod??>
    <tr><td>FOB Method:</td><td>${OVERRIDE.EDI.shippingDetails.fobMethod}</td></tr>
</#if>

<#-- For section-level guards, check multiple fields with || -->
<#if (OVERRIDE.EDI.shippingDetails.carrierCode??) || (OVERRIDE.EDI.shippingDetails.fobMethod??)>
    <h3>Shipping Details</h3>
    ...
</#if>
```

### Why This Works

| Check | Empty string `""` | Deleted/undefined |
|-------|-------------------|-------------------|
| `??` | TRUE | **FALSE** |
| `?has_content` | TRUE (BFO bug) | FALSE |
| `?trim?length > 0` | Unreliable | FALSE |

By deleting empty properties, `??` becomes the reliable check — it only returns true when the property actually exists with a real value.

---

## 4. Layout Rules

### Use Pure `<table>` Layout

BFO's page-break handling works with `<table>` elements but breaks with `<div>` wrappers.

```html
<!-- WRONG: div wrappers break across pages -->
<div class="section">
    <h3>Section Title</h3>
    <table>...</table>
</div>

<!-- CORRECT: pure table layout, BFO handles page breaks -->
<table style="width:100%; border-collapse:collapse;">
    <tr>
        <td colspan="4" style="background-color:#1B4F72; padding:6px;">
            <b style="color:white;">Section Title</b>
        </td>
    </tr>
    <tr>
        <td>Field 1:</td><td>Value 1</td>
        <td>Field 2:</td><td>Value 2</td>
    </tr>
</table>
```

### Header Height

Use `header-height="75px"` (not `60px`) for headers with dual logos (company + trading partner). 60px causes logo overlap with body content.

### Body Element

```html
<body header="nlheader" header-height="75px"
      footer="nlfooter" footer-height="40px"
      padding="0.5in 0.5in 0.5in 0.5in" size="Letter">
```

---

## 5. Logo and Image Sizing

### DPI Controls Size, Not CSS

In BFO, the `dpi` attribute on `<img>` controls rendered size. CSS `max-width`/`max-height` **conflicts** with DPI and produces unpredictable results.

```html
<!-- WRONG: CSS conflicts with DPI -->
<img src="${logo}" dpi="400" style="max-width:150px; max-height:50px;" />

<!-- CORRECT: DPI only, no CSS size constraints -->
<img src="${logo}" dpi="400" />
```

### DPI Values and Image Size

Lower DPI = larger rendered image. Higher DPI = smaller rendered image.

| Source Image | DPI | Result |
|-------------|-----|--------|
| Small (100x50px) | 200 | Normal size |
| Small (100x50px) | 2000 | Tiny (nearly invisible) |
| Large (2000x1000px) | 200 | Huge (overflows page) |
| Large (2000x1000px) | 2000 | Normal size |

### Data-Driven DPI Pattern

For consolidated templates serving multiple trading partners with different logo sizes:

**JavaScript (data extractor):**
```javascript
var TP_LOGO_DPI_MAP = {
    'Runnings': '200',      // Small source image
    'Academy': '800',       // Medium source image
    'Bomgaars': '800',
    // Partners not listed default to 2000
};
var DEFAULT_LOGO_DPI = '2000';

result.tpLogoDpi = TP_LOGO_DPI_MAP[tpName] || DEFAULT_LOGO_DPI;
```

**FreeMarker (template):**
```freemarker
<img src="${OVERRIDE.EDI.tradingPartnerLogo}"
     dpi="${OVERRIDE.EDI.tpLogoDpi!'2000'}" />
```

---

## 6. Conditional Guard Patterns

### Safe Patterns

```freemarker
<#-- SAFE: Check existence after delete cleanup in JS -->
<#if val??>
    ${val}
</#if>

<#-- SAFE: Existence + has_content (belt and suspenders, works after delete) -->
<#if val?? && val?has_content>
    ${val}
</#if>

<#-- SAFE: Default value operator -->
${val!'N/A'}
```

### Unsafe Patterns

```freemarker
<#-- UNSAFE: ?has_content alone (passes for empty strings in BFO) -->
<#if val?has_content>
    ${val}
</#if>

<#-- UNSAFE: ?trim on potentially numeric values -->
<#if val?? && val?trim?length gt 0>
    ${val}
</#if>

<#-- UNSAFE: Comparing to empty string (unreliable in BFO) -->
<#if val != "">
    ${val}
</#if>
```

---

## 7. Unsupported CSS Properties

**BFO behavior**: Many CSS properties that work in browsers are silently ignored by BFO. The element renders but the CSS has no effect — no error, no warning.

### `display: table` / `display: table-cell`

BFO does **not** support CSS `display: table`, `display: table-cell`, or `display: table-row`. Elements styled this way render as plain blocks with no table layout.

```html
<!-- WRONG: BFO ignores display:table-cell, content stacks vertically or disappears -->
<div style="display: table; width: 100%;">
    <div style="display: table-cell; width: 25%; text-align: center;">
        <span>Label</span><br/><b>Value</b>
    </div>
    <div style="display: table-cell; width: 25%; text-align: center;">
        <span>Label</span><br/><b>Value</b>
    </div>
</div>

<!-- CORRECT: Use actual table elements -->
<table style="width:100%; border-collapse:collapse;">
    <tr>
        <td style="width:25%; text-align:center;">
            <span>Label</span><br/><b>Value</b>
        </td>
        <td style="width:25%; text-align:center;">
            <span>Label</span><br/><b>Value</b>
        </td>
    </tr>
</table>
```

**Impact**: A styled `<div>` box (background, border) renders visibly but its internal layout is broken — content may be invisible or improperly positioned. This creates "empty boxes" in the PDF.

### Other Unsupported CSS

| CSS Property | BFO Support | Workaround |
|-------------|-------------|------------|
| `display: table/table-cell` | ❌ Ignored | Use actual `<table>/<td>` |
| `display: flex` | ❌ Ignored | Use `<table>` layout |
| `display: grid` | ❌ Ignored | Use `<table>` layout |
| `border-radius` | ⚠️ Partial | Works on some elements |
| `box-shadow` | ❌ Ignored | No workaround |
| `max-width`/`max-height` on `<img>` | ⚠️ Conflicts with DPI | Use `dpi` attribute only |

**Rule of thumb**: If it needs a layout, use `<table>`. BFO is a table-layout engine.

---

## 8. Numeric Zero Guard Trap

**BFO behavior**: Both `??` and `?has_content` return **TRUE** for numeric `0` values. This is standard FreeMarker behavior, not a BFO-specific bug — but it creates a trap when the data extractor always populates numeric fields.

### The Problem

When the JS data extractor always creates an object with numeric fields (even when no real data exists), FreeMarker guards pass for zero values:

```javascript
// Data extractor ALWAYS creates this, even when no 855 line data exists:
result.ackSummary = {
    totalLines: 0,       // ← numeric 0
    linesAccepted: 0,
    linesRejected: 0,
    linesModified: 0
};
```

```freemarker
<#-- WRONG: Both checks pass for numeric 0 -->
<#if OVERRIDE.EDI.ackSummary??>           <#-- TRUE: object exists -->
<#if OVERRIDE.EDI.ackSummary.totalLines?has_content>  <#-- TRUE: 0 "has content" -->
    <!-- This renders an empty summary box! -->
</#if>
```

### The Fix

Use explicit numeric comparison for guard conditions on numeric fields:

```freemarker
<#-- CORRECT: Numeric comparison catches zero -->
<#if OVERRIDE.EDI.ackSummary?? && OVERRIDE.EDI.ackSummary.totalLines?? && (OVERRIDE.EDI.ackSummary.totalLines > 0)>
    <!-- Only renders when actual data exists -->
</#if>
```

### When This Applies

- `ackSummary.totalLines` on 855 templates (always 0 when no acknowledgment data)
- Any counter/sum field that defaults to 0 in the data extractor
- Any section guard based on a numeric field value

**Rule**: For numeric fields, never rely on `??` or `?has_content` alone — always add `> 0` (or appropriate threshold).

---

## 9. Table Column Width Control

**BFO behavior**: BFO respects `<colgroup>` and `<col>` elements for controlling table column widths. This is the most reliable way to prevent text overlap in tables with many columns.

### The Problem

When table cells contain long text (e.g., "Unit Price", long item descriptions), BFO may not allocate column widths proportionally, causing text overlap.

### The Fix

Use `<colgroup>` at the top of the table to enforce explicit column widths:

```html
<table style="width:100%; border-collapse:collapse; table-layout:fixed;">
    <colgroup>
        <col style="width:5%"/>   <!-- Line # -->
        <col style="width:12%"/>  <!-- UPC -->
        <col style="width:12%"/>  <!-- Buyer SKU -->
        <col style="width:12%"/>  <!-- Vendor SKU -->
        <col style="width:25%"/>  <!-- Description -->
        <col style="width:7%"/>   <!-- Qty -->
        <col style="width:5%"/>   <!-- UOM -->
        <col style="width:11%"/> <!-- Price -->
        <col style="width:11%"/> <!-- Total -->
    </colgroup>
    <thead>...</thead>
    <tbody>...</tbody>
</table>
```

### Tips

- Always pair `<colgroup>` with `table-layout: fixed` for predictable widths
- Column widths should sum to 100%
- Shorten column header text when space is tight (e.g., "Unit Price" → "Price", "Line Total" → "Total")
- Use `word-wrap: break-word` on `<td>` for long content that must fit

---

## 10. Clickable Image Links

**BFO behavior**: Standard HTML `<a><img/></a>` syntax does **NOT** create clickable images. The image renders but is not clickable — no error, no warning.

### The Problem

```html
<!-- WRONG: Image is NOT clickable in BFO PDF -->
<a href="https://example.com"><img src="button.png" /></a>

<!-- ALSO WRONG: Even with simple URLs -->
<a href="https://www.google.com"><img src="button.png" /></a>
```

### The Fix

Use BFO-specific `href` attribute **directly on the `<img>` tag**:

```html
<!-- CORRECT: href on img tag (BFO-specific syntax) -->
<img href="https://example.com" src="button.png" border="0" />
```

### With FreeMarker Variables

FreeMarker variables work in the `href` attribute:

```html
<#assign payment_url = "https://example.com/pay?customerId=">
<img href="${payment_url}${record.id}" src="pay-button.png" border="0" style="width:2in;" />
```

### Important Notes

- Always include `border="0"` to remove default image border
- This syntax only works in BFO PDF contexts (Advanced PDF/HTML Templates, CRE2)
- Text links using `<a>` still work normally; this limitation is specific to images
- The `href` attribute on `<img>` is non-standard HTML but required for BFO

**Source**: NetSuite SuiteAnswers article "Use image as a hyperlink to website in Advanced PDF/HTML Template"

---

## 11. Quick Reference Table

| Scenario | BFO Behavior | Solution |
|----------|-------------|----------|
| Empty string `""` with `?has_content` | Returns TRUE | Delete property in JS extractor |
| `?trim` on `"006"` | Silent failure, evaluates false | Never use `?trim` in conditionals |
| `<div>` section wrappers | Break across page boundaries | Use pure `<table>` layout |
| CSS `max-width` + `dpi` on images | Unpredictable sizing | Use `dpi` only, no CSS constraints |
| `header-height="60px"` with dual logos | Logo overlaps body | Use `header-height="75px"` |
| Conditional on lookup map values | Silently evaluates false | Use direct output with `!default` |
| `display: table-cell` CSS | Silently ignored | Use actual `<table>/<td>` elements |
| `display: flex` / `display: grid` | Silently ignored | Use `<table>` layout |
| `??` / `?has_content` on numeric `0` | Returns TRUE | Use explicit `> 0` comparison |
| Table columns overlapping | Auto-width miscalculated | Use `<colgroup>` with `table-layout: fixed` |
| `<a><img/></a>` for clickable image | Image not clickable | Use `href` attribute directly on `<img>` tag |

---

## 12. Testing Checklist for BFO Templates

When developing or modifying CRE2 PDF templates:

1. [ ] All empty string properties deleted in JS extractor (not relying on FreeMarker checks)
2. [ ] No `?trim` used in conditional guards
3. [ ] No CSS size constraints on `<img>` tags (DPI only)
4. [ ] Pure `<table>` layout (no `<div>` section wrappers)
5. [ ] `header-height="75px"` for dual-logo headers
6. [ ] Test with sparse data partner (e.g., Amazon) — verify empty sections hide
7. [ ] Test with data-rich partner (e.g., Cavenders) — verify all fields display
8. [ ] Test with small-logo partner (e.g., Runnings, DPI 200) — verify logo not tiny/huge
9. [ ] No `display: table`, `display: table-cell`, `display: flex`, or `display: grid` CSS
10. [ ] Numeric guard fields use `> 0` comparison (not just `??` or `?has_content`)
11. [ ] Multi-column tables use `<colgroup>` with `table-layout: fixed` to prevent overlap
12. [ ] Image links use `href` attribute on `<img>` tag (not `<a>` wrapper)
