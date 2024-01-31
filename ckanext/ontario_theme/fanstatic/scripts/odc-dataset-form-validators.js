// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
"use strict";

ckan.module('conditional_field', function ($) {
  return {
    options : {
      conditional_option: null,
      trigger_values: null,
		},
    initialize: function () {
      console.log(this.options.trigger_field);
      this.trigger_values = (this.options.conditional_option).split(",");
      console.log(this.trigger_values);
      $(this.options.trigger_field).on('change', jQuery.proxy(this._onChange, this));
      /* $(this.options.trigger_field).on('change', jQuery.proxy(this._onChange, this));
      this.trigger_values = (this.options.conditional_option).split("")
      $(this.options.trigger_field).change() */
    },
    _onChange: function (event) {
      var option_selected = event.target.value
      var id = $(this.el).attr('id');
      if ($.inArray(option_selected, this.trigger_values) != -1) {
        console.log(id);
        $("#field-license_id option[value=other-closed]").attr('selected', true);
        //$(this.el).val("other-closed").change();
      }
    }
  }
});