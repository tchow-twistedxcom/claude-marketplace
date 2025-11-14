/**
 * @NApiVersion 2.1
 * @NScriptType Suitelet
 * @NModuleScope SameAccount
 *
 * Sync Container Dates to TO/IF
 *
 * Manually sync container ETD/ATA dates to linked Transfer Order
 * and Item Fulfillment records when automatic sync fails.
 *
 * Usage:
 * 1. Deploy as Suitelet
 * 2. Navigate to Suitelet URL
 * 3. Enter Container Internal ID
 * 4. Click "Sync Dates"
 */

define(['N/record', 'N/search', 'N/ui/serverWidget', 'N/log'],
function(record, search, serverWidget, log) {

    function onRequest(context) {
        if (context.request.method === 'GET') {
            var form = serverWidget.createForm({
                title: 'Sync Container Dates'
            });

            form.addField({
                id: 'custpage_container_id',
                type: serverWidget.FieldType.TEXT,
                label: 'Container Internal ID'
            });

            form.addSubmitButton({
                label: 'Sync Dates'
            });

            context.response.writePage(form);
        }
        else {
            // POST - Process sync
            var containerId = context.request.parameters.custpage_container_id;

            if (!containerId) {
                context.response.write('Error: Container ID required');
                return;
            }

            try {
                var result = syncContainerDates(containerId);
                context.response.write({
                    output: 'Success! ' + result
                });
            }
            catch (e) {
                context.response.write('Error: ' + e.message);
                log.error('Sync Failed', e.message);
            }
        }
    }

    function syncContainerDates(containerId) {
        // Load container
        var container = record.load({
            type: 'customrecord_pri_frgt_cnt',
            id: containerId
        });

        var etd = container.getValue('custrecord_pri_frgt_cnt_etd');
        var ata = container.getValue('custrecord_pri_frgt_cnt_ata');
        var toId = container.getValue('custrecord_pri_frgt_cnt_trnfrord');

        if (!toId) {
            return 'Container has no Transfer Order linked';
        }

        // Update Transfer Order
        record.submitFields({
            type: record.Type.TRANSFER_ORDER,
            id: toId,
            values: {
                shipdate: etd,
                expectedreceiptdate: ata
            }
        });

        log.audit('TO Dates Synced', 'TO ' + toId + ' dates updated');

        // Find and update Item Fulfillment
        var ifSearch = search.create({
            type: search.Type.ITEM_FULFILLMENT,
            filters: [
                ['createdfrom', 'is', toId]
            ],
            columns: ['internalid']
        }).run().getRange({ start: 0, end: 1 });

        var updatedRecords = 'TO ' + toId;

        if (ifSearch.length > 0) {
            var ifId = ifSearch[0].id;
            record.submitFields({
                type: record.Type.ITEM_FULFILLMENT,
                id: ifId,
                values: {
                    trandate: etd
                }
            });

            log.audit('IF Dates Synced', 'IF ' + ifId + ' date updated');
            updatedRecords += ', IF ' + ifId;
        }

        return 'Dates synced for: ' + updatedRecords;
    }

    return {
        onRequest: onRequest
    };
});
