// General UI behavior: mobile nav, mobile bottom bar, scroll-reveal animations.
(function () {
  "use strict";

  function initNavToggle() {
    var toggle = document.querySelector(".nav-toggle");
    var nav = document.querySelector(".main-nav");
    var backdrop = document.querySelector("[data-nav-backdrop]");
    if (!toggle || !nav) return;

    function setOpen(isOpen) {
      nav.classList.toggle("is-open", isOpen);
      toggle.setAttribute("aria-expanded", String(isOpen));
      if (backdrop) backdrop.classList.toggle("is-open", isOpen);
      document.body.style.overflow = isOpen ? "hidden" : "";
    }

    toggle.addEventListener("click", function () {
      setOpen(!nav.classList.contains("is-open"));
    });
    if (backdrop) {
      backdrop.addEventListener("click", function () { setOpen(false); });
    }
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") setOpen(false);
    });
    nav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () { setOpen(false); });
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

  function initGalleryTabs() {
    var galleries = document.querySelectorAll("[data-gallery]");
    galleries.forEach(function (gallery) {
      var buttons = gallery.querySelectorAll("[data-gallery-tab]");
      buttons.forEach(function (btn) {
        btn.addEventListener("click", function () {
          var target = btn.getAttribute("data-gallery-tab");
          buttons.forEach(function (b) { b.classList.toggle("is-active", b === btn); });
          gallery.querySelectorAll("[data-gallery-panel]").forEach(function (panel) {
            panel.classList.toggle("is-active", panel.getAttribute("data-gallery-panel") === target);
          });
        });
      });
    });
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

  function initExitIntent() {
    var popup = document.querySelector("[data-exit-popup]");
    if (!popup) return;

    var STORAGE_KEY = "ayka_exit_shown";
    var isDesktop = window.matchMedia("(min-width: 900px) and (pointer: fine)").matches;
    if (!isDesktop) return;
    try {
      if (sessionStorage.getItem(STORAGE_KEY)) return;
    } catch (e) {}

    var armed = false;
    var armTimer = window.setTimeout(function () { armed = true; }, 4000);

    function show() {
      if (!armed) return;
      window.clearTimeout(armTimer);
      popup.hidden = false;
      try { sessionStorage.setItem(STORAGE_KEY, "1"); } catch (e) {}
      document.removeEventListener("mouseout", onMouseOut);
    }

    function hide() {
      popup.hidden = true;
    }

    function onMouseOut(event) {
      if (event.clientY > 0 || event.relatedTarget) return;
      show();
    }

    document.addEventListener("mouseout", onMouseOut);
    popup.querySelectorAll("[data-exit-popup-dismiss]").forEach(function (el) {
      el.addEventListener("click", hide);
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !popup.hidden) hide();
    });
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
    initGalleryTabs();
    initReveal();
    initContactTracking();
    initExitIntent();
  });
})();
