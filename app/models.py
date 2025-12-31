from pydantic import BaseModel, ConfigDict
from datetime import datetime


class NotificationBase(BaseModel):
    app_name: str | None = None
    app_package: str | None = None
    title: str | None = None
    text: str | None = None
    text_big: str | None = None
    text_lines: str | None = None
    sub_text: str | None = None
    ticker: str | None = None
    timestamp: str | None = None
    system_time: str | None = None
    location: str | None = None
    location_link: str | None = None


class NotificationCreate(NotificationBase):
    pass


class NotificationResponse(NotificationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
