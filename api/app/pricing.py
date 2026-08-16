"""
Расчёт цены — независимая проверка того, что посчитал калькулятор на фронте
(BRIEF.md, раздел 6). Читает тот же site/content/pricing.json, что и сборщик
сайта (site/build.py встраивает его в HTML для калькулятора) — единый источник
правды, файл не копируется.

Формула побитово совпадает с site/static/js/calculator.js — там оставлен
комментарий с обратной ссылкой сюда.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
from pathlib import Path
from typing import Any

from .config import settings

logger = logging.getLogger("ayka.pricing")

REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_pricing_path() -> Path:
    path = Path(settings.pricing_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def load_pricing() -> dict[str, Any]:
    path = resolve_pricing_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    logger.info("pricing.json loaded from %s (sha256=%s...)", path, digest)
    return data


PRICING: dict[str, Any] = load_pricing()


def round_to_ten(value: float) -> float:
    """Round-half-up to the nearest 10, matching JS `Math.round(x / 10) * 10`
    (Python's built-in round() uses banker's rounding and would occasionally diverge)."""
    return math.floor(value / 10 + 0.5) * 10


def compute_price(
    *,
    service_type: str,
    property_type: str,
    area_m2: int | float,
    bathrooms: int,
    addons: dict[str, int] | None,
    urgency: str,
    frequency: str,
    pricing: dict[str, Any] | None = None,
) -> dict[str, float]:
    pricing = pricing or PRICING
    addons = addons or {}

    subscriptions = pricing.get("subscriptions_monthly", {})
    if frequency in subscriptions:
        # Регулярная уборка по подписке — фиксированная абонентская плата в месяц,
        # не зависит от площади/допуслуг/срочности (решение владельца, см. DECISIONS.md).
        flat_total = subscriptions[frequency]
        return {"total": flat_total, "price_min": flat_total, "price_max": flat_total}

    rate = pricing["base_rates_per_m2"][service_type]
    base = area_m2 * rate
    base += pricing["bathroom_extra"] * max(0, bathrooms - 1)

    addons_sum = 0.0
    for key, qty in addons.items():
        if qty and key in pricing["addons"]:
            addons_sum += pricing["addons"][key] * qty

    property_multiplier = 1.0
    if property_type == "house":
        property_multiplier = pricing["multipliers"]["property_house"]
    elif property_type == "office":
        property_multiplier = pricing["multipliers"]["property_office"]

    urgency_multiplier = pricing["multipliers"]["urgency_today"] if urgency == "urgent" else 1.0

    subtotal = (base + addons_sum) * property_multiplier * urgency_multiplier

    total = max(subtotal, pricing["min_order"])
    spread = pricing["price_range_spread"]

    return {
        "total": total,
        "price_min": round_to_ten(total * (1 - spread)),
        "price_max": round_to_ten(total * (1 + spread)),
    }
