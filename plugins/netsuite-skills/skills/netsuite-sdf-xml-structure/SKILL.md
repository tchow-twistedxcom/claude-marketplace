---
name: netsuite-sdf-xml-structure
description: Comprehensive NetSuite SDF object XML patterns - custom records, lists, forms, and scripts
version: 1.0.0
triggers:
  keywords: [SDF XML, custom record, customlist, entryForm, usereventscript, mapreducescript, parentsubtab, isparent, subtab, related list, script deployment, netsuite xml, sdf object]
  file_patterns: ["sdf/Objects/**/*.xml", "**/customrecordtype/*.xml", "**/customlist/*.xml", "**/entryForm/*.xml", "**/usereventscript/*.xml", "**/mapreducescript/*.xml"]
  contexts: [SDF object creation, XML editing, related list troubleshooting, script deployment, form design, custom list configuration, NetSuite development]
---

# NetSuite SDF Object XML Structure

Comprehensive guide to creating and configuring all NetSuite SDF objects via XML: custom records, lists, forms, and scripts.

## Overview

This skill covers the complete SDF XML object model found in NetSuiteBundlet, including:
- **Custom Record Types** (customrecordtype) - Parent-child relationships, subtabs, fields
- **Custom Lists** (customlist) - Dropdown values and classification systems
- **Entry Forms** (entryForm) - Form layouts and field groups
- **Scripts** (usereventscript, mapreducescript) - Script logic and deployment patterns

All examples are extracted from working production code in `~/NetSuiteBundlet/SDF/`.

---

## A. Custom Record Types (customrecordtype)

Custom record types are the foundation of NetSuite's extensibility, allowing you to create entirely new data entities.

### Parent-Child Relationship Patterns

Parent-child relationships create related lists on parent records, showing all child records linked to a parent.

**Two-Part Setup Required**:
1. **Parent Record**: Define subtab in `<subtabs>` section
2. **Child Field**: Reference parent's subtab with exact scriptid syntax

**Working Pattern**:
```xml
<!-- PARENT RECORD: customrecord_twx_edi_history -->
<subtabs>
  <subtab>
    <tabtitle>Notifications</tabtitle>
    <tabparent></tabparent>
    <scriptid>tab_notifications</scriptid>
  </subtab>
</subtabs>

<!-- CHILD FIELD: In customrecord_twx_notification_history -->
<customrecordcustomfield scriptid="custrecord_twx_nh_edi_history">
  <fieldtype>SELECT</fieldtype>
  <label>EDI Transaction History</label>
  <isparent>T</isparent>
  <selectrecordtype>[scriptid=customrecord_twx_edi_history]</selectrecordtype>
  <parentsubtab>[scriptid=customrecord_twx_edi_history.tab_notifications]</parentsubtab>
  <onparentdelete>SET_NULL</onparentdelete>
</customrecordcustomfield>
```

**Key Elements**:
- `<isparent>T</isparent>` - Marks this field as creating a parent-child relationship
- `<selectrecordtype>` - Specifies which record type this field references
- `<parentsubtab>` - **CRITICAL**: Must use exact syntax `[scriptid=parent_record.tab_scriptid]`
- `<onparentdelete>` - What happens to child when parent is deleted:
  - `SET_NULL` - Clear parent field (child survives)
  - `DELETE_CASCADE` - Delete child when parent deleted
  - `NO_ACTION` - Prevent parent deletion if children exist

**Common Mistake**:
```xml
<!-- ❌ WRONG: Empty parentsubtab - silently fails, no related list appears -->
<parentsubtab></parentsubtab>

<!-- ✅ CORRECT: Full scriptid reference -->
<parentsubtab>[scriptid=customrecord_twx_edi_history.tab_notifications]</parentsubtab>
```

### Subtab Configuration

Subtabs organize fields into logical groups on the record form.

**Basic Subtab Pattern**:
```xml
<subtabs>
  <subtab>
    <tabtitle>General Information</tabtitle>
    <tabparent></tabparent>  <!-- Empty = main tab -->
    <scriptid>tab_general</scriptid>
  </subtab>
  <subtab>
    <tabtitle>Advanced Settings</tabtitle>
    <tabparent></tabparent>
    <scriptid>tab_advanced</scriptid>
  </subtab>
</subtabs>
```

