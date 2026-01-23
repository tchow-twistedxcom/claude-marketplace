# BFO PDF Renderer Compatibility Guide

NetSuite uses the Big Faceless Organization (BFO) PDF generator for rendering HTML templates to PDF. This guide documents known quirks and workarounds discovered during template development.

## Quick Reference: Common Issues & Fixes

| Issue | Wrong Approach | Correct Approach |
|-------|---------------|------------------|
| Logo distorted | `height="50"` | `dpi="400"` |
| Lines overlapping | `<br/>` | Table with `padding-bottom` |
| Section overlap | CSS margin on div | Table with `margin-top` |
| Ampersand in URL | `&` | `&amp;` |
| Font not rendering | CSS class | Inline `style` attribute |

## Image Handling

### The DPI Solution

BFO distorts images when using `height` or `width` attributes. Use `dpi` instead.

```html
<!-- ❌ WRONG: Image will be distorted -->
<img src="${logoUrl}" height="50" />

<!-- ✅ CORRECT: Image maintains aspect ratio -->
<img src="${logoUrl}" dpi="400" />
```

### DPI Value Guidelines

The DPI value is **inversely proportional** to rendered size:
- **Higher DPI = Smaller rendered image**
- **Lower DPI = Larger rendered image**

| Source Image Size | Recommended DPI | Approximate Rendered Height |
|-------------------|-----------------|----------------------------|
| 100x100 px | 150 | ~67px |
| 200x200 px | 200 | ~100px |
| 500x500 px | 400 | ~125px |
| 1000x1000 px | 1000-2000 | ~50-100px |

### Trading Partner Logo Sizing

Different trading partners may have different logo sizes. Create partner-specific templates when logo DPI varies significantly.

```html
<!-- Generic template -->
<img src="${tradingPartnerLogo}" dpi="400" />

<!-- Rocky Brands specific (large source image) -->
<img src="${tradingPartnerLogo}" dpi="2000" />
```

### URL Escaping

Always escape ampersands in image URLs:

```html
<!-- ❌ WRONG: Will break XML parsing -->
<img src="/core/media/media.nl?id=36100&c=4138030" />

<!-- ✅ CORRECT: Properly escaped -->
<img src="/core/media/media.nl?id=36100&amp;c=4138030" />
```

## Layout and Spacing

### Vertical Spacing Between Lines

BFO does not reliably handle `<br/>` tags for spacing. Use tables instead.

```html
<!-- ❌ WRONG: Lines may overlap -->
<div>
  Line 1<br/>
  Line 2<br/>
  Line 3
</div>

<!-- ✅ CORRECT: Consistent spacing -->
<table>
  <tr><td style="padding-bottom:4px;">Line 1</td></tr>
  <tr><td style="padding-bottom:4px;">Line 2</td></tr>
  <tr><td>Line 3</td></tr>
</table>
```

### Section Spacing

CSS margins on `<div>` elements are unreliable. Wrap sections in tables.

```html
<!-- ❌ WRONG: Margin may not be respected -->
<div style="margin-top:15px;">
  Payment Terms Section
</div>

<!-- ✅ CORRECT: Table margin works reliably -->
<table style="width:100%; margin-top:15px;">
  <tr><td>Payment Terms Section</td></tr>
</table>
```

### Multi-Column Layouts

Use nested tables for side-by-side content:

```html
<table style="width:100%;">
  <tr>
    <td style="width:50%; vertical-align:top;">
      <!-- Left column content -->
    </td>
    <td style="width:50%; vertical-align:top;">
      <!-- Right column content -->
    </td>
  </tr>
</table>
```

### Header with Logos and Title

```html
<table style="width:100%;">
  <tr>
    <!-- Left logo -->
    <td style="width:25%; vertical-align:top;">
      <img src="${twistedXLogo}" dpi="400" />
    </td>

    <!-- Center title -->
    <td style="width:50%; text-align:center; vertical-align:middle;">
      <table style="margin:0 auto;">
        <tr><td style="padding-bottom:4px;">
          <span style="font-size:18px; font-weight:bold;">
            810 INVOICE
          </span>
        </td></tr>
        <tr><td>
          <span style="font-size:14px;">
            ${partnerName}
          </span>
        </td></tr>
      </table>
    </td>

    <!-- Right logo -->
    <td style="width:25%; text-align:right; vertical-align:top;">
      <img src="${tradingPartnerLogo}" dpi="400" />
    </td>
  </tr>
</table>
```

## Styling

### Inline Styles Only

BFO has limited CSS support. Always use inline styles:

```html
<!-- ❌ WRONG: CSS classes may not work -->
<style>
  .header { font-size: 18px; font-weight: bold; }
</style>
<span class="header">Title</span>

<!-- ✅ CORRECT: Inline styles always work -->
<span style="font-size:18px; font-weight:bold;">Title</span>
```

### Supported CSS Properties

