from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import admin_service
from ..config import settings
from ..database import get_db
from ..security import COOKIE_NAME, cookie_kwargs, create_access_token, verify_password
from .auth import current_admin_or_redirect

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(include_in_schema=False)


@router.get("/admin/login")
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/admin/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(default="/admin"),
):
    valid = username == settings.admin_username and verify_password(password, settings.admin_password_hash)
    if not valid:
        return templates.TemplateResponse(
            request, "login.html", {"error": "Неверный логин или пароль"}, status_code=401
        )
    token = create_access_token(subject=username)
    response = RedirectResponse(url=next or "/admin", status_code=302)
    response.set_cookie(COOKIE_NAME, token, **cookie_kwargs())
    return response


@router.get("/admin/logout")
def logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("/admin")
def dashboard(request: Request, db: Session = Depends(get_db)):
    admin = current_admin_or_redirect(request)
    if isinstance(admin, RedirectResponse):
        return admin
    stats = admin_service.compute_stats(db)
    return templates.TemplateResponse(request, "dashboard.html", {"admin": admin, "stats": stats})


@router.get("/admin/leads")
def leads_page(
    request: Request,
    status: str | None = None,
    service_type: str | None = None,
    lang: str | None = None,
    utm_source: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    page: int = 1,
    db: Session = Depends(get_db),
):
    admin = current_admin_or_redirect(request)
    if isinstance(admin, RedirectResponse):
        return admin
    filters = admin_service.LeadFilters(
        status=status, service_type=service_type, lang=lang, utm_source=utm_source,
        date_from=date_from, date_to=date_to, search=search,
    )
    items, total = admin_service.list_leads(db, filters, page=page, page_size=50)
    total_pages = max(1, (total + 49) // 50)
    return templates.TemplateResponse(
        request, "leads.html",
        {
            "admin": admin, "items": items, "total": total, "page": page, "total_pages": total_pages,
            "filters": {
                "status": status or "", "service_type": service_type or "", "lang": lang or "",
                "utm_source": utm_source or "", "date_from": date_from or "", "date_to": date_to or "",
                "search": search or "",
            },
        },
    )


@router.get("/admin/leads/{lead_id}")
def lead_detail_page(request: Request, lead_id: uuid.UUID, db: Session = Depends(get_db)):
    admin = current_admin_or_redirect(request)
    if isinstance(admin, RedirectResponse):
        return admin
    lead = admin_service.get_lead(db, lead_id)
    if not lead:
        return RedirectResponse(url="/admin/leads", status_code=302)
    return templates.TemplateResponse(request, "lead_detail.html", {"admin": admin, "lead": lead})


@router.post("/admin/leads/{lead_id}/update")
def lead_detail_update(
    request: Request,
    lead_id: uuid.UUID,
    status: str = Form(default=""),
    admin_note: str = Form(default=""),
    assigned_to: str = Form(default=""),
    db: Session = Depends(get_db),
):
    admin = current_admin_or_redirect(request)
    if isinstance(admin, RedirectResponse):
        return admin
    lead = admin_service.get_lead(db, lead_id)
    if lead:
        admin_service.update_lead(
            db, lead, status=status or None, admin_note=admin_note, assigned_to=assigned_to or None, actor=admin
        )
    return RedirectResponse(url=f"/admin/leads/{lead_id}", status_code=302)
