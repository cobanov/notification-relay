from fastapi import FastAPI, Depends, HTTPException, Header, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from contextlib import asynccontextmanager
import json
import re

from app.database import init_db, get_db, Notification
from app.models import NotificationCreate, NotificationResponse
from app.config import settings


def clean_json_string(json_str: str) -> str:
    """Remove invalid control characters from JSON string"""
    # Remove all control characters except whitespace (\n, \r, \t, space)
    cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", json_str, flags=re.MULTILINE)
    return cleaned


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    await init_db()
    yield


app = FastAPI(
    title="Notification Server",
    description="FastAPI server to receive and store notifications from mobile devices",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for reverse proxy and custom domain
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


async def verify_api_key(x_api_key: Annotated[str, Header()] = None):
    """Verify API key from header"""
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is required",
        )
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return x_api_key


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "status": "ok",
        "message": "Notification Server is running",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


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
    Create a new notification entry

    Requires X-API-Key header for authentication
    """
    try:
        # Read raw body and clean it
        body = await request.body()
        body_str = body.decode("utf-8")

        # Clean the JSON string from control characters
        cleaned_json = clean_json_string(body_str)

        # Parse the cleaned JSON
        try:
            data = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON: {str(e)}",
            )

        # Validate with Pydantic model
        notification = NotificationCreate(**data)

        # Create notification instance
        db_notification = Notification(**notification.model_dump())

        # Add to database
        db.add(db_notification)
        await db.commit()
        await db.refresh(db_notification)

        return db_notification

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
