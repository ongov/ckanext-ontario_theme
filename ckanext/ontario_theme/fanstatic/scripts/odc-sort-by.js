
(function () {
    let sortByButton = document.querySelector(".show-sort-by");
    const sortByModal = document.getElementById("sort-by-modal");
    let closeSortButton = document.querySelector(".sort-by-close");
    sortByButton.addEventListener("click", function (e) {
        e.preventDefault();
        document.body.classList.add("sort-by-modal");
    })
    window.onclick = function(e) {
        if (e.target == sortByModal) {
            closeModal();
        }
      }
    closeSortButton.addEventListener("click", closeModal)
    closeSortButton.addEventListener("keydown", (event) => {
        if (event.key === " " || event.key === "Enter") {
            closeModal();
        }
    })

    function closeModal(event) {
        document.body.classList.remove("sort-by-modal");
    }
})();