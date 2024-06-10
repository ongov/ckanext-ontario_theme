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
        if (openCheckbox.checked && !params.has(this.name)) {
            params.append(this.name, openCheckbox.value)
        }
        if (this.checked) {
            if (params.has('page')) {
                params.delete('page');
            }
            params.append(this.name, this.value);
        } else {
            if (params.has(this.name, this.value)) {
                params.delete(this.name, this.value);
            }
        }
        window.location.search = params;
    }

    window.addEventListener('load', updateAccessLevelSentence)
  
    function updateAccessLevelSentence() {
        var selectedBox = document.querySelectorAll('input[name="access_level"]:checked');
        let displayName = "";
        let allLevels = document.getElementById('access-level-checkboxes');
        var calloutElement = document.getElementById('access-level-sentence-value');
        if (selectedBox.length == accessLevelBoxes.length) {
            displayName = allLevels.dataset.value;
        } else if (selectedBox.length == 1) {
            displayName = selectedBox[0].getAttribute('data-display-name');
        } else {
            selectedBox.forEach((box, key, selectedBox) => {
                if (Object.is(selectedBox.length - 1, key)) {
                    displayName += box.getAttribute('data-display-name');
                } else {
                    displayName += box.getAttribute('data-display-name') + calloutElement.dataset.and
                }
            })
        }
        if (calloutElement) {
            calloutElement.textContent = displayName;
        }
    }
  })();