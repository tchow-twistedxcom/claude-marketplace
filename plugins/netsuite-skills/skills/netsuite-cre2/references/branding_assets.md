# Twisted X Branding Assets Reference

This document provides a central reference for Twisted X branding assets used in NetSuite templates, organized by context and use case.

---

## Logo Files by Context

Different templates use different logo files. Always use the correct one for your context.

| Context | Asset | File ID | Dimensions | Notes |
|---------|-------|---------|------------|-------|
| **Email Templates** | Main Logo | 20634688 | 300x100 | White logo on dark header |
| **Email Templates** | Banner | 47017000 | 600x auto | "The Original Driving Moc" |
| **EDI Documents** | EDI Logo | 57049 | 300x100 | PDF invoices, packing slips |
| **Item Fulfillment** | Ship Logo | 57049 | 300x100 | Shipping documents |
| **Statements** | Statement Logo | 57049 | 300x100 | Customer statements |

### When to Use Which

| Template Type | Logo ID | Banner ID |
|--------------|---------|-----------|
| SO Confirmation Email | 20634688 | 47017000 |
| Invoice Email | 20634688 | 47017000 |
| Shipping Notification | 20634688 | 47017000 |
| EDI 810 (Invoice PDF) | 57049 | N/A |
| EDI 850 (PO Ack PDF) | 57049 | N/A |
| Customer Statement | 57049 | N/A |

---

## Social Media Icons

| Platform | File ID | Size | Usage |
|----------|---------|------|-------|
| Instagram | 57140 | 20x20 | Email footers |
| Facebook | 57139 | 20x20 | Email footers |
| Twitter | 57141 | 20x20 | Email footers (if used) |

### Social Footer Pattern

```html
<ul style="list-style-type: none; text-align: center; margin: 0; padding: 0;">
  <li style="display: inline; padding: 0px 10px;">
    <a href="https://www.instagram.com/twistedx/" target="_blank">
      <img alt="instagram" border="0" height="20" width="20"
           src="https://4138030.app.netsuite.com/core/media/media.nl?id=57140&c=4138030&h=NqkTMYjgt8Lj6sd5K0Jg2NXGV-R7Zuxvz73ca7E3XloIzc1n" />
    </a>
  </li>
  <li style="display: inline; padding: 0px 10px;">
    <a href="https://www.facebook.com/twistedxofficial" target="_blank">
      <img alt="facebook" border="0" height="20" width="20"
           src="https://4138030.app.netsuite.com/core/media/media.nl?id=57139&c=4138030&h=zUFYjQO-cN_Hpo0lek4WdYSdPRXCz6a3BpPRK84Ok_1eif3-" />
    </a>
  </li>
</ul>
```

---

## External URL Format

All images in emails **MUST** use external URLs with security hash.

### URL Structure

```
https://4138030.app.netsuite.com/core/media/media.nl?id=<FILE_ID>&c=4138030&h=<HASH>
```

| Parameter | Value | Description |
|-----------|-------|-------------|
| Base URL | `https://4138030.app.netsuite.com` | NetSuite domain |
| Path | `/core/media/media.nl` | File serving endpoint |
| `id` | File internal ID | e.g., 20634688 |
| `c` | Company ID | Always `4138030` for Twisted X |
| `h` | Security hash | Required for external access |

### Complete URLs Reference

**Email Logo (20634688):**
```
https://4138030.app.netsuite.com/core/media/media.nl?id=20634688&c=4138030&h=JMQE5iAkIjWMFFjcIAPJZhvSC9sFSlCEkSEgk3KW5u8-pZD6
```

**Email Banner (47017000):**
```
https://4138030.app.netsuite.com/core/media/media.nl?id=47017000&c=4138030&h=OyRQqRvid_67HBtn89ZFDSgjYbYtqcXEHS8WsygYaCd8_l1I
```

**Instagram Icon (57140):**
```
https://4138030.app.netsuite.com/core/media/media.nl?id=57140&c=4138030&h=NqkTMYjgt8Lj6sd5K0Jg2NXGV-R7Zuxvz73ca7E3XloIzc1n
```

**Facebook Icon (57139):**
```
https://4138030.app.netsuite.com/core/media/media.nl?id=57139&c=4138030&h=zUFYjQO-cN_Hpo0lek4WdYSdPRXCz6a3BpPRK84Ok_1eif3-
```

---

## Getting Image Hash

If you need the hash for a file, query the File Cabinet:

```bash
python3 query_netsuite.py "
  SELECT id, name, url
  FROM file
  WHERE id = 20634688
" --env prod --format json
```

