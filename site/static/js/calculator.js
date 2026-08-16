// Cost calculator. Formula mirrors api/app/pricing.py exactly (see BRIEF.md section 6) —
// pricing.json is the single source of truth, embedded at build time into #pricing-data.
(function () {
  "use strict";

  var ADDONS_WITH_QTY = ["windows_per_m2", "carpet_per_m2", "ironing_per_hour", "facade_wash_per_m2"];
  var PRODUCTIVITY_M2_PER_HOUR = {
    maintenance: 30,
    general: 18,
    post_renovation: 10,
    post_move: 15,
  };

  function loadPricing() {
    var el = document.getElementById("pricing-data");
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  function roundToTen(value) {
    return Math.round(value / 10) * 10;
  }

  function computeTotal(pricing, params) {
    if (pricing.subscriptions_monthly && pricing.subscriptions_monthly[params.frequency] != null) {
      return pricing.subscriptions_monthly[params.frequency];
    }

    var rate = pricing.base_rates_per_m2[params.service_type] || 0;
    var base = params.area_m2 * rate;
    base += pricing.bathroom_extra * Math.max(0, params.bathrooms - 1);

    var addonsSum = 0;
    Object.keys(params.addons).forEach(function (key) {
      var qty = params.addons[key];
      if (qty > 0 && pricing.addons[key] != null) {
        addonsSum += pricing.addons[key] * qty;
      }
    });

    var propertyMultiplier = 1;
    if (params.property_type === "house") propertyMultiplier = pricing.multipliers.property_house;
    if (params.property_type === "office") propertyMultiplier = pricing.multipliers.property_office;

    var urgencyMultiplier = params.urgency === "urgent" ? pricing.multipliers.urgency_today : 1;

    var subtotal = (base + addonsSum) * propertyMultiplier * urgencyMultiplier;

    var total = Math.max(subtotal, pricing.min_order);
    return total;
  }

  function computeRange(pricing, params) {
    var total = computeTotal(pricing, params);
    if (pricing.subscriptions_monthly && pricing.subscriptions_monthly[params.frequency] != null) {
      // Абонемент — фиксированная цена в месяц, без разброса "от-до".
      return { total: total, price_min: total, price_max: total };
    }
    var spread = pricing.price_range_spread;
    return {
      total: total,
      price_min: roundToTen(total * (1 - spread)),
      price_max: roundToTen(total * (1 + spread)),
    };
  }

  function estimateEffort(params) {
    var productivity = PRODUCTIVITY_M2_PER_HOUR[params.service_type] || 20;
    var cleaners = params.area_m2 <= 40 ? 1 : params.area_m2 <= 120 ? 2 : params.area_m2 <= 220 ? 3 : 4;
    var personHours = params.area_m2 / productivity;
    var hours = Math.max(1.5, Math.ceil((personHours / cleaners) * 2) / 2);
    return { hours: hours, cleaners: cleaners };
  }

  function formatMoney(value) {
    return Math.round(value).toLocaleString("ru-RU");
  }

  function CalculatorWidget(root, pricing, i18n) {
    this.root = root;
    this.pricing = pricing;
    this.i18n = i18n || {};
    this.startedFired = false;
    this.bindElements();
    this.bindEvents();
    this.applyPresets();
    this.syncAreaFromRange();
    this.update();
  }

  CalculatorWidget.prototype.bindElements = function () {
    var root = this.root;
    this.serviceInputs = root.querySelectorAll('input[name="service_type"]');
    this.propertyInputs = root.querySelectorAll('input[name="property_type"]');
    this.areaRange = root.querySelector('[data-role="area-range"]');
    this.areaNumber = root.querySelector('[data-role="area-number"]');
    this.bathroomsOutput = root.querySelector('[data-role="bathrooms-output"]');
    this.bathroomsInput = root.querySelector('[data-role="bathrooms-input"]');
    this.bathroomsButtons = root.querySelectorAll('[data-step="bathrooms"]');
    this.urgencyInputs = root.querySelectorAll('input[name="urgency"]');
    this.frequencySelect = root.querySelector('select[name="frequency"]');
    this.addonCheckboxes = root.querySelectorAll("[data-addon]");
    this.priceMinEl = root.querySelector('[data-role="price-min"]');
    this.priceMaxEl = root.querySelector('[data-role="price-max"]');
    this.metaEl = root.querySelector('[data-role="meta"]');
    this.savingsEl = root.querySelector('[data-role="savings"]');
    this.ctaButton = root.querySelector('[data-role="cta"]');
    this.currency = root.dataset.currencySymbol || "";
  };

  CalculatorWidget.prototype.applyPresets = function () {
    var presetService = this.root.dataset.presetService;
    var presetProperty = this.root.dataset.presetProperty;
    if (presetService) {
      this.serviceInputs.forEach(function (input) {
        input.checked = input.value === presetService;
      });
    }
    if (presetProperty) {
      this.propertyInputs.forEach(function (input) {
        input.checked = input.value === presetProperty;
      });
    }
  };

  CalculatorWidget.prototype.bindEvents = function () {
    var self = this;
    var onAnyChange = function () {
      self.notifyStarted();
      self.update();
    };
    this.serviceInputs.forEach(function (el) { el.addEventListener("change", onAnyChange); });
    this.propertyInputs.forEach(function (el) { el.addEventListener("change", onAnyChange); });
    this.urgencyInputs.forEach(function (el) { el.addEventListener("change", onAnyChange); });
    if (this.frequencySelect) this.frequencySelect.addEventListener("change", onAnyChange);
    this.addonCheckboxes.forEach(function (el) { el.addEventListener("change", onAnyChange); el.addEventListener("input", onAnyChange); });

    if (this.areaRange) {
      this.areaRange.addEventListener("input", function () {
        self.areaNumber.value = self.areaRange.value;
        onAnyChange();
      });
    }
    if (this.areaNumber) {
      this.areaNumber.addEventListener("input", function () {
        var v = Math.min(300, Math.max(20, Number(self.areaNumber.value) || 20));
        self.areaRange.value = v;
        onAnyChange();
      });
    }
    this.bathroomsButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var delta = Number(btn.dataset.delta);
        var current = Number(self.bathroomsInput.value) || 1;
        var next = Math.min(5, Math.max(1, current + delta));
        self.bathroomsInput.value = next;
        self.bathroomsOutput.textContent = next;
        onAnyChange();
      });
    });

    if (this.ctaButton) {
      this.ctaButton.addEventListener("click", function () {
        self.transferToForm();
      });
    }
  };

  CalculatorWidget.prototype.notifyStarted = function () {
    if (!this.startedFired && window.aykaTrack) {
      window.aykaTrack("calculator_started", {});
      this.startedFired = true;
    }
  };

  CalculatorWidget.prototype.syncAreaFromRange = function () {
    if (this.areaRange && this.areaNumber) {
      this.areaNumber.value = this.areaRange.value;
    }
  };

  CalculatorWidget.prototype.getParams = function () {
    var serviceType = this.getRadioValue(this.serviceInputs) || "maintenance";
    var propertyType = this.getRadioValue(this.propertyInputs) || "apartment";
    var areaM2 = Math.min(300, Math.max(20, Number(this.areaNumber ? this.areaNumber.value : 60) || 60));
    var bathrooms = Number(this.bathroomsInput ? this.bathroomsInput.value : 1) || 1;
    var urgency = this.getRadioValue(this.urgencyInputs) || "normal";
    var frequency = this.frequencySelect ? this.frequencySelect.value : "once";

    var addons = {};
    this.addonCheckboxes.forEach(function (el) {
      var key = el.dataset.addon;
      if (!el.checked) {
        addons[key] = 0;
        return;
      }
      if (ADDONS_WITH_QTY.indexOf(key) !== -1) {
        var qtyInput = el.closest(".calc-addon").querySelector('[data-role="addon-qty"]');
        addons[key] = qtyInput ? Math.max(1, Number(qtyInput.value) || 1) : 1;
      } else {
        addons[key] = 1;
      }
    });

    return {
      service_type: serviceType,
      property_type: propertyType,
      area_m2: areaM2,
      bathrooms: bathrooms,
      addons: addons,
      urgency: urgency,
      frequency: frequency,
    };
  };

  CalculatorWidget.prototype.getRadioValue = function (nodeList) {
    var result = null;
    nodeList.forEach(function (el) {
      if (el.checked) result = el.value;
    });
    return result;
  };

  CalculatorWidget.prototype.update = function () {
    var params = this.getParams();
    var result = computeRange(this.pricing, params);
    var effort = estimateEffort(params);

    if (this.priceMinEl) this.priceMinEl.textContent = formatMoney(result.price_min);
    if (this.priceMaxEl) this.priceMaxEl.textContent = formatMoney(result.price_max);
    if (this.metaEl) {
      var template = this.i18n.meta_template || "≈ {hours} ч, {cleaners} клинера";
      this.metaEl.textContent = template
        .replace("{hours}", String(effort.hours).replace(".", ","))
        .replace("{cleaners}", effort.cleaners);
    }

    if (this.savingsEl) {
      var subMap = this.pricing.subscriptions_monthly || {};
      if (params.frequency !== "once" && subMap[params.frequency] != null) {
        var onceParams = Object.assign({}, params, { frequency: "once" });
        var onceResult = computeRange(this.pricing, onceParams);
        var visits = (this.pricing.visits_per_month && this.pricing.visits_per_month[params.frequency]) || 1;
        var savings = onceResult.total * visits - result.total;
        if (savings > 10) {
          var savingsTemplate = this.i18n.savings_template || "Вы экономите {amount} {currency} при выбранной регулярности";
          this.savingsEl.textContent = savingsTemplate
            .replace("{amount}", formatMoney(savings))
            .replace("{currency}", this.currency);
          this.savingsEl.hidden = false;
        } else {
          this.savingsEl.hidden = true;
        }
      } else {
        this.savingsEl.hidden = true;
      }
    }

    this.lastParams = params;
    this.lastResult = result;

    if (window.aykaTrack) {
      window.aykaTrack("calculator_completed", { price_min: result.price_min, price_max: result.price_max });
    }
    document.dispatchEvent(new CustomEvent("ayka:calculator-update", { detail: { params: params, result: result } }));
  };

  CalculatorWidget.prototype.transferToForm = function () {
    if (!this.lastParams || !this.lastResult) this.update();
    var payload = Object.assign({}, this.lastParams, {
      price_min: this.lastResult.price_min,
      price_max: this.lastResult.price_max,
    });
    document.dispatchEvent(new CustomEvent("ayka:calculator-transfer", { detail: payload }));
    var form = document.querySelector("[data-lead-form]");
    if (form) {
      form.scrollIntoView({ behavior: "smooth", block: "start" });
      var firstField = form.querySelector('input[name="name"]');
      if (firstField) window.setTimeout(function () { firstField.focus(); }, 400);
    }
  };

  function init() {
    var pricing = loadPricing();
    if (!pricing) return;
    var i18nEl = document.getElementById("calculator-i18n");
    var i18n = {};
    try {
      i18n = i18nEl ? JSON.parse(i18nEl.textContent) : {};
    } catch (e) {
      i18n = {};
    }
    document.querySelectorAll("[data-calculator]").forEach(function (root) {
      new CalculatorWidget(root, pricing, i18n);
    });
  }

  document.addEventListener("DOMContentLoaded", init);

  // Exposed for tests / other scripts.
  window.AykaCalculator = { computeRange: computeRange, computeTotal: computeTotal, estimateEffort: estimateEffort };
})();
