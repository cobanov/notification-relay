from fastapi import FastAPI, Depends, HTTPException, Header, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from contextlib import asynccontextmanager
from pathlib import Path
import json
import re
import logging

from app.database import init_db, get_db, Notification
from app.models import NotificationCreate, NotificationResponse
from app.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

STATIC_DIR = Path(__file__).parent.parent / "static"


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


@app.get("/")
async def root():
    return {"status": "ok", "service": "notification-relay"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/dashboard")
async def dashboard():
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(404, "Dashboard not found")
    return FileResponse(index)


@app.get("/notifications", response_model=list[NotificationResponse])
async def list_notifications(
    db: AsyncSession = Depends(get_db),
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
async def get_stats(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count(Notification.id)))).scalar()

    by_app_query = (
        select(Notification.app_name, func.count(Notification.id).label("count"))
        .group_by(Notification.app_name)
        .order_by(desc("count"))
    )
    by_app = [{"app_name": r[0], "count": r[1]} for r in await db.execute(by_app_query)]

    return {"total": total, "by_app": by_app}


@app.get("/notifications/apps")
async def get_apps(db: AsyncSession = Depends(get_db)):
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
    _: str = Depends(verify_api_key),
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
