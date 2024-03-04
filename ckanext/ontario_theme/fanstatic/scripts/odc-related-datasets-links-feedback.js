//Shows the input field in the Related datasets section at the bottom and right-hand side of the page when user clicks on no as a radio button option

(function () {

  const yesNoRadioButtons = document.querySelectorAll('[id^="radio-button-option-"');

  yesNoRadioButtons.forEach(element => {
    element.addEventListener('change', handleRadioButton)
  })

  function handleRadioButton() {
    let explanationInput = document.getElementById(`feedback-input-${this.dataset.feedback}`)
    if (this.value === 'option-no' && this.checked) {
      explanationInput.style.display = "block";
    } else {
      explanationInput.style.display = "none";
    }
  }
})();