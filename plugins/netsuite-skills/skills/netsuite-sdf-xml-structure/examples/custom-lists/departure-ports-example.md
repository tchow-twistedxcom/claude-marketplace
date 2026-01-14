# Departure Ports Custom List - Production Example

Real-world custom list with 24 port values from PRI Container Tracking module.

## File Information
- **Source**: `~/NetSuiteBundlet/SDF/PRI-Container-Tracking/Objects/customlist/customlist_pri_frgt_cnt_depature_port.xml`
- **Purpose**: Dropdown list of departure ports for freight containers
- **Values**: 24 international shipping ports

## Full XML Structure

```xml
<customlist scriptid="customlist_pri_frgt_cnt_depature_port">
  <description>List of Departure Ports purchased goods ship from</description>
  <isinactive>F</isinactive>
  <ismatrixoption>F</ismatrixoption>
  <isordered>T</isordered>  <!-- Maintains defined order -->
  <name>PRI Departure Port</name>

  <customvalues>
    <customvalue scriptid="foshan">
      <abbreviation>F</abbreviation>
      <isinactive>F</isinactive>
      <value>Foshan, CN</value>
    </customvalue>

    <customvalue scriptid="guangdong">
      <abbreviation>G</abbreviation>
      <isinactive>T</isinactive>  <!-- Hidden - marked as suspect -->
      <value>Guangdong (suspect)</value>
    </customvalue>

    <customvalue scriptid="guangzhou">
      <abbreviation>G</abbreviation>
      <isinactive>F</isinactive>
      <value>Guangzhou, CN</value>
    </customvalue>

    <customvalue scriptid="hong_kong">
      <abbreviation>H</abbreviation>
      <isinactive>F</isinactive>
      <value>Hong Kong, CN</value>
    </customvalue>

    <!-- ... 20 more ports ... -->
  </customvalues>
</customlist>
```

## Key Features

### Ordered List
```xml
<isordered>T</isordered>
```
- Maintains the defined order in dropdown
- Ports appear in XML order, not alphabetically
- Good for grouping by region or frequency

### Abbreviations
```xml
<abbreviation>F</abbreviation>
```
- Single-letter codes for compact display
- Used in list views and reports
- Multiple ports can share same abbreviation

### Inactive Values
```xml
<customvalue scriptid="guangdong">
  <isinactive>T</isinactive>
  <value>Guangdong (suspect)</value>
</customvalue>
```
- Hidden from dropdown but preserved for historical data
- Existing records with "Guangdong" still display correctly
- Can be reactivated by setting `<isinactive>F</isinactive>`

### Scriptid Naming
```xml
<customvalue scriptid="hong_kong">
```
- Lowercase with underscores
- Descriptive of value
- Unique within list

## Usage in Custom Record

```xml
<customrecordcustomfield scriptid="custrecord_container_port">
  <fieldtype>SELECT</fieldtype>
  <label>Departure Port</label>
  <selectrecordtype>[scriptid=customlist_pri_frgt_cnt_depature_port]</selectrecordtype>
</customrecordcustomfield>
```

## Setting Values in SuiteScript

**✅ CORRECT - Use setText() with display value**:
```javascript
containerRecord.setText({
    fieldId: 'custrecord_container_port',
    text: 'Shanghai, CN'  // Exact text from <value> element
});
```

**❌ WRONG - Hardcoded IDs don't work**:
```javascript
// NetSuite's internal IDs don't match 1, 2, 3...
containerRecord.setValue({
    fieldId: 'custrecord_container_port',
    value: '1'  // FAILS - wrong internal ID
});
```

## Complete Port List (24 Values)

1. Foshan, CN
2. Guangdong (suspect) - **INACTIVE**
3. Guangzhou, CN
4. Hong Kong, CN
5. Jakarta, ID
6. Jiangmen, CN
7. Nanjing, CN
8. Ningbo, CN
9. Qingdao, CN
10. Shanghai, CN
11. Shantou, CN
12. Shenzhen, CN
13. Suzhou, CN
14. Taizhou, CN
15. Tianjin, CN
16. Wenzhou, CN
17. Xiamen, CN
18. Yantian, CN
19. Yiwu, CN
20. Zhongshan, CN
21. (Additional ports...)

## Lessons Learned

### Data Integrity
- ❌ Don't delete list values with existing usage
- ✅ Mark as inactive instead
- ✅ Preserves historical data accuracy

### Display Text Standards
- Use consistent format: "City, Country Code"
- Abbreviations help in compact views
- Parenthetical notes for clarification (e.g., "suspect")

### Ordering Strategy
- Geographic grouping (all China ports together)
- Alphabetical within region
- Most common ports first (optional)

## Related Documentation

- [Custom List Structure Guide](list-structure.md)
- [setText() vs setValue() Troubleshooting](../../troubleshooting/custom-lists/list-value-errors.md)
