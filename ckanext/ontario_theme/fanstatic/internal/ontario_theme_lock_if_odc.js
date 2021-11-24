// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
"use strict";

ckan.module('lock_if_odc', function ($) {  
  return {
    initialize: function () {
      var harvest_id = $(this.el).val()
      if (!!harvest_id) {
        if (harvest_id == "ontario-data-catalogue") {
          $(".lock_if_odc textarea, .lock_if_odc input").prop("readonly","readonly")
          $(".lock_if_odc select").attr("readonly","readonly")
        }
      }
      return null
    }
  };
});