"""Cookie-аутентификация для серверных HTML-страниц /admin (в отличие от
security.get_current_admin, который используется JSON API и кидает 401)."""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import RedirectResponse

from ..security import COOKIE_NAME, decode_token


def current_admin_or_redirect(request: Request) -> str | RedirectResponse:
    token = request.cookies.get(COOKIE_NAME)
    subject = decode_token(token) if token else None
    if not subject:
        next_url = request.url.path
        return RedirectResponse(url=f"/admin/login?next={next_url}", status_code=302)
    return subject
