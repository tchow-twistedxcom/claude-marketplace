# Fix: Empty parentsubtab - No Related List Appears

## Problem

After deploying a custom record with a parent-child relationship, the related list doesn't appear on the parent record.

## Symptoms

- Deployment succeeds without errors
- Child record can select parent (dropdown works)
- Parent record shows no related list tab
- No error messages - silent failure

## Root Cause

NetSuite silently ignores empty `<parentsubtab></parentsubtab>` elements. The relationship exists in the database but has no UI representation.

## The Broken Pattern

```xml
<!-- ❌ THIS DOESN'T WORK -->
<customrecordcustomfield scriptid="custrecord_child_parent">
  <fieldtype>SELECT</fieldtype>
  <label>Parent Record</label>
  <isparent>T</isparent>
  <selectrecordtype>[scriptid=customrecord_parent]</selectrecordtype>
  <parentsubtab></parentsubtab>  <!-- ❌ EMPTY = No related list -->
  <onparentdelete>SET_NULL</onparentdelete>
</customrecordcustomfield>
```

**What Happens**:
- Database relationship created
- `isparent=T` is set but has no visible effect
- Parent record shows NO related list tab
- You CAN query children via SuiteScript
- You CANNOT see children in NetSuite UI

## The Fix (Two Steps Required)

### Step 1: Define Subtab on Parent Record

Edit the parent record XML file and add a subtab:

```xml
<!-- File: customrecord_parent.xml -->
<customrecordtype scriptid="customrecord_parent">
  <recordname>Parent Record</recordname>

  <subtabs>
    <subtab>
      <tabtitle>Children</tabtitle>  <!-- Tab name users will see -->
      <tabparent></tabparent>  <!-- Empty = main tab -->
      <scriptid>tab_children</scriptid>  <!-- CRITICAL: Referenced by child -->
    </subtab>
  </subtabs>

  <recordsublists>
    <recordsublist>
      <recorddescr>[scriptid=customrecord_child]</recorddescr>
      <recordtab>[scriptid=customrecord_parent.tab_children]</recordtab>
    </recordsublist>
  </recordsublists>
</customrecordtype>
```

### Step 2: Reference Subtab from Child Field

Edit the child record XML file and populate parentsubtab:

```xml
<!-- File: customrecord_child.xml -->
<customrecordcustomfield scriptid="custrecord_child_parent">
  <fieldtype>SELECT</fieldtype>
  <label>Parent Record</label>
  <isparent>T</isparent>
  <selectrecordtype>[scriptid=customrecord_parent]</selectrecordtype>
  <!-- ✅ CORRECT: Full scriptid reference -->
  <parentsubtab>[scriptid=customrecord_parent.tab_children]</parentsubtab>
  <onparentdelete>SET_NULL</onparentdelete>
</customrecordcustomfield>
```

## Exact Syntax Requirements

**Scriptid Reference Format**:
```
[scriptid=PARENT_RECORD_SCRIPTID.SUBTAB_SCRIPTID]
```

**Example**:
- Parent record: `customrecord_twx_edi_history`
- Subtab scriptid: `tab_notifications`
- Full reference: `[scriptid=customrecord_twx_edi_history.tab_notifications]`

**Common Mistakes**:
```xml
<!-- ❌ Missing brackets -->
<parentsubtab>customrecord_parent.tab_children</parentsubtab>

<!-- ❌ Wrong keyword -->
<parentsubtab>[id=customrecord_parent.tab_children]</parentsubtab>

<!-- ❌ No dot separator -->
<parentsubtab>[scriptid=customrecord_parent_tab_children]</parentsubtab>

<!-- ❌ Tab doesn't exist on parent -->
<parentsubtab>[scriptid=customrecord_parent.tab_nonexistent]</parentsubtab>

<!-- ✅ CORRECT -->
<parentsubtab>[scriptid=customrecord_parent.tab_children]</parentsubtab>
```

## Deployment Steps

1. **Edit parent record XML** - Add subtab definition
2. **Edit child record XML** - Add parentsubtab reference
3. **Deploy to sandbox**:
   ```bash
   cd ~/NetSuiteBundlet/SDF/Your-Project
   npx twx-deploy deploy sb2
   ```
4. **Verify in NetSuite**:
   - Open a parent record
   - Look for new subtab (e.g., "Children")
   - Create a child record and link to parent
   - Refresh parent - child should appear in related list

## Real-World Example

**Problem**: Notification History records not appearing on EDI Transaction History

**Before (Broken)**:
```xml
<!-- customrecord_twx_notification_history.xml -->
<parentsubtab></parentsubtab>
```

**After (Fixed)**:
```xml
<!-- Parent: customrecord_twx_edi_history.xml -->
<subtabs>
  <subtab>
    <scriptid>tab_notifications</scriptid>
    <tabtitle>Notifications</tabtitle>
  </subtab>
</subtabs>

<!-- Child: customrecord_twx_notification_history.xml -->
<parentsubtab>[scriptid=customrecord_twx_edi_history.tab_notifications]</parentsubtab>
```

**Result**: "Notifications" tab now appears on EDI Transaction History records showing all related notifications.

## Verification Checklist

After deployment:

- [ ] Parent record shows new subtab
- [ ] Create child record and select parent
- [ ] Refresh parent record
- [ ] Child appears in related list on correct tab
- [ ] Tab title matches `<tabtitle>` value
- [ ] Can create multiple children - all appear in list
- [ ] Test deletion policy (try deleting parent)

## Prevention

**Before Creating Parent-Child Relationships**:
1. Decide which tab will show related list
2. Define subtab on parent first
3. Reference exact scriptid in child field
4. Test in sandbox before production deployment

**Template Checklist**:
- [ ] Parent has `<subtabs>` section
- [ ] Subtab has descriptive `<scriptid>`
- [ ] Child field has `<isparent>T</isparent>`
- [ ] Child field has populated `<parentsubtab>`
- [ ] Scriptid reference uses exact syntax with brackets

## Related Resources

- [Parent-Child Relationship Patterns](../../examples/custom-records/parent-child-patterns.md)
- [Subtab Configuration Guide](../../examples/custom-records/subtab-configuration.md)
