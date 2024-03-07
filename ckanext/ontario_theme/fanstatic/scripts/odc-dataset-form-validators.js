// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.

/*
 * CKAN module function to limit the options of a conditional field 
 * based on the user's selected choice on a triggered field
 * 
 * For example: When a user selects the access level of under review or restricted,
 * the only option for users is "Not Applicable", while the other options of the Licence
 * field are disabled
 * 
 * conditional_option
 *  The option(s), in a comma separated string, that will trigger the function when selected
 *  (E.g.: "under_review,restricted")
 * trigger_field
 *  The field that contains the conditional_option(s). (E.g.: Access Level)
 * trigger_option
 *  The option to be selected from the conditional field, disabling the other options. 
 *  (E.g.: Not applicable licence)
 */
"use strict";

ckan.module('conditional_field', function ($) {
  return {
    options : {
      trigger_values: null,
      field_options: null,
		},
    initialize: function () {
      this.trigger_values = (this.options.conditional_option).split(",");
      this.field_options = (this.el.find('option'))
      $(this.options.trigger_field).on('change', jQuery.proxy(this._onChange, this));
    },
    _onChange: function (event) {
      var option_selected = event.target.value
      let id = $(this.el).attr('id');
      if ($.inArray(option_selected, this.trigger_values) != -1) {
        $(`#${id}`).val(this.options.trigger_option).change();
        $(`#${id}`).find(':not(:selected)').remove();
      } else {
        $(`#${id}`).append(this.field_options)
      }
    }
  }
});