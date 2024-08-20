// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.

/*
 * CKAN module function for submitting form on facet checkbox selection with
 * CKAN's hidden form inputs
 */

"use strict";

ckan.module('facet_checkboxes', function ($) {
  return {
    initialize: function () {
      $(".facet-fieldset :checkbox").on('click', jQuery.proxy(this._onChange, this));
    },
    _onChange: function (event) {
      const hiddenFields = $(('#fields'));
      if (event.target.checked) {
        $('<input>').attr({
          type: 'hidden',
          name: event.target.name,
          value: event.target.value
        }).appendTo(hiddenFields);
      } else {
        $(`input[name='${event.target.name}'][value='${event.target.value}']`).remove();
      }
      var form = $('form.search-form');
      form.submit();
    }
  }
});