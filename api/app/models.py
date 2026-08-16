from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Integer, JSON, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .database import Base


class LeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    scheduled = "scheduled"
    done = "done"
    canceled = "canceled"
    spam = "spam"


class ContactChannel(str, enum.Enum):
    whatsapp = "whatsapp"
    call = "call"
    telegram = "telegram"


class ServiceType(str, enum.Enum):
    maintenance = "maintenance"
    general = "general"
    post_renovation = "post_renovation"
    post_move = "post_move"


class PropertyType(str, enum.Enum):
    apartment = "apartment"
    house = "house"
    office = "office"


class Urgency(str, enum.Enum):
    normal = "normal"
    urgent = "urgent"


class Frequency(str, enum.Enum):
    once = "once"
    monthly = "monthly"
    biweekly = "biweekly"
    weekly = "weekly"


class Lang(str, enum.Enum):
    ru = "ru"
    ky = "ky"
    en = "en"


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_status_created_at", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    status: Mapped[LeadStatus] = mapped_column(
        SAEnum(LeadStatus, native_enum=False, length=20), default=LeadStatus.new, index=True
    )

    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20), index=True)
    contact_channel: Mapped[ContactChannel] = mapped_column(
        SAEnum(ContactChannel, native_enum=False, length=20), default=ContactChannel.whatsapp
    )

    # Калькулятор убран с сайта — service_type/area_m2 больше никогда не приходят
    # от клиента, менеджер уточняет это сам после осмотра (см. DECISIONS.md).
    service_type: Mapped[ServiceType | None] = mapped_column(
        SAEnum(ServiceType, native_enum=False, length=20), nullable=True
    )
    property_type: Mapped[PropertyType] = mapped_column(
        SAEnum(PropertyType, native_enum=False, length=20), default=PropertyType.apartment
    )
    area_m2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[int] = mapped_column(Integer, default=1)
    addons: Mapped[dict] = mapped_column(JSON, default=dict)
    urgency: Mapped[Urgency] = mapped_column(SAEnum(Urgency, native_enum=False, length=20), default=Urgency.normal)
    frequency: Mapped[Frequency] = mapped_column(
        SAEnum(Frequency, native_enum=False, length=20), default=Frequency.once
    )

    preferred_date: Mapped[date | None] = mapped_column(nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    price_min: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_max: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="KGS")

    lang: Mapped[Lang] = mapped_column(SAEnum(Lang, native_enum=False, length=8), default=Lang.ru)

    utm_source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(200), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(200), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(200), nullable=True)
    utm_term: Mapped[str | None] = mapped_column(String(200), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    landing_page: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)

    events: Mapped[list["LeadEvent"]] = relationship(
        "LeadEvent", back_populates="lead", cascade="all, delete-orphan", order_by="LeadEvent.created_at"
    )


class LeadEvent(Base):
    __tablename__ = "lead_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20))
    actor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    lead: Mapped[Lead] = relationship("Lead", back_populates="events")
