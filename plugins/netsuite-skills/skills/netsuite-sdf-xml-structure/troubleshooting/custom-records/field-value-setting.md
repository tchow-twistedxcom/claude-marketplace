# Fix: Custom List Field Values Not Setting (setText vs setValue)

## Problem

Setting custom list field values in SuiteScript results in empty fields, even though code executes without errors.

## Symptoms

- Code runs without errors
- Field remains empty after `setValue()`
- No error in logs
- Works in UI but not in code
- Silent failure

## Root Cause

Using `setValue()` with hardcoded numeric IDs that don't match NetSuite's internal list value IDs.

**Why It Fails**:
- NetSuite assigns internal numeric IDs to list values
- These IDs are NOT sequential (not 1, 2, 3...)
- IDs are not predictable or documented
- `setValue()` requires the exact internal ID
- Wrong ID = silent failure (no error, just empty field)

## The Broken Pattern

```javascript
// ❌ THIS DOESN'T WORK
const eventTypeValue = eventType === 'create' ? '1' : '2';

record.setValue({
    fieldId: 'custrecord_event_type',
    value: eventTypeValue  // WRONG: '1' doesn't match NetSuite's internal ID
});

// Result: Field stays empty, no error message
```

**What Happens**:
1. Code sets value to '1'
2. NetSuite looks for list value with internal ID = 1
3. Actual internal ID might be 547 or 1203 (unpredictable)
4. No match found
5. Field left empty
6. No error thrown (silent failure)

## The Correct Pattern

**✅ Use `setText()` with display text**:

```javascript
// Define the DISPLAY TEXT from your custom list XML
let eventTypeText = '';

if (eventType === 'create') {
    eventTypeText = 'Create';  // Exact text from <value> element
} else if (eventType === 'edit') {
    eventTypeText = 'Edit';
} else if (eventType === 'custom') {
    eventTypeText = 'Custom (Manual Retrigger)';
}

// ✅ Set using display text
if (eventTypeText) {
    record.setText({
        fieldId: 'custrecord_event_type',
        text: eventTypeText  // NetSuite finds correct internal ID
    });
}
```

**How It Works**:
1. You provide the display text
2. NetSuite searches custom list for matching `<value>`
3. NetSuite finds internal ID automatically
4. Field set correctly

## XML Definition Reference

**Your custom list XML defines the display text**:

```xml
<customlist scriptid="customlist_event_type">
  <customvalues>
    <customvalue scriptid="val_create">
      <value>Create</value>  <!-- THIS is what you use with setText() -->
    </customvalue>

    <customvalue scriptid="val_edit">
      <value>Edit</value>  <!-- Not "EDIT" or "edit" - exact match! -->
    </customvalue>

    <customvalue scriptid="val_custom">
      <value>Custom (Manual Retrigger)</value>  <!-- Full text with parentheses -->
    </customvalue>
  </customvalues>
</customlist>
```

## Real-World Example

**Problem**: Notification History event type field always empty

**Broken Code**:
```javascript
// File: twx_notification_lib.js (lines 436-448)
let eventTypeValue = '';

if (eventType === 'create') {
    eventTypeValue = '1';
} else if (eventType === 'edit') {
    eventTypeValue = '2';
} else if (eventType === 'custom') {
    eventTypeValue = '3';
}

auditRecord.setValue({
    fieldId: 'custrecord_twx_nh_event_type',
    value: eventTypeValue  // ❌ Always fails
});
```

**Fixed Code**:
```javascript
// File: twx_notification_lib.js (lines 433-450)
const eventType = params.eventType || 'create';
let eventTypeText = '';

if (eventType === 'create') {
    eventTypeText = 'Create';
} else if (eventType === 'edit') {
    eventTypeText = 'Edit';
} else if (eventType === 'custom') {
    eventTypeText = 'Custom (Manual Retrigger)';
}

if (eventTypeText) {
    auditRecord.setText({
        fieldId: 'custrecord_twx_nh_event_type',
        text: eventTypeText  // ✅ Works perfectly
    });
}
```

