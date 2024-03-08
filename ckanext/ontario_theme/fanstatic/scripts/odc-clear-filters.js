(function () {
    var clearFiltersButton = document.getElementById("clear-filters-button");
    if (clearFiltersButton) {
        clearFiltersButton.addEventListener('click', clearFilters);
    }
    function clearFilters() {
        const url = window.location.href.split('?')[0];
        let params = new URLSearchParams(document.location.search);
        let array = Array.from(params);
        for (const field of array) {
            const [key, value] = field;
            if (!(key == 'access_level' || key == 'q')) {
                params.delete(key);
            }
        }
        window.location.href = `${url}?${params}`;
    }
})();