// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.

"use strict";

ckan.module('facet_checkboxes', function ($) {
  return {
    initialize: function () {
          $(".facet-fieldset :checkbox").on('click', jQuery.proxy(this._onChange, this));
    },
      _onChange: function (event) {
          window.location.href = event.target.value;
    }
  }
});