**Related Lists on Subtabs**:
```xml
<recordsublists>
  <recordsublist>
    <recorddescr>[scriptid=customrecord_child_record]</recorddescr>
    <recordtab>[scriptid=customrecord_parent.tab_children]</recordtab>
  </recordsublist>
</recordsublists>
```

### Field Type Reference

**SELECT** - References another record (dropdown):
```xml
<customrecordcustomfield scriptid="custrecord_vessel">
  <fieldtype>SELECT</fieldtype>
  <label>Vessel</label>
  <selectrecordtype>[scriptid=customrecord_twx_vessel]</selectrecordtype>
  <ismandatory>T</ismandatory>
</customrecordcustomfield>
```

**MULTISELECT** - Many-to-many relationships:
```xml
<customrecordcustomfield scriptid="custrecord_locations">
  <fieldtype>MULTISELECT</fieldtype>
  <label>Locations</label>
  <selectrecordtype>-140</selectrecordtype>  <!-- -140 = Location -->
</customrecordcustomfield>
```

**TEXT/TEXTAREA/CLOBTEXT** - Text fields with different size limits:

```xml
<!-- TEXT: Short text (≤255 chars) -->
<customrecordcustomfield scriptid="custrecord_code">
  <fieldtype>TEXT</fieldtype>
  <label>Code</label>
  <maxlength>50</maxlength>
</customrecordcustomfield>

<!-- TEXTAREA: Medium text (≤4000 chars) -->
<customrecordcustomfield scriptid="custrecord_description">
  <fieldtype>TEXTAREA</fieldtype>
  <label>Description</label>
  <maxlength>999</maxlength>
</customrecordcustomfield>

<!-- CLOBTEXT: Large text (≤1M chars) - CRITICAL: Empty maxlength -->
<customrecordcustomfield scriptid="custrecord_query">
  <fieldtype>CLOBTEXT</fieldtype>
  <label>Query</label>
  <maxlength></maxlength>  <!-- MUST be empty for CLOBTEXT -->
</customrecordcustomfield>
```

**⚠️ CRITICAL for CLOBTEXT**: The `<maxlength></maxlength>` element MUST be present but EMPTY (no number). Setting any numeric value will cause deployment errors.

**CHECKBOX**:
```xml
<customrecordcustomfield scriptid="custrecord_is_active">
  <fieldtype>CHECKBOX</fieldtype>
  <label>Active</label>
  <checkspelling>F</checkspelling>
  <defaultchecked>T</defaultchecked>
</customrecordcustomfield>
```

**DATE/DATETIME**:
```xml
<customrecordcustomfield scriptid="custrecord_ship_date">
  <fieldtype>DATE</fieldtype>
  <label>Ship Date</label>
</customrecordcustomfield>
```

**CURRENCY/INTEGER/FLOAT**:
```xml
<customrecordcustomfield scriptid="custrecord_amount">
  <fieldtype>CURRENCY</fieldtype>
  <label>Amount</label>
</customrecordcustomfield>
```

**FORMULA** - Calculated fields:
```xml
<customrecordcustomfield scriptid="custrecord_full_name">
  <fieldtype>FORMULA</fieldtype>
  <label>Full Name</label>
  <formula>{first_name} || ' ' || {last_name}</formula>
  <formulatext>F</formulatext>  <!-- F = text, T = numeric/date -->
</customrecordcustomfield>
```

**URL** - Hyperlinks:
```xml
<customrecordcustomfield scriptid="custrecord_tracking_url">
  <fieldtype>URL</fieldtype>
  <label>Tracking URL</label>
  <linktext>Track Shipment</linktext>
</customrecordcustomfield>
```

### Field Constraints & Display

**Access & Display**:
```xml
<accesslevel>2</accesslevel>  <!-- 0=hidden, 1=restricted, 2=normal -->
<displaytype>NORMAL</displaytype>  <!-- NORMAL, HIDDEN, READONLY, INLINE, DISABLED -->
<storevalue>T</storevalue>  <!-- T=persist in database, F=display only -->
<globalsearch>T</globalsearch>  <!-- T=searchable -->
<showinlist>T</showinlist>  <!-- T=show in list view -->
```

