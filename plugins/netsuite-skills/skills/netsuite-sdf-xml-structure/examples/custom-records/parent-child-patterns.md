# Custom Record Parent-Child Relationship Patterns

This document shows 5 working patterns extracted from production SDF files in NetSuiteBundlet and B2bDashboard.

## Overview

Parent-child relationships create related lists on parent records, allowing you to see all child records linked to a specific parent.

**Two-Part Setup Required**:
1. **Parent Record**: Define subtab in `<subtabs>` section
2. **Child Field**: Reference parent's subtab using exact scriptid syntax

---

## Pattern 1: Mandatory Parent with Related List (Recommended)

**Use Case**: Every child MUST have a parent, and parent shows related list

**Example**: Notification History → EDI Transaction History

### Parent Record Setup
```xml
<!-- File: customrecord_twx_edi_history.xml -->
<customrecordtype scriptid="customrecord_twx_edi_history">
  <recordname>TWX EDI Transaction History</recordname>

  <subtabs>
    <subtab>
      <tabtitle>Notifications</tabtitle>
      <tabparent></tabparent>
      <scriptid>tab_notifications</scriptid>
    </subtab>
  </subtabs>

  <recordsublists>
    <recordsublist>
      <recorddescr>[scriptid=customrecord_twx_notification_history]</recorddescr>
      <recordtab>[scriptid=customrecord_twx_edi_history.tab_notifications]</recordtab>
    </recordsublist>
  </recordsublists>
</customrecordtype>
```

### Child Field Setup
```xml
<!-- File: customrecord_twx_notification_history.xml -->
<customrecordcustomfield scriptid="custrecord_twx_nh_edi_history">
  <fieldtype>SELECT</fieldtype>
  <label>EDI Transaction History</label>
  <ismandatory>T</ismandatory>
  <isparent>T</isparent>
  <selectrecordtype>[scriptid=customrecord_twx_edi_history]</selectrecordtype>
  <parentsubtab>[scriptid=customrecord_twx_edi_history.tab_notifications]</parentsubtab>
  <onparentdelete>SET_NULL</onparentdelete>
</customrecordcustomfield>
```

**Key Points**:
- ✅ `<ismandatory>T</ismandatory>` - Child must have parent
- ✅ `<isparent>T</isparent>` - Creates related list
- ✅ `<parentsubtab>[scriptid=...]</parentsubtab>` - Specifies which tab shows list
- ✅ `<onparentdelete>SET_NULL</onparentdelete>` - Clear parent field if parent deleted

**Result**: "Notifications" tab appears on EDI Transaction History records showing all linked Notification History records.

---

## Pattern 2: Optional Parent WITHOUT Related List (Anti-Pattern)

**Use Case**: Parent-child link exists but NO related list on parent

**Example**: Container → Vessel (from NetSuiteBundlet)

### Child Field Setup
```xml
<!-- File: customrecord_pri_frgt_cnt.xml -->
<customrecordcustomfield scriptid="custrecord_pri_frgt_cnt_vsl">
  <fieldtype>SELECT</fieldtype>
  <label>Container Vessel</label>
  <ismandatory>F</ismandatory>
  <isparent>T</isparent>
  <selectrecordtype>[scriptid=customrecord_pri_frgt_cnt_vsl]</selectrecordtype>
  <parentsubtab></parentsubtab>  <!-- ❌ EMPTY = No related list -->
  <onparentdelete>NO_ACTION</onparentdelete>
</customrecordcustomfield>
```

**Key Points**:
- ❌ `<parentsubtab></parentsubtab>` - Empty = no related list appears
- ⚠️ `<isparent>T</isparent>` is set but has no visual effect
- ℹ️ This creates the database relationship but no UI related list
- ℹ️ You can still query child records programmatically

**Result**: Container can link to Vessel, but Vessel record shows no "Containers" related list.

**When to Use**: You want the relationship for reporting but don't need the UI list (rare).

**Better Alternative**: Use Pattern 1 or 3 to provide full UI functionality.

---

## Pattern 3: Optional Parent with Related List

**Use Case**: Child may or may not have a parent, but parent shows related list when linked

**Setup**: Same as Pattern 1 but with `<ismandatory>F</ismandatory>`

```xml
<customrecordcustomfield scriptid="custrecord_child_parent">
  <fieldtype>SELECT</fieldtype>
  <ismandatory>F</ismandatory>  <!-- Optional parent -->
  <isparent>T</isparent>
  <selectrecordtype>[scriptid=customrecord_parent]</selectrecordtype>
  <parentsubtab>[scriptid=customrecord_parent.tab_children]</parentsubtab>
  <onparentdelete>SET_NULL</onparentdelete>
</customrecordcustomfield>
```

**Key Points**:
- ✅ Parent is optional (`ismandatory=F`)
- ✅ Related list still appears on parent records
- ✅ List only shows children that have this parent linked

