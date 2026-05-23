(function () {
  var supported = ["en", "it", "es", "fr"];
  var languageNames = {
    en: "English",
    it: "Italiano",
    es: "Español",
    fr: "Français"
  };
  var homePaths = {
    en: "/en/",
    it: "/it/",
    es: "/es/",
    fr: "/fr/"
  };
  var equivalentPaths = {
    "/en/": { it: "/it/", es: "/es/", fr: "/fr/" },
    "/en/company-profile/": { it: "/it/profilo-aziendale/", es: "/es/empresa/", fr: "/fr/entreprise/" },
    "/en/catalog/": { it: "/it/catalogo/", es: "/es/catalogo/", fr: "/fr/catalogue/" },
    "/en/catalog/spreads/": { it: "/it/catalogo/creme-spalmabili/", es: "/es/catalogo/cremas-untables/", fr: "/fr/catalogue/cremes-a-tartiner/" },
    "/en/catalog/flavored-honeys/": { it: "/it/catalogo/mieli-aromatizzati/", es: "/es/catalogo/mieles-aromatizadas/", fr: "/fr/catalogue/miels-aromatises/" },
    "/en/catalog/ready-risottos/": { it: "/it/catalogo/risotti-pronti/", es: "/es/catalogo/risottos-listos/", fr: "/fr/catalogue/risottos-prets/" },
    "/en/catalog/italian-spice-mixes/": { it: "/it/catalogo/mix-spezie-italiane/", es: "/es/catalogo/mezclas-especias-italianas/", fr: "/fr/catalogue/melanges-epices-italiennes/" },
    "/en/catalog/gastronomic-mousses/": { it: "/it/catalogo/mousse-gastronomiche/", es: "/es/catalogo/mousses-gastronomicas/", fr: "/fr/catalogue/mousses-gastronomiques/" },
    "/en/catalog/crispy-chilli/": { it: "/it/catalogo/crispy-chilli/", es: "/es/catalogo/crispy-chilli/", fr: "/fr/catalogue/crispy-chilli/" },
    "/en/catalog/cantucci/": { it: "/it/catalogo/cantucci/", es: "/es/catalogo/cantucci/", fr: "/fr/catalogue/cantucci/" },
    "/en/catalog/biscuits/": { it: "/it/catalogo/biscotti/", es: "/es/catalogo/galletas/", fr: "/fr/catalogue/biscuits/" },
    "/en/catalog/chocolate-bars/": { it: "/it/catalogo/barrette-cioccolato/", es: "/es/catalogo/barras-chocolate/", fr: "/fr/catalogue/tablettes-chocolat/" },
    "/en/catalog/chocolate-chunks/": { it: "/it/catalogo/chunks-cioccolato/", es: "/es/catalogo/chunks-chocolate/", fr: "/fr/catalogue/morceaux-chocolat/" },
    "/en/services/": { it: "/it/servizi/", es: "/es/servicios/", fr: "/fr/services/" },
    "/en/services/private-label/": { it: "/it/servizi/private-label/", es: "/es/servicios/marca-privada/", fr: "/fr/services/marque-privee/" },
    "/en/services/custom-recipes/": { it: "/it/servizi/ricette-su-misura/", es: "/es/servicios/recetas-a-medida/", fr: "/fr/services/recettes-sur-mesure/" },
    "/en/services/b2b-supply/": { it: "/it/servizi/forniture-b2b/", es: "/es/servicios/suministro-b2b/", fr: "/fr/services/approvisionnement-b2b/" },
    "/en/services/distribution/": { it: "/it/servizi/distribuzione/", es: "/es/servicios/distribucion/", fr: "/fr/services/distribution/" },
    "/en/certifications/": { it: "/it/certificazioni/", es: "/es/certificaciones/", fr: "/fr/certifications/" },
    "/en/sustainability/": { it: "/it/sostenibilita/", es: "/es/sostenibilidad/", fr: "/fr/durabilite/" },
    "/en/contact/": { it: "/it/contatti/", es: "/es/contacto/", fr: "/fr/contact/" },
    "/en/privacy-policy/": { it: "/it/privacy-policy/", es: "/es/privacy-policy/", fr: "/fr/privacy-policy/" },
    "/en/cookie-policy/": { it: "/it/cookie-policy/", es: "/es/cookie-policy/", fr: "/fr/cookie-policy/" }
  };

  function currentLanguage() {
    var lang = document.documentElement.getAttribute("lang") || "";
    lang = lang.toLowerCase().slice(0, 2);
    return supported.indexOf(lang) >= 0 ? lang : "en";
  }

  function normalizePath(pathname) {
    return pathname.endsWith("/") ? pathname : pathname + "/";
  }

  function englishKey(pathname, current) {
    var path = normalizePath(pathname);
    if (current === "en") {
      return path;
    }
    for (var enPath in equivalentPaths) {
      if (!Object.prototype.hasOwnProperty.call(equivalentPaths, enPath)) continue;
      if (equivalentPaths[enPath][current] === path || homePaths[current] === path && enPath === "/en/") {
        return enPath;
      }
    }
    return "/en/";
  }

  function targetPath(targetLanguage) {
    var current = currentLanguage();
    var key = englishKey(window.location.pathname, current);
    if (targetLanguage === "en") {
      return key;
    }
    return equivalentPaths[key] && equivalentPaths[key][targetLanguage] ? equivalentPaths[key][targetLanguage] : homePaths[targetLanguage];
  }

  function buildSelector() {
    var header = document.querySelector(".site-header");
    if (!header || header.querySelector(".language-switcher")) {
      return;
    }

    var wrapper = document.createElement("div");
    wrapper.className = "language-switcher";
    wrapper.setAttribute("aria-label", "Language selector");

    var current = currentLanguage();
    supported.forEach(function (lang) {
      var link = document.createElement("a");
      link.href = targetPath(lang);
      link.lang = lang;
      link.hreflang = lang;
      link.textContent = lang.toUpperCase();
      link.title = languageNames[lang];
      if (lang === current) {
        link.className = "active";
        link.setAttribute("aria-current", "true");
      }
      link.addEventListener("click", function () {
        try {
          window.localStorage.setItem("casafolinoPreferredLanguage", lang);
        } catch (error) {}
      });
      wrapper.appendChild(link);
    });

    header.appendChild(wrapper);
  }

  buildSelector();
})();
