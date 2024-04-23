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
    var sentenceContainer = document.querySelector(".access-level-status");
    var selectedButton = document.querySelector('input[name="access_level"]:checked');
    if (selectedButton) {
      var display_name = selectedButton.nextElementSibling.textContent.trim();
      var display_name_without_count = display_name.replace(/\s*\(\d+\)$/, '');
      sentenceContainer.querySelector('#access-level-sentence-value').textContent = display_name_without_count;
      var selectedValue = selectedButton.value;
      var selectedColor = "#7B725C";
      switch (selectedValue) {
        case "under_review":
          selectedColor = "#92278F";
          break;
        case "restricted":
          selectedColor = "#D81A21";
          break;
        case "open":
          selectedColor = "#367A76";
          break;
      }
      sentenceContainer.style.borderLeftColor = selectedColor;
    }
  }
})();