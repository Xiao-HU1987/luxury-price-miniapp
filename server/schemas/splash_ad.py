from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SplashAdCreateRequest(BaseModel):
    title: Optional[str] = ""
    image_url: Optional[str] = ""
    video_url: Optional[str] = ""
    ad_type: Optional[str] = "image"
    duration: Optional[int] = 5
    skip_enabled: Optional[bool] = True
    link_type: Optional[str] = "none"
    link_url: Optional[str] = ""
    link_page: Optional[str] = ""
    is_active: Optional[bool] = True
    sort_order: Optional[int] = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    daily_limit: Optional[int] = 1


class SplashAdUpdateRequest(BaseModel):
    title: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    ad_type: Optional[str] = None
    duration: Optional[int] = None
    skip_enabled: Optional[bool] = None
    link_type: Optional[str] = None
    link_url: Optional[str] = None
    link_page: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    daily_limit: Optional[int] = None


class SplashAdResponse(BaseModel):
    id: int
    title: str
    image_url: str
    video_url: str
    ad_type: str
    duration: int
    skip_enabled: bool
    link_type: str
    link_url: str
    link_page: str
    is_active: bool
    sort_order: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    daily_limit: int
    show_count: int
    click_count: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
