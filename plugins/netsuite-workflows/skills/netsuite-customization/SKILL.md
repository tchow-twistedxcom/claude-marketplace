---
name: netsuite-customization
description: "Advanced NetSuite customization patterns including workflows, saved searches, forms, and integrations. Use when implementing complex NetSuite business logic."
license: MIT
---

# NetSuite Advanced Customization Patterns

## Workflow Customization

### Workflow Design Patterns

**Approval Workflow Pattern**
```xml
<workflow scriptid="customworkflow_approval_process">
    <name>Approval Process</name>
    <recordtype>transaction</recordtype>

    <workflowstates>
        <workflowstate scriptid="workflowstate_pending">
            <name>Pending Approval</name>
            <positionx>100</positionx>
            <positiony>100</positiony>
        </workflowstate>
        <workflowstate scriptid="workflowstate_approved">
            <name>Approved</name>
        </workflowstate>
    </workflowstates>

    <workflowtransitions>
        <workflowtransition>
            <tostate>workflowstate_approved</tostate>
            <conditionstype>AND</conditionstype>
            <workflowconditions>
                <!-- Condition logic -->
            </workflowconditions>
        </workflowtransition>
    </workflowtransitions>
</workflow>
```

### Workflow Actions
- **Set Field Value**: Update record fields
- **Send Email**: Notify stakeholders
- **Create Record**: Generate related records
- **Execute Script**: Run custom logic

## Saved Search Patterns

### Formula-Based Search
```javascript
// Saved Search with custom formula
{
    type: search.Type.TRANSACTION,
    filters: [
        ['type', 'anyof', 'SalesOrd'],
        'AND',
        ['formulanumeric: CASE WHEN {amount} > 1000 THEN 1 ELSE 0 END', 'equalto', '1']
    ],
    columns: [
        'tranid',
        'entity',
        'amount',
        search.createColumn({
            name: 'formulacurrency',
            formula: '{amount} * 1.1',
            label: 'Amount with Tax'
        })
    ]
}
```

### Join Searches
```javascript
// Search with joins
{
    type: search.Type.CUSTOMER,
    filters: [
        ['transaction.type', 'anyof', 'SalesOrd'],
        'AND',
        ['transaction.trandate', 'within', 'thisyear']
    ],
    columns: [
        'entityid',
        search.createColumn({
            name: 'amount',
            join: 'transaction',
            summary: 'SUM'
        })
    ]
}
```

## Form Customization

### Custom Form Fields Layout
```xml
<entryform scriptid="customform_sales_order_enhanced">
    <name>Enhanced Sales Order</name>
    <recordtype>salesorder</recordtype>

    <tabs>
        <tab>
            <tablabel>Custom Info</tablabel>
            <fields>
                <field>
                    <fieldid>custbody_approval_status</fieldid>
                    <fieldlabel>Approval Status</fieldlabel>
                    <visible>T</visible>
                </field>
            </fields>
        </tab>
    </tabs>
</entryform>
```

## Script Patterns

### User Event Script (Record Validation)
```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType UserEventScript
 */
define(['N/record', 'N/error'], function(record, error) {

    function beforeSubmit(context) {
        var currentRecord = context.newRecord;

        // Validation logic
        var amount = currentRecord.getValue({
            fieldId: 'total'
        });

        if (amount > 10000) {
            var approvalStatus = currentRecord.getValue({
                fieldId: 'custbody_approval_status'
            });

            if (!approvalStatus || approvalStatus === 'Pending') {
                throw error.create({
                    name: 'APPROVAL_REQUIRED',
                    message: 'Approval required for amounts over $10,000'
                });
            }
        }
    }

    return {
        beforeSubmit: beforeSubmit
    };
});
```

### Scheduled Script (Batch Processing)
```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType ScheduledScript
 */
define(['N/search', 'N/record', 'N/runtime'], function(search, record, runtime) {

    function execute(context) {
        var script = runtime.getCurrentScript();

        // Search for records to process
        var recordsSearch = search.create({
            type: search.Type.SALES_ORDER,
            filters: [
                ['status', 'anyof', 'SalesOrd:A'],
                'AND',
                ['custbody_processed', 'is', 'F']
            ]
        });

        recordsSearch.run().each(function(result) {
            // Check remaining usage
            if (script.getRemainingUsage() < 50) {
                return false; // Stop and reschedule
            }

            try {
                // Process record
                record.submitFields({
                    type: record.Type.SALES_ORDER,
                    id: result.id,
                    values: {
                        custbody_processed: true
                    }
                });
            } catch (e) {
                log.error('Processing Error', e);
            }

            return true; // Continue processing
        });
    }

    return {
        execute: execute
    };
});
```

