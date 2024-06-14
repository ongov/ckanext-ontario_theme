(function () {
    var clearFiltersButton = document.getElementById("clear-filters-button");
    var facetsSelected = document.querySelectorAll(".filtered.pill");

    if (facetsSelected.length >= 2) {
        clearFiltersButton.style.display = "inline-block";
        clearFiltersButton.addEventListener('click', clearFilters);
    }
    function clearFilters() {
        const url = window.location.href.split('?')[0];
        let params = new URLSearchParams(document.location.search);
        let array = Array.from(params);
        for (const field of array) {
            const [key, value] = field;
            if ((key != 'q') && (key != 'access_level')) {
                params.delete(key);
            }
        }
        window.location.href = `${url}?${params}`;
    }
})();