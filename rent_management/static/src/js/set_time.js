odoo.define('field_timepicker.set_time_button', function(require) {
    "use strict";

    var FormController = require('web.FormController');
    var rpc = require('web.rpc');

    FormController.include({
        events: _.extend({}, FormController.prototype.events, {
            'click .oe_stat_button[set_current_time_js]': '_onSetCurrentTimeClick',
        }),

        /**
         * Handles the click on "Set Current Time" button
         */
        _onSetCurrentTimeClick: function(event) {
            event.preventDefault();
            var self = this;
            var record = this.model.get(this.handle);

            if (!record) {
                return;
            }

            // Call the Python function via RPC to get current time in user timezone
            rpc.query({
                model: 'sale.order',
                method: 'get_current_time_in_timezone',
                args: [],
            }).then(function(result) {
                // Update the time_field dynamically without saving
                self.model.notifyChanges({
                    time_field: result,
                });
            });
        },
    });
});
