// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.

"use strict";

ckan.module('facet_checkboxes', function ($) {
  return {
    initialize: function () {
          $(":checkbox").on('click', jQuery.proxy(this._onChange, this));
    },
      _onChange: function (event) {
        let spinner = document.getElementById("spinner");
        spinner.setAttribute('aria-hidden', 'false');
    }
  }
});