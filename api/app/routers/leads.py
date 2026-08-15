from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from .. import models
from ..antispam import is_spam
from ..config import settings
from ..database import get_db
from ..limiter import limiter
from ..notify import notify_telegram
from ..pricing import compute_price
from ..schemas import LeadCreate, LeadCreateResult
from ..security import hash_ip

router = APIRouter()


@router.post("/leads", response_model=LeadCreateResult, status_code=200)
@limiter.limit(f"{settings.rate_limit_leads_per_hour}/hour")
def create_lead(
    request: Request, payload: LeadCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> LeadCreateResult:
    spam = is_spam(payload, db)

    price = compute_price(
        service_type=payload.service_type.value,
        property_type=payload.property_type.value,
        area_m2=payload.area_m2,
        bathrooms=payload.bathrooms,
        addons=payload.addons,
        urgency=payload.urgency.value,
        frequency=payload.frequency.value,
    )

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")

    lead = models.Lead(
        status=models.LeadStatus.spam if spam else models.LeadStatus.new,
        name=payload.name,
        phone=payload.phone,
        contact_channel=payload.contact_channel,
        service_type=payload.service_type,
        property_type=payload.property_type,
        area_m2=payload.area_m2,
        bathrooms=payload.bathrooms,
        addons=payload.addons,
        urgency=payload.urgency,
        frequency=payload.frequency,
        preferred_date=payload.preferred_date,
        district=payload.district,
        address=payload.address,
        comment=payload.comment,
        price_min=price["price_min"],
        price_max=price["price_max"],
        currency="KGS",
        lang=payload.lang,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        utm_content=payload.utm_content,
        utm_term=payload.utm_term,
        referrer=payload.referrer,
        landing_page=payload.landing_page,
        user_agent=user_agent,
        ip_hash=hash_ip(client_ip),
    )
    db.add(lead)
    db.flush()
    db.add(models.LeadEvent(lead_id=lead.id, from_status=None, to_status=lead.status.value, actor="system", note="created"))
    db.commit()
    db.refresh(lead)

    if not spam:
        background_tasks.add_task(notify_telegram, lead)

    return LeadCreateResult(
        id=lead.id, status=lead.status, price_min=float(lead.price_min), price_max=float(lead.price_max)
    )
