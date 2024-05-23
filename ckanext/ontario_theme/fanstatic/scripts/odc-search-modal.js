
(function () {
    let sortByButton = document.querySelector(".show-sort-by");
    let sortByModal = document.getElementById("sort-by-modal");
    let closeSortButton = document.querySelector(".sort-by-close");
    let filterModal = document.getElementById("filter-aside");
    let filterButton = document.querySelector(".show-filters");
    
    if (sortByButton) {
        sortByButton.addEventListener("click", function (e) {
            e.preventDefault();
            document.body.classList.add("sort-by-modal");
        })
        closeSortButton.addEventListener("click", closeSortModal)
        closeSortButton.addEventListener("keydown", (event) => {
            if (event.key === " " || event.key === "Enter") {
                closeSortModal();
            }
        })
        function closeSortModal(event) {
            document.body.classList.remove("sort-by-modal");
        }
    }

    if (filterButton) {
        filterButton.addEventListener("click", function (e) {
            e.preventDefault();
        })
        let closeFilter = document.querySelector(".hide-filters");
        closeFilter.addEventListener("keydown", (event) => {
            if (event.key === " " || event.key === "Enter") {
                closeFilterModal();
            }
        })
        function closeFilterModal(event) {
            document.body.classList.remove("filters-modal");
        }
    }

    window.onclick = function(e) {
        if (e.target == sortByModal ) {
            closeSortModal();
        }
        if (e.target == filterModal ) {
            closeFilterModal();
        }
      }
    
})();