**Validation**:
```xml
<ismandatory>T</ismandatory>
<maxlength>255</maxlength>
<checkspelling>F</checkspelling>
```

### Record Configuration

**Access Type**:
```xml
<accesstype>CUSTRECORDENTRYPERM</accesstype>
<!-- NONENEEDED = no permission required -->
<!-- CUSTRECORDENTRYPERM = requires custom record permission -->
<!-- PUBLIC = publicly accessible -->
```

**Features**:
```xml
<allowattachments>T</allowattachments>  <!-- Allow file attachments -->
<enablesystemnotes>T</enablesystemnotes>  <!-- Track record history -->
<enablenumbering>T</enablenumbering>  <!-- Auto-increment record IDs -->
<hierarchical>F</hierarchical>  <!-- Parent-child hierarchies -->
```

**Permissions by Role**:
```xml
<permissions>
  <permission>
    <permittedrole>ADMINISTRATOR</permittedrole>
    <permittedlevel>FULL</permittedlevel>
    <!-- Levels: FULL, EDIT, CREATE, VIEW, NONE -->
  </permission>
</permissions>
```

**Working Examples**:
- Container records (`customrecord_twx_container`)
- Vessel records (`customrecord_twx_vessel`)
- Carrier records (`customrecord_twx_carrier`)
- Transit Times records (`customrecord_twx_transit_times`)

---

## B. Custom Lists (customlist)

Custom lists provide dropdown values for SELECT fields and classification systems.

### List Structure

**Basic List Pattern**:
```xml
<customlist scriptid="customlist_twx_departure_ports">
  <name>TWX - Departure Ports</name>
  <isordered>F</isordered>  <!-- Maintain defined order -->
  <customvalues>
    <customvalue scriptid="val_shanghai">
      <value>Shanghai, China</value>
      <abbreviation>SHA</abbreviation>
      <isinactive>F</isinactive>
    </customvalue>
    <customvalue scriptid="val_ningbo">
      <value>Ningbo, China</value>
      <abbreviation>NGB</abbreviation>
      <isinactive>F</isinactive>
    </customvalue>
    <!-- 24 total values in production example -->
  </customvalues>
</customlist>
```

**Key Elements**:
- `scriptid` - Unique identifier for list and values
- `<value>` - Display text shown to users
- `<abbreviation>` - Short code for compact display
- `<isordered>` - T = maintain order as defined, F = alphabetical
- `<isinactive>` - T = hide value, F = show
- `<ismatrixoption>` - T = use in item matrices

### Setting List Values in SuiteScript

**CRITICAL**: Always use `setText()` with exact display text, never `setValue()` with numeric IDs.

```javascript
// ✅ CORRECT: Use display text
record.setText({
    fieldId: 'custrecord_event_type',
    text: 'Create'  // Exact text from <value> element
});

// ❌ WRONG: Hardcoded numeric IDs don't match NetSuite's internal IDs
record.setValue({
    fieldId: 'custrecord_event_type',
    value: '1'  // This will FAIL silently
});
```

**Why setText() is Required**:
- NetSuite uses internal numeric IDs that don't match your expectations
- `setValue()` with '1', '2', '3' won't match NetSuite's actual IDs
- Empty fields occur without errors when IDs don't match
- `setText()` looks up the correct internal ID by matching display text

### Common Use Cases

**Status Tracking**:
```xml
<customlist scriptid="customlist_order_status">
  <customvalues>
    <customvalue scriptid="val_open"><value>Open</value></customvalue>
    <customvalue scriptid="val_processing"><value>In Progress</value></customvalue>
    <customvalue scriptid="val_complete"><value>Complete</value></customvalue>
  </customvalues>
</customlist>
```

**Geographic Data**:
```xml
<customlist scriptid="customlist_regions">
  <customvalues>
    <customvalue scriptid="val_east"><value>East Coast</value></customvalue>
    <customvalue scriptid="val_west"><value>West Coast</value></customvalue>
    <customvalue scriptid="val_central"><value>Central</value></customvalue>
  </customvalues>
</customlist>
```

**Working Example**: Departure Ports list (24 values) - See `examples/custom-lists/departure-ports-example.md`

---

## C. Entry Forms (entryForm)

