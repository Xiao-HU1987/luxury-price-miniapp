from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base


class SplashAd(Base):
    __tablename__ = "splash_ads"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), default="")
    image_url = Column(String(500), default="")
    video_url = Column(String(500), default="")
    ad_type = Column(String(32), default="image")
    duration = Column(Integer, default=5)
    skip_enabled = Column(Boolean, default=True)
    link_type = Column(String(32), default="none")
    link_url = Column(String(500), default="")
    link_page = Column(String(255), default="")
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    daily_limit = Column(Integer, default=1)
    show_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SplashAdLog(Base):
    __tablename__ = "splash_ad_logs"

    id = Column(Integer, primary_key=True, index=True)
    ad_id = Column(Integer, index=True)
    user_id = Column(String(64), index=True)
    action_type = Column(String(32), default="show")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
