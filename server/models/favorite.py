from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from database import Base


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), index=True)
    target_type = Column(String(32), default="product")
    target_id = Column(String(64), index=True)
    target_name = Column(String(255), default="")
    target_image = Column(String(255), default="")
    remark = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BrowseHistory(Base):
    __tablename__ = "browse_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), index=True)
    target_type = Column(String(32), default="product")
    target_id = Column(String(64), index=True)
    target_name = Column(String(255), default="")
    target_image = Column(String(255), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
