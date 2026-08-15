import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from .. import admin_service
from ..config import settings
from ..database import get_db
from ..limiter import limiter
from ..schemas import AdminLoginRequest, LeadDetailOut, LeadListItem, LeadListResponse, LeadUpdate, StatsResponse
from ..security import COOKIE_NAME, cookie_kwargs, create_access_token, get_current_admin, verify_password

router = APIRouter()


@router.post("/admin/login")
@limiter.limit("5/minute")
def login(request: Request, payload: AdminLoginRequest, response: Response):
    valid_username = payload.username == settings.admin_username
    valid_password = verify_password(payload.password, settings.admin_password_hash)
    if not (valid_username and valid_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    token = create_access_token(subject=payload.username)
    response.set_cookie(key=COOKIE_NAME, value=token, **cookie_kwargs())
    return {"ok": True}


@router.post("/admin/logout")
def logout(response: Response, _admin: str = Depends(get_current_admin)):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/admin/leads", response_model=LeadListResponse)
def list_leads(
    status_filter: str | None = Query(default=None, alias="status"),
    service_type: str | None = None,
    lang: str | None = None,
    utm_source: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_current_admin),
):
    filters = admin_service.LeadFilters(
        status=status_filter, service_type=service_type, lang=lang, utm_source=utm_source,
        date_from=date_from, date_to=date_to, search=search,
    )
    items, total = admin_service.list_leads(db, filters, page=page, page_size=page_size)
    return LeadListResponse(
        items=[LeadListItem.model_validate(lead) for lead in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/admin/leads/export.csv")
def export_leads_csv(
    status_filter: str | None = Query(default=None, alias="status"),
    service_type: str | None = None,
    lang: str | None = None,
    utm_source: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_current_admin),
):
    filters = admin_service.LeadFilters(
        status=status_filter, service_type=service_type, lang=lang, utm_source=utm_source,
        date_from=date_from, date_to=date_to, search=search,
    )
    items, _ = admin_service.list_leads(db, filters, page=1, page_size=100000)
    csv_text = admin_service.export_csv(items)
    return PlainTextResponse(
        csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )


@router.get("/admin/leads/{lead_id}", response_model=LeadDetailOut)
def get_lead(lead_id: uuid.UUID, db: Session = Depends(get_db), _admin: str = Depends(get_current_admin)):
    lead = admin_service.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
    return LeadDetailOut.model_validate(lead)


@router.patch("/admin/leads/{lead_id}", response_model=LeadDetailOut)
def patch_lead(
    lead_id: uuid.UUID, payload: LeadUpdate, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)
):
    lead = admin_service.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
    lead = admin_service.update_lead(
        db, lead,
        status=payload.status.value if payload.status else None,
        admin_note=payload.admin_note,
        assigned_to=payload.assigned_to,
        actor=admin,
    )
    return LeadDetailOut.model_validate(lead)


@router.get("/admin/stats", response_model=StatsResponse)
def stats(db: Session = Depends(get_db), _admin: str = Depends(get_current_admin)):
    return StatsResponse(**admin_service.compute_stats(db))
