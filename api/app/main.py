from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .admin_ui.router import router as admin_ui_router
from .config import settings
from .limiter import limiter
from .routers import admin, health, leads, quote

app = FastAPI(title="Ayka Cleaning API", version="0.1.0")

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

API_PREFIX = "/api/v1"

app.include_router(health.router, prefix=API_PREFIX, tags=["health"])
app.include_router(quote.router, prefix=API_PREFIX, tags=["quote"])
app.include_router(leads.router, prefix=API_PREFIX, tags=["leads"])
app.include_router(admin.router, prefix=API_PREFIX, tags=["admin"])

# Серверный HTML-интерфейс админки (BRIEF.md раздел 9) — отдельно от JSON API выше.
ADMIN_STATIC_DIR = Path(__file__).resolve().parent / "admin_ui" / "static"
app.mount("/admin/static", StaticFiles(directory=str(ADMIN_STATIC_DIR)), name="admin_static")
app.include_router(admin_ui_router)


# ---------- Security headers (BRIEF.md раздел 7) ----------
# JSON API отдаёт только данные -> максимально строгий CSP.
# /admin — серверный HTML со своим CSS/JS с того же домена -> чуть менее строгий self-only CSP.

API_CSP = "default-src 'none'; frame-ancestors 'none'"
ADMIN_CSP = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'"


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = ADMIN_CSP if request.url.path.startswith("/admin") else API_CSP
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["X-Frame-Options"] = "DENY"
    return response


# ---------- Единый формат ошибок: {"error": {"code": "...", "message": "..."}} ----------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    messages = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": messages}},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": str(exc.detail)}},
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": {"code": "rate_limited", "message": "Слишком много запросов, попробуйте позже."}},
    )
