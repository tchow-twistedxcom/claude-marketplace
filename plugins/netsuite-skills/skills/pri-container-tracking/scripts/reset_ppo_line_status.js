/**
 * @NApiVersion 2.1
 * @NScriptType Suitelet
 * @NModuleScope SameAccount
 *
 * Reset Production PO Line Status
 *
 * Reset a Production PO Line from "Locked" (2) to "Available" (1) status
 * when the line was incorrectly locked without a PO being generated.
 *
 * WARNING: Only use when you've verified no PO exists for this line!
 *
 * Usage:
 * 1. Deploy as Suitelet
 * 2. Navigate to Suitelet URL
 * 3. Enter Production PO Line Internal ID
 * 4. Click "Reset Status"
 */

define(['N/record', 'N/ui/serverWidget', 'N/log'],
function(record, serverWidget, log) {

    function onRequest(context) {
        if (context.request.method === 'GET') {
            var form = serverWidget.createForm({
                title: 'Reset Production PO Line Status'
            });

            form.addField({
                id: 'custpage_line_id',
                type: serverWidget.FieldType.TEXT,
                label: 'Production PO Line Internal ID'
            });

            var warningField = form.addField({
                id: 'custpage_warning',
                type: serverWidget.FieldType.INLINEHTML,
                label: 'Warning'
            });

            warningField.defaultValue = '<b style="color: red;">WARNING:</b> Only use this tool when you have verified that no Purchase Order exists for this line. Resetting the status of a line with an existing PO can cause data integrity issues.';

            form.addSubmitButton({
                label: 'Reset Status'
            });

            context.response.writePage(form);
        }
        else {
            // POST - Process reset
            var lineId = context.request.parameters.custpage_line_id;

            if (!lineId) {
                context.response.write('Error: Line ID required');
                return;
            }

            try {
                // Load line to check current state
                var line = record.load({
                    type: 'customrecord_pri_frgt_cnt_pmln',
                    id: lineId
                });

                var currentStatus = line.getValue('custrecord_pri_frgt_cnt_pmln_status');
                var linkedPO = line.getValue('custrecord_pri_frgt_cnt_pmln_linkedpo');

                if (linkedPO) {
                    context.response.write('Error: Line has a linked PO (' + linkedPO + '). Cannot reset status.');
                    return;
                }

                if (currentStatus === '1') {
                    context.response.write('Notice: Line is already in Available status (1)');
                    return;
                }

                // Reset status
                record.submitFields({
                    type: 'customrecord_pri_frgt_cnt_pmln',
                    id: lineId,
                    values: {
                        custrecord_pri_frgt_cnt_pmln_status: 1 // Available
                    }
                });

                log.audit('Status Reset', 'Line ' + lineId + ' reset from status ' + currentStatus + ' to Available (1)');

                context.response.write({
                    output: 'Success! Line ' + lineId + ' status reset to Available (1)'
                });
            }
            catch (e) {
                context.response.write('Error: ' + e.message);
                log.error('Reset Failed', e.message);
            }
        }
    }

    return {
        onRequest: onRequest
    };
});
