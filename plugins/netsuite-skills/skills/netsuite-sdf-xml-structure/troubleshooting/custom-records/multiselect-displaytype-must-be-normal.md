# Fix: SDF Rejects DISABLED/INLINE displaytype on MULTISELECT Fields

## Problem

Adding a MULTISELECT custom record field in SDF XML and deploying fails with a validation error, even though the same `displaytype` value works for other field types.

## Symptoms

- SDF deployment fails before contacting NetSuite
- Error: `"The displaytype field for the <scriptid> (customrecordcustomfield) subrecord must not be DISABLED."`
- Or: `"The displaytype field for the <scriptid> (customrecordcustomfield) subrecord must not be INLINE."`
- The field is type MULTISELECT and was intentionally set to DISABLED or INLINE to make it read-only

## Root Cause

SDF's XSD schema restricts the allowed `displaytype` values by `fieldtype`. For MULTISELECT custom record fields, only `NORMAL` is accepted. `DISABLED` and `INLINE` — which are valid for other field types — are explicitly rejected.

This constraint is not documented in the public SDF reference, so it's discovered only by hitting the error.

## The Fix

Set `<displaytype>NORMAL</displaytype>` on any MULTISELECT field:

```xml
<!-- ❌ WRONG — SDF rejects both: -->
<customrecordcustomfield scriptid="custrecord_my_multiselect">
  <displaytype>DISABLED</displaytype>
  <fieldtype>MULTISELECT</fieldtype>
  ...
</customrecordcustomfield>

<!-- ❌ ALSO WRONG: -->
<customrecordcustomfield scriptid="custrecord_my_multiselect">
  <displaytype>INLINE</displaytype>
  <fieldtype>MULTISELECT</fieldtype>
  ...
</customrecordcustomfield>

<!-- ✅ CORRECT: -->
<customrecordcustomfield scriptid="custrecord_my_multiselect">
  <displaytype>NORMAL</displaytype>
  <fieldtype>MULTISELECT</fieldtype>
  ...
</customrecordcustomfield>
```

## Making MULTISELECT Read-Only

If you want the field to be read-only (auto-populated by script only), enforce it in a Client Script:

```javascript
// In a CS on the custom record, pageInit event:
function pageInit(context) {
    context.currentRecord.getField({ fieldId: 'custrecord_my_multiselect' }).isDisabled = true;
}
```

## Quick Reference: MULTISELECT in SDF XML

| Attribute | Required value |
|-----------|----------------|
| `fieldtype` | `MULTISELECT` |
| `displaytype` | `NORMAL` (only valid value) |
| `selectrecordtype` | Record scriptid as `[scriptid=...]`, or built-in ID (e.g., `-6` for Contact) |
| `storevalue` | `T` |
| `ismandatory` | `F` (MULTISELECT fields cannot be mandatory on custom records) |

## Related Resources

- [Custom Record Field Types Reference](../../examples/custom-records/field-types-reference.md)
