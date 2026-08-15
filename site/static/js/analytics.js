// Loads GA4 / Yandex Metrica / Meta Pixel only if IDs are configured (config.json -> analytics.*).
// Exposes window.aykaTrack(eventName, params) as a single entry point used across the site.
(function () {
  "use strict";

  var configEl = document.getElementById("ayka-config");
  var config = {};
  try {
    config = configEl ? JSON.parse(configEl.textContent) : {};
  } catch (e) {
    config = {};
  }
  var analytics = config.analytics || {};

  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }

  if (analytics.ga4_id) {
    var gaScript = document.createElement("script");
    gaScript.async = true;
    gaScript.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(analytics.ga4_id);
    document.head.appendChild(gaScript);
    gtag("js", new Date());
    gtag("config", analytics.ga4_id, { anonymize_ip: true });
  }

  if (analytics.yandex_metrica_id) {
    (function (m, e, t, r, i, k, a) {
      m[i] = m[i] || function () { (m[i].a = m[i].a || []).push(arguments); };
      m[i].l = 1 * new Date();
      for (var j = 0; j < document.scripts.length; j++) {
        if (document.scripts[j].src === r) return;
      }
      k = e.createElement(t);
      a = e.getElementsByTagName(t)[0];
      k.async = 1;
      k.src = r;
      a.parentNode.insertBefore(k, a);
    })(window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");
    window.ym(Number(analytics.yandex_metrica_id), "init", {
      webvisor: true,
      clickmap: true,
      trackLinks: true,
      accurateTrackBounce: true,
    });
  }

  if (analytics.meta_pixel_id) {
    (function (f, b, e, v, n, t, s) {
      if (f.fbq) return;
      n = f.fbq = function () {
        n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
      };
      if (!f._fbq) f._fbq = n;
      n.push = n;
      n.loaded = true;
      n.version = "2.0";
      n.queue = [];
      t = b.createElement(e);
      t.async = true;
      t.src = v;
      s = b.getElementsByTagName(e)[0];
      s.parentNode.insertBefore(t, s);
    })(window, document, "script", "https://connect.facebook.net/en_US/fbevents.js");
    window.fbq("init", analytics.meta_pixel_id);
    window.fbq("track", "PageView");
  }

  // Unified conversion event dispatcher — same event names across GA4 / Metrica / Pixel.
  window.aykaTrack = function (eventName, params) {
    params = params || {};
    if (analytics.ga4_id && window.gtag) {
      window.gtag("event", eventName, params);
    } else if (analytics.ga4_id) {
      gtag("event", eventName, params);
    }
    if (analytics.yandex_metrica_id && window.ym) {
      window.ym(Number(analytics.yandex_metrica_id), "reachGoal", eventName, params);
    }
    if (analytics.meta_pixel_id && window.fbq) {
      window.fbq("trackCustom", eventName, params);
    }
  };

  document.addEventListener("DOMContentLoaded", function () {
    if (document.body.dataset.pageType === "service") {
      window.aykaTrack("service_page_view", { service: document.body.dataset.serviceSlug || "" });
    }
  });
})();