### RESTlet (External Integration)
```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 */
define(['N/record', 'N/search'], function(record, search) {

    function post(requestBody) {
        try {
            // Create record from external data
            var newRecord = record.create({
                type: record.Type.SALES_ORDER
            });

            newRecord.setValue({
                fieldId: 'entity',
                value: requestBody.customerId
            });

            // Add line items
            requestBody.items.forEach(function(item) {
                newRecord.selectNewLine({
                    sublistId: 'item'
                });
                newRecord.setCurrentSublistValue({
                    sublistId: 'item',
                    fieldId: 'item',
                    value: item.itemId
                });
                newRecord.setCurrentSublistValue({
                    sublistId: 'item',
                    fieldId: 'quantity',
                    value: item.quantity
                });
                newRecord.commitLine({
                    sublistId: 'item'
                });
            });

            var recordId = newRecord.save();

            return {
                success: true,
                recordId: recordId
            };

        } catch (e) {
            return {
                success: false,
                error: e.message
            };
        }
    }

    function get(requestParams) {
        // Retrieve record data
        var recordId = requestParams.id;
        var recordData = record.load({
            type: record.Type.SALES_ORDER,
            id: recordId
        });

        return {
            tranId: recordData.getValue('tranid'),
            customer: recordData.getText('entity'),
            total: recordData.getValue('total')
        };
    }

    return {
        get: get,
        post: post
    };
});
```

## Integration Patterns

### External API Integration
```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType MapReduceScript
 */
define(['N/https', 'N/record'], function(https, record) {

    function getInputData() {
        // Fetch data from external API
        var response = https.get({
            url: 'https://api.example.com/orders',
            headers: {
                'Authorization': 'Bearer TOKEN'
            }
        });

        return JSON.parse(response.body);
    }

    function map(context) {
        var data = JSON.parse(context.value);

        // Transform and process
        context.write({
            key: data.orderId,
            value: data
        });
    }

    function reduce(context) {
        var orderData = JSON.parse(context.values[0]);

        // Create NetSuite record
        var salesOrder = record.create({
            type: record.Type.SALES_ORDER
        });

        // Set fields from external data
        salesOrder.setValue({
            fieldId: 'custbody_external_id',
            value: orderData.orderId
        });

        salesOrder.save();
    }

    return {
        getInputData: getInputData,
        map: map,
        reduce: reduce
    };
});
```

## Performance Optimization

### Governance Best Practices
```javascript
// Use search.lookupFields for single record
var fieldValues = search.lookupFields({
    type: search.Type.CUSTOMER,
    id: customerId,
    columns: ['email', 'phone']
});

// Batch operations
var recordIds = [1, 2, 3, 4, 5];
recordIds.forEach(function(id) {
    // Use submitFields instead of load/save
    record.submitFields({
        type: record.Type.CUSTOMER,
        id: id,
        values: {
            custentity_status: 'Active'
        }
    });
});
```

### Caching Strategy
```javascript
// Cache search results
var cache = {};

function getCachedCustomer(customerId) {
    if (!cache[customerId]) {
        cache[customerId] = record.load({
            type: record.Type.CUSTOMER,
            id: customerId
        });
    }
    return cache[customerId];
}
```

## Error Handling & Logging

### Comprehensive Error Handling
```javascript
try {
    // Business logic
    var result = processRecord(recordId);

    log.audit({
        title: 'Record Processed',
        details: 'Record ID: ' + recordId + ' | Result: ' + JSON.stringify(result)
    });

} catch (e) {
    log.error({
        title: 'Processing Error',
        details: {
            name: e.name,
            message: e.message,
            stack: e.stack,
            recordId: recordId
        }
    });

    // Send notification for critical errors
    if (e.name === 'CRITICAL_ERROR') {
        email.send({
            author: ADMIN_USER_ID,
            recipients: ADMIN_EMAIL,
            subject: 'Critical Error in Script',
            body: e.message
        });
    }
}
```

## Testing Patterns

### Mock NetSuite Modules
```javascript
// test/mocks/N-record.js
module.exports = {
    create: function(options) {
        return mockRecord;
    },
    load: function(options) {
        return mockRecord;
    }
};

// test/script.test.js
var record = require('./mocks/N-record');
var myScript = require('../src/script');

// Test your script logic
```

## Deployment Checklist

- [ ] All scripts tested in sandbox
- [ ] Error handling implemented
- [ ] Logging added for audit trail
- [ ] Performance optimized (governance usage)
- [ ] Security reviewed (role permissions)
- [ ] Documentation updated
- [ ] Rollback plan prepared
- [ ] Stakeholders notified