The `url` field contains the complete external URL with hash.

---

## Color Scheme

### Primary Colors

| Element | Color | Hex | Usage |
|---------|-------|-----|-------|
| Dark Navy | #242f46 | Header/Footer background |
| White | #ffffff | Content background |
| Light Gray | #eeeeee | Outer background, title bars |
| Twisted X Red | #c41e3a | Accent, CTA buttons |
| Text Dark | #333333 | Body text |
| Text Light | #ffffff | Text on dark backgrounds |

### Usage by Section

| Section | Background | Text |
|---------|------------|------|
| Header | #242f46 | #ffffff |
| Banner | N/A (image) | N/A |
| Title Bar | #eeeeee | #242f46 |
| Content | #ffffff | #333333 |
| CTA Button | #c41e3a | #ffffff |
| Footer | #242f46 | #ffffff |
| Outer Wrapper | #eeeeee | N/A |

### Color CSS Snippets

```css
/* Header */
background-color: #242f46;
color: #ffffff;

/* Content */
background-color: #ffffff;
color: #333333;

/* Title Bar */
background-color: #eeeeee;
color: #242f46;
font-weight: 800;

/* CTA Button */
background-color: #c41e3a;
color: #ffffff;
font-weight: 700;

/* Footer */
background-color: #242f46;
color: #ffffff;
```

---

## Typography

### Font Stack

```css
font-family: 'Open Sans', Helvetica, Arial, sans-serif;
```

### Font Sizes

| Element | Size | Weight | Line Height |
|---------|------|--------|-------------|
| Title | 18px | 800 | 24px |
| Body | 14px | 400 | 24px-26px |
| Button | 18px | 700 | 24px |
| Footer | 14px | 400 | 24px |
| Fine Print | 10px | 400 | 24px |

---

## Template Patterns

### Standard Email Header

```html
<tr>
  <td align="center" bgcolor="#242f46" style="padding: 35px;">
    <img alt="Twisted X" border="0" height="100" width="300"
         src="https://4138030.app.netsuite.com/core/media/media.nl?id=20634688&c=4138030&h=JMQE5iAkIjWMFFjcIAPJZhvSC9sFSlCEkSEgk3KW5u8-pZD6" />
  </td>
</tr>
```

### Standard Email Banner

```html
<tr>
  <td align="center" bgcolor="#ffffff" style="padding: 0px;">
    <img alt="The Original Driving Moc" border="0" height="auto" width="600"
         src="https://4138030.app.netsuite.com/core/media/media.nl?id=47017000&c=4138030&h=OyRQqRvid_67HBtn89ZFDSgjYbYtqcXEHS8WsygYaCd8_l1I" />
  </td>
</tr>
```

### Standard Title Bar

```html
<tr>
  <td align="center" bgcolor="#eeeeee"
      style="font-family: Open Sans, Helvetica, Arial, sans-serif;
             font-size: 18px; font-weight: 800; line-height: 24px;
             padding: 10px; color: #242F46;">
    Sales Order Confirmation
  </td>
</tr>
```

### Standard CTA Button

```html
<a href="${link}" target="_blank"
   style="background-color: #c41e3a; color: #ffffff;
          font-family: Open Sans, Helvetica, Arial, sans-serif;
          font-size: 18px; font-weight: 700; line-height: 24px;
          padding: 15px 40px; text-decoration: none;
          display: inline-block; border-radius: 5px;">
  BUTTON TEXT
</a>
```

### Standard Footer

```html
<tr>
  <td align="center" bgcolor="#242f46" style="padding: 35px 10px;">
    <!-- Footer Logo -->
    <img alt="Twisted X" border="0" width="180" height="60"
         src="https://4138030.app.netsuite.com/core/media/media.nl?id=20634688&c=4138030&h=JMQE5iAkIjWMFFjcIAPJZhvSC9sFSlCEkSEgk3KW5u8-pZD6" />

    <!-- Social Icons -->
    <div style="margin-top: 20px;">
      <!-- See Social Footer Pattern above -->
    </div>
  </td>
</tr>
```

---

## Asset Verification Query

Verify all assets exist and get their URLs:

```bash
python3 query_netsuite.py "
  SELECT id, name, url
  FROM file
  WHERE id IN (20634688, 47017000, 57049, 57139, 57140, 57141)
" --env prod --format table
```

---

## Related Documentation

- `email_profiles.md` - Email profile configuration
- `migration_workflow.md` - Template migration steps
- `common_patterns.md` - FreeMarker patterns
