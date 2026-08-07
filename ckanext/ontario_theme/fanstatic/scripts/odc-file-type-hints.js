(function () {
    "use strict";

    if (!("addEventListener" in window)) {
        return;
    }

    var dialog = document.getElementById("file-type-dialog");
    var triggers = document.querySelectorAll(".file-type-hint-trigger");

    if (!dialog || !triggers.length) {
        return;
    }

    var title = dialog.querySelector(".file-type-dialog__title");
    var body = dialog.querySelector(".file-type-dialog__body");
    var backdrop = dialog.querySelector(".file-type-dialog__backdrop");
    var closeButton = dialog.querySelector(".file-type-dialog__close");
    var activeTrigger = null;
    var cleanUpFocusTrap = null;

    function closeDialog() {
        dialog.hidden = true;
        dialog.setAttribute("aria-hidden", "true");
        document.body.classList.remove("file-type-dialog-open");

        if (cleanUpFocusTrap) {
            cleanUpFocusTrap();
            cleanUpFocusTrap = null;
        }

        if (activeTrigger) {
            activeTrigger.focus();
            activeTrigger = null;
        }
    }

    function openDialog(event) {
        var paragraphs = [];

        event.preventDefault();
        event.stopPropagation();

        activeTrigger = event.currentTarget;

        title.textContent =
            activeTrigger.getAttribute("data-file-type-heading") || "";

        body.innerHTML = "";

        try {
            paragraphs = JSON.parse(
                activeTrigger.getAttribute("data-file-type-body") || "[]"
            );
        } catch (error) {
            paragraphs = [];
        }

        paragraphs.forEach(function (paragraph) {
            var element = document.createElement("p");
            element.textContent = paragraph;
            body.appendChild(element);
        });

        dialog.hidden = false;
        dialog.setAttribute("aria-hidden", "false");
        document.body.classList.add("file-type-dialog-open");

        cleanUpFocusTrap = focusUser({
            element: dialog,
            callbackOnEscape: closeDialog,
        });
    }

    Array.prototype.forEach.call(triggers, function (trigger) {
        trigger.addEventListener("click", openDialog);
    });

    closeButton.addEventListener("click", closeDialog);
    backdrop.addEventListener("click", closeDialog);
})();