**Result**: Event type field now populates correctly - "Create", "Edit", or "Custom (Manual Retrigger)"

## Critical Rules

### ✅ Always Use setText() for Custom Lists
```javascript
record.setText({ fieldId: 'field_id', text: 'Display Text' });
```

### ❌ Never Use setValue() with Hardcoded Numbers
```javascript
record.setValue({ fieldId: 'field_id', value: '1' });  // DON'T DO THIS
```

### ✅ Exact Text Match Required
```javascript
// If XML has <value>Open</value>
record.setText({ text: 'Open' });     // ✅ Works
record.setText({ text: 'open' });     // ❌ Case sensitive!
record.setText({ text: 'OPEN' });     // ❌ Case sensitive!
record.setText({ text: ' Open' });    // ❌ Extra space!
```

## When You CAN Use setValue()

**Only use `setValue()` when you have the actual internal ID**:

```javascript
// ✅ Getting and setting with actual internal ID
const currentValue = record.getValue({ fieldId: 'custrecord_status' });

// Later... set to same value
record.setValue({
    fieldId: 'custrecord_status',
    value: currentValue  // OK - this is the real internal ID
});
```

**Or when using getText() → setText() pattern**:
```javascript
// ✅ Safe round-trip pattern
const displayText = record.getText({ fieldId: 'custrecord_status' });

// Use display text elsewhere
otherRecord.setText({
    fieldId: 'custrecord_status_copy',
    text: displayText  // Safe - using display text
});
```

## Common Mistakes

### Mistake 1: Assuming Sequential IDs
```javascript
// ❌ WRONG ASSUMPTION
// "First value = 1, second = 2, third = 3"
record.setValue({ fieldId: 'custrecord_priority', value: '1' });
```

**Reality**: First value might have internal ID 1547

### Mistake 2: Using Scriptid
```javascript
// ❌ WRONG - Using scriptid instead of display text
record.setText({
    fieldId: 'custrecord_port',
    text: 'val_shanghai'  // This is the scriptid, not the display text!
});

// ✅ CORRECT - Use display text
record.setText({
    fieldId: 'custrecord_port',
    text: 'Shanghai, CN'  // This matches <value>
});
```

### Mistake 3: Case Sensitivity
```xml
<!-- XML Definition -->
<value>In Progress</value>
```

```javascript
// ❌ WRONG - Case doesn't match
record.setText({ text: 'in progress' });
record.setText({ text: 'IN PROGRESS' });

// ✅ CORRECT - Exact match
record.setText({ text: 'In Progress' });
```

## Debugging Steps

If field still empty after setText():

1. **Check XML** - Verify exact display text:
   ```bash
   grep -A 2 "value_scriptid" customlist_file.xml
   ```

2. **Check Case** - Display text is case-sensitive

3. **Check Spaces** - Leading/trailing spaces matter

4. **Check Inactive** - Value might be inactive:
   ```xml
   <isinactive>T</isinactive>  <!-- Can't set inactive values -->
   ```

5. **Check Field Type** - Field must be SELECT or MULTISELECT

6. **Check Permissions** - User must have permission to set field

7. **Add Logging**:
   ```javascript
   log.debug('Setting Value', {
       fieldId: 'custrecord_event_type',
       text: eventTypeText,
       xmlValue: 'Create'  // From XML
   });
   ```

## Prevention Checklist

- [ ] Using `setText()` not `setValue()`
- [ ] Display text matches XML `<value>` exactly
- [ ] Case matches exactly
- [ ] No extra spaces
- [ ] Value is not inactive in XML
- [ ] Field type is SELECT or MULTISELECT
- [ ] Custom list is deployed and active

## Related Resources

- [Departure Ports Example](../../examples/custom-lists/departure-ports-example.md)
- [Custom List Structure Guide](../../examples/custom-lists/list-structure.md)
- [Custom Record Field Types](../../examples/custom-records/field-types-reference.md)