**Result**: Parent record has related list tab showing linked children, but not all children must have a parent.

---

## Pattern 4: Multiple Parent Relationships

**Use Case**: Child can have relationships to multiple different parent record types

**Example**: A document record that can link to both Orders and Invoices

```xml
<!-- Parent Relationship 1: Order -->
<customrecordcustomfield scriptid="custrecord_doc_order">
  <fieldtype>SELECT</fieldtype>
  <label>Related Order</label>
  <ismandatory>F</ismandatory>
  <isparent>T</isparent>
  <selectrecordtype>-32</selectrecordtype>  <!-- Sales Order -->
  <parentsubtab>[scriptid=transaction.tab_documents]</parentsubtab>
  <onparentdelete>SET_NULL</onparentdelete>
</customrecordcustomfield>

<!-- Parent Relationship 2: Invoice -->
<customrecordcustomfield scriptid="custrecord_doc_invoice">
  <fieldtype>SELECT</fieldtype>
  <label>Related Invoice</label>
  <ismandatory>F</ismandatory>
  <isparent>T</isparent>
  <selectrecordtype>-29</selectrecordtype>  <!-- Invoice -->
  <parentsubtab>[scriptid=transaction.tab_documents]</parentsubtab>
  <onparentdelete>SET_NULL</onparentdelete>
</customrecordcustomfield>
```

**Key Points**:
- ✅ Each parent relationship is independent
- ✅ Child can have 0, 1, or multiple parents (different types)
- ✅ Each parent shows its related children on appropriate tab
- ⚠️ Use validation logic to ensure business rules (e.g., can't have both Order AND Invoice)

---

## Pattern 5: Cascading Delete

**Use Case**: When parent is deleted, automatically delete all children

**Example**: Order → Order Lines (child can't exist without parent)

```xml
<customrecordcustomfield scriptid="custrecord_line_order">
  <fieldtype>SELECT</fieldtype>
  <label>Order</label>
  <ismandatory>T</ismandatory>
  <isparent>T</isparent>
  <selectrecordtype>[scriptid=customrecord_order]</selectrecordtype>
  <parentsubtab>[scriptid=customrecord_order.tab_lines]</parentsubtab>
  <onparentdelete>DELETE_CASCADE</onparentdelete>  <!-- ⚠️ Deletes child! -->
</customrecordcustomfield>
```

**Key Points**:
- ⚠️ **DANGEROUS**: Deleting parent deletes ALL children
- ✅ Use when child has no meaning without parent
- ✅ Ensures data integrity (no orphaned records)
- ⚠️ Cannot be undone - deleted children are gone

**Deletion Policy Options**:
- `SET_NULL` - Clear parent field (child survives) - **Safest**
- `NO_ACTION` - Prevent parent deletion if children exist
- `DELETE_CASCADE` - Delete children when parent deleted - **Use with caution**

---

## Common Mistakes

### ❌ Empty parentsubtab
```xml
<parentsubtab></parentsubtab>  <!-- No related list appears! -->
```

**Fix**:
```xml
<parentsubtab>[scriptid=customrecord_parent.tab_children]</parentsubtab>
```

### ❌ Missing subtab definition on parent
```xml
<!-- Child references tab that doesn't exist -->
<parentsubtab>[scriptid=customrecord_parent.tab_missing]</parentsubtab>
```

**Fix**: First define the subtab on parent record:
```xml
<subtabs>
  <subtab>
    <scriptid>tab_missing</scriptid>
    <tabtitle>Children</tabtitle>
  </subtab>
</subtabs>
```

### ❌ Wrong scriptid syntax
```xml
<parentsubtab>customrecord_parent.tab_children</parentsubtab>  <!-- Missing brackets! -->
```

**Fix**:
```xml
<parentsubtab>[scriptid=customrecord_parent.tab_children]</parentsubtab>
```

---

## Testing Checklist

After deploying parent-child relationships:

1. ✅ Create child record and link to parent
2. ✅ View parent record - verify related list tab appears
3. ✅ Verify child appears in related list
4. ✅ Test deletion policy (try deleting parent)
5. ✅ Verify search functionality (find parent from child, vice versa)
6. ✅ Test permissions (can appropriate roles see related lists?)

---

## Summary

**Best Practice**: Use Pattern 1 (Mandatory Parent with Related List)
- Clearest data model
- Best user experience
- Enforces data integrity

**Avoid**: Pattern 2 (Empty parentsubtab)
- Creates confusion (relationship exists but not visible)
- Use only if you genuinely don't want the UI list

**Common Pattern**: Pattern 3 (Optional Parent with Related List)
- Good for flexible relationships
- Parent list shows "opt-in" children

**Use Cautiously**: Pattern 5 (Cascading Delete)
- Powerful but dangerous
- Test thoroughly before production
