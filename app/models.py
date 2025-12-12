from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class NotificationCreate(BaseModel):
    """Model for creating a notification"""

    app_name: Optional[str] = None
    app_package: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    text_big: Optional[str] = None
    text_lines: Optional[str] = None
    sub_text: Optional[str] = None
    ticker: Optional[str] = None
    timestamp: Optional[str] = None
    system_time: Optional[str] = None
    location: Optional[str] = None
    location_link: Optional[str] = None

    @field_validator("*", mode="before")
    @classmethod
    def sanitize_strings(cls, v):
        """Remove invalid control characters from strings"""
        if isinstance(v, str):
            # Remove null bytes and other problematic control characters
            # but keep valid ones like \n, \r, \t
            return v.replace("\x00", "").strip()
        return v


class NotificationResponse(BaseModel):
    """Model for notification response"""

    id: int
    app_name: Optional[str] = None
    app_package: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    text_big: Optional[str] = None
    text_lines: Optional[str] = None
    sub_text: Optional[str] = None
    ticker: Optional[str] = None
    timestamp: Optional[str] = None
    system_time: Optional[str] = None
    location: Optional[str] = None
    location_link: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
