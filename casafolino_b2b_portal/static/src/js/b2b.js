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

document.addEventListener("input", (event) => {
    const input = event.target.closest("[data-cf-product-search]");
    if (!input) {
        return;
    }
    const query = input.value.trim().toLowerCase();
    document.querySelectorAll("[data-cf-search]").forEach((card) => {
        const text = (card.dataset.cfSearch || "").toLowerCase();
        card.classList.toggle("is-hidden", query && !text.includes(query));
    });
});

const categoryRules = [
    {
        value: "restaurant",
        label: "Ristorante",
        googleTypes: ["restaurant", "meal_takeaway", "meal_delivery", "bar", "cafe", "bakery"],
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
        googleTypes: [
            "grocery_or_supermarket",
            "supermarket",
            "food",
            "store",
            "convenience_store",
            "liquor_store",
            "bakery",
        ],
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
        googleTypes: ["lodging", "hotel"],
        words: ["hotel", "albergo", "resort", "b&b", "bed and breakfast", "guest house", "hospitality"],
    },
    {
        value: "distributor",
        label: "Distributore",
        googleTypes: ["storage", "moving_company", "point_of_interest"],
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

function inferPlaceCategory(place) {
    const types = place?.types || [];
    const fromType = categoryRules.find((rule) => rule.googleTypes?.some((type) => types.includes(type)));
    return fromType || inferCompanyCategory(`${place?.name || ""} ${types.join(" ")}`);
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

function clearPlaceMetadata(input) {
    const form = input.closest("form");
    const placeId = form?.querySelector("[data-cf-google-place-id]");
    const placeTypes = form?.querySelector("[data-cf-google-place-types]");
    if (placeId) {
        placeId.value = "";
    }
    if (placeTypes) {
        placeTypes.value = "";
    }
}

function setPlaceSuggestion(input, place) {
    const form = input.closest("form");
    const select = form?.querySelector("[data-cf-category-select]");
    const hint = form?.querySelector("[data-cf-category-hint]");
    const placeId = form?.querySelector("[data-cf-google-place-id]");
    const placeTypes = form?.querySelector("[data-cf-google-place-types]");
    if (!form || !select || !hint) {
        return;
    }
    if (placeId) {
        placeId.value = place.place_id || "";
    }
    if (placeTypes) {
        placeTypes.value = (place.types || []).join(",");
    }
    if (place.name) {
        input.value = place.name;
    }
    if (place.formatted_address) {
        const street = form.querySelector("[name='street']");
        if (street && !street.value.trim()) {
            street.value = place.formatted_address;
        }
    }
    const website = place.website ? `Sito Google Maps: ${place.website}` : "";
    if (website) {
        const notes = form.querySelector("[name='notes']");
        if (notes && !notes.value.includes(website)) {
            notes.value = [notes.value.trim(), website].filter(Boolean).join("\n");
        }
    }
    const suggestion = inferPlaceCategory(place);
    if (suggestion) {
        select.value = suggestion.value;
        hint.textContent = `Attivita suggerita da Google: ${suggestion.label}`;
    } else {
        select.value = "other";
        hint.textContent = "Attivita suggerita da Google: Altro";
    }
}

function initPlacesAutocomplete() {
    if (!window.google?.maps?.places?.Autocomplete) {
        return;
    }
    document.querySelectorAll("[data-cf-company-name]").forEach((input) => {
        if (input.dataset.cfPlacesReady === "1") {
            return;
        }
        input.dataset.cfPlacesReady = "1";
        const autocomplete = new google.maps.places.Autocomplete(input, {
            fields: ["address_components", "formatted_address", "name", "place_id", "types", "website"],
            types: ["establishment"],
        });
        autocomplete.addListener("place_changed", () => {
            const place = autocomplete.getPlace();
            if (place?.place_id) {
                setPlaceSuggestion(input, place);
            }
        });
    });
}

document.addEventListener("input", (event) => {
    const input = event.target.closest("[data-cf-company-name]");
    if (input) {
        clearPlaceMetadata(input);
        updateCategorySuggestion(input);
    }
});

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-cf-company-name]").forEach(updateCategorySuggestion);
    initPlacesAutocomplete();
});

document.addEventListener("cf-b2b-places-ready", initPlacesAutocomplete);

window.cfB2BInitPlaces = function () {
    window.cfB2BPlacesReady = true;
    document.dispatchEvent(new Event("cf-b2b-places-ready"));
};

if (window.cfB2BPlacesReady) {
    initPlacesAutocomplete();
}
