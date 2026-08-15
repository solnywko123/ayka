"""Общая логика админки — используется и JSON API (routers/admin.py),
и серверным HTML-интерфейсом (admin_ui/), без дублирования и без внутренних HTTP-вызовов."""
from __future__ import annotations

import csv
import io
import uuid
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models


class LeadFilters:
    def __init__(
        self,
        status: str | None = None,
        service_type: str | None = None,
        lang: str | None = None,
        utm_source: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
    ) -> None:
        self.status = status or None
        self.service_type = service_type or None
        self.lang = lang or None
        self.utm_source = utm_source or None
        self.date_from = date_from
        self.date_to = date_to
        self.search = search or None

    def apply(self, query):
        if self.status:
            query = query.filter(models.Lead.status == self.status)
        if self.service_type:
            query = query.filter(models.Lead.service_type == self.service_type)
        if self.lang:
            query = query.filter(models.Lead.lang == self.lang)
        if self.utm_source:
            query = query.filter(models.Lead.utm_source == self.utm_source)
        if self.date_from:
            query = query.filter(models.Lead.created_at >= self.date_from)
        if self.date_to:
            query = query.filter(models.Lead.created_at < self.date_to + timedelta(days=1))
        if self.search:
            like = f"%{self.search}%"
            query = query.filter((models.Lead.name.ilike(like)) | (models.Lead.phone.ilike(like)))
        return query


def list_leads(db: Session, filters: LeadFilters, page: int = 1, page_size: int = 50):
    query = db.query(models.Lead)
    query = filters.apply(query)
    total = query.count()
    items = (
        query.order_by(models.Lead.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_lead(db: Session, lead_id: uuid.UUID) -> models.Lead | None:
    return db.get(models.Lead, lead_id)


def update_lead(db: Session, lead: models.Lead, *, status: str | None, admin_note: str | None,
                 assigned_to: str | None, actor: str) -> models.Lead:
    if status and status != lead.status.value:
        db.add(models.LeadEvent(lead_id=lead.id, from_status=lead.status.value, to_status=status, actor=actor))
        lead.status = models.LeadStatus(status)
    if admin_note is not None:
        lead.admin_note = admin_note
    if assigned_to is not None:
        lead.assigned_to = assigned_to
    db.commit()
    db.refresh(lead)
    return lead


def export_csv(leads: list[models.Lead]) -> str:
    buffer = io.StringIO()
    buffer.write("﻿")  # UTF-8 BOM, чтобы Excel корректно показывал кириллицу
    writer = csv.writer(buffer)
    writer.writerow([
        "id", "created_at", "status", "name", "phone", "contact_channel", "service_type",
        "property_type", "area_m2", "bathrooms", "urgency", "frequency", "preferred_date",
        "district", "address", "comment", "price_min", "price_max", "currency", "lang",
        "utm_source", "utm_medium", "utm_campaign", "assigned_to",
    ])
    for lead in leads:
        writer.writerow([
            str(lead.id), lead.created_at.isoformat(), lead.status.value, lead.name, lead.phone,
            lead.contact_channel.value, lead.service_type.value, lead.property_type.value,
            lead.area_m2, lead.bathrooms, lead.urgency.value, lead.frequency.value,
            lead.preferred_date.isoformat() if lead.preferred_date else "",
            lead.district or "", lead.address or "", lead.comment or "",
            lead.price_min, lead.price_max, lead.currency, lead.lang.value,
            lead.utm_source or "", lead.utm_medium or "", lead.utm_campaign or "", lead.assigned_to or "",
        ])
    return buffer.getvalue()


def compute_stats(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    d7 = today_start - timedelta(days=7)
    d30 = today_start - timedelta(days=30)

    leads_today = db.query(models.Lead).filter(models.Lead.created_at >= today_start).count()
    leads_7d = db.query(models.Lead).filter(models.Lead.created_at >= d7).count()
    leads_30d = db.query(models.Lead).filter(models.Lead.created_at >= d30).count()

    potential = (
        db.query(func.coalesce(func.sum(models.Lead.price_max), 0))
        .filter(models.Lead.status != models.LeadStatus.spam)
        .scalar()
        or 0
    )

    by_status_rows = db.query(models.Lead.status, func.count(models.Lead.id)).group_by(models.Lead.status).all()
    by_status = {status.value: count for status, count in by_status_rows}

    by_day_rows = (
        db.query(func.date(models.Lead.created_at), func.count(models.Lead.id))
        .filter(models.Lead.created_at >= d30)
        .group_by(func.date(models.Lead.created_at))
        .order_by(func.date(models.Lead.created_at))
        .all()
    )
    by_day = [{"date": str(d), "count": c} for d, c in by_day_rows]

    utm_rows = (
        db.query(models.Lead.utm_source, func.count(models.Lead.id))
        .filter(models.Lead.utm_source.isnot(None))
        .group_by(models.Lead.utm_source)
        .order_by(func.count(models.Lead.id).desc())
        .limit(10)
        .all()
    )
    top_utm_sources = [{"source": source, "count": count} for source, count in utm_rows]

    return {
        "leads_today": leads_today,
        "leads_7d": leads_7d,
        "leads_30d": leads_30d,
        "potential_total_kgs": float(potential),
        "by_status": by_status,
        "by_day": by_day,
        "top_utm_sources": top_utm_sources,
    }