| Property | Support | Notes |
|----------|---------|-------|
| `font-size` | ✅ Full | Use px or pt |
| `font-weight` | ✅ Full | bold, normal |
| `font-family` | ⚠️ Limited | Stick to Arial, Helvetica, Times |
| `color` | ✅ Full | Hex or named colors |
| `background-color` | ✅ Full | |
| `text-align` | ✅ Full | left, center, right |
| `vertical-align` | ✅ Full | top, middle, bottom |
| `padding` | ✅ Full | All sides |
| `margin` | ⚠️ Limited | Works on tables, not divs |
| `border` | ✅ Full | Shorthand supported |
| `width` | ✅ Full | px, %, auto |
| `height` | ⚠️ Limited | May not work on images |

### Font Recommendations

```html
<!-- Safe font stack -->
<span style="font-family: Arial, Helvetica, sans-serif;">Text</span>

<!-- Monospace for codes/numbers -->
<span style="font-family: Courier, monospace;">INV123456</span>
```

## Tables

### Border Styles

```html
<!-- Full border -->
<table style="border:1px solid #000; border-collapse:collapse;">
  <tr>
    <td style="border:1px solid #000; padding:5px;">Cell</td>
  </tr>
</table>

<!-- Header row with background -->
<table style="width:100%; border-collapse:collapse;">
  <tr style="background-color:#f0f0f0;">
    <th style="border:1px solid #000; padding:5px; text-align:left;">Header</th>
  </tr>
  <tr>
    <td style="border:1px solid #000; padding:5px;">Data</td>
  </tr>
</table>
```

### Cell Alignment

```html
<!-- Right-align numbers -->
<td style="text-align:right; padding:5px;">$1,234.56</td>

<!-- Center-align status -->
<td style="text-align:center; padding:5px;">Shipped</td>

<!-- Top-align multiline content -->
<td style="vertical-align:top; padding:5px;">
  Line 1<br/>
  Line 2
</td>
```

## Page Breaks

```html
<!-- Force page break before element -->
<div style="page-break-before:always;"></div>

<!-- Keep content together (avoid breaking inside) -->
<table style="page-break-inside:avoid;">
  <!-- Important content that should stay together -->
</table>
```

## Debugging Tips

### 1. Add Visible Borders

Temporarily add borders to diagnose layout issues:

```html
<table style="border:1px solid red;">
  <tr>
    <td style="border:1px solid blue;">Content</td>
  </tr>
</table>
```

### 2. Use Background Colors

Identify element boundaries:

```html
<td style="background-color:#ffff00;">Debug this cell</td>
```

### 3. Check XML Validity

BFO requires valid XHTML. Common issues:
- Unclosed tags: `<br>` should be `<br/>`
- Unescaped ampersands: `&` should be `&amp;`
- Missing quotes: `style=width:100%` should be `style="width:100%"`

### 4. Test with CRE2 Debug Mode

Use `cre2_render.py debug` to see template data:

```bash
python3 cre2_render.py debug --profile-id 17 --record-id 12345 --env sb2
```

## Common Patterns

### Summary Box

```html
<table style="border:2px solid #000; padding:10px; width:300px;">
  <tr>
    <td style="padding:3px;">
      <table style="width:100%;">
        <tr>
          <td style="font-weight:bold;">Invoice #:</td>
          <td style="text-align:right;">${invoiceNumber}</td>
        </tr>
        <tr>
          <td style="font-weight:bold;">Date:</td>
          <td style="text-align:right;">${invoiceDate}</td>
        </tr>
        <tr>
          <td style="font-weight:bold;">Total:</td>
          <td style="text-align:right; font-weight:bold; font-size:14px;">
            ${totalAmount}
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
```

### Address Block

```html
<table>
  <tr><td style="font-weight:bold; padding-bottom:4px;">${addressType}</td></tr>
  <tr><td style="padding-bottom:2px;">${name}</td></tr>
  <tr><td style="padding-bottom:2px;">${address}</td></tr>
  <tr><td>${city}, ${state} ${zip}</td></tr>
</table>
```

### Line Items Table

```html
<table style="width:100%; border-collapse:collapse; margin-top:15px;">
  <tr style="background-color:#e0e0e0;">
    <th style="border:1px solid #000; padding:5px; text-align:left;">Item</th>
    <th style="border:1px solid #000; padding:5px; text-align:left;">Description</th>
    <th style="border:1px solid #000; padding:5px; text-align:right;">Qty</th>
    <th style="border:1px solid #000; padding:5px; text-align:right;">Price</th>
    <th style="border:1px solid #000; padding:5px; text-align:right;">Total</th>
  </tr>
  <#list invoiceDetails as line>
  <tr>
    <td style="border:1px solid #000; padding:5px;">${line.itemNumber}</td>
    <td style="border:1px solid #000; padding:5px;">${line.description}</td>
    <td style="border:1px solid #000; padding:5px; text-align:right;">${line.quantity}</td>
    <td style="border:1px solid #000; padding:5px; text-align:right;">${line.unitPrice}</td>
    <td style="border:1px solid #000; padding:5px; text-align:right;">${line.totalPrice}</td>
  </tr>
  </#list>
</table>
```