Entry forms control the layout and appearance of custom record edit/view screens.

### Form Structure

**Basic Form Pattern**:
```xml
<entryForm scriptid="customform_container_record">
  <name>Container Record</name>
  <standard>F</standard>
  <recordType>customrecord_twx_container</recordType>
  <preferred>T</preferred>  <!-- Default form for this record -->

  <mainFields>
    <fieldGroup>
      <label>General Information</label>
      <defaultFieldGroup>F</defaultFieldGroup>
      <singleColumn>F</singleColumn>

      <fields>
        <field>
          <id>custrecord_container_number</id>
          <label>Container Number</label>
          <visible>T</visible>
          <mandatory>T</mandatory>
          <displayType>NORMAL</displayType>
        </field>
        <!-- More fields... -->
      </fields>
    </fieldGroup>
  </mainFields>
</entryForm>
```

**Key Elements**:
- `<recordType>` - Links form to custom record type
- `<preferred>T</preferred>` - Makes this the default form
- `<fieldGroup>` - Organizes related fields with a label
- `<singleColumn>` - T = single column, F = multi-column layout

### Field Layout Properties

**Visibility & Behavior**:
```xml
<field>
  <id>custrecord_field_id</id>
  <label>Field Label</label>
  <visible>T</visible>  <!-- Show/hide field -->
  <mandatory>T</mandatory>  <!-- Required field -->
  <displayType>NORMAL</displayType>  <!-- NORMAL, HIDDEN, LOCKED, STATICTEXT -->
</field>
```

**Layout Control**:
```xml
<field>
  <id>custrecord_field_id</id>
  <columnBreak>T</columnBreak>  <!-- Start new column -->
  <sameRowAsPrevious>T</sameRowAsPrevious>  <!-- Inline with previous -->
  <quickAdd>T</quickAdd>  <!-- Enable inline record creation -->
</field>
```

### Form Design Patterns

**Group Organization**:
```xml
<fieldGroup>
  <label>General</label>
  <singleColumn>F</singleColumn>  <!-- Two-column layout -->
  <fields>
    <field><id>custrecord_name</id></field>
    <field><id>custrecord_type</id></field>
  </fields>
</fieldGroup>

<fieldGroup>
  <label>Logistical Details</label>
  <singleColumn>T</singleColumn>  <!-- Single-column layout -->
  <fields>
    <field><id>custrecord_carrier</id></field>
    <field><id>custrecord_vessel</id></field>
  </fields>
</fieldGroup>
```

**Hidden Mandatory Fields**:
```xml
<!-- System fields: hidden but still required for data integrity -->
<field>
  <id>custrecord_internal_id</id>
  <visible>F</visible>  <!-- Hidden from user -->
  <mandatory>T</mandatory>  <!-- Still required -->
  <displayType>HIDDEN</displayType>
</field>
```

**Quick-Add for Linked Records**:
```xml
<!-- Enable inline creation of related records -->
<field>
  <id>custrecord_vessel</id>
  <quickAdd>T</quickAdd>  <!-- "+" button to create new vessel -->
</field>
```

**Working Examples**:
- Container form - See `examples/entry-forms/container-vessel-forms.md`
- Vessel form - See `examples/entry-forms/container-vessel-forms.md`

---

## D. Scripts (usereventscript, mapreducescript)

Scripts automate business logic and extend NetSuite functionality.

### User Event Scripts

User event scripts trigger on record actions (create, edit, delete, view).

**Basic Structure**:
```xml
<usereventscript scriptid="customscript_twx_tracking">
  <name>TWX - RIEM Schedule Log Tracking</name>
  <scriptfile>[/SuiteScripts/Twisted X/Scripts/riem_tracking.js]</scriptfile>
  <status>RELEASED</status>
  <notifyemails></notifyemails>

  <scriptdeployments>
    <scriptdeployment scriptid="customdeploy_twx_tracking">
      <status>RELEASED</status>
      <title>RIEM Schedule Log Tracking</title>
      <allroles>T</allroles>  <!-- Applies to all roles -->
      <eventtype></eventtype>  <!-- Empty = all events -->
      <loglevel>ERROR</loglevel>
      <runasrole>ADMINISTRATOR</runasrole>

      <executioncontext>
        <context>USERINTERFACE</context>
        <context>WEBSERVICES</context>
        <context>RESTLET</context>
      </executioncontext>

      <recordtype>customrecord_twx_schedule_log</recordtype>
    </scriptdeployment>
  </scriptdeployments>
</usereventscript>
```

