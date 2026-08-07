from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import redis.asyncio as redis
from aiogram import Bot
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from admin_web.constants import SESSION_COOKIE, TEMPLATES_DIR
from admin_web.deps import require_admin
from chat_bot.matching import ChatMatching
from common.config import get_settings
from common.db.repository import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db = Database(settings.database_path)
    await db.init()
    app.state.db = db
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    yield
    await app.state.redis.aclose()
    await db.close()


app = FastAPI(title="Podslyshano Admin", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse("/login", status_code=303)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


def db_from_state(request: Request) -> Database:
    return request.app.state.db


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"title": "Вход"})


@app.get("/auth")
async def auth(request: Request, token: str):
    db = db_from_state(request)
    admin_id = await db.consume_admin_token(token)
    if admin_id is None:
        return RedirectResponse("/login?error=1", status_code=303)
    session = await db.create_web_session(admin_id)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(SESSION_COOKIE, session, httponly=True, max_age=86400, samesite="lax")
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, admin_id: int = Depends(require_admin)):
    db = db_from_state(request)
    stats = await db.dashboard_stats()
    matching = ChatMatching(request.app.state.redis)
    stats["online_chat"] = await matching.online_count()
    activity = await db.activity_by_day()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"title": "Dashboard", "stats": stats, "activity": activity, "admin_id": admin_id},
    )


@app.get("/posts", response_class=HTMLResponse)
async def posts_page(request: Request, admin_id: int = Depends(require_admin)):
    db = db_from_state(request)
    posts = await db.list_posts()
    settings = get_settings()
    return templates.TemplateResponse(
        request,
        "posts.html",
        {"title": "Публикации", "posts": posts, "tgk": settings.tgk, "admin_id": admin_id},
    )


@app.get("/support", response_class=HTMLResponse)
async def support_page(request: Request, admin_id: int = Depends(require_admin)):
    db = db_from_state(request)
    threads = await db.list_support_threads()
    return templates.TemplateResponse(
        request,
        "support.html",
        {"title": "Обращения", "threads": threads, "admin_id": admin_id},
    )


@app.get("/support/{thread_id}", response_class=HTMLResponse)
async def support_detail(request: Request, thread_id: int, admin_id: int = Depends(require_admin)):
    db = db_from_state(request)
    messages = await db.get_support_messages(thread_id)
    threads = await db.list_support_threads()
    thread = next((item for item in threads if item["id"] == thread_id), None)
    if not thread:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request,
        "support_detail.html",
        {"title": f"Обращение #{thread_id}", "thread": thread, "messages": messages, "admin_id": admin_id},
    )


@app.post("/support/{thread_id}/reply")
async def support_reply(
    request: Request,
    thread_id: int,
    text: str = Form(...),
    admin_id: int = Depends(require_admin),
):
    db = db_from_state(request)
    threads = await db.list_support_threads()
    thread = next((item for item in threads if item["id"] == thread_id), None)
    if not thread:
        raise HTTPException(status_code=404)

    settings = get_settings()
    bot = Bot(token=settings.proposal_bot_token)
    try:
        sent = await bot.send_message(thread["user_id"], text)
        await db.add_support_message(thread_id, admin_id, "admin", _FakeMessage(text), sent.message_id)
    finally:
        await bot.session.close()
    return RedirectResponse(f"/support/{thread_id}", status_code=303)


@app.post("/support/{thread_id}/close")
async def support_close(request: Request, thread_id: int, admin_id: int = Depends(require_admin)):
    db = db_from_state(request)
    await db.close_support_thread(thread_id)
    return RedirectResponse("/support", status_code=303)


@app.get("/chats", response_class=HTMLResponse)
async def chats_page(request: Request, admin_id: int = Depends(require_admin)):
    db = db_from_state(request)
    sessions = await db.list_chat_sessions()
    return templates.TemplateResponse(
        request,
        "chats.html",
        {"title": "Анонка", "sessions": sessions, "admin_id": admin_id},
    )


@app.get("/chats/{session_id}", response_class=HTMLResponse)
async def chat_detail(request: Request, session_id: int, admin_id: int = Depends(require_admin)):
    db = db_from_state(request)
    messages = await db.get_chat_messages(session_id)
    sessions = await db.list_chat_sessions()
    session = next((item for item in sessions if item["id"] == session_id), None)
    if not session:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request,
        "chat_detail.html",
        {"title": f"Диалог #{session_id}", "session": session, "messages": messages, "admin_id": admin_id},
    )


@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, q: str = "", admin_id: int = Depends(require_admin)):
    db = db_from_state(request)
    users = await db.search_users(q) if q else []
    return templates.TemplateResponse(
        request,
        "users.html",
        {"title": "Пользователи", "users": users, "query": q, "admin_id": admin_id},
    )


@app.get("/users/{user_id}", response_class=HTMLResponse)
async def user_detail(request: Request, user_id: int, admin_id: int = Depends(require_admin)):
    db = db_from_state(request)
    user = await db.get_user_card(user_id)
    if not user:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request,
        "user_detail.html",
        {"title": f"User {user_id}", "user": user, "admin_id": admin_id},
    )


@app.post("/users/{user_id}/block")
async def block_user(request: Request, user_id: int, admin_id: int = Depends(require_admin)):
    db = db_from_state(request)
    await db.set_block(user_id, True)
    referer = request.headers.get("referer", "/users")
    return RedirectResponse(referer, status_code=303)


@app.post("/users/{user_id}/unblock")
async def unblock_user(request: Request, user_id: int, admin_id: int = Depends(require_admin)):
    db = db_from_state(request)
    await db.set_block(user_id, False)
    referer = request.headers.get("referer", "/users")
    return RedirectResponse(referer, status_code=303)


@app.get("/blocks", response_class=HTMLResponse)
async def blocks_page(request: Request, admin_id: int = Depends(require_admin)):
    db = db_from_state(request)
    blocks = await db.list_blocks()
    return templates.TemplateResponse(
        request,
        "blocks.html",
        {"title": "Блокировки", "blocks": blocks, "admin_id": admin_id},
    )


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.caption = None
        self.content_type = "text"


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
