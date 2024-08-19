/*
 * Function for adding role = "tab" to all tabs
 * Selected state is added to active tab to alert screen reader users the tab
 * they are currently viewing.
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