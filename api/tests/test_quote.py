from conftest import make_valid_lead_payload


def test_quote_matches_lead_price(client):
    """Раздел 15: совпадение результата фронтового и бэкового расчёта.
    /quote — то же, что считает calculator.js на клиенте; /leads — независимый пересчёт
    на сервере. Оба должны сойтись, потому что читают один и тот же pricing.json
    и реализуют одну и ту же формулу (см. DECISIONS.md)."""
    quote_payload = {
        "service_type": "post_renovation", "property_type": "house", "area_m2": 120,
        "bathrooms": 2, "addons": {"windows_per_m2": 4}, "urgency": "urgent", "frequency": "weekly",
    }
    quote_response = client.post("/api/v1/quote", json=quote_payload)
    assert quote_response.status_code == 200
    quote_body = quote_response.json()

    lead_payload = make_valid_lead_payload(**quote_payload)
    lead_response = client.post("/api/v1/leads", json=lead_payload)
    assert lead_response.status_code == 200
    lead_body = lead_response.json()

    assert lead_body["price_min"] == quote_body["price_min"]
    assert lead_body["price_max"] == quote_body["price_max"]


def test_quote_rate_limit_per_minute(client):
    for i in range(30):
        response = client.post(
            "/api/v1/quote",
            json={"service_type": "general", "area_m2": 60, "bathrooms": 1},
        )
        assert response.status_code == 200, response.text

    response = client.post("/api/v1/quote", json={"service_type": "general", "area_m2": 60, "bathrooms": 1})
    assert response.status_code == 429
