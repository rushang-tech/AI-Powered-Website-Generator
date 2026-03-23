const marketingMenuToggle = document.querySelector("[data-marketing-menu-toggle]");
const marketingMenu = document.querySelector("[data-marketing-menu]");

if (marketingMenuToggle && marketingMenu) {
    marketingMenuToggle.addEventListener("click", () => {
        const nextExpanded = marketingMenuToggle.getAttribute("aria-expanded") !== "true";
        marketingMenuToggle.setAttribute("aria-expanded", String(nextExpanded));
        marketingMenu.classList.toggle("is-open", nextExpanded);
    });
}

const showcaseFilters = Array.from(document.querySelectorAll("[data-showcase-filter]"));
const showcaseCards = Array.from(document.querySelectorAll("[data-showcase-card]"));

if (showcaseFilters.length && showcaseCards.length) {
    const applyFilter = (value) => {
        showcaseFilters.forEach((button) => {
            button.classList.toggle("is-active", button.dataset.showcaseFilter === value);
        });

        showcaseCards.forEach((card) => {
            const categories = String(card.dataset.category || "")
                .split(" ")
                .filter(Boolean);
            const matches = value === "all" || categories.includes(value);
            card.hidden = !matches;
        });
    };

    showcaseFilters.forEach((button) => {
        button.addEventListener("click", () => applyFilter(button.dataset.showcaseFilter || "all"));
    });

    applyFilter("all");
}
