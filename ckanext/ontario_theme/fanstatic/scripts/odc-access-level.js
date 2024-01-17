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

})();