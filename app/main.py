from fastapi import FastAPI, Depends, HTTPException, Header, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from contextlib import asynccontextmanager
import json
from json.decoder import JSONDecodeError

from app.database import init_db, get_db, Notification
from app.models import NotificationCreate, NotificationResponse
from app.config import settings


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


# Custom middleware to handle malformed JSON
@app.middleware("http")
async def sanitize_json_middleware(request: Request, call_next):
    """Clean malformed JSON from mobile requests"""
    if request.method == "POST" and "application/json" in request.headers.get(
        "content-type", ""
    ):
        try:
            body = await request.body()
            body_str = body.decode("utf-8")

            # Try to parse as-is first
            try:
                json.loads(body_str)
            except JSONDecodeError:
                # If parsing fails, sanitize the string
                # Remove control characters except \n, \r, \t
                sanitized = "".join(
                    char if char in ["\n", "\r", "\t"] or ord(char) >= 32 else " "
                    for char in body_str
                )

                # Try parsing the sanitized version
                try:
                    json.loads(sanitized)

                    # If successful, replace the body
                    async def receive():
                        return {"type": "http.request", "body": sanitized.encode()}

                    request._receive = receive
                except JSONDecodeError:
                    # Still invalid, return error
                    return JSONResponse(
                        status_code=400,
                        content={
                            "detail": "Invalid JSON format. Please check your request body."
                        },
                    )
        except Exception:
            pass  # Let FastAPI handle other errors

    response = await call_next(request)
    return response


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
    notification: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """
    Create a new notification entry

    Requires X-API-Key header for authentication
    """
    try:
        # Create notification instance
        db_notification = Notification(**notification.model_dump())

        # Add to database
        db.add(db_notification)
        await db.commit()
        await db.refresh(db_notification)

        return db_notification

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
