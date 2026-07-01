(function () {
  // TODO(Antonio): set the real GTM container id once created on tagmanager.google.com, then redeploy.
  var CF_GTM_ID = "";
  var CF_GA4_ID = "G-B7V6TVHWT2";
  var STORAGE_KEY = "cf_consent";

  function gtag() {
    window.dataLayer.push(arguments);
  }

  function loadScript(src) {
    var s = document.createElement("script");
    s.async = true;
    s.src = src;
    document.head.appendChild(s);
  }

  function loadGA4() {
    if (!CF_GA4_ID) return;
    loadScript("https://www.googletagmanager.com/gtag/js?id=" + CF_GA4_ID);
    gtag("js", new Date());
    gtag("config", CF_GA4_ID);
  }

  function loadGTM() {
    if (!CF_GTM_ID) return;
    window.dataLayer.push({ "gtm.start": new Date().getTime(), event: "gtm.js" });
    loadScript("https://www.googletagmanager.com/gtm.js?id=" + CF_GTM_ID);
  }

  function grantConsent() {
    gtag("consent", "update", {
      ad_storage: "granted",
      analytics_storage: "granted",
      ad_user_data: "granted",
      ad_personalization: "granted"
    });
    loadGA4();
    loadGTM();
  }

  function storedConsent() {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch (error) {
      return null;
    }
  }

  function storeConsent(value) {
    try {
      window.localStorage.setItem(STORAGE_KEY, value);
    } catch (error) {}
  }

  function buildBanner() {
    var banner = document.createElement("div");
    banner.className = "cookie-consent-banner";
    banner.setAttribute("role", "dialog");
    banner.setAttribute("aria-label", "Cookie consent");
    banner.innerHTML =
      '<p>CasaFolino uses cookies to measure website traffic (Google Analytics). No tracking cookie is set until you accept. Read our <a href="/en/cookie-policy/">Cookie Policy</a>.</p>' +
      '<div class="cookie-consent-actions">' +
      '<button type="button" class="button" data-consent-action="reject">Reject</button>' +
      '<button type="button" class="button primary" data-consent-action="accept">Accept</button>' +
      "</div>";
    document.body.appendChild(banner);
    banner.querySelector('[data-consent-action="accept"]').addEventListener("click", function () {
      storeConsent("granted");
      grantConsent();
      banner.remove();
    });
    banner.querySelector('[data-consent-action="reject"]').addEventListener("click", function () {
      storeConsent("denied");
      banner.remove();
    });
  }

  function init() {
    var consent = storedConsent();
    if (consent === "granted") {
      grantConsent();
    } else if (consent !== "denied") {
      buildBanner();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.cfTrackEvent = function (name, params) {
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push(Object.assign({ event: name }, params || {}));
  };

  window.cfOpenConsentSettings = function () {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch (error) {}
    var existing = document.querySelector(".cookie-consent-banner");
    if (existing) existing.remove();
    buildBanner();
  };
})();
