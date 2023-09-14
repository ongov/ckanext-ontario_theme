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
        let showMoreId = this.id.substring(8);
        var listItems = document.querySelectorAll('.facet-' + showMoreId);
        listItems.forEach(listItem => {
            listItem.classList.toggle("show-more-items"); 
        });
        this.classList.toggle("hide-button");
        if (this.classList.contains("facets-show-less")){
           let showMore = document.querySelector('#toggle1-' + showMoreId + '.facets-show-more');
           showMore.classList.toggle("hide-button");
        } else {
            let showLess = document.querySelector('#toggle2-' + showMoreId + '.facets-show-less');
            showLess.classList.toggle("hide-button");
        }
    }

})();