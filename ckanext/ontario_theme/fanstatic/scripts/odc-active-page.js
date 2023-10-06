/*
 * Function for adding aria-current = "page" to the current active page in the header
 * Current page state is added to active item in each screen size (i.e. mobile, medium, desktop)
 */

(function () {
    var navigationList = document.querySelectorAll("#navigation li, #medium-navigation li, #ontario-navigation li");
    navigationList.forEach(item => {
        if (item.classList.contains('active')) {
            var link = item.querySelector('a');
            link.setAttribute('aria-current', 'page');
        }
    })
})();