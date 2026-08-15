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
    return (
        f"🧹 Новая заявка Ayka Cleaning\n"
        f"Имя: {lead.name}\n"
        f"Телефон: {lead.phone}\n"
        f"Услуга: {lead.service_type.value}\n"
        f"Площадь: {lead.area_m2} м²\n"
        f"Цена: {lead.price_min}–{lead.price_max} {lead.currency}\n"
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
