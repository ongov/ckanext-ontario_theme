/*
 * Function for changing URL parameters when an access level
 * radio button is clicked.
 *
 */

(function () {
    var accessLevelButtons = document.querySelectorAll('input[name="access_level"]');
    let params = new URLSearchParams(document.location.search);
    var openRadioButton = document.getElementById("radio-button-option-open");
    if (!params.has("access_level") && openRadioButton) {
        openRadioButton.checked = true;
    } else if (params.has("access_level")) {
        let selected_levels = params.getAll("access_level");
        selected_levels.forEach((e) =>
            document.getElementById(`radio-button-option-${e}`).checked = true);
    }
    accessLevelButtons.forEach(element => {
        element.addEventListener('change', showAccessLevel)
    })
    function showAccessLevel() {
        if (this.checked) {
          let params = new URLSearchParams(document.location.search);
          if (params.has('page')) {
            params.delete('page');
          } else {
            params.append(this.name, this.value);
          }
          window.location.search = params;
        } else {
            if (params.has(this.name, this.value)) {
                params.delete(this.name, this.value);
            }
            window.location.search = params;
        }
    }
  
    // window.addEventListener('load', updateAccessLevelSentence)
  
    /* function updateAccessLevelSentence() {
      var selectedButton = document.querySelector('input[name="access_level"]:checked');
      if (selectedButton) {
        var displayName = selectedButton.getAttribute('data-display-name').trim();
        var calloutElement = document.querySelector('.access-level-status');
        calloutElement.querySelector('#access-level-sentence-value').textContent = displayName;
        var selectedColor = selectedButton.getAttribute('data-color')
        calloutElement.classList.add(`ontario-border-highlight--${selectedColor}`);
      }
    } */
  })();