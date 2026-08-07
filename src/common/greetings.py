from __future__ import annotations

from datetime import datetime, timedelta, timezone

from common.config import get_settings


def make_hello() -> str:
    settings = get_settings()
    utc_time = datetime.now(timezone.utc)
    hour = utc_time.astimezone(timezone(timedelta(hours=settings.msk_offset))).hour
    if 5 <= hour < 12:
        return "Здорово почивали!"
    if 12 <= hour < 18:
        return "Здорово дневали!"
    return "Здорово вечеряли!"
