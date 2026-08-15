"""
Валидатор site/content/config.json (BRIEF.md, раздел 19.3).

- сверяет config.json со схемой (обязательные поля, формат телефона, валидность URL);
- печатает список полей, оставшихся демонстрационными;
- BUILD_ENV=dev  -> предупреждение (жёлтое), сборка продолжается;
- BUILD_ENV=prod -> прерывает сборку (exit code 1), если остались плейсхолдеры.

Может использоваться и как отдельная команда (`make check-config`), и импортироваться build.py.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SITE_DIR / "content" / "config.json"

PLACEHOLDER_PATTERNS = {
    "phone": [r"\+996\s?700\s?000\s?000"],
    "whatsapp": [r"\+996\s?700\s?000\s?000"],
    "email": [r"@example\.kg$", r"^info@example\.kg$"],
    "domain": [r"^example\.kg$"],
}

REQUIRED_FIELDS = [
    "company_name",
    "tagline",
    "city",
    "country",
    "service_area",
    "phone",
    "whatsapp",
    "email",
    "work_hours",
    "domain",
    "currency",
    "currency_symbol",
    "languages",
    "default_language",
]

PHONE_RE = re.compile(r"^\+996\d{9}$")


def _normalize_phone_digits(value: str) -> str:
    return re.sub(r"[\s-]", "", value)
DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ConfigError(Exception):
    pass


def load_config(path: Path = CONFIG_PATH) -> dict:
    if not path.exists():
        raise ConfigError(f"Файл не найден: {path}")
    with path.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f"config.json содержит невалидный JSON: {e}") from e


def check_schema(config: dict) -> list[str]:
    """Returns a list of hard schema errors (missing fields, malformed values)."""
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in config:
            errors.append(f"отсутствует обязательное поле «{field}» в site/content/config.json")

    phone = config.get("phone", "")
    if phone and not PHONE_RE.match(_normalize_phone_digits(phone)):
        errors.append(f"поле «phone» не похоже на киргизский номер (+996 XXX XXX XXX): {phone!r}")

    whatsapp = config.get("whatsapp", "")
    if whatsapp and not PHONE_RE.match(_normalize_phone_digits(whatsapp)):
        errors.append(f"поле «whatsapp» не похоже на номер в формате +996 XXX XXX XXX: {whatsapp!r}")

    email = config.get("email", "")
    if email and not EMAIL_RE.match(email):
        errors.append(f"поле «email» не похоже на email: {email!r}")

    domain = config.get("domain", "")
    if domain and not DOMAIN_RE.match(domain):
        errors.append(f"поле «domain» не похоже на домен: {domain!r}")

    languages = config.get("languages", [])
    default_language = config.get("default_language")
    if default_language and default_language not in languages:
        errors.append("«default_language» должен входить в список «languages»")

    return errors


def find_placeholders(config: dict) -> list[str]:
    """Returns a list of human-readable descriptions of demo/placeholder values still present."""
    found = []
    for field, patterns in PLACEHOLDER_PATTERNS.items():
        value = config.get(field, "")
        if not isinstance(value, str):
            continue
        for pattern in patterns:
            if re.search(pattern, value):
                found.append(f"{field} = {value!r} (демо-значение из BRIEF.md, раздел 0)")
                break
    return found


def run(build_env: str | None = None, config_path: Path = CONFIG_PATH) -> dict:
    """Runs the full check. Returns the parsed config. Raises SystemExit(1) in prod if placeholders remain."""
    build_env = (build_env or os.environ.get("BUILD_ENV", "dev")).lower()
    config = load_config(config_path)

    schema_errors = check_schema(config)
    if schema_errors:
        print("check_config: ошибки схемы config.json:", file=sys.stderr)
        for err in schema_errors:
            print(f"  - {err}", file=sys.stderr)
        raise SystemExit(1)

    placeholders = find_placeholders(config)

    if placeholders:
        header = "ДЕМО-ЗНАЧЕНИЯ, ОСТАВШИЕСЯ В site/content/config.json:"
        lines = [header] + [f"  - {p}" for p in placeholders]
        message = "\n".join(lines)
        if build_env == "prod":
            print("\033[91mBUILD_ENV=prod: сборка прервана.\033[0m", file=sys.stderr)
            print(message, file=sys.stderr)
            print(
                "\nЗаполните эти поля в site/content/config.json реальными данными "
                "перед сборкой в проде (см. НАСТРОЙКА.md).",
                file=sys.stderr,
            )
            raise SystemExit(1)
        else:
            print(f"\033[93m{message}\033[0m")
            print("\033[93mBUILD_ENV=dev: сборка продолжается, на сайте будет показан демо-баннер.\033[0m")
    else:
        print("check_config: демо-значений не найдено, config.json готов к продакшену.")

    config["_has_placeholders"] = bool(placeholders)
    config["_build_env"] = build_env
    return config


if __name__ == "__main__":
    run()
