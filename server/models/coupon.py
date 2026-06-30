from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from database import Base


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    coupon_id = Column(String(64), unique=True, index=True)
    title = Column(String(255))
    type = Column(String(16), default="discount")
    discount = Column(Float, default=0)
    threshold = Column(Float, default=0)
    country = Column(String(8), index=True)
    store_id = Column(String(32), default="")
    store_name = Column(String(128), default="")
    expire_date = Column(String(32))
    status = Column(String(16), default="available")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
