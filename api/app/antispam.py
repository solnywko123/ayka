"""Антиспам без капчи — она режет конверсию (BRIEF.md раздел 7):

1. Honeypot-поле `company_website`, скрытое CSS. Заполнено -> спам.
2. Time-trap: форма отправлена быстрее 3 секунд после рендера -> спам.
3. Блок-лист повторяющихся текстов: тот же телефон + тот же комментарий
   уже встречались -> спам. Ссылки в имени/комментарии -> спам.

Rate limiting (5 заявок/час на IP, 30 /quote/мин) настроен отдельно через
slowapi в main.py/limiter.py.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from . import models
from .schemas import LeadCreate

TIME_TRAP_SECONDS = 3
_LINK_RE = re.compile(r"https?://|www\.", re.IGNORECASE)


def _rendered_too_fast(rendered_at: str | None) -> bool:
    if not rendered_at:
        # Поле отсутствует — форма отправлена не через наш JS (или JS не выполнился).
        # Такое поведение типично для ботов, бьющих напрямую по API.
        return True
    try:
        rendered = datetime.fromisoformat(rendered_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if rendered.tzinfo is None:
        rendered = rendered.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - rendered).total_seconds()
    return elapsed < TIME_TRAP_SECONDS


def _has_link(*values: str | None) -> bool:
    return any(v and _LINK_RE.search(v) for v in values)


def _is_duplicate_text(db: Session, payload: LeadCreate) -> bool:
    if not payload.comment:
        return False
    existing = (
        db.query(models.Lead.id)
        .filter(models.Lead.phone == payload.phone, models.Lead.comment == payload.comment)
        .first()
    )
    return existing is not None


def is_spam(payload: LeadCreate, db: Session) -> bool:
    if payload.company_website:
        return True
    if _rendered_too_fast(payload.rendered_at):
        return True
    if _has_link(payload.name, payload.comment):
        return True
    if _is_duplicate_text(db, payload):
        return True
    return False