**Key Elements**:
- `<scriptfile>` - Path to JavaScript file in FileCabinet
- `<recordtype>` - Which custom record triggers this script
- `<eventtype>` - Specific event (empty = all beforeLoad, beforeSubmit, afterSubmit)
- `<executioncontext>` - Where script can run (USERINTERFACE, WEBSERVICES, etc.)
- `<allroles>` - T = applies globally, F = specific roles only
- `<runasrole>` - Role to execute script as (for permissions)
- `<loglevel>` - DEBUG, INFO, WARN, ERROR

### Map/Reduce Scripts

Map/reduce scripts process large datasets in batches with parallel execution.

**Basic Structure**:
```xml
<mapreducescript scriptid="customscript_link_schedule_logs">
  <name>Link Schedule Logs to EDI History</name>
  <scriptfile>[/SuiteScripts/Twisted X/Scripts/link_logs.js]</scriptfile>
  <status>RELEASED</status>

  <scriptcustomfields>
    <scriptcustomfield scriptid="custscript_start_date">
      <fieldtype>DATE</fieldtype>
      <label>Start Date</label>
    </scriptcustomfield>
  </scriptcustomfields>

  <scriptdeployments>
    <scriptdeployment scriptid="customdeploy_link_logs_daily">
      <status>RELEASED</status>
      <title>Daily Schedule Log Linking</title>
      <loglevel>DEBUG</loglevel>

      <!-- Performance settings -->
      <buffersize>100</buffersize>  <!-- Records per stage -->
      <concurrencylimit>5</concurrencylimit>  <!-- Max concurrent executions -->
      <yieldaftermins>60</yieldaftermins>  <!-- Yield control after 60 min -->
      <queueallstagesatonce>F</queueallstagesatonce>  <!-- Sequential stages -->

      <!-- Scheduling -->
      <recurrence>
        <repeat>DAILY</repeat>
        <dailyfreq>EVERYWEEKDAY</dailyfreq>
        <starttime>02:00 am</starttime>
      </recurrence>
    </scriptdeployment>
  </scriptdeployments>
</mapreducescript>
```

**Key Elements**:
- `<scriptcustomfields>` - Custom parameters for script
- `<buffersize>` - Records processed per map/reduce stage
- `<concurrencylimit>` - Maximum concurrent executions
- `<yieldaftermins>` - When to yield control back to NetSuite
- `<queueallstagesatonce>` - T = parallel stages, F = sequential
- `<recurrence>` - Scheduling configuration

### Script Deployment Patterns

**Multiple Deployments**:
- One script can have multiple deployments with different settings
- Example: Manual deployment + Scheduled deployment
- Each deployment can have different parameters

**Role Restrictions**:
```xml
<allroles>F</allroles>
<roles>
  <role>ADMINISTRATOR</role>
  <role>CUSTOMROLE_MANAGER</role>
</roles>
```

**Context Restrictions**:
```xml
<executioncontext>
  <context>USERINTERFACE</context>  <!-- UI clicks -->
  <context>SCHEDULED</context>  <!-- Scheduled execution -->
  <context>WEBSERVICES</context>  <!-- SOAP web services -->
  <context>RESTLET</context>  <!-- RESTlet calls -->
  <context>CSVIMPORT</context>  <!-- CSV imports -->
  <context>SUITELET</context>  <!-- Suitelet calls -->
</executioncontext>
```

**Working Examples**:
- RIEM schedule log tracking (User Event) - See `examples/scripts/user-event-script.md`
- Link schedule logs (Map/Reduce) - See `examples/scripts/map-reduce-script.md`

---

## Common Issues & Solutions

### Custom Records

#### Issue: Empty parentsubtab - Related list doesn't appear

**Symptom**: Related list not showing on parent record after deployment

**Cause**: Empty `<parentsubtab></parentsubtab>` is silently ignored by NetSuite

