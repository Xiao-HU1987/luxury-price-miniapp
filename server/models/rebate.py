from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean
from sqlalchemy.sql import func
from database import Base


class Rebate(Base):
    __tablename__ = "rebates"

    id = Column(Integer, primary_key=True, index=True)
    rebate_id = Column(String(64), unique=True, index=True)
    title = Column(String(255))
    brand_id = Column(String(32), default="")
    brand_name = Column(String(128), default="")
    store_id = Column(String(32), default="")
    store_name = Column(String(128), default="")
    country = Column(String(8), index=True)
    rate = Column(Float, default=0)
    is_vip_only = Column(Boolean, default=False)
    status = Column(String(16), default="available")
    start_date = Column(String(32), default="")
    end_date = Column(String(32), default="")
    description = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())