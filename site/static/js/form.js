// Lead form: UTM capture, honeypot/time-trap fields, graceful WhatsApp fallback.
(function () {
  "use strict";

  var UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"];
  var STORAGE_KEY = "ayka_utm";

  function captureUtm() {
    var params = new URLSearchParams(window.location.search);
    var hasAny = UTM_KEYS.some(function (k) { return params.has(k); });
    if (hasAny) {
      var data = {};
      UTM_KEYS.forEach(function (k) { data[k] = params.get(k) || ""; });
      data.referrer = document.referrer || "";
      data.landing_page = window.location.pathname;
      try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch (e) {}
      return data;
    }
    try {
      var stored = sessionStorage.getItem(STORAGE_KEY);
      if (stored) return JSON.parse(stored);
    } catch (e) {}
    return { referrer: document.referrer || "", landing_page: window.location.pathname };
  }

  function fillHiddenFields(form, data) {
    Object.keys(data).forEach(function (key) {
      var field = form.querySelector('[name="' + key + '"]');
      if (field) field.value = data[key] || "";
    });
  }

  function normalizeDisplayPhone(value) {
    return value.replace(/[^\d+]/g, "");
  }

  function buildWhatsappFallbackUrl(form, whatsappNumber) {
    var name = form.querySelector('[name="name"]');
    var phone = form.querySelector('[name="phone"]');
    var comment = form.querySelector('[name="comment"]');
    var lines = [];
    lines.push("Здравствуйте! Хочу заказать уборку.");
    if (name && name.value) lines.push("Имя: " + name.value);
    if (phone && phone.value) lines.push("Телефон: " + phone.value);
    if (comment && comment.value) lines.push("Комментарий: " + comment.value);
    var digits = (whatsappNumber || "").replace(/[^\d]/g, "");
    return "https://wa.me/" + digits + "?text=" + encodeURIComponent(lines.join("\n"));
  }

  function setStatus(form, message, kind) {
    var status = form.querySelector("[data-form-status]");
    if (!status) return;
    status.textContent = message;
    status.className = "form-status form-status--" + kind;
  }

  function validate(form) {
    var errors = {};
    var name = form.querySelector('[name="name"]');
    var phone = form.querySelector('[name="phone"]');
    if (!name || name.value.trim().length < 2) errors.name = true;
    if (!phone || phone.value.replace(/\D/g, "").length < 9) errors.phone = true;
    Object.keys(errors).forEach(function (key) {
      var field = form.querySelector('[name="' + key + '"]');
      if (field) field.closest(".form-field").classList.add("form-field--error");
    });
    return Object.keys(errors).length === 0;
  }

  function clearErrors(form) {
    form.querySelectorAll(".form-field--error").forEach(function (el) {
      el.classList.remove("form-field--error");
    });
  }

  // Fields marked [data-merge-comment="Label"] have no name= attribute (so
  // FormData never sends them under an unknown key the API would silently
  // drop) — instead their value is folded into the real "comment" field
  // right before submit. Used by the B2B form (company name, object type).
  function mergeExtraFieldsIntoComment(form) {
    var extras = form.querySelectorAll("[data-merge-comment]");
    if (!extras.length) return;
    var commentField = form.querySelector('[name="comment"]');
    if (!commentField) return;
    var lines = [];
    extras.forEach(function (el) {
      if (el.value) lines.push(el.dataset.mergeComment + ": " + el.value);
    });
    if (lines.length) {
      commentField.value = lines.join("\n") + (commentField.value ? "\n" + commentField.value : "");
    }
  }

  function initForm(form) {
    var utm = captureUtm();
    fillHiddenFields(form, utm);

    var renderedAtField = form.querySelector('[name="rendered_at"]');
    if (renderedAtField) renderedAtField.value = new Date().toISOString();

    var langField = form.querySelector('[name="lang"]');
    if (langField && !langField.value) langField.value = document.documentElement.lang || "ru";

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      clearErrors(form);
      if (!validate(form)) {
        setStatus(form, form.dataset.errorText || "Проверьте, пожалуйста, поля формы.", "error");
        return;
      }

      var submitButton = form.querySelector('[type="submit"]');
      if (submitButton) submitButton.disabled = true;

      mergeExtraFieldsIntoComment(form);
      var formData = new FormData(form);
      var payload = {};
      formData.forEach(function (value, key) {
        payload[key] = value;
      });

      var apiBase = form.dataset.apiBase || "/api/v1";

      fetch(apiBase + "/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
        .then(function (response) {
          if (!response.ok) throw new Error("API error " + response.status);
          return response.json();
        })
        .then(function () {
          setStatus(form, form.dataset.successText || "Заявка отправлена! Мы свяжемся с вами в ближайшее время.", "success");
          form.reset();
          if (window.aykaTrack) {
            window.aykaTrack("lead_submitted", {});
          }
        })
        .catch(function () {
          var waNumber = form.dataset.whatsapp;
          if (waNumber) {
            setStatus(
              form,
              form.dataset.fallbackText || "Не удалось отправить форму. Открываем WhatsApp — так заявка дойдёт быстрее.",
              "error"
            );
            window.open(buildWhatsappFallbackUrl(form, waNumber), "_blank", "noopener");
          } else {
            setStatus(form, form.dataset.errorText || "Не удалось отправить форму. Позвоните нам, пожалуйста.", "error");
          }
        })
        .finally(function () {
          if (submitButton) submitButton.disabled = false;
        });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-lead-form]").forEach(initForm);
  });
})();
