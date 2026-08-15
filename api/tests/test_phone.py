import pytest

from app.utils import InvalidPhoneError, normalize_kg_phone


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("0555123456", "+996555123456"),
        ("996555123456", "+996555123456"),
        ("+996 555 12-34-56", "+996555123456"),
        ("555123456", "+996555123456"),
        ("+996555123456", "+996555123456"),
        ("8 996 555 12 34 56", "+996555123456"),
        ("0 700 000 000", "+996700000000"),
    ],
)
def test_normalize_valid_formats(raw: str, expected: str):
    assert normalize_kg_phone(raw) == expected


@pytest.mark.parametrize("raw", ["123", "", "abc", "996123", "+7 900 123-45-67", "99655512345678"])
def test_normalize_rejects_invalid(raw: str):
    with pytest.raises(InvalidPhoneError):
        normalize_kg_phone(raw)
