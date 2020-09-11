// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
"use strict";

ckan.module('conditional_behaviours', function ($) {  
  return {
    hide_if: null,
    show_if: null,
    trigger_values: null,
    initialize: function () {

      $(this.options.trigger_field).on('change', jQuery.proxy(this._onChange, this));
      // which values will trigger hide/show
      this.trigger_values = ("show_if" in this.options ? this.options.show_if : this.options.hide_if).split(",")
      this.field_container = this.el.parents("div.controls.row")

      $(this.options.trigger_field).change()
      return null
    },
    _onChange: function (event) {
      var value_selected = event.target.value

      if ($.inArray(value_selected, this.trigger_values) != -1) {
        if (!!this.options.hide_if) {
          this.field_container.hide()
        }
        else if (!!this.options.show_if) {
          this.field_container.show()

        }
      } else {
        if (!!this.options.hide_if) {
          this.field_container.show()
        }
        else if (!!this.options.show_if) {
          this.field_container.hide()

        }
      }
    }
  };
});


