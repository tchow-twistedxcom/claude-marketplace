# Common CRE 2.0 Template Patterns

Reusable patterns for CRE 2.0 FreeMarker templates.

## Data Iteration Patterns

### Simple List
```freemarker
<#list tran.rows as row>
    <tr>
        <td>${row.tranid}</td>
        <td>${row.amount}</td>
    </tr>
</#list>
```

### List with Running Total
```freemarker
<#assign running_total = 0>
<#list tran.rows as row>
    <#assign running_total = running_total + row.amount?number>
    <tr>
        <td>${row.tranid}</td>
        <td>${row.amount}</td>
        <td>${running_total}</td>
    </tr>
</#list>
```

### List with Group Breaks
```freemarker
<#assign current_group = "">
<#assign previous_group = "">
<#assign group_total = 0>

<#list tran.rows as row>
    <#assign current_group = row.custname?string>

    <#if current_group != previous_group && previous_group != "">
        <!-- Group subtotal row -->
        <tr class="subtotal">
            <td colspan="3">${previous_group} Subtotal</td>
            <td>${group_total}</td>
        </tr>
        <#assign group_total = 0>
    </#if>

    <!-- Data row -->
    <tr>
        <td>${row.custname}</td>
        <td>${row.tranid}</td>
        <td>${row.amount}</td>
    </tr>

    <#assign group_total = group_total + row.amount?number>
    <#assign previous_group = current_group>
</#list>

<!-- Final group subtotal -->
<tr class="subtotal">
    <td colspan="3">${previous_group} Subtotal</td>
    <td>${group_total}</td>
</tr>
```

## Null-Safe Patterns

### Simple Null Check
```freemarker
<#if value?has_content>
    ${value}
<#else>
    -
</#if>
```

### Inline Default
```freemarker
${value!"N/A"}
${value!"-"}
${value!0}
```

### Safe Number Conversion
```freemarker
<#if value?has_content>
    ${value?number}
<#else>
    0
</#if>
```

### Nested Property Access
```freemarker
<#if (object.property)?has_content>
    ${object.property}
</#if>
```

## Formatting Patterns

### Currency Display
```freemarker
<#assign currency_symbol = "$">

${currency_symbol}${amount?string["#,##0.00"]}
```

### Conditional Currency (hide zero)
```freemarker
<#if amount?number != 0>
    ${currency_symbol}${amount}
</#if>
```

### Date Formatting
```freemarker
<#assign today = .now?date>
${today?string("MM/dd/yyyy")}
${today?string.medium}
```

### Number with Sign
```freemarker
<#if value?number >= 0>
    ${value}
<#else>
    (${value?number?abs})
</#if>
```

## Conditional Styling Patterns

### Color by Value
```freemarker
<td style="color:
    <#if value?number > 0>green
    <#elseif value?number < 0>red
    <#else>black
    </#if>;">
    ${value}
</td>
```

### Status Badge
```freemarker
<span class="badge
    <#if status == 'Active'>badge-success
    <#elseif status == 'Pending'>badge-warning
    <#else>badge-danger
    </#if>">
    ${status}
</span>
```

### Aging Color Coding
```freemarker
<#if days_overdue?number <= 0>
    <span style="color: green;">Current</span>
<#elseif days_overdue?number <= 30>
    <span style="color: orange;">1-30 Days</span>
<#elseif days_overdue?number <= 60>
    <span style="color: darkorange;">31-60 Days</span>
<#else>
    <span style="color: red;">60+ Days</span>
</#if>
```

## Table Patterns

### Alternating Row Colors
```freemarker
<#list items as item>
    <tr style="background-color:
        <#if item_index % 2 == 0>#ffffff<#else>#f9f9f9</#if>;">
        <td>${item.name}</td>
    </tr>
</#list>
```

### Column Totals
```freemarker
<#assign col1_total = 0>
<#assign col2_total = 0>

<#list items as item>
    <tr>
        <td>${item.col1}</td>
        <td>${item.col2}</td>
    </tr>
    <#assign col1_total = col1_total + item.col1?number>
    <#assign col2_total = col2_total + item.col2?number>
</#list>

<tr class="total">
    <td><strong>${col1_total}</strong></td>
    <td><strong>${col2_total}</strong></td>
</tr>
```

## Debug Patterns

### Debug Mode Toggle
```freemarker
<#assign debug_on = 0>

<#if debug_on == 1>
    <div style="background: #ffffcc; padding: 10px; margin: 10px 0;">
        <h4>Debug Info</h4>
        <p>Record ID: ${record.id}</p>
        <p>Row count: ${tran.rows?size}</p>
    </div>
</#if>
```

### Show Available Fields
```freemarker
<#if debug_on == 1>
    <pre>
    <#if tran.rows?has_content && tran.rows[0]??>
        First row keys: ${tran.rows[0]?keys?join(", ")}
    </#if>
    </pre>
</#if>
```

## Address Patterns

### Multi-line Address
```freemarker
${record.billaddressee}<br/>
${record.billaddr1}<br/>
<#if record.billaddr2?has_content>${record.billaddr2}<br/></#if>
${record.billcity}, ${record.billstate} ${record.billzip}<br/>
${record.billcountry}
```

### Conditional Address Lines
```freemarker
<#macro formatAddress addr>
    <#if addr.addressee?has_content>${addr.addressee}<br/></#if>
    <#if addr.attention?has_content>Attn: ${addr.attention}<br/></#if>
    <#if addr.addr1?has_content>${addr.addr1}<br/></#if>
    <#if addr.addr2?has_content>${addr.addr2}<br/></#if>
    <#if addr.city?has_content || addr.state?has_content || addr.zip?has_content>
        ${addr.city!""}<#if addr.city?has_content && addr.state?has_content>, </#if>${addr.state!""} ${addr.zip!""}
    </#if>
</#macro>
```

## Customer Name Patterns

### Person vs Company
```freemarker
<#if customer[0].isperson>
    ${customer[0].firstname} ${customer[0].lastname}
<#else>
    ${customer[0].companyname}
</#if>
```

### With Fallback
```freemarker
<#if customer[0].isperson && (customer[0].firstname?has_content || customer[0].lastname?has_content)>
    ${customer[0].firstname!""} ${customer[0].lastname!""}
<#elseif !customer[0].isperson && customer[0].companyname?has_content>
    ${customer[0].companyname}
<#else>
    Valued Customer
</#if>
```

## PDF-Specific Patterns

### Page Break
```freemarker
<pbr/>
```

### Keep Together
```freemarker
<table style="page-break-inside: avoid;">
    <!-- Content that should stay on same page -->
</table>
```

### Header/Footer with Page Numbers
```freemarker
<macro id="footer">
    <table style="width: 100%;">
        <tr>
            <td align="left">Confidential</td>
            <td align="right">Page <pagenumber/> of <totalpages/></td>
        </tr>
    </table>
</macro>
```
