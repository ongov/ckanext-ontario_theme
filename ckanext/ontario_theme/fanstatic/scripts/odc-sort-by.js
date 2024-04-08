
(function () {
    let sortByButton = document.querySelector(".show-sort-by");
    // let hideSortBy = document.querySelector(".hide-sort-by");
    sortByButton.addEventListener("click", function (e) {
        e.preventDefault();
        document.body.classList.add("sort-by-modal");
    })
    /* hideSortBy.addEventListener("click", function (e) {
        document.body.classList.remove("sort-by-modal");
    })*/

})();