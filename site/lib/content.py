"""Loading of JSON/Markdown content — single source of truth for the whole build."""
from __future__ import annotations

import json
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_config() -> dict:
    return load_json(CONTENT_DIR / "config.json")


def load_pricing() -> dict:
    return load_json(CONTENT_DIR / "pricing.json")


def load_lang_content(lang: str) -> dict:
    d = CONTENT_DIR / lang
    return {
        "ui": load_json(d / "ui.json"),
        "calculator": load_json(d / "calculator.json"),
        "services": load_json(d / "services.json")["services"],
        "pages": load_json(d / "pages.json"),
        "faq": load_json(d / "faq.json")["items"],
        "reviews": load_json(d / "reviews.json")["items"],
        "districts": load_json(d / "districts.json")["items"],
        "seo": load_json(d / "seo.json"),
    }


def service_by_slug(services: list[dict], slug: str) -> dict | None:
    for s in services:
        if s["slug"] == slug:
            return s
    return None
