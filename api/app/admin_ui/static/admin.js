// Автообновление списка заявок каждые 60 секунд + звуковой сигнал на новую заявку
// (переключатель хранится в localStorage). BRIEF.md раздел 9.
(function () {
  "use strict";

  var SOUND_KEY = "ayka_admin_sound_enabled";
  var POLL_MS = 60000;

  function isSoundEnabled() {
    return localStorage.getItem(SOUND_KEY) !== "0";
  }

  function setSoundEnabled(enabled) {
    localStorage.setItem(SOUND_KEY, enabled ? "1" : "0");
  }

  function beep() {
    try {
      var ctx = new (window.AudioContext || window.webkitAudioContext)();
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.4);
    } catch (e) {
      /* audio unsupported — silently ignore */
    }
  }

  function initSoundToggle() {
    var toggle = document.querySelector("[data-sound-toggle]");
    if (!toggle) return;
    toggle.checked = isSoundEnabled();
    toggle.addEventListener("change", function () {
      setSoundEnabled(toggle.checked);
    });
  }

  function initAutoRefresh() {
    var marker = document.querySelector("[data-leads-today]");
    if (!marker) return;
    var lastCount = Number(marker.dataset.leadsToday || 0);

    setInterval(function () {
      fetch("/api/v1/admin/stats", { credentials: "same-origin" })
        .then(function (res) {
          if (!res.ok) throw new Error("stats request failed");
          return res.json();
        })
        .then(function (data) {
          if (data.leads_today > lastCount) {
            if (isSoundEnabled()) beep();
            lastCount = data.leads_today;
            window.location.reload();
          }
        })
        .catch(function () {
          /* network hiccup — try again next tick */
        });
    }, POLL_MS);
  }

  document.addEventListener("DOMContentLoaded", function () {
    initSoundToggle();
    initAutoRefresh();
  });
})();
