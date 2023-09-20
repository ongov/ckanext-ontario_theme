/*
 * Function for facets to show more or show less without being redirected to a new page
 *
 * For each facet, the Show more and Show less buttons have an event listener for a button click.
 * On click: list items are toggled to display: block or display: none,
 * button clicked is toggled to display: none or visible,
 * Show more or Show less button is shown depending on the original button clicked.
 *
 */

(function () {
    var showMoreButtons = document.querySelectorAll(".facets-show-more");
    var showLessButtons = document.querySelectorAll(".facets-show-less");
    showMoreButtons.forEach(element => {
        element.addEventListener('click', toggleShowMore)
    })
    showLessButtons.forEach(element => {
        element.addEventListener('click', toggleShowMore)
    })
    function toggleShowMore() {
        /* Toggle list items according to the facet */
        var showMoreId = this.id.substring(5);
        var listItems = document.querySelectorAll('.facet-' + showMoreId);
        listItems.forEach(listItem => {
            listItem.classList.toggle("show-more-items");
        });
        this.classList.toggle("ontario-hide");
        /* Show the Show more or Show less button depending on which button was clicked */
        var toggleButton = this.classList.contains("facets-show-less") ? 'more-' : 'less-';
        var showButton = document.getElementById(toggleButton + showMoreId);
        showButton.classList.toggle("ontario-hide");
    }

})();