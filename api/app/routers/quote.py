from fastapi import APIRouter, Request

from ..config import settings
from ..limiter import limiter
from ..pricing import compute_price
from ..schemas import QuoteRequest, QuoteResponse

router = APIRouter()


@router.post("/quote", response_model=QuoteResponse)
@limiter.limit(f"{settings.rate_limit_quote_per_minute}/minute")
def quote(request: Request, payload: QuoteRequest) -> QuoteResponse:
    result = compute_price(
        service_type=payload.service_type.value,
        property_type=payload.property_type.value,
        area_m2=payload.area_m2,
        bathrooms=payload.bathrooms,
        addons=payload.addons,
        urgency=payload.urgency.value,
        frequency=payload.frequency.value,
    )
    return QuoteResponse(price_min=result["price_min"], price_max=result["price_max"], currency="KGS")
