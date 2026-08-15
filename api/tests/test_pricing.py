"""Раздел 15 BRIEF.md: базовый случай, минимальный заказ, все допы, все множители, скидки.
Ожидаемые значения посчитаны независимым эталонным скриптом по site/content/pricing.json
(см. DECISIONS.md) — единый источник правды и для фронта, и для бэка."""
from app.pricing import compute_price


def test_base_case():
    result = compute_price(
        service_type="general", property_type="apartment", area_m2=60, bathrooms=1,
        addons={}, urgency="normal", frequency="once",
    )
    assert result["price_min"] == 9180
    assert result["price_max"] == 12420


def test_minimum_order_floor():
    result = compute_price(
        service_type="maintenance", property_type="apartment", area_m2=20, bathrooms=1,
        addons={}, urgency="normal", frequency="once",
    )
    assert result["price_min"] == 2130
    assert result["price_max"] == 2880


def test_all_addons():
    result = compute_price(
        service_type="general", property_type="apartment", area_m2=60, bathrooms=1,
        addons={
            "windows_per_sash": 1, "sofa_seat": 1, "carpet_per_m2": 1,
            "fridge_inside": 1, "oven_inside": 1, "balcony": 1, "ironing_per_hour": 1,
        },
        urgency="normal", frequency="once",
    )
    assert result["price_min"] == 13050
    assert result["price_max"] == 17650


def test_all_multipliers_house_urgent():
    result = compute_price(
        service_type="general", property_type="house", area_m2=60, bathrooms=1,
        addons={}, urgency="urgent", frequency="once",
    )
    assert result["price_min"] == 12120
    assert result["price_max"] == 16390


def test_office_multiplier():
    result = compute_price(
        service_type="maintenance", property_type="office", area_m2=60, bathrooms=1,
        addons={}, urgency="normal", frequency="once",
    )
    assert result["price_min"] == 4820
    assert result["price_max"] == 6520


def test_weekly_discount():
    result = compute_price(
        service_type="general", property_type="apartment", area_m2=60, bathrooms=1,
        addons={}, urgency="normal", frequency="weekly",
    )
    assert result["price_min"] == 7800
    assert result["price_max"] == 10560


def test_extra_bathroom_surcharge():
    result = compute_price(
        service_type="general", property_type="apartment", area_m2=60, bathrooms=2,
        addons={}, urgency="normal", frequency="once",
    )
    assert result["price_min"] == 9610
    assert result["price_max"] == 12990


def test_price_max_always_above_price_min():
    result = compute_price(
        service_type="post_renovation", property_type="house", area_m2=150, bathrooms=3,
        addons={"windows_per_sash": 6}, urgency="urgent", frequency="monthly",
    )
    assert result["price_max"] > result["price_min"]
