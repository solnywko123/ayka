"""Опциональное уведомление о новой заявке в Telegram (BRIEF.md раздел 9).
Выключено по умолчанию — TELEGRAM_BOT_TOKEN="" в .env. Скорость первого контакта
напрямую влияет на конверсию, поэтому стоит включить после настройки бота (см. README)."""
from __future__ import annotations

import logging

import httpx

from .config import settings
from .models import Lead

logger = logging.getLogger("ayka.notify")


def format_lead_message(lead: Lead) -> str:
    service_line = f"Услуга: {lead.service_type.value}\n" if lead.service_type else ""
    area_line = f"Площадь: {lead.area_m2} м²\n" if lead.area_m2 else ""
    price_line = (
        f"Цена: {lead.price_min}–{lead.price_max} {lead.currency}\n"
        if lead.price_min is not None and lead.price_max is not None
        else "Цена: уточняется после осмотра объекта\n"
    )
    return (
        f"🧹 Новая заявка All Clean\n"
        f"Имя: {lead.name}\n"
        f"Телефон: {lead.phone}\n"
        f"{service_line}"
        f"{area_line}"
        f"{price_line}"
        f"Канал связи: {lead.contact_channel.value}\n"
        f"Комментарий: {lead.comment or '—'}"
    )


def notify_telegram(lead: Lead) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        response = httpx.post(
            url,
            json={"chat_id": settings.telegram_chat_id, "text": format_lead_message(lead)},
            timeout=5.0,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        logger.exception("Failed to send Telegram notification for lead %s", lead.id)
