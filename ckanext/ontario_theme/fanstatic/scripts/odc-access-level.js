/*
 * Function for facets to show more or show less without being redirected to a new page
 *
 * For each facet, the Show more button has an event listener for a button click.
 * On click: list items are toggled to display: block or display: none,
 * button clicked is toggled to display Show less or Show more
 *
 */

(function () {
  var accessLevelButtons = document.querySelectorAll('input[name="access_level"]');
  accessLevelButtons.forEach(element => {
      element.addEventListener('change', showAccessLevel)
  })
  function showAccessLevel() {
      if (this.checked) {
        let params = new URLSearchParams(document.location.search)
        if (params.has(this.name)) {
          params.set(this.name, this.value);
        } else {
          params.append(this.name, this.value);
        }
        window.location.search = params;
      }
  }

})();