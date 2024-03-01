//Shows the input field in the Related datasets section at the bottom and right-hand side of the page when user clicks on no as a radio button option

(function () {
  var noRadioButton = document.getElementById("radio-button-option-no");
  var yesRadioButton = document.getElementById("radio-button-option-yes");
  var noRadioButtonRight = document.getElementById("radio-button-option-no-right");
  var yesRadioButtonRight = document.getElementById("radio-button-option-yes-right");

  var explanationInput = document.getElementById("feedback-input-bottom");
  var explanationInputRight = document.getElementById("feedback-input-right");

  noRadioButton.addEventListener('change', handleRadioButton);
  yesRadioButton.addEventListener('change', handleRadioButton);
  noRadioButtonRight.addEventListener('change', handleRadioButtonRight);
  yesRadioButtonRight.addEventListener('change', handleRadioButtonRight);

  function handleRadioButton() {
    if (noRadioButton.checked) {
      explanationInput.style.display = "block";
    } else {
      explanationInput.style.display = "none";
    }
  }

  function handleRadioButtonRight() {
    if (noRadioButtonRight.checked) {
      explanationInputRight.style.display = "block";
    } else {
      explanationInputRight.style.display = "none";
    }
  }

})();