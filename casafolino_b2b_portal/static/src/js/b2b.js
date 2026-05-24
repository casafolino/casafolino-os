/** @odoo-module **/

document.addEventListener("change", (event) => {
    const input = event.target.closest(".cf-qty");
    if (!input) {
        return;
    }
    const step = Number(input.step || 1);
    const min = Number(input.min || step);
    let value = Number(input.value || min);
    value = Math.max(value, min);
    if (step > 1 && value % step) {
        value = Math.ceil(value / step) * step;
    }
    input.value = value;
});

const categoryRules = [
    {
        value: "restaurant",
        label: "Ristorante",
        words: [
            "ristorante",
            "restaurant",
            "trattoria",
            "osteria",
            "pizzeria",
            "bistro",
            "bistrot",
            "catering",
            "bar",
            "pub",
            "food service",
            "ristorazione",
        ],
    },
    {
        value: "grocery",
        label: "Gastronomia / Retail",
        words: [
            "gastronomia",
            "alimentari",
            "salumeria",
            "market",
            "supermercato",
            "retail",
            "shop",
            "store",
            "emporio",
            "delicatessen",
            "gourmet",
            "enoteca",
            "bottega",
        ],
    },
    {
        value: "hotel",
        label: "Hotel",
        words: ["hotel", "albergo", "resort", "b&b", "bed and breakfast", "guest house", "hospitality"],
    },
    {
        value: "distributor",
        label: "Distributore",
        words: [
            "distrib",
            "wholesale",
            "grossista",
            "import",
            "export",
            "trading",
            "commerce",
            "e-commerce",
            "ecommerce",
            "logistic",
            "logistica",
            "broker",
        ],
    },
];

function inferCompanyCategory(value) {
    const normalized = value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    return categoryRules.find((rule) => rule.words.some((word) => normalized.includes(word))) || null;
}

function updateCategorySuggestion(input) {
    const form = input.closest("form");
    const select = form?.querySelector("[data-cf-category-select]");
    const hint = form?.querySelector("[data-cf-category-hint]");
    if (!select || !hint) {
        return;
    }
    const suggestion = inferCompanyCategory(input.value || "");
    if (!suggestion) {
        hint.textContent = input.value.trim().length >= 3 ? "Attivita suggerita: Altro" : "";
        if (input.value.trim().length >= 3) {
            select.value = "other";
        }
        return;
    }
    select.value = suggestion.value;
    hint.textContent = `Attivita suggerita: ${suggestion.label}`;
}

document.addEventListener("input", (event) => {
    const input = event.target.closest("[data-cf-company-name]");
    if (input) {
        updateCategorySuggestion(input);
    }
});

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-cf-company-name]").forEach(updateCategorySuggestion);
});
