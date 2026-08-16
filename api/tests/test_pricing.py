"""Раздел 15 BRIEF.md: базовый случай, минимальный заказ, все допы, все множители, абонементы.
Ожидаемые значения посчитаны независимым эталонным скриптом по site/content/pricing.json
(см. DECISIONS.md) — единый источник правды и для фронта, и для бэка."""
from app.pricing import compute_price


def test_base_case():
    result = compute_price(
        service_type="general", property_type="apartment", area_m2=60, bathrooms=1,
        addons={}, urgency="normal", frequency="once",
    )
    assert result["price_min"] == 7650
    assert result["price_max"] == 10350


def test_minimum_order_floor():
    result = compute_price(
        service_type="maintenance", property_type="apartment", area_m2=20, bathrooms=1,
        addons={}, urgency="normal", frequency="once",
    )
    assert result["price_min"] == 7650
    assert result["price_max"] == 10350


def test_all_addons():
    result = compute_price(
        service_type="general", property_type="apartment", area_m2=60, bathrooms=1,
        addons={
            "windows_per_m2": 1, "sofa_dry_clean": 1, "carpet_per_m2": 1,
            "fridge_inside": 1, "oven_inside": 1, "balcony": 1, "ironing_per_hour": 1,
        },
        urgency="normal", frequency="once",
    )
    assert result["price_min"] == 11200
    assert result["price_max"] == 15150


def test_all_multipliers_house_urgent():
    result = compute_price(
        service_type="general", property_type="house", area_m2=60, bathrooms=1,
        addons={}, urgency="urgent", frequency="once",
    )
    assert result["price_min"] == 10100
    assert result["price_max"] == 13660


def test_office_multiplier():
    result = compute_price(
        service_type="maintenance", property_type="office", area_m2=60, bathrooms=1,
        addons={}, urgency="normal", frequency="once",
    )
    assert result["price_min"] == 7650
    assert result["price_max"] == 10350


def test_extra_bathroom_surcharge():
    result = compute_price(
        service_type="general", property_type="apartment", area_m2=60, bathrooms=2,
        addons={}, urgency="normal", frequency="once",
    )
    assert result["price_min"] == 8080
    assert result["price_max"] == 10930


def test_price_max_always_above_price_min():
    result = compute_price(
        service_type="post_renovation", property_type="house", area_m2=150, bathrooms=3,
        addons={"windows_per_m2": 6}, urgency="urgent", frequency="once",
    )
    assert result["price_max"] > result["price_min"]


def test_subscription_tiers_are_flat_monthly_rates():
    """Абонемент на регулярную уборку — фиксированная плата в месяц, не зависит
    от площади, допуслуг, срочности или типа объекта (решение владельца, см. DECISIONS.md)."""
    expected = {"weekly": 12000, "biweekly": 8000, "monthly": 5000}
    for frequency, price in expected.items():
        result = compute_price(
            service_type="post_renovation", property_type="house", area_m2=200, bathrooms=4,
            addons={"windows_per_m2": 10}, urgency="urgent", frequency=frequency,
        )
        assert result["total"] == price
        assert result["price_min"] == price
        assert result["price_max"] == price
