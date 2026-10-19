from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), unique=True, index=True)
    openid = Column(String(128), unique=True, index=True)
    nickname = Column(String(64), default="")
    avatar = Column(String(255), default="")
    phone = Column(String(20), default="")
    is_vip = Column(Boolean, default=False)
    vip_expire_time = Column(DateTime, nullable=True)
    is_admin = Column(Boolean, default=False)
    is_buyer = Column(Boolean, default=False)
    status = Column(String(16), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
