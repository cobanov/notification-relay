from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class NotificationCreate(BaseModel):
    """Schema for creating a notification"""

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


class NotificationResponse(BaseModel):
    """Schema for notification response"""

    model_config = ConfigDict(from_attributes=True)

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
