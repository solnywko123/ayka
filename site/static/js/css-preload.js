// Swaps the deferred main.css <link> from rel="preload" to rel="stylesheet" once it
// finishes downloading. Kept as an external, synchronous script (not an inline
// onload="" attribute) because the site's CSP has no 'unsafe-inline' for script-src —
// an inline event handler would be silently blocked, leaving the CSS never applied.
// Placed directly after the preload link in <head> so it attaches before the
// resource can finish loading (no race with the load event).
(function () {
  "use strict";
  var link = document.getElementById("main-css-preload");
  if (!link) return;
  link.addEventListener("load", function () {
    link.rel = "stylesheet";
  });
})();
