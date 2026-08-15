// General UI behavior: mobile nav, mobile bottom bar, scroll-reveal animations.
(function () {
  "use strict";

  function initNavToggle() {
    var toggle = document.querySelector(".nav-toggle");
    var nav = document.querySelector(".main-nav");
    if (!toggle || !nav) return;
    toggle.addEventListener("click", function () {
      var isOpen = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(isOpen));
    });
  }

  function initMobileBar() {
    var bar = document.querySelector(".mobile-bar");
    if (!bar) return;
    var threshold = 0.3;
    var shown = false;
    function onScroll() {
      var scrolled = window.scrollY;
      var max = document.documentElement.scrollHeight - window.innerHeight;
      var ratio = max > 0 ? scrolled / max : 0;
      var shouldShow = ratio > threshold;
      if (shouldShow !== shown) {
        shown = shouldShow;
        bar.classList.toggle("is-visible", shown);
      }
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  function initReveal() {
    var items = document.querySelectorAll(".reveal");
    if (!items.length) return;
    if (!("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      items.forEach(function (el) { el.classList.add("is-visible"); });
      return;
    }
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    items.forEach(function (el) { observer.observe(el); });
  }

  function initContactTracking() {
    document.querySelectorAll('a[href^="tel:"]').forEach(function (a) {
      a.addEventListener("click", function () {
        if (window.aykaTrack) window.aykaTrack("phone_click", {});
      });
    });
    document.querySelectorAll('a[href*="wa.me"]').forEach(function (a) {
      a.addEventListener("click", function () {
        if (window.aykaTrack) window.aykaTrack("whatsapp_click", {});
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initNavToggle();
    initMobileBar();
    initReveal();
    initContactTracking();
  });
})();
