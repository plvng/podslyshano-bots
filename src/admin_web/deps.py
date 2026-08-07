from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from admin_web.constants import SESSION_COOKIE
from common.config import get_settings
from common.db.repository import Database


async def get_db() -> Database:
    settings = get_settings()
    db = Database(settings.database_path)
    await db.init()
    return db


async def require_admin(request: Request) -> int:
    session = request.cookies.get(SESSION_COOKIE)
    if not session:
        raise HTTPException(status_code=401, detail="Unauthorized")

    settings = get_settings()
    db = Database(settings.database_path)
    await db.init()
    admin_id = await db.get_admin_by_session(session)
    if admin_id is None or admin_id not in settings.admins:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return admin_id


def redirect_login() -> RedirectResponse:
    return RedirectResponse("/login", status_code=303)
