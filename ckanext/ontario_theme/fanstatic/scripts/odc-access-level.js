/*
 * Function for changing URL parameters when an access level
 * checkbox is clicked.
 *
 */

(function () {
    var accessLevelBoxes = document.querySelectorAll('input[name="access_level"][type="checkbox"]');
    let params = new URLSearchParams(document.location.search);
    var openCheckbox = document.getElementById("checkbox-option-open");
    if (!params.has("access_level") && openCheckbox) {
        openCheckbox.checked = true;
    } else if (params.has("access_level")) {
        let selected_levels = params.getAll("access_level");
        selected_levels.forEach((e) => {
            document.getElementById(`checkbox-option-${e}`).checked = true
        });
    }

    accessLevelBoxes.forEach(element => {
        element.addEventListener('change', showAccessLevel)
    })

    function showAccessLevel() {
        let params = new URLSearchParams(document.location.search);
        const isChecked = this.checked;
        const paramName = this.name;
        const paramValue = this.value;
        if (openCheckbox.checked && !params.has(paramName)) {
            params.append(paramName, openCheckbox.value)
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
    }

    window.addEventListener('load', updateAccessLevelSentence)
  
    function updateAccessLevelSentence() {
        const selectedBoxes = document.querySelectorAll('input[name="access_level"]:checked');
        const allLevels = document.getElementById('access-level-checkboxes');
        const calloutElement = document.getElementById('access-level-sentence-value');
    
        let displayName = "";
    
        if (selectedBoxes.length === accessLevelBoxes.length) {
            displayName = allLevels.dataset.value;
        } else if (selectedBoxes.length === 1) {
            displayName = selectedBoxes[0].getAttribute('data-display-name');
        } else {
            selectedBoxes.forEach((box, index) => {
                displayName += box.getAttribute('data-display-name');
                if (index < selectedBoxes.length - 1) {
                    displayName += calloutElement.dataset.and;
                }
            });
        }
    
        if (calloutElement) {
            calloutElement.textContent = displayName;
        }
    }
    
  })();