from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import ContactChannel, Frequency, Lang, LeadStatus, PropertyType, ServiceType, Urgency
from .utils import InvalidPhoneError, normalize_kg_phone, strip_html


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ---------- /quote ----------

class QuoteRequest(BaseModel):
    service_type: ServiceType
    property_type: PropertyType = PropertyType.apartment
    area_m2: int = Field(ge=5, le=1000)
    bathrooms: int = Field(default=1, ge=1, le=5)
    addons: dict[str, int] = Field(default_factory=dict)
    urgency: Urgency = Urgency.normal
    frequency: Frequency = Frequency.once


class QuoteResponse(BaseModel):
    price_min: float
    price_max: float
    currency: str = "KGS"


# ---------- /leads ----------

class LeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str
    contact_channel: ContactChannel = ContactChannel.whatsapp

    service_type: ServiceType
    property_type: PropertyType = PropertyType.apartment
    area_m2: int = Field(ge=5, le=1000)
    bathrooms: int = Field(default=1, ge=1, le=5)
    addons: dict[str, int] = Field(default_factory=dict)
    urgency: Urgency = Urgency.normal
    frequency: Frequency = Frequency.once

    preferred_date: date | None = None
    district: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=300)
    comment: str | None = Field(default=None, max_length=1000)
    lang: Lang = Lang.ru

    # Клиентский расчёт передаётся, но не используется для сохранения — сервер пересчитывает сам (раздел 6).
    price_min: float | None = None
    price_max: float | None = None

    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    utm_term: str | None = None
    referrer: str | None = None
    landing_page: str | None = None

    # Антиспам (раздел 7): rendered_at — момент рендера формы (time-trap),
    # company_website — honeypot-поле, скрытое CSS, должно оставаться пустым.
    rendered_at: str | None = None
    company_website: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        try:
            return normalize_kg_phone(value)
        except InvalidPhoneError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("comment", "district", "address")
    @classmethod
    def sanitize_text(cls, value: str | None) -> str | None:
        return strip_html(value)

    @field_validator("preferred_date")
    @classmethod
    def validate_preferred_date(cls, value: date | None) -> date | None:
        if value is None:
            return value
        today = date.today()
        if value < today:
            raise ValueError("preferred_date не может быть в прошлом")
        if value > today + timedelta(days=90):
            raise ValueError("preferred_date не может быть дальше 90 дней")
        return value


class LeadCreateResult(BaseModel):
    id: uuid.UUID
    status: LeadStatus
    price_min: float
    price_max: float
    currency: str = "KGS"


# ---------- Admin ----------

class AdminLoginRequest(BaseModel):
    username: str
    password: str


class LeadEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    from_status: str | None
    to_status: str
    actor: str | None
    note: str | None


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    status: LeadStatus
    name: str
    phone: str
    contact_channel: ContactChannel
    service_type: ServiceType
    property_type: PropertyType
    area_m2: int
    bathrooms: int
    addons: dict
    urgency: Urgency
    frequency: Frequency
    preferred_date: date | None
    district: str | None
    address: str | None
    comment: str | None
    price_min: float
    price_max: float
    currency: str
    lang: Lang
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_content: str | None
    utm_term: str | None
    referrer: str | None
    landing_page: str | None
    admin_note: str | None
    assigned_to: str | None


class LeadDetailOut(LeadOut):
    events: list[LeadEventOut] = Field(default_factory=list)


class LeadListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    status: LeadStatus
    name: str
    phone: str
    service_type: ServiceType
    area_m2: int
    price_min: float
    price_max: float
    lang: Lang
    utm_source: str | None


class LeadListResponse(BaseModel):
    items: list[LeadListItem]
    total: int
    page: int
    page_size: int


class LeadUpdate(BaseModel):
    status: LeadStatus | None = None
    admin_note: str | None = None
    assigned_to: str | None = None


class StatsDayCount(BaseModel):
    date: str
    count: int


class StatsResponse(BaseModel):
    leads_today: int
    leads_7d: int
    leads_30d: int
    potential_total_kgs: float
    by_status: dict[str, int]
    by_day: list[StatsDayCount]
    top_utm_sources: list[dict]