**Solution**:
```xml
<!-- ❌ BROKEN -->
<parentsubtab></parentsubtab>

<!-- ✅ FIXED -->
<parentsubtab>[scriptid=customrecord_parent.tab_children]</parentsubtab>
```

**Prerequisites**:
1. Parent must define subtab: `<subtab scriptid="tab_children">`
2. Child must reference with exact syntax: `[scriptid=parent_record.tab_scriptid]`

#### Issue: Hardcoded list values not setting correctly

**Symptom**: Custom list fields stay empty even though code sets values

**Cause**: Using `setValue()` with numeric IDs that don't match NetSuite's internal IDs

**Solution**:
```javascript
// ❌ WRONG: Numeric IDs don't match
record.setValue({ fieldId: 'custrecord_status', value: '1' });

// ✅ CORRECT: Use display text
record.setText({ fieldId: 'custrecord_status', text: 'Open' });
```

### Custom Lists

#### Issue: List value setting errors

**Symptom**: Values not appearing or showing incorrect values

**Cause**: Case sensitivity or scriptid mismatches

**Solution**:
- Match exact scriptid and display text from XML
- Check case sensitivity (Text ≠ text)
- Verify value isn't marked `<isinactive>T</isinactive>`

### Entry Forms

#### Issue: Form structure errors - "customrecordtypelists is invalid"

**Symptom**: Deployment fails with invalid element error

**Cause**: Forms must be embedded in customrecordtype, not standalone files

**Solution**:
```xml
<!-- ❌ WRONG: Standalone form file -->
<entryForm>...</entryForm>

<!-- ✅ CORRECT: Embedded in customrecordtype -->
<customrecordtype>
  <forms>
    <entryForm>...</entryForm>
  </forms>
</customrecordtype>
```

### Scripts

#### Issue: Execution context mismatches - Script not firing

**Symptom**: Script doesn't execute when expected

**Cause**: Deployment `executioncontext` doesn't match trigger context

**Solution**:
```xml
<!-- Script triggered from UI but context only allows scheduled -->
<executioncontext>
  <context>USERINTERFACE</context>  <!-- Add UI context -->
  <context>SCHEDULED</context>
</executioncontext>
```

**Common Contexts**:
- USERINTERFACE - UI form submissions
- WEBSERVICES - SOAP web services
- RESTLET - RESTlet API calls
- SCHEDULED - Scheduled scripts
- CSVIMPORT - CSV import operations

#### Issue: Role access errors

**Symptom**: Script fails with permission errors

**Cause**: `runasrole` doesn't have required permissions

**Solution**:
- Verify role has access to all records/fields script touches
- Use ADMINISTRATOR for development/testing
- Use specific role for production with minimum required permissions

---

## Quick Reference

### Parent-Child Setup Checklist

**Step 1: Parent Record** - Define subtab:
```xml
<subtabs>
  <subtab>
    <scriptid>tab_children</scriptid>
    <tabtitle>Children</tabtitle>
  </subtab>
</subtabs>
```

**Step 2: Child Field** - Reference parent:
```xml
<customrecordcustomfield scriptid="custrecord_parent">
  <fieldtype>SELECT</fieldtype>
  <isparent>T</isparent>
  <selectrecordtype>[scriptid=customrecord_parent]</selectrecordtype>
  <parentsubtab>[scriptid=customrecord_parent.tab_children]</parentsubtab>
  <onparentdelete>SET_NULL</onparentdelete>
</customrecordcustomfield>
```

### Custom List Value Setting

**XML Definition**:
```xml
<customvalue scriptid="val_create">
  <value>Create</value>
</customvalue>
```

**SuiteScript Usage**:
```javascript
// ✅ ALWAYS use setText() with exact display text
record.setText({ fieldId: 'custrecord_event_type', text: 'Create' });

// ❌ NEVER use setValue() with numeric IDs
record.setValue({ fieldId: 'custrecord_event_type', value: '1' });
```

### Script Deployment Checklist

- ✅ `<executioncontext>` includes context where script will run
- ✅ `<runasrole>` has all required permissions
- ✅ `<status>` set to RELEASED for production
- ✅ `<loglevel>` appropriate for environment (ERROR for prod, DEBUG for dev)
- ✅ For Map/Reduce: `<buffersize>`, `<concurrencylimit>`, `<yieldaftermins>` tuned
- ✅ `<recordtype>` matches target record (for User Event scripts)

