import datetime

from conftest import make_valid_lead_payload


def test_create_lead_valid_data(client):
    """Раздел про удаление калькулятора (DECISIONS.md): без калькулятора клиент
    не присылает цену вообще — заявка создаётся нормально, price_min/price_max = null,
    менеджер называет цену сам после осмотра."""
    response = client.post("/api/v1/leads", json=make_valid_lead_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "new"
    assert body["price_min"] is None
    assert body["price_max"] is None


def test_create_lead_normalizes_phone(client):
    payload = make_valid_lead_payload(phone="+996 555 12-34-56")
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 200


def test_create_lead_without_calculator_context(client):
    """Калькулятор убран с сайта — service_type/area_m2 больше никогда не приходят
    от клиента, заявка обязана создаваться и без них (см. DECISIONS.md)."""
    payload = make_valid_lead_payload()
    del payload["service_type"]
    del payload["area_m2"]
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "new"
    assert body["price_min"] is None
    assert body["price_max"] is None


def test_create_lead_invalid_phone_rejected(client):
    response = client.post("/api/v1/leads", json=make_valid_lead_payload(phone="123"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_lead_honeypot_marks_spam(client):
    payload = make_valid_lead_payload(company_website="http://spammer.example")
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "spam"


def test_create_lead_time_trap_marks_spam(client):
    payload = make_valid_lead_payload(
        rendered_at=datetime.datetime.now(datetime.timezone.utc).isoformat()  # отправлено мгновенно
    )
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "spam"


def test_create_lead_missing_rendered_at_marks_spam(client):
    payload = make_valid_lead_payload()
    del payload["rendered_at"]
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "spam"


def test_create_lead_link_in_comment_marks_spam(client):
    payload = make_valid_lead_payload(comment="Check this out https://spam.example/promo")
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "spam"


def test_create_lead_duplicate_comment_marks_second_as_spam(client):
    payload = make_valid_lead_payload(phone="0555777777", comment="Уборка нужна срочно, перезвоните")
    first = client.post("/api/v1/leads", json=payload)
    assert first.json()["status"] == "new"
    second = client.post("/api/v1/leads", json=payload)
    assert second.json()["status"] == "spam"


def test_create_lead_rate_limit(client):
    for i in range(5):
        payload = make_valid_lead_payload(phone=f"055500000{i}")
        response = client.post("/api/v1/leads", json=payload)
        assert response.status_code == 200, response.text

    response = client.post("/api/v1/leads", json=make_valid_lead_payload(phone="0555000099"))
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"


def test_preferred_date_in_past_rejected(client):
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    payload = make_valid_lead_payload(preferred_date=yesterday)
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 422


def test_preferred_date_too_far_rejected(client):
    far_future = (datetime.date.today() + datetime.timedelta(days=91)).isoformat()
    payload = make_valid_lead_payload(preferred_date=far_future)
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 422


def test_preferred_date_empty_string_accepted(client):
    """<input type="date"> отправляет "" когда поле оставлено пустым (оно
    необязательное на сайте) — form.js шлёт его как есть, не опуская ключ."""
    payload = make_valid_lead_payload(preferred_date="")
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 200
    assert response.json()["id"]


def test_comment_html_is_sanitized(client):
    payload = make_valid_lead_payload(phone="0555888888", comment="<script>alert(1)</script>Hello")
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 200
