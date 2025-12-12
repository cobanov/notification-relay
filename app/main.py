from fastapi import FastAPI, Depends, HTTPException, Header, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from contextlib import asynccontextmanager
import json
import re
import logging

from app.database import init_db, get_db, Notification
from app.models import NotificationCreate, NotificationResponse
from app.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def clean_json_string(json_str: str) -> str:
    """
    Remove invalid control characters from JSON string.

    This handles malformed JSON from mobile devices that may contain
    unescaped control characters (common in WhatsApp and other apps).
    """
    # Remove all control characters except whitespace (\n, \r, \t, space)
    cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", json_str, flags=re.MULTILINE)
    return cleaned


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - handles startup and shutdown"""
    # Startup
    logger.info("Starting Notification Relay API...")
    try:
        await init_db()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Notification Relay API...")


app = FastAPI(
    title="Notification Relay API",
    description="FastAPI server to receive and store notifications from mobile devices",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
allowed_origins = (
    settings.allowed_origins.split(",") if settings.allowed_origins != "*" else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def verify_api_key(x_api_key: Annotated[str | None, Header()] = None) -> str:
    """Verify API key from request header"""
    if x_api_key is None:
        logger.warning("Request received without API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is required",
        )
    if x_api_key != settings.api_key:
        logger.warning("Request received with invalid API key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return x_api_key


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "status": "ok",
        "message": "Notification Relay API is running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "notifications": "/notifications",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "notification-relay"}


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
    """
    Create a new notification entry.

    Requires X-API-Key header for authentication.
    Handles malformed JSON from mobile devices automatically.
    """
    try:
        # Read and clean raw body
        body = await request.body()
        body_str = body.decode("utf-8")

        # Clean the JSON string from control characters
        cleaned_json = clean_json_string(body_str)

        # Parse the cleaned JSON
        try:
            data = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON format: {str(e)}",
            )

        # Validate with Pydantic model
        notification = NotificationCreate(**data)

        # Create notification instance
        db_notification = Notification(**notification.model_dump())

        # Save to database
        db.add(db_notification)
        await db.commit()
        await db.refresh(db_notification)

        logger.info(
            f"Created notification: id={db_notification.id}, app={db_notification.app_name}"
        )
        return db_notification

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create notification: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create notification. Please try again.",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
