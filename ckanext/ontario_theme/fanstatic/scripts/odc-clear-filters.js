// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.

"use strict";

ckan.module('clear_filters', function ($) {
  return {
      initialize: function () {
          var clearFiltersButton = $("#clear-filters-button");
          var facetsSelected = $(".filtered.pill");
          if (facetsSelected.length >= 2) {
              clearFiltersButton.css({ display: "inline-block" });
              clearFiltersButton.on('click', jQuery.proxy(this._onChange, this));
          }
    },
    _onChange: function (event) {
        $(('#fields')).empty();

      var form = $('form.search-form');
      form.submit();
    }
  }
});