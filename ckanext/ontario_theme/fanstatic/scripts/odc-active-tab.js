/*
 * Function for adding aria-current = "page" to the current active page in the header
 * Current page state is added to active item in each screen size (i.e. mobile, medium, desktop)
 */

(function () {
    var tabList = document.querySelectorAll("#dataset-tablist li, #organization-tablist li, #groups-tablist li");
    tabList.forEach(item => {
        item.setAttribute('role', 'tab');
        if (item.classList.contains('active')) {
            item.setAttribute('aria-selected', 'true');
        }
    })
})();