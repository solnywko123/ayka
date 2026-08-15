from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie
from jose import JWTError, jwt

from .config import settings

ALGORITHM = "HS256"
TOKEN_TTL_HOURS = 12
COOKIE_NAME = "ayka_admin_token"

_cookie_scheme = APIKeyCookie(name=COOKIE_NAME, auto_error=False)


def verify_password(plain_password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    return jwt.encode({"sub": subject, "exp": expire}, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        return None
    return payload.get("sub")


def get_current_admin(token: str | None = Depends(_cookie_scheme)) -> str:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    subject = decode_token(token)
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    return subject


def cookie_kwargs() -> dict:
    """httpOnly + Secure + SameSite=Lax (BRIEF.md раздел 7). Secure отключается только в
    BUILD_ENV=dev, иначе локальная разработка по обычному http:// невозможна — браузер
    (и http.cookiejar) не отправляют Secure-куки без TLS."""
    return {
        "httponly": True,
        "secure": settings.build_env != "dev",
        "samesite": "lax",
        "max_age": TOKEN_TTL_HOURS * 60 * 60,
    }


def hash_ip(ip_address: str) -> str:
    """IP хранится только как SHA-256 хеш с солью (персональные данные, BRIEF.md раздел 7)."""
    return hashlib.sha256(f"{ip_address}{settings.ip_hash_salt}".encode("utf-8")).hexdigest()
