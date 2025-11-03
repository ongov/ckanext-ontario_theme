// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.

/*
 * CKAN module function to redirect to logical page in the admin panel step
 * indicator
 * 
 * url
 *  URL to be redirected to when clicking the back button
 */
"use strict";

ckan.module('step-indicator', function ($) {
  return {
      initialize: function () {
      this.el.on('click', jQuery.proxy(this._onClick, this));
    },
    _onClick: function (event) {
        window.location.href = this.options.url;
    }
  }
});