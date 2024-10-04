// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.

/*
 * CKAN module function for submitting form with empty facets once the clear
 * filters button is clicked
 */

"use strict";

ckan.module('clear_filters', function ($) {
  return {
      initialize: function () {
          const facetsSelected = $(".filtered.pill");
          if (facetsSelected.length >= 2) {
              this.el.css({ display: "inline-block" });
              this.el.on('click', jQuery.proxy(this._onClick, this));
          }
    },
    _onClick: function (event) {
        $('#fields').empty();
        let form = $('form.search-form');
        form.submit();
    }
  }
});