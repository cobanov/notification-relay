from fastapi import FastAPI, Depends, HTTPException, Header, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from contextlib import asynccontextmanager
from pathlib import Path
import base64
import hashlib
import hmac
import json
import os
import re
import time
import logging

from app.database import init_db, get_db, Notification
from app.models import NotificationCreate, NotificationResponse
from app.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

STATIC_DIR = Path(__file__).parent / "static"


def clean_json(text: str) -> str:
    """Remove control characters from JSON string."""
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")
    await init_db()
    logger.info("Application started")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Notification Relay",
    version="1.0.0",
    lifespan=lifespan,
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(",")
    if settings.allowed_origins != "*"
    else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def verify_api_key(x_api_key: str | None = Header(None)) -> str:
    if not x_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "API key required")
    if x_api_key != settings.api_key:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid API key")
    return x_api_key


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * ((4 - (len(data) % 4)) % 4)
    return base64.urlsafe_b64decode((data + pad).encode("utf-8"))


def _sign_session_payload(payload: str) -> str:
    # HMAC secret is the API key. This keeps the solution dependency-free.
    return hmac.new(
        settings.api_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _make_session_cookie_value() -> str:
    ts = int(time.time())
    nonce = _b64url_encode(os.urandom(16))
    payload = f"v1:{ts}:{nonce}"
    sig = _sign_session_payload(payload)
    return _b64url_encode(f"{payload}.{sig}".encode("utf-8"))


def _is_session_valid(request: Request) -> bool:
    raw = request.cookies.get(settings.session_cookie_name)
    if not raw:
        return False
    try:
        decoded = _b64url_decode(raw).decode("utf-8")
        payload, sig = decoded.rsplit(".", 1)
        expected = _sign_session_payload(payload)
        if not hmac.compare_digest(sig, expected):
            return False

        parts = payload.split(":")
        if len(parts) != 3 or parts[0] != "v1":
            return False
        ts = int(parts[1])
        if int(time.time()) - ts > settings.session_max_age_seconds:
            return False
        return True
    except Exception:
        return False


async def require_auth(
    request: Request,
    x_api_key: str | None = Header(None),
) -> None:
    # Allow either:
    # - API clients: X-API-Key header
    # - Dashboard: HTTP-only session cookie
    if x_api_key is not None:
        if hmac.compare_digest(x_api_key, settings.api_key):
            return
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid API key")

    if _is_session_valid(request):
        return

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login required")


@app.get("/")
async def root():
    return {"status": "ok", "service": "notification-relay"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/dashboard")
async def dashboard(request: Request):
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(404, "Dashboard not found")
    if not _is_session_valid(request):
        login = STATIC_DIR / "login.html"
        if not login.exists():
            raise HTTPException(404, "Login page not found")
        return FileResponse(login)
    return FileResponse(index)


@app.get("/login")
async def login_page():
    login = STATIC_DIR / "login.html"
    if not login.exists():
        raise HTTPException(404, "Login page not found")
    return FileResponse(login)


@app.get("/auth/me")
async def auth_me(request: Request):
    if _is_session_valid(request):
        return {"authenticated": True}
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login required")


@app.post("/auth/login")
async def auth_login(request: Request):
    data = await request.json()
    password = (data.get("password") or "").strip()
    if not password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password required")

    if not hmac.compare_digest(password, settings.api_key):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid password")

    res = JSONResponse({"ok": True})
    res.set_cookie(
        key=settings.session_cookie_name,
        value=_make_session_cookie_value(),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_max_age_seconds,
        path="/",
    )
    return res


@app.post("/auth/logout")
async def auth_logout():
    res = JSONResponse({"ok": True})
    res.delete_cookie(key=settings.session_cookie_name, path="/")
    return res


@app.get("/notifications", response_model=list[NotificationResponse])
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_auth),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    app_name: str | None = Query(None),
):
    query = select(Notification).order_by(desc(Notification.created_at))
    if app_name:
        query = query.where(Notification.app_name == app_name)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@app.get("/notifications/stats")
async def get_stats(db: AsyncSession = Depends(get_db), _: None = Depends(require_auth)):
    total = (await db.execute(select(func.count(Notification.id)))).scalar()

    by_app_query = (
        select(Notification.app_name, func.count(Notification.id).label("count"))
        .group_by(Notification.app_name)
        .order_by(desc("count"))
    )
    by_app = [{"app_name": r[0], "count": r[1]} for r in await db.execute(by_app_query)]

    return {"total": total, "by_app": by_app}


@app.get("/notifications/apps")
async def get_apps(db: AsyncSession = Depends(get_db), _: None = Depends(require_auth)):
    query = (
        select(Notification.app_name)
        .distinct()
        .where(Notification.app_name.isnot(None))
    )
    result = await db.execute(query)
    return {"apps": sorted([r[0] for r in result])}


@app.post(
    "/notifications",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_notification(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_auth),
):
    try:
        body = await request.body()
        data = json.loads(clean_json(body.decode()))
        notification = NotificationCreate(**data)

        db_notification = Notification(**notification.model_dump())
        db.add(db_notification)
        await db.commit()
        await db.refresh(db_notification)

        logger.info(f"Created notification: {db_notification.id}")
        return db_notification

    except json.JSONDecodeError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid JSON: {e}")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create notification: {e}")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to create notification"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