### Field Type Selection Guide

| Need | Field Type | Notes |
|------|-----------|-------|
| Link to another record | SELECT | Use for lookups and relationships |
| Multiple selections | MULTISELECT | Many-to-many relationships |
| Short text (≤255 chars) | TEXT | Names, codes, IDs - maxlength required |
| Long text (≤4000 chars) | TEXTAREA | Descriptions, notes - maxlength required |
| Very long text (≤1M chars) | CLOBTEXT | Large text blocks - maxlength MUST be empty |
| Yes/No | CHECKBOX | Boolean values |
| Calendar date | DATE | No time component |
| Date + time | DATETIME | Full timestamp |
| Money | CURRENCY | Auto-formats with currency symbol |
| Whole numbers | INTEGER | No decimals |
| Decimals | FLOAT | Precision numbers |
| Calculated value | FORMULA | Read-only computed field |
| Clickable link | URL | External links |
| Predefined options | Custom List + SELECT | Dropdowns |

---

## Resources

### Examples
- [Custom Record Parent-Child Patterns](examples/custom-records/parent-child-patterns.md)
- [Field Types Reference](examples/custom-records/field-types-reference.md)
- [Subtab Configuration](examples/custom-records/subtab-configuration.md)
- [Custom List Structure](examples/custom-lists/list-structure.md)
- [Departure Ports Example](examples/custom-lists/departure-ports-example.md)
- [Form Layout Patterns](examples/entry-forms/form-layout-patterns.md)
- [Container & Vessel Forms](examples/entry-forms/container-vessel-forms.md)
- [User Event Script](examples/scripts/user-event-script.md)
- [Map/Reduce Script](examples/scripts/map-reduce-script.md)

### Patterns (Reusable Templates)
- [Mandatory Parent Template](patterns/customrecordtype/mandatory-parent.xml)
- [Optional Parent Template](patterns/customrecordtype/optional-parent.xml)
- [Multi-Parent Template](patterns/customrecordtype/multi-parent.xml)
- [Basic List Template](patterns/customlist/basic-list.xml)
- [Basic Form Template](patterns/entryForm/basic-form.xml)
- [User Event Script Template](patterns/scripts/usereventscript.xml)
- [Map/Reduce Script Template](patterns/scripts/mapreducescript.xml)

### Troubleshooting
- [Empty parentsubtab Fix](troubleshooting/custom-records/empty-parentsubtab.md)
- [setText vs setValue Fix](troubleshooting/custom-records/field-value-setting.md)
- [List Value Errors](troubleshooting/custom-lists/list-value-errors.md)
- [Form XML Errors](troubleshooting/entry-forms/form-xml-errors.md)
- [Execution Context Errors](troubleshooting/scripts/execution-context-errors.md)
- [Deployment Issues](troubleshooting/scripts/deployment-issues.md)

---

## Best Practices

### Development Workflow
1. **Plan First**: Understand data model and relationships before creating objects
2. **Use Templates**: Start with patterns from this skill for consistency
3. **Test in Sandbox**: Always deploy to sandbox (sb1/sb2) before production
4. **Document Dependencies**: Track which objects depend on others
5. **Version Control**: Commit SDF objects to git for change tracking

### Naming Conventions
- **Scriptids**: Use lowercase with underscores (`customrecord_twx_container`)
- **Prefixes**: Use company prefix for all custom objects (`twx_`, `company_`)
- **Descriptive Names**: Make purpose clear (`custrecord_edi_transaction_type`)
- **Consistency**: Follow existing patterns in your codebase

### Performance
- **Indexed Fields**: Use `<globalsearch>T</globalsearch>` for frequently searched fields
- **Formula Fields**: Minimize complex formulas, consider server-side calculation
- **Map/Reduce**: Tune `buffersize` and `concurrencylimit` based on data volume
- **Script Context**: Limit execution contexts to only what's needed

### Maintenance
- **Document Changes**: Comment why, not just what
- **Test Relationships**: Verify parent-child relationships after deployment
- **Monitor Scripts**: Check logs regularly for errors
- **Clean Up**: Deactivate unused list values, don't delete them
