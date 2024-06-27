// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.

/*
 * CKAN module function for changing URL parameters on checkbox selection and
 * updating callout
 *
 * accessLevelBoxes
 *  All the access level checkboxes in the search bar
 * openCheckbox
 *  The checkbox with value open
 */
"use strict";

ckan.module('access_level_checkboxes', function ($) {
    return {
        options: {
            accessLevelBoxes: null,
            openCheckbox: null,
		},
        initialize: function () {
            this.accessLevelBoxes = $('input[name="access_level"][type="checkbox"]');
            var params = new URLSearchParams(document.location.search);
            this.openCheckbox = $("#checkbox-option-open");
            // "Open" checkbox checked by default
            // else get access_level params and check the appropriate boxes
            if (!params.has("access_level") && this.openCheckbox) {
                this.openCheckbox.prop('checked', true);
            } else if (params.has("access_level")) {
                var selected_levels = params.getAll("access_level");
                selected_levels.forEach(function(e) {
                    $(`#checkbox-option-${e}`).prop('checked', true);
                });
            }
            // Update checkboxes and callout
            $(this.accessLevelBoxes).on('change', jQuery.proxy(this._onChange, this));
            $(document).ready(jQuery.proxy(this._updateAccessLevelSentence, this));
        },
        _onChange: function (event) {
            var target = event.target;
            var isChecked = $(target).prop('checked');
            const paramName = $(target).attr('name');
            var paramValue = $(target).val();
            var params = new URLSearchParams(document.location.search);

            // Add "access_level=open" to queries by default
            if (this.openCheckbox.is(':checked') && !params.has(paramName)) {
                params.append(paramName, this.openCheckbox.val());
            }

            if (isChecked) {
                if (params.has('page')) {
                    params.delete('page');
                }
                params.append(paramName, paramValue);
            } else {
                if (params.has(paramName, paramValue)) {
                    params.delete(paramName, paramValue);
                }
            }
            window.location.search = params;
        },
        _updateAccessLevelSentence: function () {
            var selectedBoxes = $('input[name="access_level"]:checked');
            var calloutElement = $('#access-level-sentence-value');
            const and = this._(' and ');
            const all_levels = this._('All levels');

            var displayName = "";

            // Update callout based on number of checkboxes checked and the value
            if (selectedBoxes.length === this.accessLevelBoxes.length) {
                displayName = all_levels;
            } else if (selectedBoxes.length === 1) {
                displayName = selectedBoxes.first().data('display-name');
            } else {
                selectedBoxes.each(function(index) {
                    displayName += $(this).data('display-name');
                    if (index < selectedBoxes.length - 1) {
                        displayName += and
                    }
                });
            }
            if (calloutElement) {
                calloutElement.text(displayName);
            }
        }
    }
});
