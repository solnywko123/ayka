"""Rate limiting общий объект (BRIEF.md раздел 7): 5 заявок/час на IP, 30 /quote в минуту."""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
