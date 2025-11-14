/**
 * @NApiVersion 2.1
 * @NScriptType Suitelet
 * @NModuleScope SameAccount
 *
 * Reset Stuck Queue Entries
 *
 * This script resets queue entries that have been stuck in "Processing"
 * status for more than 1 hour. Use this when queue processing appears
 * to be frozen.
 *
 * Usage:
 * 1. Deploy as Suitelet
 * 2. Navigate to Suitelet URL
 * 3. Enter queue name (PRI_PMLN_QUEUE, PRI_LC_TEMPLATE, etc.)
 * 4. Click "Reset Stuck Entries"
 */

define(['N/record', 'N/search', 'N/ui/serverWidget', 'N/log'],
function(record, search, serverWidget, log) {

    function onRequest(context) {
        if (context.request.method === 'GET') {
            var form = serverWidget.createForm({
                title: 'Reset Stuck Queue Entries'
            });

            form.addField({
                id: 'custpage_queue_name',
                type: serverWidget.FieldType.SELECT,
                label: 'Queue Name'
            }).addSelectOption({
                value: '',
                text: ''
            }).addSelectOption({
                value: 'PRI_PMLN_QUEUE',
                text: 'Production PO Line Queue'
            }).addSelectOption({
                value: 'PRI_LC_TEMPLATE',
                text: 'Landed Cost Template Queue'
            }).addSelectOption({
                value: 'PRI_RECEIVE_CONTAINER',
                text: 'Receive Container Queue'
            }).addSelectOption({
                value: 'PRI_MARK_INTRANSIT',
                text: 'Mark In-Transit Queue'
            });

            form.addSubmitButton({
                label: 'Reset Stuck Entries'
            });

            context.response.writePage(form);
        }
        else {
            // POST - Process reset
            var queueName = context.request.parameters.custpage_queue_name;

            if (!queueName) {
                context.response.write('Error: Queue name required');
                return;
            }

            // Find stuck entries (Processing status, created > 1 hour ago)
            var stuckEntries = search.create({
                type: 'customrecord_pri_qm_queue',
                filters: [
                    ['custrecord_pri_qm_queue_name', 'is', queueName],
                    'AND',
                    ['custrecord_pri_qm_queue_status', 'is', 'Processing'],
                    'AND',
                    ['created', 'before', 'hoursago1']
                ],
                columns: ['internalid']
            }).run().getRange({ start: 0, end: 100 });

            var resetCount = 0;
            stuckEntries.forEach(function(entry) {
                try {
                    record.submitFields({
                        type: 'customrecord_pri_qm_queue',
                        id: entry.id,
                        values: {
                            custrecord_pri_qm_queue_status: 'Pending'
                        }
                    });
                    resetCount++;
                }
                catch (e) {
                    log.error('Reset Failed', 'Entry ' + entry.id + ': ' + e.message);
                }
            });

            context.response.write({
                output: 'Success! Reset ' + resetCount + ' queue entries for ' + queueName
            });

            log.audit('Queue Reset', resetCount + ' entries reset for ' + queueName);
        }
    }

    return {
        onRequest: onRequest
    };
});
