(function () {
    document.querySelectorAll(".site-header").forEach(function (header) {
        var toggle = header.querySelector(".site-header-toggle");
        var navigation =
            header.querySelector(".site-header-navigation") ||
            header.querySelector(".links-top");
        if (!toggle || !navigation) return;

        header.classList.add("site-header-enabled");
        toggle.hidden = false;

        function setOpen(open) {
            header.classList.toggle("open", open);
            toggle.setAttribute("aria-expanded", String(open));
        }

        toggle.addEventListener("click", function () {
            setOpen(!header.classList.contains("open"));
        });

        navigation.addEventListener("click", function (event) {
            if (event.target.closest("a")) setOpen(false);
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") setOpen(false);
        });
    });
})();
