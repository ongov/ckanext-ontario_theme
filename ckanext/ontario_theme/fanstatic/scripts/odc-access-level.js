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
  }
  accessLevelButtons.forEach(element => {
      element.addEventListener('change', showAccessLevel)
  })
  function showAccessLevel() {
      if (this.checked) {
        let params = new URLSearchParams(document.location.search);
        if (params.has('page')) {
          params.delete('page');
        }
        if (params.has(this.name)) {
          params.set(this.name, this.value);
        } else {
          params.append(this.name, this.value);
        }
        window.location.search = params;
      }
  }

  window.addEventListener('load', updateAccessLevelSentence)

  function updateAccessLevelSentence() {
    var selectedButton = document.querySelector('input[name="access_level"]:checked');
    if (selectedButton) {
      var displayName = selectedButton.getAttribute('data-display-name').trim();
      var calloutElement = document.querySelector('.access-level-status');
      calloutElement.querySelector('#access-level-sentence-value').textContent = displayName;
      var selectedColor = selectedButton.getAttribute('data-color')
      calloutElement.classList.add(`ontario-border-highlight--${selectedColor}`);
    }
  }
})();