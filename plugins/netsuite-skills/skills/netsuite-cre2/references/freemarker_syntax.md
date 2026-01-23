# FreeMarker Syntax Reference for CRE 2.0

Quick reference for FreeMarker templating in NetSuite CRE 2.0.

## Variable Interpolation

```freemarker
${variable}                    <!-- Simple variable -->
${object.property}             <!-- Object property -->
${array[0]}                    <!-- Array index -->
${map["key"]}                  <!-- Map key access -->
```

## Conditionals

### Basic If/Else
```freemarker
<#if condition>
    content
</#if>

<#if condition>
    content when true
<#else>
    content when false
</#if>

<#if condition1>
    first
<#elseif condition2>
    second
<#else>
    default
</#if>
```

### Condition Examples
```freemarker
<#if value?has_content>           <!-- Not null/empty -->
<#if value??>                     <!-- Not null -->
<#if (value > 0)>                 <!-- Numeric comparison -->
<#if value == "text">             <!-- String comparison -->
<#if value?number != 0>           <!-- Number comparison -->
<#if condition1 && condition2>    <!-- AND -->
<#if condition1 || condition2>    <!-- OR -->
<#if !condition>                  <!-- NOT -->
```

## Loops

### List Iteration
```freemarker
<#list items as item>
    ${item}
</#list>

<#list items as item>
    ${item_index}: ${item}        <!-- 0-based index -->
</#list>

<#list 1..10 as i>                <!-- Range -->
    ${i}
</#list>
```

### List with Else
```freemarker
<#list items as item>
    ${item}
<#else>
    No items found
</#list>
```

## Variables

### Assignment
```freemarker
<#assign name = "value">
<#assign count = 0>
<#assign total = price * quantity>
<#assign items = []>              <!-- Empty list -->
<#assign map = {}>                <!-- Empty map -->
```

### Scope
```freemarker
<#assign globalVar = 1>           <!-- Template scope -->
<#local localVar = 1>             <!-- Macro scope -->
<#global globalVar = 1>           <!-- All templates -->
```

## Built-in Functions

### String Functions
```freemarker
${str?upper_case}                 <!-- UPPERCASE -->
${str?lower_case}                 <!-- lowercase -->
${str?cap_first}                  <!-- Capitalize first -->
${str?trim}                       <!-- Remove whitespace -->
${str?length}                     <!-- String length -->
${str?replace("old", "new")}      <!-- Replace text -->
${str?split(",")}                 <!-- Split to list -->
${str?contains("sub")}            <!-- Contains check -->
${str?starts_with("pre")}         <!-- Starts with -->
${str?ends_with("suf")}           <!-- Ends with -->
${str?substring(0, 5)}            <!-- Substring -->
```

### Number Functions
```freemarker
${num?string["0.00"]}             <!-- Format: 2 decimals -->
${num?string.currency}            <!-- Currency format -->
${num?string.percent}             <!-- Percent format -->
${num?abs}                        <!-- Absolute value -->
${num?round}                      <!-- Round -->
${num?floor}                      <!-- Floor -->
${num?ceiling}                    <!-- Ceiling -->
```

### Date/Time Functions
```freemarker
${date?string("MM/dd/yyyy")}      <!-- Custom format -->
${date?string.short}              <!-- Short format -->
${date?string.medium}             <!-- Medium format -->
${date?string.long}               <!-- Long format -->
${.now}                           <!-- Current datetime -->
${.now?date}                      <!-- Current date -->
${.now?time}                      <!-- Current time -->
```

### Collection Functions
```freemarker
${list?size}                      <!-- List size -->
${list?first}                     <!-- First element -->
${list?last}                      <!-- Last element -->
${list?reverse}                   <!-- Reverse order -->
${list?sort}                      <!-- Sort ascending -->
${list?sort_by("prop")}           <!-- Sort by property -->
${list?join(", ")}                <!-- Join to string -->
${map?keys}                       <!-- Map keys -->
${map?values}                     <!-- Map values -->
```

### Type Checking & Conversion
```freemarker
${value?has_content}              <!-- Not null/empty -->
${value??}                        <!-- Not null -->
${value?string}                   <!-- To string -->
${value?number}                   <!-- To number -->
${value?boolean}                  <!-- To boolean -->
${value?date}                     <!-- To date -->
${value?is_string}                <!-- Type check -->
${value?is_number}                <!-- Type check -->
${value?is_boolean}               <!-- Type check -->
```

### Default Values
```freemarker
${value!"default"}                <!-- Default if null -->
${value!}                         <!-- Empty if null -->
${(object.prop)!"default"}        <!-- Safe navigation -->
```

## Macros

### Define Macro
```freemarker
<#macro name>
    content
</#macro>

<#macro name param1 param2="default">
    ${param1} ${param2}
</#macro>
```

### Call Macro
```freemarker
<@name/>
<@name param1="value1" param2="value2"/>
```

### Nested Content
```freemarker
<#macro wrapper>
    <div>
        <#nested>
    </div>
</#macro>

<@wrapper>
    This content goes inside
</@wrapper>
```

## Include/Import

```freemarker
<#include "other_template.ftl">
<#import "macros.ftl" as m>
<@m.someMacro/>
```

## Comments

```freemarker
<#-- This is a FreeMarker comment -->
<#--
    Multi-line
    comment
-->
```

## Special Values

```freemarker
.now                              <!-- Current datetime -->
.data_model                       <!-- Root data model -->
.main                             <!-- Main template -->
true                              <!-- Boolean true -->
false                             <!-- Boolean false -->
```

## CRE 2.0 Specific

### Data Source Access
```freemarker
${record.fieldname}               <!-- Record field -->
${datasource.rows[0].field}       <!-- First row -->
${datasource.rows}                <!-- All rows (for list) -->
```

### PDF Macros
```freemarker
<macrolist>
    <macro id="header">
        <!-- Header content -->
    </macro>
    <macro id="footer">
        <pagenumber/> of <totalpages/>
    </macro>
</macrolist>
```

### Body Attributes
```freemarker
<body header="header" header-height="15%"
      footer="footer" footer-height="5%"
      size="Letter" padding="0.5in">
```
